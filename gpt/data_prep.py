"""
Code for transforming text into a Q&A format that can be used to train LLMs.
"""

import asyncio
import json
import time

from utils import log_msg, log_debug

from .common import async_fetch_from_openai, get_context_window_size
from .text import get_token_length, split_to_token_size


DATA_PREP_SM_TEMPLATE = (
    "In the user message, there will be an extract from a scientific paper. Perform the following steps:"
    "\n"
    "\n1. Generate a series of questions and answers about the content in the extract that could be used to train an LLM."
    '\n2. List each question and answer in a ("question", "answer") tuple. '
    "Make sure there are quotes around each question and answer. "
    "Also make sure that each tuple is on its own line, and that the question always comes first in the tuple."
    "\n\n"
    'For example, if the provided input is: "{sample_input}", an output could look like this:'
    "\n"
    "\n```\n"
    "{sample_output}"
    "\n```\n"
)
SAMPLE_DATA_PREP_INPUT = (
    "Hypophosphatasia (HP) (MIM 241510) is an inborn error of bone metabolism, characterized by a genetic "
    "defect in the gene encoding the tissue-nonspecific alkaline phosphatase (TNSALP)."
)
SAMPLE_DATA_PREP_OUTPUT = (
    '("What is Hypophosphatasia?", "Hypophosphatasia is an inborn error of bone metabolism.")\n'
    '("What is Hypophosphatasia characterized by?", "Hypophosphatasia is characterized by a genetic defect in the gene '
    'encoding the tissue-nonspecific alkaline phosphatase (TNSALP).")'
)

DATA_PREP_SYSTEM_MESSAGE = {
    "role": "system",
    "content": DATA_PREP_SM_TEMPLATE.format(
        sample_input=SAMPLE_DATA_PREP_INPUT, sample_output=SAMPLE_DATA_PREP_OUTPUT
    ),
}


def _get_output_reservation(model, input=None):
    """
    Return the maximum number of tokens to reserve for the response from a given model.
    """

    if model == "gpt-4o" or model == "gpt-4o-mini":
        # Max completion tokens: 16,384
        max_tokens = 16000  # Leave a small buffer
    elif model == "gpt-4-32k":
        # Max context size: 32,768 tokens
        max_tokens = 12000
    elif model == "gpt-3.5-turbo-16k":
        # Max context size: 16,384 tokens
        max_tokens = 8000
    elif model == "gpt-4":
        # Max context size: 8,192 tokens
        max_tokens = 4000
    else:
        # Asssuming GPT-3.5-turbo
        # Max context size: 4,096 tokens
        max_tokens = 2000

    if not input:
        return max_tokens

    # Optimization to avoid TPM limits when processing small text chunks: never reserve more than 5x input length
    input_length = get_token_length(input, model=model)
    return min(max_tokens, input_length * 5)


def _get_input_token_limit(model):
    """
    Returns max of length of input, in number of tokens, based on model to be used.
    """

    # The number of tokens in the system message prompt.
    parse_prompt_tokens = get_token_length(
        DATA_PREP_SYSTEM_MESSAGE["content"], model=model
    )

    # The maximum number of tokens in this model's context window.
    max_context_tokens = get_context_window_size(model)

    # The number of tokens to reserve for the output.
    output_reservation = _get_output_reservation(model)

    # Leave ourselves a margin of error to account for structural overhead + just to be safe.
    margin_of_error = 100

    tokens_for_input = (
        max_context_tokens - parse_prompt_tokens - output_reservation - margin_of_error
    )

    return tokens_for_input


def _get_timeout_limit(model):
    return 180
    # if model == 'gpt-3.5-turbo-16k':
    #     return 75
    # elif model == 'gpt-4':
    #     return 90
    # else:
    #     return 60


def fetch_training_data_for_text(
    input, model="gpt-3.5-turbo", input_token_limit=None, output_token_limit=None
):
    """
    Retrieve parse response from GPT for given block of text.
    """
    timeout = _get_timeout_limit(model)

    log_debug(f'Fetching training data using model "{model}"...')

    if not input_token_limit:
        input_token_limit = _get_input_token_limit(model)
    else:
        input_token_limit = min(input_token_limit, _get_input_token_limit(model))

    if isinstance(input, list):
        input = "\n\n".join(input)
    input_list = split_to_token_size(input, input_token_limit, model=model)
    log_debug(f"Input broken into {len(input_list)} chunks.")

    for i, input in enumerate(input_list):
        log_msg(f"Fetching training data for input chunk {i + 1} of {len(input_list)}")

        max_tokens = _get_output_reservation(model, input)
        if output_token_limit:
            max_tokens = min(output_token_limit, max_tokens)

        messages = [DATA_PREP_SYSTEM_MESSAGE, {"role": "user", "content": input}]
        start_time = time.time()
        result = asyncio.run(
            async_fetch_from_openai(
                messages,
                log_label="Data prep",
                model=model,
                max_tokens=max_tokens,
                timeout=timeout,
                expect_json_result=False,
            )
        )
        end_time = time.time()
        time_spent = end_time - start_time
        log_msg(f"Training data fetched in {time_spent:.2f} seconds.")
        structured_result = {"source_text": input, "training_data": result}
        yield json.dumps(structured_result)
