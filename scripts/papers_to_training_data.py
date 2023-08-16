import argparse
import asyncio
import logging
import multiprocessing
import os
import queue
import signal
import sys
import threading
import xml.etree.ElementTree as ET

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gpt


def _prep_output_file(out_file):
    # Make intermediate directories if necessary
    if os.path.dirname(out_file):
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
    # Clear any previous log contents
    open(out_file, 'w').close()


def _configure_logger(log_level=logging.INFO, log_file=None):
    log_format = '[%(asctime)s] [%(name)s] [%(processName)s] [%(levelname)s] %(message)s'
    logging.basicConfig(format=log_format, level=log_level)

    # Quiet down OpenAI logging
    logging.getLogger('openai').setLevel(logging.INFO)

    if log_file:
        _prep_output_file(log_file)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)

    logging.info('Logger initialized.')


def _make_logger_thread(logger_queue):
    def thread_target():
        while True:
            record = logger_queue.get()
            if record is None:
                break
            logger = logging.getLogger(record.name)
            logger.handle(record)

    return threading.Thread(target=thread_target)


def _make_output_thread(output_file, output_queue):
    def thread_target():
        with open(output_file, 'a') as f:
            while True:
                try:
                    data = output_queue.get(timeout=5)
                    if data is None:
                        break
                    if not data.endswith('\n'):
                        data += '\n'
                    f.write(data)
                except queue.Empty:
                    # Opportunistically flush the file when there's no data queued
                    logging.debug('Output queue empty, flushing file to disk before continuing...')
                    f.flush()

    return threading.Thread(target=thread_target)


def _find_files_to_process(file_paths):
    to_process = []
    for path in file_paths:
        if os.path.isdir(path):
            logging.info(
                f'Finding all files in directory {path} to be processed...')
            dir_files = []
            for root, _, files in os.walk(path):
                for file in files:
                    dir_files.append(os.path.join(root, file))
            logging.debug(f'{len(dir_files)} files found: {dir_files}')
            to_process.extend(dir_files)
        else:
            to_process.append(path)

    logging.info(f'{len(to_process)} files found for extraction.')
    return to_process


def _configure_worker_logger(logger_queue=None, log_level=logging.INFO):
    if not logger_queue:
        raise Exception(
            'Must provide a Queue to route worker logs through.')

    # Clear any inherited log handlers so all logging will go through queue
    logging.getLogger().handlers.clear()

    from logging.handlers import QueueHandler
    log_handler = QueueHandler(logger_queue)
    logging.getLogger().addHandler(log_handler)

    logging.getLogger().setLevel(log_level)

    logging.info('Worker logger initialized.')


def _extract_text_from_el(element):
    if element.text:
        text_list = [element.text]
    else:
        text_list = []

    for child in element:
        # Skip tables
        if child.tag == 'table-wrap' or child.tag == 'table':
            continue
        text_list.append(_extract_text_from_el(child))
        if child.tail:
            text_list.append(child.tail)

    return ''.join(text_list)


def _proccess_file(
        file_path,
        gpt_model='gpt-3.5-turbo',
        abstracts_only=False,
        extract_text_only=False,
        limit_tokens=False,
        **kwargs):
    tree = ET.parse(file_path)
    root = tree.getroot()

    abstract = root.find('.//abstract')
    if abstract:
        a_text = [_extract_text_from_el(p) for p in abstract.findall('.//p')]
    else:
        logging.warning(f'No <abstract> tag found in file {file_path}')
        a_text = []

    body = root.find('.//body')
    if body:
        b_text = [_extract_text_from_el(p) for p in body.findall('.//p')]
    else:
        logging.warning(f'No <body> tag found in file {file_path}')
        b_text = []

    if abstracts_only:
        paragraphs = a_text
    else:
        paragraphs = [*a_text, *b_text]

    if extract_text_only:
        yield f'### {file_path}\n'
        yield from paragraphs
        yield '###\n\n'
        return

    if limit_tokens:
        input_token_limit = 512
        output_token_limit = 2560
    else:
        input_token_limit = None
        output_token_limit = None

    yield from gpt.data_prep.fetch_training_data_for_text(
        paragraphs,
        model=gpt_model,
        input_token_limit=input_token_limit,
        output_token_limit=output_token_limit,
    )


def _process_files(
        files=[],
        output_queue=None,
        **kwargs):
    logging.info(f'Processing {len(files)} files...')
    for i, f in enumerate(files):
        logging.info(f'Processing file {i+1}/{len(files)}: {f}')
        try:
            for data_chunk in _proccess_file(f, **kwargs):
                output_queue.put(data_chunk)
        except Exception as e:
            logging.error(f'Error processing file {f}: {e}')
            continue


def _make_worker(work_args={}, logger_args={}):
    def process_target():
        _configure_worker_logger(**logger_args)
        _process_files(**work_args)

    return multiprocessing.Process(target=process_target)


# Handle keyboard interrupts (ctrl+C from console); without this, workers will not be terminated
def _handle_keyboard_interrupt(*args):
    # Get the current process ID
    current_process_id = os.getpid()

    # Terminate all child processes
    for process in multiprocessing.active_children():
        if process.pid != current_process_id:
            process.terminate()

    # Exit the main process (if needed)
    raise SystemExit(f"KeyboardInterrupt (PID: {current_process_id})")


signal.signal(signal.SIGINT, _handle_keyboard_interrupt)


def main(args):
    _configure_logger(args.log_level, args.log_file)
    logger_queue = multiprocessing.Queue()
    logger_thread = _make_logger_thread(logger_queue)
    logger_thread.start()

    files = _find_files_to_process(args.file_paths)

    worker_processes = []
    files_per_worker = len(files) // args.num_workers
    file_segments = [files[i:i + files_per_worker]
                     for i in range(0, len(files), files_per_worker)]

    output_queue = multiprocessing.Queue()
    _prep_output_file(args.output_file)
    output_thread = _make_output_thread(args.output_file, output_queue)
    output_thread.start()

    for segment in file_segments:
        worker = _make_worker(
            work_args={
                'files': segment,
                'abstracts_only': args.abstracts_only,
                'gpt_model': args.gpt_model,
                'extract_text_only': args.extract_text_only,
                'limit_tokens': args.limit_tokens,
                'output_queue': output_queue,
            },
            logger_args={
                'logger_queue': logger_queue,
                'log_level': args.log_level,
            }
        )
        worker_processes.append(worker)
        worker.start()

    for worker in worker_processes:
        worker.join()

    # Tell the output thread to stop
    output_queue.put(None)
    output_thread.join()

    logging.info('All processing across all workers complete.')

    # Tell the logger thread to stop
    logger_queue.put(None)
    logger_thread.join()


def parse_args(args):
    parser = argparse.ArgumentParser(description='Extract article metadata from XML')

    parser.add_argument(
        '--abstracts_only',
        action='store_true',
        default=False,
        help='Only process abstracts from articles, ignoring the body text'
    )
    parser.add_argument(
        '--gpt_model',
        default='gpt-3.5-turbo',
        help='Name of the GPT model to use'
    )
    parser.add_argument(
        '--limit_tokens',
        action='store_true',
        default=False,
        help='Limit the number of across input and output to 3000 (useful for training chunking LLMs)'
    )
    parser.add_argument(
        '--extract_text_only',
        action='store_true',
        default=False,
        help="Only extract text from the XML files, don't process with GPT"
    )
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
    parser.add_argument(
        '--file_paths',
        nargs='+',
        help='File paths to extract metadata from'
    )
    parser.add_argument(
        '--output_file',
        help='Where to write a CSV file of extracted metadata'
    )
    parser.add_argument(
        '--num_workers',
        type=int,
        default=1,
        help='Number of worker processes to use for processing.'
    )

    return parser.parse_args(args)


if __name__ == '__main__':
    # Passing None to parse_args will cue it to parse sys.argv
    args = parse_args(None)
    main(args)
