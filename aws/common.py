import os

import boto3

import utils
from utils import log_error


def check_for_env_vars(throw_if_missing=True):
    '''
    Check for AWS credentials in the environment and print a warning if they are not found.
    '''
    aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    if not aws_access_key_id or not aws_secret_access_key:
        log_error(
            'AWS credentials not found in environment! Various code assumes '
            'AWS_SECRET_KEY_ID and AWS_SECRET_ACCESS_KEY are set in order to work. '
        )
        if throw_if_missing:
            raise Exception('AWS credentials not found in environment!')


def get_s3_client(cl_args=None):
    '''
    Create an S3 client, optionally using credential overrides from the commandline.
    '''
    config = utils.load_config(cl_args=cl_args)['aws']
    if config.get('aws_use_iam_role'):
        return boto3.client('s3')

    aws_access_key_id = config.get('aws_access_key_id')
    aws_secret_access_key = config.get('aws_secret_access_key')
    if not aws_access_key_id or not aws_secret_access_key:
        log_error(
            'AWS credentials not found! '
            'AWS_SECRET_KEY_ID and AWS_SECRET_ACCESS_KEY must be provided in environment.'
        )
        raise Exception('AWS credentials not found')

    return boto3.client('s3', **config)


def get_sagemaker_client(cl_args=None):
    '''
    Create an S3 client, optionally using credential overrides from the commandline.
    '''
    config = utils.load_config(cl_args=cl_args)['aws']
    if config.get('aws_use_iam_role'):
        return boto3.client('sagemaker-runtime', region_name='us-east-1')

    aws_access_key_id = config.get('aws_access_key_id')
    aws_secret_access_key = config.get('aws_secret_access_key')
    if not aws_access_key_id or not aws_secret_access_key:
        log_error(
            'AWS credentials not found! '
            'AWS_SECRET_KEY_ID and AWS_SECRET_ACCESS_KEY must be provided in environment.'
        )
        raise Exception('AWS credentials not found')

    return boto3.client('sagemaker-runtime', region_name='us-east-1', **config)
