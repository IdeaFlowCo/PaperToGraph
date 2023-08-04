import argparse
import asyncio

import aws
import batch
import utils


def main(args):
    config = utils.environment.load_config(cl_args=args)
    utils.setup_logger(**config['logger'])
    utils.log_msg('Logger initialized')

    asyncio.run(
        batch.save_to_neo4j(args.data_source, config['neo4j'])
    )


def parse_args(args):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--data_source',
        default='s3://paper2graph-parse-results',
        help="The URI for the data to be ingested, like an S3 bucket location."
    )
    utils.add_neo_credential_override_args(parser)

    return parser.parse_args(args)
