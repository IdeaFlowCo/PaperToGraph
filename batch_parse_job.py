import argparse
import asyncio

import aws
import parse
from utils import log_msg

from test_text import SAMPLE_LONG_INPUT


GPT_MODEL = 'gpt-3.5-turbo'


async def __load_input(data_source):
    files = aws.get_objects_at_s3_uri(data_source)
    if not files:
      log_msg(f'No files found at {data_source}')
      log_msg('Using hard-coded test input instead')
      return SAMPLE_LONG_INPUT

    log_msg(f'Found {len(files)} files to process')
    log_msg(files)
    log_msg(f'Loading first file: {files[0]}')
    data = aws.read_file_from_s3(files[0])
    log_msg(f'Loaded {len(data)} bytes')
    log_msg(data)
    return data


def __write_output(data, output_uri):
    bucket, path = aws.parse_s3_uri(output_uri)
    output_path = aws.create_output_subdirectory(bucket, path)
    log_msg(f'Created a subdirectory for output of this job at s3://{bucket}/{output_path}')
    for i, datum in enumerate(data):
        key = f'{output_path.rstrip("/")}/output_{i}.json'
        log_msg(f'Writing output to s3://{bucket}/{key}')
        aws.write_file_to_s3(bucket, key, datum)


async def parse_with_gpt(data_source, output_uri):
    input = await __load_input(data_source)
    parsed_data = await parse.parse_with_gpt(input, model=GPT_MODEL)
    __write_output(parsed_data, output_uri)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--data_source',
        default='s3://paper2graph-parse-inputs',
        help="The URI for the text to be parsed, like an S3 bucket location."
    )
    parser.add_argument(
        '--output_uri',
        default='s3://paper2graph-parse-results',
        help="The URI where output is saved, like an S3 bucket location."
    )
    args = parser.parse_args()

    asyncio.run(
        parse_with_gpt(args.data_source, args.output_uri)
    )
