'''
Utilities for accesing AWS services.
'''
from datetime import datetime
import os
from urllib.parse import urlparse

import boto3


def check_for_aws_env_vars():
    '''
    Check for AWS credentials in the environment and print a warning if they are not found.
    '''
    aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    if not aws_access_key_id or not aws_secret_access_key:
        print(
            'WARNING: AWS credentials not found in environment! Batch job code assumes '
            'AWS_SECRET_KEY_ID and AWS_SECRET_ACCESS_KEY are set in order to work. '
        )

def parse_s3_uri(uri):
    '''
    Given an S3 URI, return the bucket and path or (None, None) otherwise.
    '''
    parsed = urlparse(uri)
    if parsed.scheme != 's3':
        return None, None
    return parsed.netloc, parsed.path.lstrip('/')


def get_objects_at_s3_uri(uri):
    '''
    Given an S3 URI, return a list of objects at that location.
    '''
    bucket_name, path = parse_s3_uri(uri)
    if not bucket_name:
        raise Exception(f'Invalid S3 URI: {uri}')
    s3_client = boto3.client('s3')
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=path, Delimiter='/')
    
    # if 'Contents' not in response and 'CommonPrefixes' not in response:
        # raise Exception('No objects found at {uri}')

    contents = response.get('Contents', [])
    # Filter out directories and empty files
    contents = [obj for obj in contents if obj.get('Size', 0) > 0]
    objects = [f's3://{bucket_name}/{obj["Key"]}' for obj in contents]

    if 'CommonPrefixes' in response:
        # This is a directory with subdirectories
        # Grab all the objects in the subdirectories and return those too
        subdirectories = response['CommonPrefixes']
        for subdir in subdirectories:
            subdir_uri = f's3://{bucket_name}/{subdir["Prefix"]}'
            objects.extend(get_objects_at_s3_uri(subdir_uri))
    
    return objects


def read_file_from_s3(uri):
    '''
    Read a file from S3 and return its contents.
    '''
    bucket, path = parse_s3_uri(uri)
    file_name = os.path.basename(path)

    s3_client = boto3.client('s3')
    response = s3_client.get_object(Bucket=bucket, Key=path)
    file_data = response['Body'].read().decode('utf-8')

    return file_name, file_data


def create_timestamped_output_dir(output_uri):
    '''
    Create a subdirectory for output of this job at the given path and return the key for the new subdirectory.
    '''
    bucket, path = parse_s3_uri(output_uri)
    s3_client = boto3.client('s3')
    output_path = f'{path}/{datetime.now().timestamp()}-output/'.lstrip('/')
    response = s3_client.put_object(Bucket=bucket, Key=output_path)
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return f's3://{bucket}/{output_path}'
    else:
        raise Exception(f'Error creating output subdirectory at {output_path}', response)


def create_output_dir_for_file(output_uri, file_name):
    '''
    Create a subdirectory for output of a specific file and return the key for the new subdirectory.
    '''
    bucket, output_path = parse_s3_uri(output_uri)
    s3_client = boto3.client('s3')
    output_path = f'{output_path.strip("/")}/{file_name.strip("/")}/'
    response = s3_client.put_object(Bucket=bucket, Key=output_path)
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return f's3://{bucket}/{output_path}'
    else:
        raise Exception(f'Error creating output subdirectory at {output_path}', response)


def write_file_to_s3(output_uri, data):
    '''
    Write a file to S3.
    '''
    bucket, key = parse_s3_uri(output_uri)
    s3_client = boto3.client('s3')
    response = s3_client.put_object(Bucket=bucket, Key=key, Body=data)
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        raise Exception(f'Error writing file to {key}', response)
