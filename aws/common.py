import os

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
