import os

import openai


openai.api_key = os.getenv("OPENAI_API_KEY")


SAMPLE_INPUT = (
    "Tom Currier is a great guy who built lots of communities after he studied at Stanford and Harvard. "
    "He also won the Thiel fellowship. "
    "RPC is a software engineer who has worked at Google, Facebook, and Stripe. "
    "He studied at the University of Maryland, College Park. "
)

SAMPLE_OUTPUT = (
    "Tom Currier\n "
    "\n- studied at: Stanford, Harvard"
    "\n- winner of: Thiel Fellowship\n"
    "\n"
    "RPC\n"
    "\n- worked at: Google, Facebook, Stripe"
    "\n- studied at: University of Maryland, College Park"
)

SYSTEM_MESSAGE_CONTENT = (
    "Extract the named entities and relations between them in subsequent queries as per the following format. "
    "Specifically list the named entities, then sub-bullets showing each of their relationships after a colon. "
    "Don't forget newlines between entries."
    "Input: \n" + SAMPLE_INPUT + "\n\n"
    "Output: \n" + SAMPLE_OUTPUT + "\n"
)

SYSTEM_MESSAGE = {"role": "system", "content": SYSTEM_MESSAGE_CONTENT}


def __fetch_parse(message:str):
    messages = [
        SYSTEM_MESSAGE,
        {"role": "user", "content": message}
    ]

    result = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=3000,
        temperature=1.2
    )
    return result["choices"][0]["message"]["content"]


def parse_with_gpt(message: str):
    parsed = __fetch_parse(message)
    return parsed
