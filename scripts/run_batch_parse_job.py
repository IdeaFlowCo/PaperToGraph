import argparse
import asyncio

from batch import BatchParseJob
import gpt
import utils
from utils import log_msg


def main(args):
    config = utils.environment.load_config(cl_args=args)
    utils.setup_logger(**config['logger'])
    log_msg('Logger initialized')

    gpt.init_module(config)

    parse_job = BatchParseJob(gpt_model=args.gpt_model, dry_run=args.dry_run)

    asyncio.run(
        parse_job.run(args.data_source, args.output_uri)
    )


def parse_args(args):
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
    parser.add_argument(
        '--gpt_model',
        default='gpt-3.5-turbo',
        help="The GPT model to use when parsing."
    )
    parser.add_argument(
        '--dry_run',
        action="store_true",
        default=False,
        help="The URI where output is saved, like an S3 bucket location."
    )

    return parser.parse_args(args)
