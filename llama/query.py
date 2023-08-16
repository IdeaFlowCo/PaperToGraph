import asyncio
import json
import os
import sys
import time

import boto3


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import log_msg, log_debug


FINE_TUNED_ENDPOINT = 'jumpstart-ftc-meta-textgeneration-llama-2-7b'


def _fetch_response(payload):
    client = boto3.client("sagemaker-runtime", region_name="us-east-1")
    response = client.invoke_endpoint(
        EndpointName=FINE_TUNED_ENDPOINT,
        ContentType="application/json",
        Body=json.dumps(payload),
        CustomAttributes="accept_eula=true",
    )
    response = response["Body"].read().decode("utf8")
    response = json.loads(response)
    return response


def ask_llama(query):
    log_msg(f'Fetching Llama 2 completion for query: {query}')
    payload = {
        "inputs": [query],
        "parameters": {"max_new_tokens": 256, "top_p": 0.9, "temperature": 0.2, "return_full_text": False}
    }
    response = _fetch_response(payload)
    log_debug(response)
    result = response[0]['generation'].split('\n')
    result = result[0] if result[0] else result[1]
    return result


async def aask_llama(query):
    query_st = time.time()
    result = await asyncio.to_thread(lambda: ask_llama(query))
    query_et = time.time()
    log_msg(f'search_docs call completed in {(query_et - query_st):.2f} seconds')
    return {'answer': result}


def _cli_demo():
    payloads = [
        # {
        #     "inputs": ['What is Hypophosphatasia?'],
        #     "parameters": {"max_new_tokens": 256, "top_p": 0.9, "temperature": 0.2, "return_full_text": False, 'stop_sequence': '\n'}
        # },
        # {
        #     "inputs": ['What is Ehlers-Danlos Syndrome?'],
        #     "parameters": {"max_new_tokens": 256, "top_p": 0.9, "temperature": 0.2, "return_full_text": False, 'stop_sequence': ['\n']}
        # },
        # {
        #     "inputs": ['What is TNXB EDS?'],
        #     "parameters": {"max_new_tokens": 256, "top_p": 0.9, "temperature": 0.2, "return_full_text": False, 'stop_sequence': ['\n']}
        # },
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
        query_response = _fetch_response(payload)
        print(payload["inputs"])
        response = query_response[0]['generation']  # .split('\n')[1]
        print(f"> {response}")
        print("\n==================================\n")


if __name__ == '__main__':
    _cli_demo()
