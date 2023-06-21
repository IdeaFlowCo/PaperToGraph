'''
Functions for parsing text into maps of entities and relationships.
'''

import gpt
from utils import log_msg
import tasks
from text import is_text_oversized, split_to_size


def get_text_size_limit(model):
    '''
    Returns desired length of text to be parsed, in number of characters, based on model to be used.
    '''
    # Different models have different max context sizes, where "context size" is the total number of tokens
    # used in the completion request, inclduding all of: the prompt in the system message, the text to be parsed,
    # and the reesrvation for the output.
    # Can check token length using https://platform.openai.com/tokenizer

    # The default parse prompt sent as system message is 243 tokens; round up to 250 to be safe.
    parse_prompt_tokens = 250
    
    # Can see max context size for different models here: https://platform.openai.com/docs/models/overview
    if model == 'gpt-3.5-turbo-16k':
        max_context_tokens = 16384
    if model == 'gpt-4':
        # Max context size: 8,192 tokens
        max_context_tokens = 8192
    else:
        # Asssuming GPT-3.5-turbo
        max_context_tokens = 4096

    # This margin of error is based off empirical testing.
    margin_of_error = 1000

    # Each token is about 3-4 characters for freeform text (e.g. the text to be parsed, which is the longest part of our requests).
    # Round down to 3 to be safe.
    chars_per_token = 3

    return (max_context_tokens - parse_prompt_tokens - margin_of_error) * chars_per_token


async def parse_with_gpt(text: str, model="gpt-3.5-turbo"):
    '''
    Splits provided text into smaller pieces and parses each piece in parallel using GPT.
    '''
    text_limit = get_text_size_limit(model)
    text_chunks = split_to_size(text, limit=text_limit)
    # Note: an error will make any given chunk be skipped. Because of the large number of parse jobs/chunks looked at,
    # this is hopefully acceptable behavior.
    # The benefit is that the total parsing is much more resilient with some fault tolerance.
    parse_work_fn = lambda chunk: gpt.async_fetch_parse(chunk, model=model, skip_on_error=True)
    
    master_parse_task = tasks.create_task_of_tasks(
        task_inputs=text_chunks, 
        work_fn=parse_work_fn, 
        task_label='Parse'
    )
    return await master_parse_task


async def parse_with_gpt_multitask(text: str, model="gpt-3.5-turbo"):
    '''
    Splits provided text into smaller pieces and parses each piece in parallel using GPT, yielding results as they come in.
    '''
    text_limit = get_text_size_limit(model)
    text_chunks = split_to_size(text, limit=text_limit)
    # Note: an error will make any given chunk be skipped. Because of the large number of parse jobs/chunks looked at,
    # this is hopefully acceptable behavior.
    # The benefit is that the total parsing is much more resilient with some fault tolerance.
    parse_work_fn = lambda chunk: gpt.async_fetch_parse(chunk, model=model, skip_on_error=True)

    async for result in tasks.create_and_run_tasks(
        task_inputs=text_chunks, 
        work_fn=parse_work_fn, 
        task_label='Parse'
    ):
        yield result


async def async_parse_with_heartbeat(text: str, model="gpt-3.5-turbo", prompt_override=None):
    '''
    Parser structured as generator that periodically yields blank characters to keep HTTP connection alive.
    '''
    log_msg(f'Parsing text using GPT model {model}')
    log_msg('Sending connection heartbeat')
    yield ' '
    text_limit = get_text_size_limit(model)
    text_chunks = split_to_size(text, limit=text_limit)
    # Note: an error will make any given chunk be skipped. Because of the large number of parse jobs/chunks looked at,
    # this is hopefully acceptable behavior.
    # The benefit is that the total parsing is much more resilient with some fault tolerance.
    parse_work_fn = lambda chunk: gpt.async_fetch_parse(chunk, model=model, skip_on_error=True, prompt_override=prompt_override)
    async for chunk in tasks.split_and_run_tasks_with_heartbeat(
        task_inputs=text_chunks, 
        work_fn=parse_work_fn, 
        task_label='Parse'
    ):
        yield chunk



# ***********
# Legacy code
# ***********

def parse_with_gpt_sequentially(text: str, model="gpt-3.5-turbo"):
    '''
    Legacy code for parsing a text block sequentially through GPT.

    If the text is oversized, it's split into smaller pieces and each piece is fed to GPT with the previous parse response
    as context. This turned out to not work very well as GPT has a hard time merging the new entity data with the old.

    This function no longer used by any active code paths but might be revisited in the future.
    '''
    if not is_text_oversized(text):
        parsed = gpt.fetch_parse_sequentially(text, model=model)
        return parsed
    
    text_chunks = split_to_size(text)
    parsed = None
    for chunk in text_chunks:
        parsed = gpt.fetch_parse_sequentially(chunk, prev_context=parsed, model=model)

    return parsed
