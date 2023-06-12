'''
Functions for parsing text into maps of entities and relationships.
'''

import gpt
from utils import log_msg
from tasks import create_task_of_tasks, split_and_run_tasks_with_heartbeat
from text import is_text_oversized, split_to_size


async def parse_with_gpt(text: str, model="gpt-3.5-turbo"):
    '''
    Splits provided text into smaller pieces and parses each piece in parallel using GPT.
    '''
    text_limit = 10000 if model == 'gpt-4' else 8000
    text_chunks = split_to_size(text, limit=text_limit)
    # Note: an error will make any given chunk be skipped. Because of the large number of parse jobs/chunks looked at,
    # this is hopefully acceptable behavior.
    # The benefit is that the total parsing is much more resilient with some fault tolerance.
    max_tokens = 2000 if model == 'gpt-4' else 1600
    parse_task_creator = lambda chunk: gpt.async_fetch_parse(chunk, model=model, max_tokens=max_tokens, skip_on_error=True)
    
    master_parse_task = create_task_of_tasks(
        task_inputs=text_chunks, 
        task_creator=parse_task_creator, 
        task_label='parsing'
    )
    return await master_parse_task


async def async_parse_with_heartbeat(text: str, model="gpt-3.5-turbo"):
    '''
    Parser structured as generator that periodically yields blank characters to keep HTTP connection alive.
    '''
    log_msg('Sending connection heartbeat')
    yield ' '
    text_limit = 10000 if model == 'gpt-4' else 8000
    text_chunks = split_to_size(text, limit=text_limit)
    # Note: an error will make any given chunk be skipped. Because of the large number of parse jobs/chunks looked at,
    # this is hopefully acceptable behavior.
    # The benefit is that the total parsing is much more resilient with some fault tolerance.
    max_tokens = 2000 if model == 'gpt-4' else 1600
    parse_task_creator = lambda chunk: gpt.async_fetch_parse(chunk, model=model, max_tokens=max_tokens, skip_on_error=True)
    async for chunk in split_and_run_tasks_with_heartbeat(
        task_inputs=text_chunks, 
        task_creator=parse_task_creator, 
        task_label='parsing'
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
