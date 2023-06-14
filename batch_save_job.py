import argparse
import asyncio

import aws
import save
import utils
from utils import log_msg



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


async def __process_file(file_uri, neo_config):
    log_msg(f'Processing file {file_uri}')

    input_file_name, input_data = await __fetch_input_file(file_uri)

    log_msg(f'Saving data from {input_file_name} to Neo4j')
    save.save_json_data(input_data, neo_config=neo_config)
    

async def save_to_neo4j(data_source, neo_config):
    input_files = await __find_input_files(data_source)
    for file_uri in input_files:
        await __process_file(file_uri, neo_config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--data_source',
        default='s3://paper2graph-parse-results',
        help="The URI for the data to be ingested, like an S3 bucket location."
      )
    utils.add_neo_credential_override_args(parser)

    args = parser.parse_args()

    neo_config = utils.neo_config_from_args_or_env(args)
    aws.check_for_aws_env_vars()

    asyncio.run(
        save_to_neo4j(args.data_source, neo_config)
    )
