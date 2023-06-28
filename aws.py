'''
Utilities for accesing AWS services.
'''
from datetime import datetime
import os
from urllib.parse import urlparse, parse_qs

import boto3

from utils import log_msg


def check_for_aws_env_vars():
    '''
    Check for AWS credentials in the environment and print a warning if they are not found.
    '''
    aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    if not aws_access_key_id or not aws_secret_access_key:
        print(
            'WARNING: AWS credentials not found in environment! Various code assumes '
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


S3_HTTP_PREFIX = 'https://s3.console.aws.amazon.com/s3/'

def s3_uri_to_http(uri):
     if uri.startswith('s3://'):
         bucket, key = parse_s3_uri(uri)
         return f'{S3_HTTP_PREFIX.rstrip("/")}/buckets/{bucket}?prefix={key}'
     elif uri.startswith(S3_HTTP_PREFIX):
         return uri
     else:
         return None


def http_to_s3_uri(url):
     if url.startswith(S3_HTTP_PREFIX):
        parsed = urlparse(url)
        # URLs will either be in the form
        # https://s3.console.aws.amazon.com/s3/buckets/{bucket}?prefix={prefix}
        # or
        # https://s3.console.aws.amazon.com/s3/object/{bucket}?prefix={prefix}
        # with (optional) additional query parameters.
        # In either case, the bucket name is the last part of the URL path
        bucket = os.path.basename(parsed.path)
        # Parse query string to separate arguments into dict
        query_params = parse_qs(parsed.query)
        # Because query params are always parsed to lists, need to specifically get first element
        key = query_params.get('prefix', [''])[0]
        return f'{S3_HTTP_PREFIX.rstrip("/")}/{bucket}/{key}'
     elif url.startswith('s3://'):
         return url
     else:
         return None


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


def __get_dir_name(path):
    base_path, _ = os.path.split(path)
    return os.path.basename(base_path)


def get_objects_by_folder_at_s3_uri(uri):
    '''
    Given an S3 URI, return a list of objects at that location.
    '''
    bucket_name, path = parse_s3_uri(uri)
    if not bucket_name:
        raise Exception(f'Invalid S3 URI: {uri}')
    s3_client = boto3.client('s3')
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=path, Delimiter='/')

    contents = response.get('Contents', [])
    # Filter out directories and empty files
    contents = [obj for obj in contents if obj.get('Size', 0) > 0]
    objects = {
        '/': [f's3://{bucket_name}/{obj["Key"]}' for obj in contents]
    }

    if 'CommonPrefixes' in response:
        # This is a directory with subdirectories
        # Grab all the objects in the subdirectories and return those too
        subdirectories = response['CommonPrefixes']
        for subdir in subdirectories:
            subdir_path = subdir["Prefix"]
            subdir_name = __get_dir_name(subdir_path)
            subdir_uri = f's3://{bucket_name}/{subdir_path}'
            subdir_objects = get_objects_by_folder_at_s3_uri(subdir_uri)
            objects[subdir_name] = subdir_objects.pop('/')
            while len(subdir_objects) > 0:
                nested_subdir_name, nested_objects = subdir_objects.popitem()
                objects[f'{subdir_name}/{nested_subdir_name}'] = nested_objects
    
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
        log_msg(f'Would have created a subdirectory for job output at s3://{bucket}/{output_path}')
        return f's3://{bucket}/{output_path}'

    log_msg(f'Creating a subdirectory for job output at s3://{bucket}/{output_path}')
    s3_client = boto3.client('s3')
    response = s3_client.put_object(Bucket=bucket, Key=output_path)

    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return f's3://{bucket}/{output_path}'
    else:
        raise Exception(f'Error creating output subdirectory at {output_path}', response)


def create_output_dir_for_file(output_uri, file_name, dry_run=False):
    '''
    Create a subdirectory for output of a specific file and return the key for the new subdirectory.
    '''
    bucket, output_path = parse_s3_uri(output_uri)
    output_path = f'{output_path.strip("/")}/{file_name.strip("/")}/'

    if dry_run:
        log_msg(f'Would have created a subdirectory for parse output of {file_name} at s3://{bucket}/{output_path}')
        return f's3://{bucket}/{output_path}'
    
    log_msg(f'Creating a subdirectory for parse output of {file_name} at s3://{bucket}/{output_path}')
    s3_client = boto3.client('s3')
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
