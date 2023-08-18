import asyncio
import time

from utils import log_msg, log_debug

from .common import fetch_response


def ask_llama(query):
    log_msg(f'Fetching Llama 2 completion for query: {query}')
    payload = {
        "inputs": [query],
        "parameters": {"max_new_tokens": 256, "top_p": 0.9, "temperature": 0.2, "return_full_text": False}
    }
    fetch_st = time.time()
    response = fetch_response(payload)
    fetch_et = time.time()
    log_msg(f'Llama response fetched in {(fetch_et - fetch_st):.2f} seconds')
    log_debug(response)
    result = response[0]['generation'].split('\n')
    result = result[0] if result[0] else result[1]
    return result


async def aask_llama(query):
    # query_st = time.time()
    result = await asyncio.to_thread(lambda: ask_llama(query))
    # query_et = time.time()
    # log_msg(f'ask_llama call completed in {(query_et - query_st):.2f} seconds')
    return {'answer': result}


def _cli_demo():
    payloads = [
        {
            "inputs": ['Is Telomere to Telomere sequencing going to be essential in profiling the full breadth of TNXB disorders?'],
            "parameters": {"max_new_tokens": 256, "top_p": 0.90, "temperature": 0.2, "return_full_text": False, 'stop_sequence': ['\n']}
        },
        {
            "inputs": ['What sequencing technologies are recommended for diagnosing such disorders involving TNXB?'],
            "parameters": {"max_new_tokens": 256, "top_p": 0.90, "temperature": 0.2, "return_full_text": False, 'stop_sequence': ['\n']}
        },
    ]
    for payload in payloads:
        query_response = fetch_response(payload)
        print(payload["inputs"])
        response = query_response[0]['generation']  # .split('\n')[1]
        print(f"> {response}")
        print("\n==================================\n")


if __name__ == '__main__':
    _cli_demo()
