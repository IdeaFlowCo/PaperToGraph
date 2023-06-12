'''
All GPT-specific code used for merging entity blocks after parsing.
'''


from gpt.common import async_fetch_from_openai


SAMPLE_MERGE_INPUT = (
    "\n---"
    "\n{"
    "\n  \"Tom Currier\": {"
    "\n    \"studied at\": \"Stanford, Harvard\","
    "\n  }"
    "\n}"
    "\n---"
    "\n{"
    "\n  \"RPC\": {"
    "\n    \"studied at\": \"University of Maryland\","
    "\n  }"
    "\n}"
    "\n---"
    "\n{"
    "\n  \"Tom Currier\": {"
    "\n    \"winner of\": \"Thiel Fellowship\""
    "\n  }"
    "\n}"
    "\n}"
    "\n---"
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
    "Each provided block of information will be separated by the character sequence \"---\"\n"
    "Merge the provided JSON objects so that each entity has only one JSON object with properties for all deduplicated relationships."
    "Remove any entity objects that do not have any relationship properties. Make sure the final result is valid JSON."
    "\n\n"
    "Input: \n" + SAMPLE_MERGE_INPUT + "\n\n"
    "Output: \n" + SAMPLE_MERGE_OUTPUT + "\n\n"
)
MERGE_SYSTEM_MESSAGE = {"role": "system", "content": MERGE_SYSTEM_MESSAGE_CONTENT}


async def async_fetch_merge(text:str, model="gpt-3.5-turbo", skip_on_error=False, should_retry=True):
    '''
    Retrieve merge response from GPT for given block of text.
    '''
    messages = [
        MERGE_SYSTEM_MESSAGE
    ]

    messages.append(
        {"role": "user", "content": text}
    )

    max_tokens = 2000 if model == 'gpt-4' else 1200

    return await async_fetch_from_openai(
        messages,
        log_label='Merge',
        model=model,
        max_tokens=max_tokens,
        skip_on_error=skip_on_error, 
        should_retry=should_retry
    )
