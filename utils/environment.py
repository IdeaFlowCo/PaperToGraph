import json
import os

from dotenv import dotenv_values
from .logging import log_msg


def load_config(cl_args=None):
    if cl_args:
        # Convert commandline args to uppercase to match the format of environment variables
        cl_args = {key.upper(): value for key, value in vars(cl_args).items() if value}
    else:
        cl_args = {}

    config_vars = {
        **dotenv_values('.env'),  # Use values from local .env file as base, if available
        **os.environ,  # Override values loaded from file with those set in shell (if any)
        **cl_args,  # Override values from both file and shell with those passed in as commandline args
    }

    # Make sub-dicts with lowercase keys so clients can be made via dict spreading
    logger_config = {
        'log_file': config_vars.pop('LOG_FILE', None),
        'level': config_vars.pop('LOG_LEVEL', 'INFO'),
    }
    config_vars['logger'] = logger_config

    aws_config = {
        'aws_access_key_id': config_vars.pop('AWS_ACCESS_KEY_ID', None),
        'aws_secret_access_key': config_vars.pop('AWS_SECRET_ACCESS_KEY', None),
        'aws_session_token': config_vars.pop('AWS_SESSION_TOKEN', None),
    }
    config_vars['aws'] = aws_config

    neo_config = {
        'uri': config_vars.pop('NEO_URI', None),
        'user': config_vars.pop('NEO_USER', None),
        'password': config_vars.pop('NEO_PASS', None)
    }
    config_vars['neo4j'] = neo_config

    pg_config = {
        'host': config_vars.pop('PG_HOST', None),
        'port': config_vars.pop('PG_PORT', None),
        'user': config_vars.pop('PG_USER', None),
        'password': config_vars.pop('PG_PASS', None),
        'database': config_vars.pop('PG_DATABASE', None),
    }
    config_vars['postgres'] = pg_config

    es_config = {}
    elastic_cloud_id = config_vars.pop('ELASTIC_CLOUD_ID', None)
    elastic_url = config_vars.pop('ELASTIC_URL', None)
    if elastic_cloud_id and elastic_url:
        # If both are set, use the cloud ID
        es_config['cloud_id'] = elastic_cloud_id
    elif elastic_cloud_id:
        es_config['cloud_id'] = elastic_cloud_id
    elif elastic_url:
        es_config['hosts'] = [elastic_url]
    es_config['basic_auth'] = (config_vars.pop('ELASTIC_USER', 'elastic'), config_vars.pop('ELASTIC_PASSWORD', None))
    config_vars['elastic'] = es_config

    return config_vars


def add_neo_credential_override_args(parser):
    parser.add_argument(
        '--neo_uri',
        default=None,
        help='The URI for the Neo4j instance to save loaded data to.'
    )
    parser.add_argument(
        '--neo_user',
        default=None,
        help='The username to use when connecting to the Neo4j database'
    )
    parser.add_argument(
        '--neo_pass',
        default=None,
        help='The password to use when connecting to the Neo4j database'
    )


def add_logger_args(parser):
    parser.add_argument(
        '--log_file',
        default=None,
        help='Mirror logs to a file in addition to stdout'
    )
    parser.add_argument(
        '--log_level',
        default='INFO',
        help='Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)'
    )


def secret_to_log_str(secret):
    return f'{secret[:3]}...{secret[-3:]}'


def log_config_vars(config):
    logger_config = config['logger'].copy()

    aws_config = config['aws'].copy()
    if 'aws_secret_access_key' in aws_config and aws_config['aws_secret_access_key']:
        aws_config['aws_secret_access_key'] = secret_to_log_str(aws_config['aws_secret_access_key'])
    if 'aws_session_token' in aws_config and aws_config['aws_session_token']:
        aws_config['aws_session_token'] = secret_to_log_str(aws_config['aws_session_token'])

    neo_config = config['neo4j'].copy()
    if 'password' in neo_config and neo_config['password']:
        neo_config['password'] = secret_to_log_str(neo_config['password'])

    pg_config = config['postgres'].copy()
    if 'password' in pg_config and pg_config['password']:
        pg_config['password'] = secret_to_log_str(pg_config['password'])

    es_config = config['elastic'].copy()
    if 'basic_auth' in es_config and es_config['basic_auth']:
        es_config['basic_auth'] = (
            es_config['basic_auth'][0],
            secret_to_log_str(es_config['basic_auth'][1])
        )

    configs_to_log = {
        'logger': logger_config,
        'aws': aws_config,
        'neo4j': neo_config,
        'es': es_config,
        'postgres': pg_config,
    }
    configs_to_log = json.dumps(configs_to_log, indent=2)
    log_msg(f'Using the following configuration:\n{configs_to_log}')
