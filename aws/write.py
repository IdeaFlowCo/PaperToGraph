'''
Utilities for accesing AWS services.
'''
from datetime import datetime
import os

import boto3

from utils import log_msg

from .uri import parse_s3_uri


def create_output_dir_for_job(data_source, output_uri, dry_run=False):
    '''
    Create a subdirectory for output of this job at the given path and return the key for the new subdirectory.
    '''
    bucket, output_uri_path = parse_s3_uri(output_uri)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    _, inputpath = parse_s3_uri(data_source)
    dir_name, base_name = os.path.split(inputpath)
    # If our data source is a directory, base_name will be empty and we need to split again to get the directory name
    input_dir_name = base_name if base_name else os.path.basename(dir_name)

    # Assemble the full path for the output directory we're creating
    output_path = f'{output_uri_path}/{timestamp}-{input_dir_name}-output/'
    # If output_uri_path is empty (writing to bucket base), we need to trim the leading slash
    output_path = output_path.lstrip('/')

    if dry_run:
        log_msg(
            f'Would have created a subdirectory for job output at s3://{bucket}/{output_path}')
        return f's3://{bucket}/{output_path}'

    log_msg(
        f'Creating a subdirectory for job output at s3://{bucket}/{output_path}')
    s3_client = boto3.client('s3')
    response = s3_client.put_object(Bucket=bucket, Key=output_path)

    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return f's3://{bucket}/{output_path}'
    else:
        raise Exception(
            f'Error creating output subdirectory at {output_path}', response)


def create_output_dir_for_file(output_uri, file_name, dry_run=False):
    '''
    Create a subdirectory for output of a specific file and return the key for the new subdirectory.
    '''
    bucket, output_path = parse_s3_uri(output_uri)
    output_path = f'{output_path.strip("/")}/{file_name.strip("/")}/'

    if dry_run:
        log_msg(
            f'Would have created a subdirectory for parse output of {file_name} at s3://{bucket}/{output_path}')
        return f's3://{bucket}/{output_path}'

    log_msg(
        f'Creating a subdirectory for parse output of {file_name} at s3://{bucket}/{output_path}')
    s3_client = boto3.client('s3')
    response = s3_client.put_object(Bucket=bucket, Key=output_path)

    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return f's3://{bucket}/{output_path}'
    else:
        raise Exception(
            f'Error creating output subdirectory at {output_path}', response)


def write_to_s3_file(output_uri, data):
    '''
    Write data to a file in S3.
    '''
    bucket, key = parse_s3_uri(output_uri)
    s3_client = boto3.client('s3')
    response = s3_client.put_object(Bucket=bucket, Key=key, Body=data)
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        raise Exception(f'Error writing file to {key}', response)


def upload_to_s3(output_uri, file_path):
    '''
    Upload a file to S3.
    '''
    bucket, key = parse_s3_uri(output_uri)
    s3_client = boto3.client('s3')
    s3_client.upload_file(file_path, bucket, key)


def create_new_batch_set_dir(base_dir_uri):
    bucket, base_dir_path = parse_s3_uri(base_dir_uri)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    # Assemble the full path for the output directory we're creating
    output_path = f'{base_dir_path}/{timestamp}-web-search-upload/'
    # If base_dir_path is empty (making new dir at bucket base), we'll have a leading slash we need to trim
    output_path = output_path.lstrip('/')

    log_msg(
        f'Creating a subdirectory for job output at s3://{bucket}/{output_path}')
    s3_client = boto3.client('s3')
    response = s3_client.put_object(Bucket=bucket, Key=output_path)

    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return f's3://{bucket}/{output_path}'
    else:
        raise Exception(
            f'Error creating output subdirectory at {output_path}', response)
