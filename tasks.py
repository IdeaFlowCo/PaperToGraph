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
    tasks_to_create = len(task_inputs)
    # Make a maximum of 8 tasks at a time to avoid OpenAI rate limit
    for i in range(min(tasks_to_create, MAX_API_TASKS)):
        input = task_inputs[i]
        tasks.append(asyncio.create_task(task_creator(input)))
        tasks_created += 1
    log_msg(f'Created {tasks_created} {task_label} tasks')
    # Wait for all tasks to complete
    while True:
        tasks_done = 0
        for task in tasks:
            if not task.done():
                continue
            tasks_done += 1
        tasks_in_progress = tasks_created - tasks_done
        # Check if we were capped by MAX_API_TASKS and some tasks finished; if so, replace them
        if tasks_created < tasks_to_create and tasks_in_progress < MAX_API_TASKS:
            new_tasks = []
            new_tasks_to_create = min(tasks_to_create - tasks_created, MAX_API_TASKS - tasks_in_progress)
            for i in range(new_tasks_to_create):
                input = task_inputs[tasks_created]
                new_tasks.append(asyncio.create_task(task_creator(input)))
                tasks_created += 1
            tasks.extend(new_tasks)
        log_msg(f'{tasks_done} out of {tasks_created} {task_label} tasks completed')
        if tasks_done == tasks_created:
            return [task.result() for task in tasks]
        await asyncio.sleep(5)


def create_task_of_tasks(task_inputs, task_creator, task_label):
    return asyncio.create_task(create_and_run_tasks(task_inputs, task_creator, task_label))


async def split_and_run_tasks_with_heartbeat(task_inputs, task_creator, task_label):
    log_msg('Sending connection heartbeat')
    yield ' '
    all_tasks = create_task_of_tasks(
        task_inputs=task_inputs, 
        task_creator=task_creator, 
        task_label=task_label
    )
    results = None
    while True:
        if all_tasks.done():
            results = all_tasks.result()
            break
        log_msg('Sending connection heartbeat')
        yield ' '
        await asyncio.sleep(10)
    log_msg('All parsing complete')

    result = []
    for result_str in results:
        try:
            result.append(json.loads(result_str))
        except json.decoder.JSONDecodeError:
            # Some of these won't have been recognizable JSON; skip them
            continue

    yield json.dumps({"translation": result}, indent=2)
