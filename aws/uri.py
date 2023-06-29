import os
from urllib.parse import urlparse, parse_qs


# We're using console URLs because our buckets aren't configured for general HTTP access.
S3_URL_NETLOC = 's3.console.aws.amazon.com'


def parse_s3_uri(uri):
    '''
    Given a valid S3 URI of any form, returns the bucket and item key. Returns (None, None) otherwise.
    '''
    parsed = urlparse(uri)
    if parsed.scheme == 's3':
        # S3 URIs are straightforward, taking the form s3://bucket/key
        # The key might be a full path like s3://bucket/some/long/path/to/item but that doesn't matter here.
        return parsed.netloc, parsed.path.lstrip('/')
    elif parsed.scheme == 'https':
        # HTTPS URLs will either be in the form
        # https://s3.console.aws.amazon.com/s3/buckets/{bucket}?prefix={prefix}
        # or
        # https://s3.console.aws.amazon.com/s3/object/{bucket}?prefix={prefix}
        # with (optional) additional query parameters.

        # First, check that the URL is for the S3 console. If not, we don't consider it a valid S3 URI.
        if parsed.netloc != S3_URL_NETLOC:
            return None, None

        # The bucket name is always the last part of the URL path
        bucket = os.path.basename(parsed.path)

        # Parse query string to separate arguments into dict
        query_params = parse_qs(parsed.query)
        # Because query params are always parsed to lists, need to specifically get first element
        key = query_params.get('prefix', [''])[0]

        return bucket, key
    else:
        # S3 URIs must use either the S3 scheme or HTTPS.
        # If neither, URI is invalid
        return None, None


def s3_uri_to_http(uri):
    '''
    Given a valid S3 URI of any form, returns the HTTPS URL for the same object. Returns None otherwise.
    '''
    bucket, key = parse_s3_uri(uri)

    if not bucket:
        return None

    return f'https://{S3_URL_NETLOC}/buckets/{bucket}?prefix={key}'


def http_to_s3_uri(url):
    '''
    Given a valid S3 URI of any form, returns the URI in s3:// form for the same object. Returns None otherwise.
    '''
    bucket, key = parse_s3_uri(url)

    if not bucket:
        return None

    return f's3://{bucket}/{key}'


def is_valid_s3_uri(uri):
    bucket, _ = parse_s3_uri(uri)

    return bool(bucket)


def source_uri_to_s3_and_http(uri):
    '''
    Given a URI, return the S3 URI and HTTP URI for the same object.
    '''
    s3_uri = http_to_s3_uri(uri)
    http_uri = s3_uri_to_http(uri)
    return s3_uri, http_uri
