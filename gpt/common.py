"""
Shared code for interacting with OpenAI APIs.
"""

import asyncio
import json
import math
import random

import openai
import tiktoken

import google.generativeai as genai

import utils
from utils import log_msg, log_debug


VALID_GPT_MODELS = [
    # Google Gemini models (default provider)
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    # OpenAI models (currently non-functional: org deactivated, but kept selectable)
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
    "gpt-4",
    "gpt-4-32k",
    "gpt-4o",
    "gpt-4o-mini",
]
DEFAULT_GPT_MODEL = "gemini-2.5-flash"


def init_module(config):
    openai.api_key = config.get("OPENAI_API_KEY", None)
    log_msg(f"Using OpenAI API key: {utils.secret_to_log_str(openai.api_key)}")

    gemini_api_key = config.get("GEMINI_API_KEY", None)
    genai.configure(api_key=gemini_api_key)
    log_msg(f"Using Gemini API key: {utils.secret_to_log_str(gemini_api_key)}")


def sanitize_gpt_model_choice(model):
    if model not in VALID_GPT_MODELS:
        model = "gemini-2.5-flash"
    return model


def clean_json(response):
    cleaned = {}
    try:
        if response.startswith("Output:"):
            # Remove extraneous "Output:" signifier that shows up sometimes.
            response = response[len("Output:") :].strip()
        response_dict = json.loads(response)
        for key, value in response_dict.items():
            # We want to skip the empty values to avoid overloading GPT in subsequent queries.
            if not value:
                continue
            if isinstance(value, dict):
                cleaned_value = {}
                # Sometimes a dict will have a bunch of key => empty dict pairs inside of it for some reason?
                # Trim those too.
                for subkey, subvalue in value.items():
                    if subvalue:
                        cleaned_value[subkey] = subvalue
                # Check that the cleaned up value dict actually has anything in it; if not, skip
                if not cleaned_value:
                    continue
                value = cleaned_value
            elif isinstance(value, list):
                # Do nothing to clean list values for now
                pass
            elif isinstance(value, str):
                # Sometimes we get really long string pairs that are more trouble than they are informative
                if len(key) + len(value) > 200:
                    continue
            else:
                # We don't know how to handle other kinds of values, so skip them
                log_debug(f'Unexpected value type for key "{key}": {type(value)}')
                continue
            cleaned[key] = value
        cleaned = json.dumps(cleaned, indent=2)
        # log_msg(f'Cleaned up response JSON: \n{cleaned}')
        return cleaned, True
    except json.decoder.JSONDecodeError:
        log_msg("Response not valid JSON!")
        if "{" in response:
            # Response isn't valid JSON but may be close enough that it can still be used, so we'll just return it as-is
            return response, False
        return None, False
    except Exception as err:
        log_msg(f"Error while attempting to clean response JSON: {err}")
        log_msg(f"Response was valid JSON, though, so returning it unchanged.")
        return response, True


def get_token_length(text, model="gpt-3.5-turbo"):
    if model.startswith("gemini"):
        # tiktoken doesn't know about Gemini models (encoding_for_model raises
        # KeyError). Use a cheap heuristic (~4 chars/token) rather than a network
        # call for token counting.
        return max(1, len(text) // 4)
    encoding = tiktoken.encoding_for_model(model)
    text_as_tokens = encoding.encode(text)
    return len(text_as_tokens)


def split_input_list_to_chunks(input_list, max_chunk_tokens, model="gpt-3.5-turbo"):
    input_chunks = []
    cur_chunk = []
    cur_chunk_token_count = 0
    for input in input_list:
        # Add 1 to account for the newline that will be added between each input
        input_token_count = get_token_length(input, model=model) + 1
        if (
            cur_chunk_token_count + input_token_count > max_chunk_tokens
            or len(cur_chunk) > 300
        ):
            input_chunks.append(cur_chunk)
            cur_chunk = []
            cur_chunk_token_count = 0
        cur_chunk.append(input)
        cur_chunk_token_count += input_token_count
    if cur_chunk:
        input_chunks.append(cur_chunk)
    return input_chunks


def get_context_window_size(model):
    # Can see max context size for different models here: https://platform.openai.com/docs/models/overview
    if model.startswith("gemini"):
        # Gemini 2.x flash models support a 1M-token context window.
        max_context_tokens = 1048576
    elif model == "gpt-4o" or model == "gpt-4o-mini":
        max_context_tokens = 128000
    elif model == "gpt-4-32k":
        max_context_tokens = 32768
    elif model == "gpt-3.5-turbo-16k":
        max_context_tokens = 16384
    elif model == "gpt-4":
        max_context_tokens = 8192
    else:
        # Assume gpt-3.5-turbo
        max_context_tokens = 4096

    return max_context_tokens


def get_max_requests_per_minute(model):
    # All rate limits can be found at https://platform.openai.com/docs/guides/rate-limits/what-are-the-rate-limits-for-our-api
    if model.startswith("gemini"):
        # Conservative request cap for Gemini models.
        return 300.0

    if model == "gpt-4o":
        # 500 RPM
        requests_per_minute_limit = 500.0
        # 300k TPM
        tokens_per_minute_limit = 300000.0
    elif model == "gpt-4o-mini":
        # 750 RPM
        requests_per_minute_limit = 750.0
        # 400k TPM
        tokens_per_minute_limit = 400000.0
    elif model == "gpt-4-32k":
        # 200 RPM
        requests_per_minute_limit = 200.0
        # 80k TPM
        tokens_per_minute_limit = 80000.0
    elif model == "gpt-4":
        # GPT-4 has extra aggressive rate limiting in place.
        # 200 RPM
        requests_per_minute_limit = 200.0
        # 40k TPM
        tokens_per_minute_limit = 40000.0
    elif model == "gpt-3.5-turbo-16k":
        # 60 RPM
        requests_per_minute_limit = 60.0
        # 120k TPM
        tokens_per_minute_limit = 120000.0
    else:
        # Assume gpt-3.5-turbo
        # 60 RPM
        requests_per_minute_limit = 60.0
        # 60k TPM
        tokens_per_minute_limit = 60000.0

    # Assume we're using full context window tokens in every request
    tokens_per_request = get_context_window_size(model)
    # Round down to be extra conservative
    requests_per_minute_by_tpm = math.floor(
        tokens_per_minute_limit / tokens_per_request
    )

    # Use whichever limit is stricter
    return min(requests_per_minute_limit, requests_per_minute_by_tpm)


def get_rl_backoff_time(model):
    """
    Returns the number of seconds to wait before retrying a request for a given model.
    """
    rpm_limit = get_max_requests_per_minute(model)

    # Round up to be extra conservative
    seconds_per_request = math.ceil(60.0 / rpm_limit)

    # Use a jitter factor so delays don't all hit at once
    jitter_factor = 1 + random.random()
    delay = seconds_per_request * jitter_factor

    return delay


def _postprocess_result(result, params):
    """
    Shared post-processing for both the OpenAI and Gemini branches.

    `result` is the plain-string model output. This handles the skip-message
    short-circuit and the optional `expect_json_result` -> `clean_json` flow,
    including the "retry / skip_on_error" semantics when the output isn't JSON.

    Returns either a final value (str) or the sentinel object RETRY to signal
    that the caller should re-issue the request with decremented retries.
    """
    skip_msg = params["skip_msg"]
    expect_json_result = params["expect_json_result"]
    retries_remaining = params["retries_remaining"]
    skip_on_error = params["skip_on_error"]

    if result == skip_msg:
        log_msg(
            f'Model returned designated skip message "{skip_msg}". Returning empty string for this block.'
        )
        return ""

    if not expect_json_result:
        return result

    result, is_valid = clean_json(result)
    log_debug(f"Cleaned response data: \n{result}")
    if not is_valid:
        if retries_remaining > 0:
            return _RETRY
        if skip_on_error:
            log_msg(
                "Doesn't look like the model gave us JSON. "
                "No retries left and skip_on_error=true, so returning blank to contain damages."
            )
            return ""
    return result


# Sentinel used by _postprocess_result to request a retry from the caller.
_RETRY = object()


async def _async_fetch_from_gemini(params):
    """
    Fetch a response from Google Gemini, mapping the OpenAI-style `messages`
    interface onto Gemini's system_instruction + contents model.
    """
    messages = params["messages"]
    log_label = params["log_label"]
    model = params["model"]
    max_tokens = params["max_tokens"]
    timeout = params["timeout"]
    skip_on_error = params["skip_on_error"]
    retries_remaining = params["retries_remaining"]
    expect_json_result = params["expect_json_result"]
    response_format = params["response_format"]

    # Split OpenAI-style messages into a joined system instruction and a joined
    # user/assistant prompt. Keep it simple and correct rather than clever.
    system_parts = []
    content_parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content is None:
            content = ""
        if role == "system":
            system_parts.append(content)
        else:
            content_parts.append(content)
    system_instruction = "\n\n".join(p for p in system_parts if p) or None
    prompt = "\n\n".join(content_parts)

    generation_config = {"temperature": 0.4}
    if max_tokens:
        generation_config["max_output_tokens"] = max_tokens
    # Honor JSON requests from either the OpenAI-style response_format or the
    # expect_json_result flag.
    wants_json = expect_json_result or bool(response_format)
    if wants_json:
        generation_config["response_mime_type"] = "application/json"

    try:
        log_msg(f"[{log_label}] Sending request to Gemini...")
        model_obj = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_instruction,
        )
        response = await asyncio.wait_for(
            model_obj.generate_content_async(
                prompt,
                generation_config=generation_config,
            ),
            timeout=timeout,
        )
    except TimeoutError as err:
        if retries_remaining > 0:
            log_msg(f"Gemini request timeout. Trying again...")
            params["retries_remaining"] = retries_remaining - 1
            return await async_fetch_from_openai(**params)
        log_msg(f"Gemini request timeout. Out of retries, abandoning request.")
        if skip_on_error:
            return ""
        raise err
    except BaseException as err:
        log_msg(f"Error encountered during Gemini API call: {err}")
        if retries_remaining:
            log_msg(f"Trying again...")
            params["retries_remaining"] = retries_remaining - 1
            return await async_fetch_from_openai(**params)
        if skip_on_error:
            return ""
        raise err

    result = response.text.strip()
    log_msg(f"Received response from Gemini")
    log_debug(f"Response data: \n{result}")

    outcome = _postprocess_result(result, params)
    if outcome is _RETRY:
        log_msg("Doesn't look like Gemini gave us JSON. Trying again...")
        params["retries_remaining"] = retries_remaining - 1
        return await async_fetch_from_openai(**params)
    return outcome


async def async_fetch_from_openai(
    messages,
    log_label="GPT",
    model="gpt-3.5-turbo",
    max_tokens=None,
    timeout=60,
    skip_on_error=False,
    skip_msg=None,
    expect_json_result=False,
    response_format=None,
    retries_remaining=2,
):
    """
    Fetch a response from the configured LLM provider with error handling and
    retries. Routes to Gemini for "gemini*" models and to OpenAI otherwise.
    """
    # Wrap all parameters into a dictionary so we can pass them around easily
    params = {
        "messages": messages,
        "log_label": log_label,
        "model": model,
        "skip_msg": skip_msg,
        "max_tokens": max_tokens,
        "timeout": timeout,
        "skip_on_error": skip_on_error,
        "retries_remaining": retries_remaining,
        "expect_json_result": expect_json_result,
        "response_format": response_format,
    }

    # Route Gemini models to the Gemini implementation.
    if model.startswith("gemini"):
        return await _async_fetch_from_gemini(params)

    rate_limit_errors = 0

    try:
        log_msg(f"[{log_label}] Sending request to OpenAI...")
        completion_args = {
            "model": model,
            "messages": messages,
            "temperature": 0.4,
        }
        if max_tokens:
            completion_args["max_tokens"] = max_tokens
        if response_format:
            completion_args["response_format"] = response_format

        result = await asyncio.wait_for(
            openai.ChatCompletion.acreate(**completion_args),
            timeout=timeout,
        )
    except openai.error.RateLimitError as err:
        if "exceeded your current quota" in err.__str__():
            log_msg("Quota exceeded error from OpenAI")
            log_msg(
                "Abandoning this request and letting error bubble up since it will not resolve itself."
            )
            raise err

        log_msg("Rate limit error from OpenAI")
        if rate_limit_errors > 4:
            # We've already retried this request 5 times, so we'll just give up.
            # It's likely that there's some issue on OpenAI's end that will resolve itself soon.
            log_msg(
                "Too many rate limit errors; abandoning this request and letting error bubble up."
            )
            raise err

        backoff_time = get_rl_backoff_time(model)
        # Every time we get a rate limit error, we double the backoff time.
        backoff_time = backoff_time * (2**rate_limit_errors)
        await asyncio.sleep(backoff_time)

        # We track rate limit errors separately from other retries because they should always be fixable by waiting.
        params["rate_limit_errors"] = rate_limit_errors + 1
        return await async_fetch_from_openai(**params)
    except openai.error.InvalidRequestError as err:
        log_msg(f"Invalid request error from OpenAI: {err}")
        # This is probably an issue with context size, which we're not handling yet, so we'll just skip this chunk because
        # retrying won't help.
        # In the future we'll let this bubble up so calling code can split the request into smaller chunks and try again.
        log_msg("Skipping this chunk.")
        return ""
    except TimeoutError as err:
        if retries_remaining > 0:
            log_msg(f"OpenAI request timeout. Trying again...")
            params["retries_remaining"] = retries_remaining - 1
            return await async_fetch_from_openai(**params)
        log_msg(f"OpenAI request timeout. Out of retries, abandoning request.")
        if skip_on_error:
            return ""
        raise err
    except BaseException as err:
        log_msg(f"Error encountered during OpenAI API call: {err}")
        if retries_remaining:
            log_msg(f"Trying again...")
            params["retries_remaining"] = retries_remaining - 1
            return await async_fetch_from_openai(**params)
        if skip_on_error:
            return ""
        raise err

    result = result["choices"][0]
    if result["finish_reason"] != "stop":
        # "stop" is the standard finish reason; if we get something else, we might want to investigate.
        # See: https://platform.openai.com/docs/guides/gpt/chat-completions-response-format
        log_msg(f'OpenAI finish reason: "{result["finish_reason"]}".')

    result = result["message"]["content"].strip()
    log_msg(f"Received response from OpenAI")
    log_debug(f"Response data: \n{result}")
    if result == skip_msg:
        log_msg(
            f'OpenAI returned designated skip message "{skip_msg}". Returning empty string for this block.'
        )
        return ""

    if not expect_json_result:
        return result

    result, is_valid = clean_json(result)
    log_debug(f"Cleaned response data: \n{result}")
    if not is_valid:
        if retries_remaining > 0:
            log_msg("Doesn't look like GPT gave us JSON. Trying again...")
            params["retries_remaining"] = retries_remaining - 1
            return await async_fetch_from_openai(**params)
        if skip_on_error:
            log_msg(
                "Doesn't look like GPT gave us JSON. "
                "No reties left and skip_on_error=true, so returning blank to contain damages."
            )
            return ""
    return result
