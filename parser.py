from datetime import datetime
import json
import os
import time

import openai


openai.api_key = os.getenv("OPENAI_API_KEY")

def __log_msg(msg:str):
    ts = datetime.now().isoformat(timespec='seconds')
    print(f'[{ts}] {msg}')


SAMPLE_INPUT = (
    "Tom Currier is a great guy who built lots of communities after he studied at Stanford and Harvard. "
    "He also won the Thiel fellowship. "
)

SAMPLE_OUTPUT = (
    "Tom Currier"
    "\n- studied at: Stanford, Harvard"
    "\n- winner of: Thiel Fellowship"
    "\n\n"
    "{"
    "\n  \"Tom Currier\": {"
    "\n    \"studied at\": \"Stanford, Harvard\","
    "\n    \"winner of\": \"Thiel Fellowship\""
    "\n  }"
    "\n}"
)

SYSTEM_MESSAGE_CONTENT = (
    "Extract the named entities and relations between them in subsequent queries as per the following format. "
    "Specifically list the named entities, then sub-bullets showing each of their relationships after a colon. "
    "Don't forget newlines between entries. Also include a JSON version of the output that explicitly shows relationships and targets. "
    "Make sure to merge the information about extracted entities with any previously extracted information. "
    "\n\n"
    "Input: \n" + SAMPLE_INPUT + "\n\n"
    "Output: \n" + SAMPLE_OUTPUT + "\n\n"
    "Also, do a second degree of entity extraction on all the entities named as targets, connecting, for instance"
    "\n\"constitutive Wnt signalling\""
    "\n- Wnt"
    "\n"
    "\n\"part of the β-catenin degradation complex\""
    "\n- β-catenin"
)

SYSTEM_MESSAGE = {"role": "system", "content": SYSTEM_MESSAGE_CONTENT}


def __fetch_parse(text:str, prev_context=None, model="gpt-3.5-turbo"):
    messages = [
        SYSTEM_MESSAGE
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


TEXT_BLOCK_SIZE_LIMIT = 3000


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


def parse_generator(text: str, model="gpt-3.5-turbo"):
    __log_msg('Sending connection heartbeat')
    yield ' '
    text_chunks = __split_to_size(text)
    parsed = None
    for chunk in text_chunks:
        __log_msg('Sending connection heartbeat')
        yield ' '
        parsed = __fetch_parse(chunk, prev_context=parsed, model=model)

    yield json.dumps({"translation": parsed})
