'''
Code for merging parse results using GPT.

This turned out to not work very well (GPT has issues with merging) and so is currently unused by any active code paths.
The gap might be addressable through some prompt engineering; we can revisit at a future point.
'''

import asyncio
import json

import gpt
from tasks import create_task_of_tasks

from utils import log_msg


def __group_parse_results(parse_results):
    grouped = []
    while len(parse_results):
        to_group = parse_results[:3]
        grouped.append('\n---\n'.join(to_group))
        parse_results = parse_results[3:]
    return grouped


async def async_merge_with_gpt(parse_results, model="gpt-3.5-turbo"):
    log_msg('Sending connection heartbeat')
    yield ' '

    grouped_parse_results = __group_parse_results(parse_results)
    # Merge groups of parse results cumulatively until we're ready for a final merge
    while len(grouped_parse_results) > 1:
        merge_task_creator = lambda merge_group: gpt.async_fetch_merge(merge_group, model=model, skip_on_error=True)
        all_merging = create_task_of_tasks(
            task_inputs=grouped_parse_results, 
            task_creator=merge_task_creator, 
            task_label='merge'
        )
        merge_results = []
        while True:
            if all_merging.done():
                merge_results = all_merging.result()
                break
            log_msg('Sending connection heartbeat')
            yield ' '
            await asyncio.sleep(10)
        # Potentially redo grouping and merging for long lists
        grouped_parse_results = __group_parse_results(merge_results)
    log_msg('All preliminary merges complete')

    all_parsed_text = grouped_parse_results[0]
    log_msg('Fetching final merge of all parse outputs')
    log_msg(all_parsed_text)
    merge_task = asyncio.create_task(gpt.async_fetch_merge(all_parsed_text, model=model))
    result = ''
    while True:
        if merge_task.done():
            result = merge_task.result()
            break
        log_msg('Sending connection heartbeat')
        yield ' '
        await asyncio.sleep(10)

    log_msg('Final merge complete, resturning result')

    yield json.dumps({"translation": result})
