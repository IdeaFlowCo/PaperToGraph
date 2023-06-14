'''
Utilities for splitting processing into groups of async tasks.
'''

import asyncio
import json

from utils import log_msg


MAX_API_TASKS = 8

async def create_and_run_tasks(task_inputs, task_creator, task_label):
    '''
    Create separate tasks for each input in task_inputs and run them in parallel.

    Note that no more than MAX_API_TASKS will actually be running simultaneously to avoid rate limits.
    '''
    tasks = []
    tasks_created = 0
    tasks_completed = 0
    total_tasks = len(task_inputs)
    # Make a maximum of 8 tasks at a time to avoid OpenAI rate limit
    for i in range(min(total_tasks, MAX_API_TASKS)):
        input = task_inputs[i]
        new_task = asyncio.create_task(task_creator(input))
        tasks.append(new_task)
        tasks_created += 1

    log_msg(f'{task_label}: {tasks_completed} of {total_tasks} tasks completed ({len(tasks)} currently running)')
    
    while tasks_completed < len(task_inputs):
        # Wait for any of the running tasks to complete
        completed, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # Process the completed tasks and collect results
        for task in completed:
            result = await task
            tasks_completed += 1
            yield result
            tasks.remove(task)

        # Start new tasks up to the maximum allowed concurrent tasks
        while len(tasks) < MAX_API_TASKS and tasks_created < total_tasks:
            input = task_inputs[tasks_created]
            task = asyncio.create_task(task_creator(input))
            tasks.append(task)
            tasks_created += 1

        log_msg(f'{task_label}: {tasks_completed} of {total_tasks} tasks completed ({len(tasks)} currently running)')


def create_task_of_tasks(task_inputs, task_creator, task_label):
    '''
    Create subtasks for each input in task_inputs and return a task that will complete when all subtasks are complete.
    '''
    async def gather_results():
        results = []
        async for task_result in create_and_run_tasks(task_inputs, task_creator, task_label):
            results.append(task_result)
        return results

    return asyncio.create_task(gather_results())



async def split_and_run_tasks_with_heartbeat(task_inputs, task_creator, task_label):
    '''
    Create separate tasks for each input and await completion while yielding occasional heartbeat messages.
    '''
    log_msg('Sending connection heartbeat')
    yield ' '
    all_tasks = create_task_of_tasks(
        task_inputs=task_inputs, 
        task_creator=task_creator, 
        task_label=task_label
    )
    results = None
    skips = 0
    while True:
        if all_tasks.done():
            results = all_tasks.result()
            break
        skips += 1
        if skips > 3:
            skips = 0
            log_msg('Sending connection heartbeat')
            yield ' '
        await asyncio.sleep(2)
    log_msg('All parsing complete')

    result = []
    for result_str in results:
        try:
            result.append(json.loads(result_str))
        except json.decoder.JSONDecodeError:
            # Some of these won't have been recognizable JSON; skip them
            continue

    yield json.dumps({"translation": result}, indent=2)
