import logging
import os
import sys
import threading

BATCH_PARSE_THREAD_NAME = 'p2g-batch-parse'
BATCH_SAVE_THREAD_NAME = 'p2g-batch-save'
BATCH_THREAD_NAMES = {BATCH_PARSE_THREAD_NAME, BATCH_SAVE_THREAD_NAME}

ENT_TYPES_THREAD_NAME = 'p2g-ent-types'
REL_TYPES_THREAD_NAME = 'p2g-rel-types'
GRAPH_SOURCES_THREAD_NAME = 'p2g-graph-sources'
SCRIPT_THREAD_NAMES = {ENT_TYPES_THREAD_NAME, REL_TYPES_THREAD_NAME, GRAPH_SOURCES_THREAD_NAME}


def get_logger():
    thread_name = threading.current_thread().name
    if thread_name in BATCH_THREAD_NAMES or thread_name in SCRIPT_THREAD_NAMES:
        logger_name = thread_name
    else:
        logger_name = 'paper2graph'
    return logging.getLogger(logger_name)


def log_msg(msg: str, level=logging.INFO):
    '''
    Log provided message in a standardized way.
    '''
    return get_logger().log(level, msg)


def log_debug(msg: str):
    return log_msg(msg, level=logging.DEBUG)


def log_warn(msg: str):
    return log_msg(msg, level=logging.WARNING)


def log_error(msg: str):
    return log_msg(msg, level=logging.ERROR)


def setup_logger(name=None, log_file=None, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')

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

    if level == logging.DEBUG:
        # Quiet down OpenAI logging
        logging.getLogger('openai').setLevel(logging.INFO)

    # Quiet chatty request logging from elasticsearch library
    # logging.getLogger('elastic_transport.transport').setLevel(logging.WARNING)

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
