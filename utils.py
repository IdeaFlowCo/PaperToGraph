from datetime import datetime
import json
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


def clean_json(response):
    cleaned = {}
    try:
        if response.startswith('Output:'):
            # Remove extraneous "Output:" signifier that shows up sometimes.
            response = response[len('Output:'):].strip()
        response_dict = json.loads(response)
        for key, value in response_dict.items():
            # We want to skip the empty values to avoid overloading GPT in subsequent queries.
            if not value:
                continue
            if isinstance(value, dict):
                cleaned_value = {}
                # Sometimes a dict will have a bunch of key => empty dict pairs inside of it for some reason?
                # Trim those too.
                for subkey, subvalue in value.items():
                    if subvalue:
                        cleaned_value[subkey] = subvalue
                # Check that the cleaned up value dict actually has anything in it; if not, skip
                if not cleaned_value:
                    continue
                value = cleaned_value
            else:
                # Sometimes we get really long string pairs that are more trouble than they are informative
                if len(key) + len(value) > 200:
                    continue
            cleaned[key] = value
        cleaned = json.dumps(cleaned, indent=2)
        log_msg(f'Cleaned up response JSON: \n{cleaned}')
        return cleaned
    except json.decoder.JSONDecodeError:
        log_msg('Response not valid JSON!')
        if '{' in response:
            # Response isn't valid JSON but may be close enough that it can still be used, so we'll just return it as-is
            return response
        return None
