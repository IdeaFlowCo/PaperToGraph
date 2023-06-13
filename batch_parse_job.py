import argparse
import asyncio

import parse

from test_text import SAMPLE_LONG_INPUT


GPT_MODEL = 'gpt-3.5-turbo'


async def __load_input(data_source):
    return SAMPLE_LONG_INPUT


def __write_output(data, output_uri):
    for datum in data:
        print(datum)


async def parse_with_gpt(data_source, output_uri):
    input = await __load_input(data_source)
    parsed_data = await parse.parse_with_gpt(input, model=GPT_MODEL)
    __write_output(parsed_data, output_uri)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--data_source', help="The URI for the text to be parsed, like an S3 bucket location.")
    parser.add_argument(
        '--output_uri', help="The URI where output is saved, like an S3 bucket location.")
    args = parser.parse_args()

    asyncio.run(
        parse_with_gpt(args.data_source, args.output_uri)
    )
