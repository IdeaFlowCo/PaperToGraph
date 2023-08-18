import argparse
import csv
import logging
import multiprocessing
import os
import signal
import threading
import xml.etree.ElementTree as ET


def _prep_output_file(out_file):
    # Make intermediate directories if necessary
    if os.path.dirname(out_file):
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
    # Clear any previous log contents
    open(out_file, 'w').close()


def _configure_logger(log_level=logging.INFO, log_file=None):
    log_format = '[%(asctime)s] [%(name)s] [%(processName)s] [%(levelname)s] %(message)s'
    logging.basicConfig(format=log_format, level=log_level)

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
        with open(output_file, 'w') as f:
            # Make sure any changes here are matched in _process_files and vice versa
            fieldnames = ['path', 'pmc_id', 'article_type', 'article_title', 'doi']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            while True:
                metadata_dict = output_queue.get()
                if metadata_dict is None:
                    break
                writer.writerow(metadata_dict)

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


def _extract_metadata_from_file(file_path):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        if root.tag == 'article':
            article = root
        else:
            article = root.find('article')

        article_type = article.attrib['article-type']

        article_ids_by_type = {}
        for article_id_tag in article.findall(".//article-id"):
            pub_id_type = article_id_tag.get("pub-id-type")
            article_id = article_id_tag.text
            article_ids_by_type[pub_id_type] = article_id

        title = article.find('.//article-title').text

        return {
            'file_path': file_path,
            'article_type': article_type,
            'article_ids': article_ids_by_type,
            'title': title,
        }
    except Exception as e:
        logging.error(f'Error extracting metadata for file {file_path}: {e}')
        return None


def _process_files(files=[], output_queue=None):
    logging.info(f'Processing {len(files)} files...')
    for i, f in enumerate(files):
        metadata = _extract_metadata_from_file(f)
        if metadata:
            # Unpack extracted info
            file_path = metadata['file_path']
            title = metadata['title']
            article_type = metadata['article_type']
            article_ids = metadata['article_ids']
            pmc_id = article_ids.get('pmc', '')
            doi = article_ids.get('doi', '')

            # Make sure any changes here are matched in _make_output_thread and vice versa
            output = {
                'path': file_path,
                'pmc_id': pmc_id,
                'article_type': article_type,
                'article_title': title,
                'doi': doi
            }
            output_queue.put(output)

        if i % 500 == 0:
            logging.info(
                f'{i} files processed so far ({i/len(files):.2f}%)...')

    logging.info('Worker done processing files.')


def _make_extract_worker(extract_args={}, logger_args={}):
    def process_target():
        _configure_worker_logger(**logger_args)
        _process_files(**extract_args)

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

    xml_files = _find_files_to_process(args.file_paths)

    worker_processes = []
    files_per_worker = len(xml_files) // args.num_workers
    file_segments = [xml_files[i:i + files_per_worker]
                     for i in range(0, len(xml_files), files_per_worker)]

    output_queue = multiprocessing.Queue()
    _prep_output_file(args.output_file)
    output_thread = _make_output_thread(args.output_file, output_queue)
    output_thread.start()

    for segment in file_segments:
        worker = _make_extract_worker(
            extract_args={
                'files': segment,
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

    logging.info('All extraction across all workers complete.')

    # Tell the logger thread to stop
    logger_queue.put(None)
    logger_thread.join()


def parse_args(args):
    parser = argparse.ArgumentParser(description='Extract article metadata from XML')

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
