'''
Code for tagging entity types with OpenAI.
'''

import time

from utils import log_msg

from .common import async_fetch_from_openai, get_context_window_size
from .text import get_token_length


REL_TYPES_SM_TEMPLATE = (
    "In the user message, there will be a list of relationships. Perform the following steps:"
    '\n'
    '\n1. For each relationship, categorize it as one of the following: '
    'Promotes, Inhibits, Associated With, Disconnected From, or Other.'
    '\n2. List each entity along with its type in an ("entity", "type") tuple. '
    'Make sure there are quotes around each entity name and type. '
    'Also make sure that each tule is on its own line, and that the entity name always comes first in the tuple.'
    '\n\n'
    'For example, if the provided input is: "{sample_input}", an output could look like this:'
    '\n```\n'
    '{sample_output}'
    '\n```\n')
SAMPLE_REL_TYPES_INPUT = (
    'induces'
)
SAMPLE_REL_TYPES_OUTPUT = (
    '("induces", "Promotes")'
)

REL_TYPES_SYSTEM_MESSAGE = {
    "role": "system",
    "content": REL_TYPES_SM_TEMPLATE.format(sample_input=SAMPLE_REL_TYPES_INPUT, sample_output=SAMPLE_REL_TYPES_OUTPUT)
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
        return 6000
    else:
        # Asssuming GPT-3.5-turbo
        # Max context size: 4,096 tokens
        return 2000


def get_input_token_limit(model):
    '''
    Returns max of length of input, in number of tokens, based on model to be used.
    '''

    # The number of tokens in the system message prompt.
    parse_prompt_tokens = get_token_length(REL_TYPES_SYSTEM_MESSAGE['content'])

    # The maximum number of tokens in this model's context window.
    max_context_tokens = get_context_window_size(model)

    # The number of tokens to reserve for the output.
    output_reservation = get_output_reservation(model)

    # Leave ourselves a margin of error to account for structural overhead + just to be safe.
    margin_of_error = 100

    tokens_for_input = max_context_tokens - parse_prompt_tokens - output_reservation - margin_of_error

    return tokens_for_input


def get_timeout_limit(model):
    return 360
    # if model == 'gpt-3.5-turbo-16k':
    #     return 75
    # elif model == 'gpt-4':
    #     return 90
    # else:
    #     return 60


async def fetch_relationship_types(input, model="gpt-3.5-turbo", prompt_override=None):
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
        system_message = REL_TYPES_SYSTEM_MESSAGE

    if isinstance(input, list):
        ent_names_str = '\n'.join(input)
    else:
        ent_names_str = input

    messages = [
        system_message,
        {"role": "user", "content": ent_names_str}
    ]

    result = ''
    try:
        log_msg(f'Fetching relationship types using model "{model}"...')
        start_time = time.time()
        result = await async_fetch_from_openai(
            messages,
            log_label='Relationship types',
            model=model,
            max_tokens=max_tokens,
            timeout=timeout,
            expect_json_result=False
        )
        end_time = time.time()
        time_spent = end_time - start_time
        log_msg(f'Relationship types fetched in {time_spent:.2f} seconds.')
    finally:
        return result
