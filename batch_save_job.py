import argparse
import asyncio
import json
import os

import aws
import save
import utils
from utils import log_msg


async def __find_input_files(data_source):
    log_msg(f'Finding input files at {data_source}')
    files = aws.get_objects_by_folder_at_s3_uri(data_source)
    if not files:
        raise Exception(f'No files found at {data_source}')

    log_msg(f'Found {len(files)} directories to process')
    log_msg(files)
    return files


async def __fetch_input_file(file_uri):
    log_msg(f'Fetching file {file_uri}')
    file_name, data = aws.read_file_from_s3(file_uri)
    log_msg(f'Loaded {len(data)} bytes')
    return file_name, data


def __source_matches_output(source_uri, output_uri):
    source_basename = os.path.basename(source_uri)
    output_basename = os.path.basename(output_uri)
    return source_basename == output_basename.rstrip('.json') + '.source.txt'


async def __process_folder(folder_files, neo_config):
    parse_output_uris = list(filter(lambda uri: uri.endswith('.json'), folder_files))
    source_text_uris = list(filter(lambda uri: uri.endswith('source.txt'), folder_files))

    if len(source_text_uris) == 0:
        log_msg(f'No source text files found for output folder. Will default to output chunk URIs being saved as entity/relationship sources.')
        for file_uri in folder_files:
            await __process_file(file_uri, neo_config, source_text_uri=source_text_uri)
    elif len(source_text_uris) == 1:
        source_text_uri = source_text_uris[0]
        log_msg(
            f'Found single source text file {source_text_uri} for output folder. Using as input source for all chunks here.')
        folder_files.remove(source_text_uri)
        for file_uri in folder_files:
            await __process_file(file_uri, neo_config, source_text_uri=source_text_uri)
    else:
        log_msg(f'Found multiple source text files for output folder. Assuming one source text for each parse chunk + one master file for folder.')
        master_source_uri = list(filter(lambda uri: os.path.basename(uri) == 'source.txt', folder_files))[0]
        source_text_uris.remove(master_source_uri)
        for output_uri in parse_output_uris:
            source_candidates = list(filter(lambda uri: __source_matches_output(uri, output_uri), source_text_uris))
            source_uri = source_candidates[0] if len(source_candidates) == 1 else master_source_uri
            await __process_file(output_uri, neo_config, source_text_uri=source_uri)


async def __process_file(file_uri, neo_config, source_text_uri=None):
    log_msg(f'Processing file {file_uri}')

    try:
        input_file_name, input_data = await __fetch_input_file(file_uri)
    except Exception as err:
        log_msg(f'Exception raised when fetching input file. Swallowing to proceed with rest of job.')
        log_msg(f'Exception: {err}')
        return

    try:
        json.loads(input_data)
    except json.decoder.JSONDecodeError:
        log_msg(f'File contents at {file_uri} not valid JSON. Skipping.')
        return

    log_msg(f'Saving data from {input_file_name} to Neo4j')
    input_uri = source_text_uri if source_text_uri else file_uri
    log_msg(f'Specifying input source as {input_uri}')
    try:
        save.save_json_data(input_data, source_uri=input_uri, neo_config=neo_config)
    except Exception as err:
        log_msg('Exception raised when saving data. Swallowing to proceed with rest of job.')
        log_msg(f'Exception: {err}')


async def save_to_neo4j(data_source, neo_config):
    log_msg(f'Running batch save job for {data_source}')
    input_files_by_folder = await __find_input_files(data_source)
    for folder_key in input_files_by_folder:
        folder_files = input_files_by_folder[folder_key]
        log_msg(f'Processing {len(folder_files)} files from folder {folder_key}')
        await __process_folder(folder_files, neo_config)


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
