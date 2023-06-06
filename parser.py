import os
import time

import openai


openai.api_key = os.getenv("OPENAI_API_KEY")


SAMPLE_INPUT = (
    "Tom Currier is a great guy who built lots of communities after he studied at Stanford and Harvard. "
    "He also won the Thiel fellowship. "
    "RPC is a software engineer who has worked at Google, Facebook, and Stripe. "
    "He studied at the University of Maryland, College Park. "
)

SAMPLE_OUTPUT = (
    "Tom Currier"
    "\n- studied at: Stanford, Harvard"
    "\n- winner of: Thiel Fellowship\n"
    "\n"
    "RPC"
    "\n- worked at: Google, Facebook, Stripe"
    "\n- studied at: University of Maryland, College Park"
)

SYSTEM_MESSAGE_CONTENT = (
    "Extract the named entities and relations between them in subsequent queries as per the following format. "
    "Specifically list the named entities, then sub-bullets showing each of their relationships after a colon. "
    "Don't forget newlines between entries. Also include a JSON version of the output that explicitly shows relationships and targets. "
    "Make sure to merge the information about extracted entities with any previously extracted information. "
    "\n\n"
    "Input: \n" + SAMPLE_INPUT + "\n\n"
    "Output: \n" + SAMPLE_OUTPUT + "\n"
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

    # print(messages)

    try:
        result = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=3000,
            temperature=1.2
        )
    except openai.error.RateLimitError:
        # Wait a quarter second and try again
        time.sleep(0.25)
        return __fetch_parse(text, prev_context=prev_context, model=model)

    return result["choices"][0]["message"]["content"]


def __split_to_size(text:str):
    # Split by paragraphs first
    og_text_chunks = list(filter(lambda x : x != '', text.split('\n\n')))

    rechunked_text = [og_text_chunks[0]]
    i = 0
    j = 1
    while j < len(og_text_chunks):
        if len(rechunked_text[i]) + len(og_text_chunks[j]) < 1800:
            rechunked_text[i] = rechunked_text[i] + '\n\n' + og_text_chunks[j]
            j += 1
        else:
            i += 1
            rechunked_text.append(og_text_chunks[j])
            j += 1

    return rechunked_text


def parse_with_gpt(text: str, model="gpt-3.5-turbo"):
    if len(text) <= 3000:
        parsed = __fetch_parse(text, model=model)
        return parsed
    
    text_chunks = __split_to_size(text)
    parsed = None
    for chunk in text_chunks:
        parsed = __fetch_parse(chunk, prev_context=parsed, model=model)

    return parsed
