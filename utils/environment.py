import os

from dotenv import dotenv_values
from quart import Quart


def load_config(cl_args=None):
    if cl_args:
        # Convert commandline args to uppercase to match the format of environment variables
        cl_args = {key.upper(): value for key, value in vars(cl_args).items()}
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


def configure_app(app: Quart, cl_args=None):
    config = load_config(cl_args=cl_args)
    app.config.update(config)


def add_neo_credential_override_args(parser):
    parser.add_argument(
        '--neo_uri', help="The URI for the Neo4j instance to save loaded data to.")
    parser.add_argument(
        '--neo_user', help='The username to use when connecting to the Neo4j database')
    parser.add_argument(
        '--neo_pass', help='The password to use when connecting to the Neo4j database')
