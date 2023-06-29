'''
Shared code for interacting with OpenAI APIs.
'''

import asyncio
import json
import math
import os
import random

import openai

openai.api_key = os.getenv("OPENAI_API_KEY")


from utils import log_msg, log_debug


def clean_json(response):
    cleaned = {}
    try:
        if response.startswith('Output:'):
            # Remove extraneous "Output:" signifier that shows up sometimes.
            response = response[len('Output:'):].strip()
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
        return cleaned
    except json.decoder.JSONDecodeError:
        log_msg('Response not valid JSON!')
        if '{' in response:
            # Response isn't valid JSON but may be close enough that it can still be used, so we'll just return it as-is
            return response
        return None
    except Exception as err:
        log_msg(f'Error while attempting to clean response JSON: {err}')
        log_msg(f'Response was valid JSON, though, so returning it unchanged.')
        return response


def get_context_window_size(model):
    # Can see max context size for different models here: https://platform.openai.com/docs/models/overview
    if model == 'gpt-3.5-turbo-16k':
        max_context_tokens = 16384
    elif model == 'gpt-4':
        max_context_tokens = 8192
    else:
        # Assume gpt-3.5-turbo
        max_context_tokens = 4096

    return max_context_tokens


def get_max_requests_per_minute(model):
    # All rate limits can be found at https://platform.openai.com/docs/guides/rate-limits/what-are-the-rate-limits-for-our-api
    if model == 'gpt-4':
        # GPT-4 has extra aggressive rate limiting in place.
        # https://platform.openai.com/docs/guides/rate-limits/gpt-4-rate-limits
        # 200 RPM
        requests_per_minute_limit = 200.0
        # 40k TPM
        tokens_per_minute_limit = 40000.0
    elif model == 'gpt-3.5-turbo-16k':
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
    requests_per_minute_by_tpm = math.floor(tokens_per_minute_limit / tokens_per_request)

    # Use whichever limit is stricter
    return min(requests_per_minute_limit, requests_per_minute_by_tpm)


def get_rl_backoff_time(model):
    '''
    Returns the number of seconds to wait before retrying a request for a given model.
    '''
    rpm_limit = get_max_requests_per_minute(model)

    # Round up to be extra conservative
    seconds_per_request = math.ceil(60.0 / rpm_limit)

    # Use a jitter factor so delays don't all hit at once
    jitter_factor = 1 + random.random()
    delay = seconds_per_request * jitter_factor

    return delay


async def async_fetch_from_openai(
        messages,
        log_label,
        model="gpt-3.5-turbo",
        skip_msg=None,
        max_tokens=1500,
        timeout=60,
        skip_on_error=False,
        should_retry=True,
        rate_limit_errors=0):
    '''
    Common scaffolding code for fetching from OpenAI, with shared logic for different kinds of error handling.
    '''

    try:
        log_msg(f'Sending {log_label.lower()} request to OpenAI...')
        async with asyncio.timeout(timeout):
            result = await openai.ChatCompletion.acreate(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.5
            )
    except openai.error.RateLimitError as err:
        if 'exceeded your current quota' in err.__str__():
            log_msg('Quota exceeded error from OpenAI')
            log_msg('Abandoning this request and letting error bubble up since it will not resolve itself.')
            raise err

        log_msg('Rate limit error from OpenAI')
        if rate_limit_errors > 4:
            log_msg('Too many rate limit errors; abandoning this request and letting error bubble up.')
            raise err

        backoff_time = get_rl_backoff_time(model)
        # Every time we get a rate limit error, we double the backoff time.
        backoff_time = backoff_time * (2 ** rate_limit_errors)
        await asyncio.sleep(backoff_time)

        return await async_fetch_from_openai(
            messages,
            log_label,
            model=model,
            max_tokens=max_tokens,
            skip_on_error=skip_on_error,
            should_retry=should_retry,
            rate_limit_errors=rate_limit_errors + 1
        )
    except openai.error.InvalidRequestError as err:
        log_msg(f'Invalid request error from OpenAI: {err}')
        # This is probably an issue with context size, which we're not handling yet, so we'll just skip this chunk because
        # retrying won't help.
        # In the future we'll let this bubble up so calling code can split the request into smaller chunks and try again.
        log_msg('Skipping this chunk.')
        return ''
    except TimeoutError:
        if should_retry:
            log_msg(f'{log_label} request timeout. Trying again one more time...')
            return await async_fetch_from_openai(
                messages,
                log_label,
                model=model,
                max_tokens=max_tokens,
                skip_on_error=skip_on_error,
                should_retry=False
            )
        log_msg(f'{log_label} request timed out multiple times.')
        if skip_on_error:
            return ''
        raise TimeoutError
    except BaseException as err:
        log_msg(f'Error encountered during OpenAI API call: {err}')
        if should_retry:
            log_msg(f'Trying again one more time...')
            return await async_fetch_from_openai(
                messages,
                log_label,
                model=model,
                max_tokens=max_tokens,
                skip_on_error=skip_on_error,
                should_retry=False
            )
        if skip_on_error:
            return ''
        raise err

    result = result["choices"][0]
    if result['finish_reason'] != 'stop':
        # "stop" is the standard finish reason; if we get something else, we might want to investigate.
        # See: https://platform.openai.com/docs/guides/gpt/chat-completions-response-format
        log_msg(f'OpenAI finish reason: "{result["finish_reason"]}".')

    result = result["message"]["content"].strip()
    log_msg(f'Received {log_label.lower()} response from OpenAI')
    log_debug(f'Response data: \n{result}')
    if result == skip_msg:
        log_msg(f'OpenAI returned designated skip message "{skip_msg}". Returning empty string for this block.')
        return ''
    result = clean_json(result)
    log_debug(f'Cleaned response data: \n{result}')
    if result is None:
        if should_retry:
            log_msg("Doesn't look like GPT gave us JSON. Trying again one more time...")
            return await async_fetch_from_openai(
                messages,
                log_label,
                model=model,
                max_tokens=max_tokens,
                skip_on_error=skip_on_error,
                should_retry=False
            )
        if skip_on_error:
            log_msg(
                "Doesn't look like GPT gave us JSON. "
                "No reties left and skip_on_error=true, so returning blank to contain damages."
            )
            return ''
    return result
