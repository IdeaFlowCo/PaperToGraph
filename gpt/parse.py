'''
All GPT-specific code used for parsing entities and relationships out of text.
'''

import os
import time

import openai

openai.api_key = os.getenv('OPENAI_API_KEY')

from utils import log_msg

from .common import async_fetch_from_openai, get_context_window_size
from .text import get_token_length


PARSE_SM_TEMPLATE = (
    "In the user message, there will be text to process. I'd like you to do the following steps:"
    '\n'
    '\n1. Find named entities in the text. The entities could be Drugs, Diseases, or Other entities.'
    '\n2. Identify relationships between these entities.'
    "\n3. Format your findings as a JSON object where each key is an entity and each value is another object that describes the entity's "
    "relationships and entity type. If an entity has more than one relationship, make sure to list each one separately. Also, if a single "
    "relationship points to multiple entities, list those entities in an array."
    '\n4. For every entity, add a special field called "_ENTITY_TYPE" that classifies the entity as either a Drug, Disease, or Other.'
    '\n5. If an entity name includes an abbreviation, treat the abbreviation as a separate entity. The abbreviation should have a '
    'relationship "abbreviation of" pointing to the full name, and the full-named entity should have a relationship "abbreviation" pointing '
    'to the abbreviation.'
    '\n\n'
    'For example, if the text is: "{sample_input}", an output could look like this:'
    '\n```\n'
    '{sample_output}'
    '\n```\n'
    '\n'
    "If you can't find any entities or relationships in the text, please respond with the phrase \"{none_found}\". "
    'Your response should only contain the JSON data of extracted entities and relationships, or the phrase "{none_found}".')

SAMPLE_PARSE_INPUT = (
    "Tom Currier is a great guy who built lots of communities after he studied at Stanford University (SU) and Harvard. "
    "He also won the Thiel Fellowship.")
SAMPLE_PARSE_OUTPUT = (
    '{'
    '\n"Tom Currier": {'
    '\n  "studied at": ["Stanford University", "Harvard"],'
    '\n  "winner of": "Thiel Fellowship"'
    '\n  "_ENTITY_TYPE": "Other"'
    '\n},'
    '\n"Stanford University": {'
    '\n  "students": ["Tom Currier"],'
    '\n  "abbreviation": "SU"'
    '\n  "_ENTITY_TYPE": "Other"'
    '\n},'
    '\n"SU": {'
    '\n  "abbreviation of": ["Stanford University"],'
    '\n  "_ENTITY_TYPE": "Other"'
    '\n},'
    '\n}'
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
    if model == 'gpt-4-32k':
        # Max context size: 32,000 tokens
        return 4000
    elif model == 'gpt-3.5-turbo-16k':
        # Max context size: 16,384 tokens
        return 3000
    elif model == 'gpt-4':
        # Max context size: 8,192 tokens
        return 2000
    else:
        # Asssuming GPT-3.5-turbo
        # Max context size: 4,096 tokens
        return 1600


def get_text_token_limit(model):
    '''
    Returns desired length of text to be parsed, in number of tokens, based on model to be used.
    '''
    # Different models have different max context sizes, where "context size" is the total number of tokens
    # used in the completion request, inclduding all of: the prompt in the system message, the text to be parsed,
    # and the reesrvation for the output.
    # Can check token length using https://platform.openai.com/tokenizer

    # The number of tokens in the system message prompt.
    parse_prompt_tokens = get_token_length(PARSE_SYSTEM_MESSAGE['content'], model=model)

    # The maximum number of tokens in this model's context window.
    max_context_tokens = get_context_window_size(model)

    # The number of tokens to reserve for the output.
    output_reservation = get_output_reservation(model)

    # Leave ourselves a margin of error to account for structural overhead + just to be safe.
    margin_of_error = 200

    tokens_for_input = max_context_tokens - parse_prompt_tokens - output_reservation - margin_of_error

    return tokens_for_input


def get_text_size_limit(model):
    '''
    Returns desired length of text to be parsed, in number of characters, based on model to be used.
    '''
    tokens_for_input = get_text_token_limit(model)

    # Each token is about 3-4 characters for freeform text (e.g. the text to be parsed, which is what we're sizing here).
    chars_per_token = 3.5

    return int(tokens_for_input * chars_per_token)


def get_timeout_limit(model):
    if model == 'gpt-3.5-turbo-16k':
        return 75
    elif model == 'gpt-4':
        return 90
    elif model == 'gpt-4-32k':
        return 120
    else:
        return 60


def get_default_parse_prompt():
    '''
    Returns default prompt for parse query.
    '''
    return PARSE_SYSTEM_MESSAGE['content']


async def async_fetch_parse(text: str, model="gpt-3.5-turbo", skip_on_error=False, prompt_override=None, return_source=False):
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

    start_time = time.time()
    parse_result = await async_fetch_from_openai(
        messages,
        log_label='Parse',
        model=model,
        max_tokens=max_tokens,
        timeout=timeout,
        skip_on_error=skip_on_error,
        skip_msg=NO_ENTITIES_MARKER,
        expect_json_result=True
    )
    end_time = time.time()
    time_spent = end_time - start_time
    log_msg(f'Parse results fetched in {time_spent:.2f} seconds.')

    if return_source:
        return text, parse_result
    else:
        return parse_result


# ***********
# Legacy code
# ***********

def fetch_parse_sequentially(text: str, prev_context=None, model="gpt-3.5-turbo"):
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
