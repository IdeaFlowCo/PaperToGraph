import asyncio
from datetime import datetime
from functools import reduce
import json
import os
import pprint
import time

import openai


openai.api_key = os.getenv("OPENAI_API_KEY")

def __log_msg(msg:str):
    ts = datetime.now().isoformat(timespec='seconds')
    print(f'[{ts}] {msg}')


SAMPLE_PARSE_INPUT = (
    "Tom Currier is a great guy who built lots of communities after he studied at Stanford and Harvard. "
    "He also won the Thiel fellowship. "
)

SAMPLE_PARSE_OUTPUT = (
    # "Tom Currier"
    # "\n- studied at: Stanford, Harvard"
    # "\n- winner of: Thiel Fellowship"
    # "\n\n"
    "{"
    "\n  \"Tom Currier\": {"
    "\n    \"studied at\": \"Stanford, Harvard\","
    "\n    \"winner of\": \"Thiel Fellowship\""
    "\n  }"
    "\n}"
)

PARSE_SYSTEM_MESSAGE_CONTENT = (
    "Extract the named entities and relations between them in subsequent queries as per the following format. "
    "Specifically list the named entities as JSON objects, with properties for each of their relationships. "
    "Ignore any named entities that do not have specified relationships to other entities. "
    "Don't forget newlines between entries and make sure that response is valid JSON."
    # "Make sure to merge the information about extracted entities with any previously extracted information. "
    "\n\n"
    "Input: \n" + SAMPLE_PARSE_INPUT + "\n\n"
    "Output: \n" + SAMPLE_PARSE_OUTPUT + "\n\n"
    # "Also, do a second degree of entity extraction on all the entities named as targets, connecting, for instance"
    # "\n\"constitutive Wnt signalling\""
    # "\n- Wnt"
    # "\n"
    # "\n\"part of the β-catenin degradation complex\""
    # "\n- β-catenin"
)
PARSE_SYSTEM_MESSAGE = {"role": "system", "content": PARSE_SYSTEM_MESSAGE_CONTENT}


SAMPLE_MERGE_INPUT = (
    "{"
    "\n  \"Tom Currier\": {"
    "\n    \"studied at\": \"Stanford, Harvard\","
    "\n  }"
    "\n}"
    "\n{"
    "\n  \"RPC\": {"
    "\n    \"studied at\": \"University of Maryland\","
    "\n  }"
    "\n}"
    "\n{"
    "\n  \"Tom Currier\": {"
    "\n    \"winner of\": \"Thiel Fellowship\""
    "\n  }"
    "\n}"
    "\n}"
    "\n{"
    "\n  \"Empty\": {}"
    "\n}"
)

SAMPLE_MERGE_OUTPUT = (
    "{"
    "\n  \"Tom Currier\": {"
    "\n    \"studied at\": \"Stanford, Harvard\","
    "\n    \"winner of\": \"Thiel Fellowship\""
    "\n  },"
    "\n  \"RPC\": {"
    "\n    \"studied at\": \"University of Maryland\","
    "\n  }"
    "\n}"
)

MERGE_SYSTEM_MESSAGE_CONTENT = (
    "The following queries will provide JSON objects representing different entites and their relationships. "
    "Merge the provided JSON objects so that each entity has only one JSON object with properties for all deduplicated relationships."
    "Remove any entity objects that do not have any relationship properties. Make sure the final result is valid JSON."
    "\n\n"
    "Input: \n" + SAMPLE_MERGE_INPUT + "\n\n"
    "Output: \n" + SAMPLE_MERGE_OUTPUT + "\n\n"
)
MERGE_SYSTEM_MESSAGE = {"role": "system", "content": MERGE_SYSTEM_MESSAGE_CONTENT}



def __fetch_parse(text:str, prev_context=None, model="gpt-3.5-turbo"):
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
        __log_msg('Requesting parse from OpenAI...')
        result = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=2000,
            # temperature=1.2
        )
    except openai.error.RateLimitError:
        __log_msg('Rate limit error from OpenAI')
        # Wait a quarter second and try again
        time.sleep(0.25)
        return __fetch_parse(text, prev_context=prev_context, model=model)
    except BaseException as err:
        __log_msg(f'Error encountered during OpenAI API call: {err}')
        raise err

    result = result["choices"][0]["message"]["content"].strip()
    __log_msg('Received parse response from OpenAI')
    __log_msg(result)
    return result


def __clean_json(response):
    cleaned = {}
    try:
        response_dict = json.loads(response)
        for key, value in response_dict.items():
            # We want to skip the empty values to avoid overloading GPT in subsequent queries.
            if not value:
                continue
            if isinstance(value, dict):
                cleaned_value = {}
                # Sometimes a dict will have a bunch of key => empty dict pairs inside of it for some reason?
                # Trim those too.
                for subkey, subvalue in value.items():
                    if subvalue:
                        cleaned_value[subkey] = subvalue
                value = cleaned_value
            cleaned[key] = value
        to_log = pprint.pformat(cleaned, indent=2, width=160)
        __log_msg(f'Cleaned up response JSON: \n{to_log}')
        return json.dumps(cleaned)
    except json.decoder.JSONDecodeError:
        __log_msg('Response not valid JSON!')
        if response.startswith('{'):
            # Response isn't valid JSON but may be close enough that it can still be used, so we'll just return it as-is
            return response
        return None

async def __async_fetch_parse(text:str, model="gpt-3.5-turbo", skip_on_error=False, should_retry=True):
    messages = [
        PARSE_SYSTEM_MESSAGE
    ]

    messages.append(
        {"role": "user", "content": text}
    )

    try:
        __log_msg('Requesting parse from OpenAI...')
        async with asyncio.timeout(90):
            result = await openai.ChatCompletion.acreate(
                model=model,
                messages=messages,
                max_tokens=1500,
                # temperature=1.2
            )
    except openai.error.RateLimitError:
        __log_msg('Rate limit error from OpenAI')
        # Wait a quarter second and try again
        # This is common enough and the exception triggers fast enough that it
        # doesn't "use up" a retry in our logic.
        await asyncio.sleep(0.25)
        return await __async_fetch_parse(
            text, 
            model=model, 
            skip_on_error=skip_on_error, 
            should_retry=should_retry
        )
    except TimeoutError:
        if should_retry:
            __log_msg(f'Parse request timeout. Trying again one more time...')
            return await __async_fetch_parse(
                text,
                model=model,
                skip_on_error=skip_on_error,
                should_retry=False
            )
        __log_msg(f'Parse request timed out multiple times.')
        if skip_on_error:
            return ''
        raise TimeoutError
    except BaseException as err:
        __log_msg(f'Error encountered during OpenAI API call: {err}')
        if should_retry:
            __log_msg(f'Trying again one more time...')
            return await __async_fetch_parse(
                text,
                model=model,
                skip_on_error=skip_on_error,
                should_retry=False
            )
        if skip_on_error:
            return ''
        raise err

    result = result["choices"][0]["message"]["content"].strip()
    __log_msg('Received parse response from OpenAI')
    __log_msg(result)
    result = __clean_json(result)
    if result is None:
        if should_retry:
            __log_msg("Doesn't look like GPT gave us JSON. Trying again one more time...")
            return await __async_fetch_parse(
                text,
                model=model,
                skip_on_error=skip_on_error,
                should_retry=False
            )
        if skip_on_error:
            __log_msg(
                "Doesn't look like GPT gave us JSON. "
                "No reties left and skip_on_error=true, so returning blank to contain damages."
            )
            return ''
    return result


async def __async_fetch_merge(text:str, model="gpt-3.5-turbo", skip_on_error=False, should_retry=True):
    messages = [
        MERGE_SYSTEM_MESSAGE
    ]

    messages.append(
        {"role": "user", "content": text}
    )

    try:
        __log_msg('Requesting merge from OpenAI...')
        # GPT-4 has higher capacity so we can use more tokens for it
        max_tokens = 2000 if model == 'gpt-4' else 1200
        async with asyncio.timeout(120):
            result = await openai.ChatCompletion.acreate(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                # temperature=1.2
            )
    except openai.error.RateLimitError:
        __log_msg('Rate limit error from OpenAI')
        # Wait a quarter second and try again.
        # This is common enough and the exception triggers fast enough that it
        # doesn't "use up" a retry in our logic.
        await asyncio.sleep(0.25)
        return await __async_fetch_merge(
            text,
            model=model, 
            skip_on_error=skip_on_error, 
            should_retry=should_retry
        )
    except TimeoutError:
        if should_retry:
            __log_msg(f'Merge request timeout. Trying again one more time...')
            return await __async_fetch_merge(
                text, 
                model=model, 
                skip_on_error=skip_on_error, 
                should_retry=False
            )
        __log_msg(f'Merge request timed out multiple times.')
        if skip_on_error:
            return ''
        raise TimeoutError
    except BaseException as err:
        __log_msg(f'Error encountered during OpenAI API call: {err}')
        if should_retry:
            __log_msg(f'Trying again one more time...')
            return await __async_fetch_parse(
                text,
                model=model,
                skip_on_error=skip_on_error,
                should_retry=False
            )
        if skip_on_error:
            return ''
        raise err

    result = result["choices"][0]["message"]["content"].strip()
    __log_msg('Received merge response from OpenAI')
    __log_msg(result)
    result = __clean_json(result)
    if result is None:
        if should_retry:
            __log_msg("Doesn't look like GPT gave us JSON. Trying again one more time...")
            return await __async_fetch_parse(
                text,
                model=model,
                skip_on_error=skip_on_error,
                should_retry=False
            )
        if skip_on_error:
            __log_msg(
                "Doesn't look like GPT gave us JSON. "
                "No reties left and skip_on_error=true, so returning blank to contain damages."
            )
            return ''
    return result


TEXT_BLOCK_SIZE_LIMIT = 6000


def __split_to_size(text:str):
    # Split by paragraphs first
    og_text_chunks = list(filter(lambda x : x != '', text.split('\n\n')))

    # Look for any chunks that are still too big
    # TODO

    # Try to recombine chunks that are smaller than they need to be
    rechunked_text = [og_text_chunks[0]]
    i = 0
    j = 1
    while j < len(og_text_chunks):
        if len(rechunked_text[i]) + len(og_text_chunks[j]) < TEXT_BLOCK_SIZE_LIMIT:
            rechunked_text[i] = rechunked_text[i] + '\n\n' + og_text_chunks[j]
            j += 1
        else:
            i += 1
            rechunked_text.append(og_text_chunks[j])
            j += 1

    __log_msg(f'Split into {len(rechunked_text)} blocks of text')

    return rechunked_text


def parse_with_gpt(text: str, model="gpt-3.5-turbo"):
    if len(text) <= TEXT_BLOCK_SIZE_LIMIT:
        parsed = __fetch_parse(text, model=model)
        return parsed
    
    text_chunks = __split_to_size(text)
    parsed = None
    for chunk in text_chunks:
        parsed = __fetch_parse(chunk, prev_context=parsed, model=model)

    return parsed


def __group_parse_results(parse_results):
    grouped = []
    while len(parse_results):
        to_group = parse_results[:3]
        grouped.append('\n'.join(to_group))
        parse_results = parse_results[3:]
    return grouped


MAX_API_TASKS = 8

async def __create_and_run_tasks(task_inputs, task_creator, task_label):
    tasks = []
    tasks_created = 0
    tasks_to_create = len(task_inputs)
    # Make a maximum of 12 tasks at a time to avoid OpenAI rate limit
    for i in range(min(tasks_to_create, MAX_API_TASKS)):
        input = task_inputs[i]
        tasks.append(asyncio.create_task(task_creator(input)))
        tasks_created += 1
    __log_msg(f'Created {tasks_created} {task_label} tasks')
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
        __log_msg(f'{tasks_done} out of {tasks_created} {task_label} tasks completed')
        if tasks_done == tasks_created:
            return [task.result() for task in tasks]
        await asyncio.sleep(5)

async def async_parse_with_gpt(text: str, model="gpt-3.5-turbo"):
    __log_msg('Sending connection heartbeat')
    yield ' '
    text_chunks = __split_to_size(text)
    # Note: an error will make any given chunk be skipped. Because of the large number of parse jobs/chunks looked at,
    # this is hopefully acceptable behavior.
    # The benefit is that the total parsing is much more resilient with some fault tolerance.
    parse_task_creator = lambda chunk: __async_fetch_parse(chunk, model=model, skip_on_error=True)
    all_parsing = asyncio.create_task(__create_and_run_tasks(text_chunks, parse_task_creator, task_label='parsing'))
    parsed = None
    while True:
        if all_parsing.done():
            parsed = all_parsing.result()
            break
        __log_msg('Sending connection heartbeat')
        yield ' '
        await asyncio.sleep(10)
    __log_msg('All parsing complete')

    grouped_parse_results = __group_parse_results(parsed)
    while len(grouped_parse_results) > 1:
        merge_task_creator = lambda merge_group: __async_fetch_merge(merge_group, model=model, skip_on_error=True)
        all_merging = asyncio.create_task(__create_and_run_tasks(grouped_parse_results, merge_task_creator, task_label='merge'))
        merge_results = []
        while True:
            if all_merging.done():
                merge_results = all_merging.result()
                break
            __log_msg('Sending connection heartbeat')
            yield ' '
            await asyncio.sleep(10)
        # Potentially redo grouping and merging for long lists
        grouped_parse_results = __group_parse_results(merge_results)
    __log_msg('All preliminary merges complete')

    all_parsed_text = '\n'.join(grouped_parse_results)
    __log_msg('Fetching final merge of all parse outputs')
    merge_task = asyncio.create_task(__async_fetch_merge(all_parsed_text, model=model))
    result = ''
    while True:
        if merge_task.done():
            result = merge_task.result()
            break
        __log_msg('Sending connection heartbeat')
        yield ' '
        await asyncio.sleep(10)

    __log_msg('Final merge complete, resturning result')

    yield json.dumps({"translation": result})
