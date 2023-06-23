from datetime import datetime
import logging
import os
import sys
import threading


BATCH_PARSE_THREAD_NAME = 'p2g-batch-parse'
BATCH_SAVE_THREAD_NAME = 'p2g-batch-save'
BATCH_THREAD_NAMES = {BATCH_PARSE_THREAD_NAME, BATCH_SAVE_THREAD_NAME}

def get_logger():
    if threading.current_thread().name in BATCH_THREAD_NAMES:
        logger_name = threading.current_thread().name
    else:
        logger_name = 'paper2graph'
    return logging.getLogger(logger_name)


def log_msg(msg:str, level=logging.INFO):
    '''
    Log provided message in a standardized way.
    '''
    return get_logger().log(level, msg)


def log_debug(msg:str):
    return log_msg(msg, level=logging.DEBUG)


def setup_logger(name=None, log_file=None, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter('[%(asctime)s][%(name)s][%(levelname)s] %(message)s')

    if len(logger.handlers) > 0:
        # Logger already exists/has handlers, so don't add any more
        # We'll still run setup_log_file to clear the log file if necessary
        if log_file:
            setup_log_file(log_file)
        return logger

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    if log_file:
        setup_log_file(log_file)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False

    return logger


def setup_log_file(log_file):
    # Make intermediate directories if necessary
    if os.path.dirname(log_file):
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    # Clear any previous log contents
    open(log_file, 'w').close()


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
    if model not in ['gpt-3.5-turbo', 'gpt-3.5-turbo-16k', 'gpt-4']:
        model = 'gpt-3.5-turbo'
    return model
