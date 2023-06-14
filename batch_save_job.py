import argparse
import asyncio
import json

import aws
import save
import utils
from utils import log_msg



TEST_INPUT = '''
[
  {
    "Trifluoperazine": {
      "may treat": "Wilms' Tumor",
      "antagonizes": "CALM1"
    },
    "CALM1": {
      "regulated by": "Trifluoperazine",
      "regulates": "IL-6"
    },
    "IL-6": {
      "associated with": "Wilms' Tumor",
      "regulated by": "CALM1"
    }
  }
]
'''


async def __load_input(data_source):
    files = aws.get_objects_at_s3_uri(data_source)
    if not files:
      log_msg(f'No files found at {data_source}')
      log_msg('Using hard-coded test input instead')
      return TEST_INPUT

    log_msg(f'Found {len(files)} files to process')
    log_msg(files)
    log_msg(f'Loading first file: {files[0]}')
    data = aws.read_file_from_s3(files[0])
    log_msg(f'Loaded {len(data)} bytes')
    log_msg(data)
    return data
    


async def save_to_neo4j(data_source, neo_config):
    data = await __load_input(data_source)
    save.save_json_data(data, neo_config=neo_config)


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
