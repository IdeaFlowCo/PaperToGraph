'''
All GPT-specific code used for parsing entities and relationships out of text.
'''

import os
import time


import openai

openai.api_key = os.getenv("OPENAI_API_KEY")


from utils import log_msg
from gpt.common import async_fetch_from_openai


SAMPLE_PARSE_INPUT = (
    "Tom Currier is a great guy who built lots of communities after he studied at Stanford and Harvard. "
    "He also won the Thiel fellowship. "
)

SAMPLE_PARSE_OUTPUT = (
    # "Tom Currier"
    # "\n- studied at: Stanford, Harvard"
    # "\n- winner of: Thiel Fellowship"
    # "\n\n"
    "{"
    "\n  \"Tom Currier\": {"
    "\n    \"studied at\": \"Stanford, Harvard\","
    "\n    \"winner of\": \"Thiel Fellowship\""
    "\n  }"
    "\n}"
)

PARSE_SYSTEM_MESSAGE_CONTENT = (
    "Extract the named entities and relations between them in subsequent queries as per the following format. "
    "Specifically list the named entities as JSON objects, with properties for each of their relationships. "
    "Ignore any named entities that do not have specified relationships to other entities. "
    "Don't forget newlines between entries and make sure that response is valid JSON."
    # "Make sure to merge the information about extracted entities with any previously extracted information. "
    "\n\n"
    "Input: \n" + SAMPLE_PARSE_INPUT + "\n\n"
    "Output: \n" + SAMPLE_PARSE_OUTPUT + "\n\n"
    # "Also, do a second degree of entity extraction on all the entities named as targets, connecting, for instance"
    # "\n\"constitutive Wnt signalling\""
    # "\n- Wnt"
    # "\n"
    # "\n\"part of the β-catenin degradation complex\""
    # "\n- β-catenin"
)
PARSE_SYSTEM_MESSAGE = {"role": "system", "content": PARSE_SYSTEM_MESSAGE_CONTENT}



async def async_fetch_parse(text:str, model="gpt-3.5-turbo", max_tokens=1500, skip_on_error=False, should_retry=True):
    '''
    Retrieve parse response from GPT for given block of text.
    '''
    messages = [
        PARSE_SYSTEM_MESSAGE
    ]

    messages.append(
        {"role": "user", "content": text}
    )

    return await async_fetch_from_openai(
        messages,
        log_label='Parse',
        model=model,
        max_tokens=max_tokens,
        skip_on_error=skip_on_error, 
        should_retry=should_retry
    )





# ***********
# Legacy code
# ***********

def fetch_parse_sequentially(text:str, prev_context=None, model="gpt-3.5-turbo"):
    '''
    Legacy code for parsing a text block sequentially through GPT.

    Offers prev_context argument which can be used to load a previous response into the completion context sent to GPT.
    It was thought this might be useful for having GPT merge responses with each other, but it turned out to be easier
    to split text into chunks and fetch a parse for all of them at once, merging later.
    '''
    messages = [
        PARSE_SYSTEM_MESSAGE
    ]

    if prev_context:
        messages.append(
            {"role": "assistant", "content": prev_context}
        )

    messages.append(
        {"role": "user", "content": text}
    )

    try:
        log_msg('Requesting parse from OpenAI...')
        result = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=2000,
            # temperature=1.2
        )
    except openai.error.RateLimitError:
        log_msg('Rate limit error from OpenAI')
        # Wait a quarter second and try again
        time.sleep(0.25)
        return fetch_parse_sequentially(text, prev_context=prev_context, model=model)
    except BaseException as err:
        log_msg(f'Error encountered during OpenAI API call: {err}')
        raise err

    result = result["choices"][0]["message"]["content"].strip()
    log_msg('Received parse response from OpenAI')
    log_msg(result)
    return result
