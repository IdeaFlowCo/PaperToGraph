import os


def get_neo_config_from_env():
    neo_credentials = {
        'uri': os.environ.get('NEO_URI'),
        'user': os.environ.get('NEO_USER'),
        'password': os.environ.get('NEO_PASS')
    }
    # Ignore any override values that are None or empty strings
    neo_credentials = {k: v for k, v in neo_credentials.items() if v}
    return neo_credentials


def add_neo_credential_override_args(parser):
    parser.add_argument(
        '--neo_uri', help="The URI for the Neo4j instance to save loaded data to.")
    parser.add_argument(
        '--neo_user', help='The username to use when connecting to the Neo4j database')
    parser.add_argument(
        '--neo_pass', help='The password to use when connecting to the Neo4j database')


def neo_config_from_args_or_env(args):
    uri_override = args.neo_uri if args.neo_uri is not None else os.environ.get(
        'NEO_URI')
    user_override = args.neo_user if args.neo_user is not None else os.environ.get(
        'NEO_USER')
    pass_override = args.neo_pass if args.neo_pass is not None else os.environ.get(
        'NEO_PASS')
    neo_credentials = {
        'uri': uri_override,
        'user': user_override,
        'password': pass_override
    }
    # Ignore any override values that are None or empty strings
    neo_credentials = {k: v for k, v in neo_credentials.items() if v}
    return neo_credentials
