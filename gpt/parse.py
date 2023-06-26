'''
All GPT-specific code used for parsing entities and relationships out of text.
'''

import os
import time


import openai

openai.api_key = os.getenv("OPENAI_API_KEY")


from utils import log_msg
from gpt.common import async_fetch_from_openai


PARSE_SM_TEMPLATE = (
    "Each user message will be input text to process. "
    "Extract the named entities and their relationships from the text provided. "
    "The output should be formatted as a JSON object. Each key in the output object should be the name of an extracted entity. "
    "Each value should be an object with a key for each relationship and values representing the target of the relationship. "
    "Be sure to separate all comma separated entities that may occur in results into separate items in a list. "
    "\n\n"
    "For example, if provided the following input:"
    "\n```\n"
    "{sample_input}"
    "\n```\n"
    "An acceptable output would be:"
    "\n```\n"
    "{sample_output}"
    "\n```\n"
    "\n"
    "If no entities or relationships can be extracted from the text provided, respond with {none_found}. "
    "Responses should consist only of the extracted data in JSON format, or the string {none_found}."
)

SAMPLE_PARSE_INPUT = (
    "Tom Currier is a great guy who built lots of communities after he studied at Stanford and Harvard. "
    "He also won the Thiel fellowship. "
)
SAMPLE_PARSE_OUTPUT = (
    "{"
    "\n  \"Tom Currier\": {"
    "\n    \"studied at\": [\"Stanford\", \"Harvard\"],"
    "\n    \"winner of\": \"Thiel Fellowship\""
    "\n  }"
    "\n}"
)
NO_ENTITIES_MARKER = 'NO_ENTITIES_FOUND'


PARSE_SYSTEM_MESSAGE = {
    "role": "system", 
    "content": PARSE_SM_TEMPLATE.format(
        sample_input=SAMPLE_PARSE_INPUT, sample_output=SAMPLE_PARSE_OUTPUT, none_found=NO_ENTITIES_MARKER)
    }


def get_output_reservation(model):
    '''
    Return the maximum number of tokens to reserve for the response from a given model.
    '''
    # Note: response size should not scale linearly with max context size because the whole point is that we're
    # extracting/refining data with this query.
    # That said, there's a somewhat high "floor" here because JSON ouptput consumes a lot of tokens for
    # structural characters like {} and ""
    if model == 'gpt-3.5-turbo-16k':
        # Max context size: 16,384 tokens
        return 3000
    elif model == 'gpt-4':
        # Max context size: 8,192 tokens
        return 2000
    else:
        # Asssuming GPT-3.5-turbo
        # Max context size: 4,096 tokens
        return 1600


def get_timeout_limit(model):
    if model == 'gpt-3.5-turbo-16k':
        return 75
    elif model == 'gpt-4':
        return 75
    else:
        return 60


async def async_fetch_parse(text:str, model="gpt-3.5-turbo", skip_on_error=False, prompt_override=None):
    '''
    Retrieve parse response from GPT for given block of text.
    '''
    max_tokens = get_output_reservation(model)
    timeout = get_timeout_limit(model)

    if prompt_override:
        system_message = {
            "role": "system", 
            "content": prompt_override
        }
    else:
        system_message = PARSE_SYSTEM_MESSAGE

    messages = [
        system_message,
        {"role": "user", "content": text}
    ]

    return await async_fetch_from_openai(
        messages,
        log_label='Parse',
        model=model,
        max_tokens=max_tokens,
        timeout=timeout,
        skip_on_error=skip_on_error,
        skip_msg=NO_ENTITIES_MARKER
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
