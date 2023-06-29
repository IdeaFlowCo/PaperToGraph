'''
Shared code for interacting with OpenAI APIs.
'''

import asyncio
import json
import os

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


async def async_fetch_from_openai(
        messages, 
        log_label, 
        model="gpt-3.5-turbo", 
        skip_msg=None,
        max_tokens=1500,
        timeout=60,
        skip_on_error=False,
        should_retry=True):
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
        # Worst case rate limit is 60 requests-per-minute, 60,000 tokens-per-minute, per rate limit docs.
        # https://platform.openai.com/docs/guides/rate-limits/overview
        # Max tokens per request is ~8000, meaning we can send ~7.5 requests/minute, so we'll wait 8 seconds and try again.
        await asyncio.sleep(8)
        # This is common enough and the exception triggers fast enough that it shouldn't "use up" a retry in our logic.
        return await async_fetch_from_openai(
            messages,
            log_label,
            model=model,
            max_tokens=max_tokens,
            skip_on_error=skip_on_error, 
            should_retry=should_retry
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

    result = result["choices"][0]["message"]["content"].strip()
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

