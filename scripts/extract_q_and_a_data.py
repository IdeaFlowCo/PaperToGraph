import argparse
import ast
import json
import logging
import os


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


def main(args):
    _configure_logger(args.log_level, args.log_file)

    files = _find_files_to_process(args.file_paths)

    _prep_output_file(args.output_file)

    with open(args.output_file, 'w') as output_file:
        for f in files:
            logging.info(f'Processing file {f}...')
            with open(f, 'r') as input_file:
                for line in input_file:
                    try:
                        data = json.loads(line)
                        if not 'training_data' in data:
                            logging.warning(f'Line parsed as JSON but "training_data" key not found: {line}')
                            continue
                        td = data['training_data'].split('\n')
                        td = [ast.literal_eval(x) for x in td]
                        td = [t for t in td if isinstance(t, tuple)]
                        td = [{'prompt': t[0], 'completion': t[1]} for t in td]
                        for data_dict in td:
                            output_file.write(json.dumps(data_dict) + '\n')
                    except json.JSONDecodeError:
                        logging.warning(f'Could not parse line: {line}')
                        continue
                    except Exception as e:
                        logging.error(f'Error processing line: {line}')
                        logging.error(e)
                        continue


def parse_args(args):
    parser = argparse.ArgumentParser(description='Extract Q&A from training data.')

    parser.add_argument(
        '--file_paths',
        nargs='+',
        help='File paths to extract Q&A from.'
    )
    parser.add_argument(
        '--output_file',
        help='Where to write a CSV file of extracted metadata'
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

    return parser.parse_args(args)


if __name__ == '__main__':
    args = parse_args(None)
    main(args)
