'''
Shared code for interacting with OpenAI APIs.
'''

import asyncio
import os

import openai

openai.api_key = os.getenv("OPENAI_API_KEY")


from utils import log_msg, clean_json


async def async_fetch_from_openai(messages, log_label, model="gpt-3.5-turbo", max_tokens=1500, skip_on_error=False, should_retry=True):
    '''
    Common scaffolding code for fetching from OpenAI, with shared logic for different kinds of error handling.
    '''

    try:
        log_msg(f'Sending {log_label.lower()} request to OpenAI...')
        async with asyncio.timeout(60):
            result = await openai.ChatCompletion.acreate(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.5
            )
    except openai.error.RateLimitError:
        log_msg('Rate limit error from OpenAI')
        # Wait a quarter second and try again
        # This is common enough and the exception triggers fast enough that it
        # doesn't "use up" a retry in our logic.
        await asyncio.sleep(0.25)
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
    log_msg(result)
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

