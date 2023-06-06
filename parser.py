import os

import openai


openai.api_key = os.getenv("OPENAI_API_KEY")

PROMPT_TEMPLATE = (
    "Extract the named entities and relations between them in subsequent queries as per the following format. "
    "Specifically list the named entities, then sub-bullets showing each of their relationships after a colon. "
    "Don't forget newlines between entries."
    "Input: "
    "\"Tom Currier is a great guy who built lots of communities after he studied at Stanford and Harvard. He also won the Thiel fellowship\""
    "Output: "
    "Tom Currier\n "
    "\n- studied at: Stanford, Harvard "
    "\n- winner of: Thiel Fellowship \n"
    "\n------\n"
    "Query: \n"
)

def __fetch_gpt_response(message:str):
    new_prompt = PROMPT_TEMPLATE + message

    result = openai.Completion.create(
        model="text-davinci-003",
        prompt=new_prompt,
        max_tokens=3000,
        temperature=1.2
    )
    return result["choices"][0]["text"]


def parse_with_gpt(message: str):
    return __fetch_gpt_response(message)
