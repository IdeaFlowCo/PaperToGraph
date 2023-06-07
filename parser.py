import asyncio
from datetime import datetime
import json
import os
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
    "Don't forget newlines between entries."
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
    "Remove any entity objects that do not have any relationship properties."
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

    result = result["choices"][0]["message"]["content"]
    __log_msg('Received parse response from OpenAI')
    __log_msg(result)
    return result


async def __async_fetch_parse(text:str, prev_context=None, model="gpt-3.5-turbo"):
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
        result = await openai.ChatCompletion.acreate(
            model=model,
            messages=messages,
            max_tokens=1500,
            # temperature=1.2
        )
    except openai.error.RateLimitError:
        __log_msg('Rate limit error from OpenAI')
        # Wait a quarter second and try again
        time.sleep(0.25)
        return await __fetch_parse(text, prev_context=prev_context, model=model)
    except BaseException as err:
        __log_msg(f'Error encountered during OpenAI API call: {err}')
        raise err

    result = result["choices"][0]["message"]["content"]
    __log_msg('Received parse response from OpenAI')
    __log_msg(result)
    return result


async def __async_fetch_merge(text:str, model="gpt-3.5-turbo"):
    messages = [
        MERGE_SYSTEM_MESSAGE
    ]

    messages.append(
        {"role": "user", "content": text}
    )

    try:
        __log_msg('Requesting merge from OpenAI...')
        result = await openai.ChatCompletion.acreate(
            model=model,
            messages=messages,
            max_tokens=1200,
            # temperature=1.2
        )
    except openai.error.RateLimitError:
        __log_msg('Rate limit error from OpenAI')
        # Wait a quarter second and try again
        time.sleep(0.25)
        return await __async_fetch_merge(text, model=model)
    except BaseException as err:
        __log_msg(f'Error encountered during OpenAI API call: {err}')
        raise err

    result = result["choices"][0]["message"]["content"]
    __log_msg('Received merge response from OpenAI')
    __log_msg(result)
    return result


TEXT_BLOCK_SIZE_LIMIT = 8000


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

async def parse_generator(text: str, model="gpt-3.5-turbo"):
    __log_msg('Sending connection heartbeat')
    yield ' '
    text_chunks = __split_to_size(text)
    parsed = []
    for i in range(len(text_chunks)):
        __log_msg(f'Parsing text chunk {i + 1} of {len(text_chunks)}')
        chunk = text_chunks[i]
        parse_task = asyncio.create_task(__async_fetch_parse(chunk, model=model))
        while True:
            if parse_task.done():
                parsed.append(parse_task.result())
                break
            __log_msg('Sending connection heartbeat')
            yield ' '
            await asyncio.sleep(10)
    __log_msg('All parsing complete')

    grouped_parse_results = __group_parse_results(parsed)
    while len(grouped_parse_results) > 1:
        merge_results = []
        for i in range(len(grouped_parse_results)):
            __log_msg(f'Merging parse group {i + 1} of {len(grouped_parse_results)}')
            merge_group = grouped_parse_results[i]
            merge_task = asyncio.create_task(__async_fetch_merge(merge_group, model=model))
            while True:
                if merge_task.done():
                    merge_results.append(merge_task.result())
                    break
                __log_msg('Sending connection heartbeat')
                yield ' '
                await asyncio.sleep(10)
        # Potentially redo grouping and merging for long lists
        grouped_parse_results = __group_parse_results(merge_results)

    all_parsed_text = '\n'.join(parsed)
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

    yield json.dumps({"translation": result})
