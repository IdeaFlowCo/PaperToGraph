'''
Shared code for interacting with OpenAI APIs.
'''

import asyncio
import json
import os

import openai

openai.api_key = os.getenv("OPENAI_API_KEY")


from utils import log_msg


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
            else:
                # Sometimes we get really long string pairs that are more trouble than they are informative
                if len(key) + len(value) > 200:
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
    except openai.error.RateLimitError:
        log_msg('Rate limit error from OpenAI')
        # Wait half a second and try again
        # This is common enough and the exception triggers fast enough that it
        # shouldn't "use up" a retry in our logic.
        await asyncio.sleep(0.5)
        return await async_fetch_from_openai(
            messages,
            log_label,
            model=model,
            max_tokens=max_tokens,
            skip_on_error=skip_on_error, 
            should_retry=should_retry
        )
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
    # log_msg(result)
    if result == skip_msg:
        log_msg(f'OpenAI returned designated skip message "{skip_msg}". Returning empty string for this block.')
        return ''
    result = clean_json(result)
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

