import argparse
import asyncio

import aws
import parse
from utils import log_msg

from test_text import SAMPLE_LONG_INPUT


GPT_MODEL = 'gpt-3.5-turbo'


async def __find_input_files(data_source):
    files = aws.get_objects_at_s3_uri(data_source)
    if not files:
      raise Exception(f'No files found at {data_source}')

    log_msg(f'Found {len(files)} files to process')
    log_msg(files)
    return files


async def __fetch_input_file(file_uri):
    log_msg(f'Fetching file {file_uri}')
    file_name, data = aws.read_file_from_s3(file_uri)
    log_msg(f'Loaded {len(data)} bytes')
    return file_name, data


async def __process_file(file_uri, job_output_uri):
    log_msg(f'Processing file {file_uri}')

    input_file_name, input_data = await __fetch_input_file(file_uri)

    file_output_uri = aws.create_output_dir_for_file(job_output_uri, input_file_name)
    log_msg(f'Created a subdirectory for parse output of {input_file_name} at {file_output_uri}')

    log_msg(f'Beginning parse of file: {input_file_name}')
    parsed_data = await parse.parse_with_gpt(input_data, model=GPT_MODEL)

    await __write_output_for_file(parsed_data, file_output_uri)


async def __write_output_for_file(data, file_output_uri):
    if not isinstance(data, list):
        raise Exception(f'Unexpected data type for file output. Expected list, got {type(data)}')

    for i, datum in enumerate(data):
        output_chunk_uri = f'{file_output_uri.rstrip("/")}/output_{i}.json'
        log_msg(f'Writing output chunk {i} of {len(data)} to {output_chunk_uri}')
        aws.write_file_to_s3(output_chunk_uri, datum)


async def parse_with_gpt(data_source, output_uri):
    input_files = await __find_input_files(data_source)
    job_output_uri = aws.create_timestamped_output_dir(output_uri)
    for input_file in input_files:
       await __process_file(input_file, job_output_uri)


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
