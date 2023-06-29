import os
from urllib.parse import urlparse, parse_qs


S3_HTTP_PREFIX = 'https://s3.console.aws.amazon.com/s3/'


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


def is_valid_source_uri(uri):
    '''
    Return True if the given URI is a valid source URI.
    '''
    return uri.startswith('s3://') or uri.startswith(S3_HTTP_PREFIX)


def source_uri_to_s3_and_http(uri):
    '''
    Given a URI, return the S3 URI and HTTP URI for the same object.
    '''
    s3_uri = http_to_s3_uri(uri)
    http_uri = s3_uri_to_http(uri)
    return s3_uri, http_uri
