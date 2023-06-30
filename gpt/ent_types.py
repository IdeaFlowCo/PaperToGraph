'''
Code for tagging entity types with OpenAI.
'''

import os
import time

import openai

openai.api_key = os.getenv('OPENAI_API_KEY')

from utils import log_msg

from .common import async_fetch_from_openai, get_context_window_size
from .text import get_token_length


ENT_TYPES_SM_TEMPLATE = (
    "In the user message, there will be a list of entity names. Perform the following steps:"
    '\n'
    '\n1. For each entity, determine if it is a Drugs, Diseases, or Other.'
    '\n2. List each entity along with its type in an (entity, type) tuple.'
    '\n\n'
    'For example, if the provided input is: "{sample_input}", an output could look like this:'
    '\n```\n'
    '{sample_output}'
    '\n```\n')
SAMPLE_ENT_TYPES_INPUT = (
    "Wilm's Tumor"
)
SAMPLE_ENT_TYPES_OUTPUT = (
    '("Wilm\'s Tumor", "Disease")'
)

ENT_TYPES_SYSTEM_MESSAGE = {
    "role": "system",
    "content": ENT_TYPES_SM_TEMPLATE.format(sample_input=SAMPLE_ENT_TYPES_INPUT, sample_output=SAMPLE_ENT_TYPES_OUTPUT)
}


def get_output_reservation(model):
    '''
    Return the maximum number of tokens to reserve for the response from a given model.
    '''
    # Because output should be all of inputs + extra data, want at least half of context window to be output.
    if model == 'gpt-3.5-turbo-16k':
        # Max context size: 16,384 tokens
        return 10000
    elif model == 'gpt-4':
        # Max context size: 8,192 tokens
        return 5000
    else:
        # Asssuming GPT-3.5-turbo
        # Max context size: 4,096 tokens
        return 2000


def get_input_token_limit(model):
    '''
    Returns max of length of input, in number of tokens, based on model to be used.
    '''

    # The number of tokens in the system message prompt.
    parse_prompt_tokens = get_token_length(ENT_TYPES_SYSTEM_MESSAGE['content'])

    # The maximum number of tokens in this model's context window.
    max_context_tokens = get_context_window_size(model)

    # The number of tokens to reserve for the output.
    output_reservation = get_output_reservation(model)

    # Leave ourselves a margin of error to account for structural overhead + just to be safe.
    margin_of_error = 100

    tokens_for_input = max_context_tokens - parse_prompt_tokens - output_reservation - margin_of_error

    return tokens_for_input


def get_timeout_limit(model):
    return 180
    # if model == 'gpt-3.5-turbo-16k':
    #     return 75
    # elif model == 'gpt-4':
    #     return 90
    # else:
    #     return 60


async def fetch_entity_types(input, model="gpt-3.5-turbo", prompt_override=None):
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
        system_message = ENT_TYPES_SYSTEM_MESSAGE

    if isinstance(input, list):
        ent_names_str = '\n'.join(input)
    else:
        ent_names_str = input

    messages = [
        system_message,
        {"role": "user", "content": ent_names_str}
    ]

    log_msg(f'Fetching entity types using model "{model}"...')
    start_time = time.time()
    result = await async_fetch_from_openai(
        messages,
        log_label='Entity types',
        model=model,
        max_tokens=max_tokens,
        timeout=timeout,
        expect_json_result=False
    )
    end_time = time.time()
    time_spent = end_time - start_time
    log_msg(f'Entity types fetched in {time_spent:.2f} seconds.')

    return result
