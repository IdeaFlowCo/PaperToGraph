from datetime import datetime
import os


def log_msg(msg:str):
    '''
    Log provided message in a standardized way.
    '''
    ts = datetime.now().isoformat(timespec='seconds')
    print(f'[{ts}] {msg}')


def add_neo_credential_override_args(parser):
    parser.add_argument(
        '--neo_uri', help="The URI for the Neo4j instance to save loaded data to.")
    parser.add_argument(
        '--neo_user', help='The username to use when connecting to the Neo4j database')
    parser.add_argument(
        '--neo_pass', help='The password to use when connecting to the Neo4j database')


def neo_config_from_args_or_env(args):
    uri_override = args.neo_uri if args.neo_uri is not None else os.environ.get('NEO_URI')
    user_override = args.neo_user if args.neo_user is not None else os.environ.get('NEO_USER')
    pass_override = args.neo_pass if args.neo_pass is not None else os.environ.get('NEO_PASS')
    neo_credentials = {
        'uri': uri_override,
        'user': user_override,
        'password': pass_override
    }
    # Ignore any override values that are None or empty strings
    neo_credentials = {k: v for k, v in neo_credentials.items() if v}
    return neo_credentials


def sanitize_gpt_model_choice(model):
    if model not in ['gpt-3.5-turbo', 'gpt-4']:
        model = 'gpt-3.5-turbo'
    return model
