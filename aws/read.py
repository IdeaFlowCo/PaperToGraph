'''
Utilities for accesing AWS services.
'''
import os

from utils import log_msg

from .common import get_s3_client
from .uri import parse_s3_uri


def get_objects_at_s3_uri(uri):
    '''
    Given an S3 URI, return a list of objects at that location.
    '''
    bucket_name, path = parse_s3_uri(uri)
    if not bucket_name:
        raise Exception(f'Invalid S3 URI: {uri}')
    s3_client = get_s3_client()
    response = s3_client.list_objects_v2(
        Bucket=bucket_name, Prefix=path, Delimiter='/')

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
    s3_client = get_s3_client()
    response = s3_client.list_objects_v2(
        Bucket=bucket_name, Prefix=path, Delimiter='/')

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

    s3_client = get_s3_client()
    response = s3_client.get_object(Bucket=bucket, Key=path)
    file_data = response['Body'].read().decode('utf-8')

    return file_name, file_data
