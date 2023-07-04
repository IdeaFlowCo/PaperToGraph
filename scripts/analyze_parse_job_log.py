import argparse
import json
import re

import aws


def _get_log_lines(log_file):
    if aws.is_valid_s3_uri(log_file):
        _, log_data = aws.read_file_from_s3(log_file)
        for line in log_data.split('\n'):
            yield line
    else:
        with open(log_file, 'r') as f:
            for line in f:
                yield line


def main(args):
    sending_req_regex = r'Sending request to OpenAI'
    request_count = 0

    invalid_json_regex = r'Response not valid JSON'
    invalid_json_count = 0

    timeout_regex = r'OpenAI request timeout'
    timeout_count = 0

    parse_time_regex = r'Parse results fetched in (\d+\.\d{1,2}) seconds'
    parse_times = []

    result_length_regex = r'Parse result length \(in tokens\): (\d+)'
    result_lengths = []

    finish_reason_regex = r'OpenAI finish reason: "(\w+)"'
    finish_reasons = {}

    for line in _get_log_lines(args.log_file):
        sending_req_match = re.search(sending_req_regex, line)
        if sending_req_match:
            request_count += 1
            continue

        invalid_json_match = re.search(invalid_json_regex, line)
        if invalid_json_match:
            invalid_json_count += 1
            continue

        timeout_match = re.search(timeout_regex, line)
        if timeout_match:
            timeout_count += 1
            continue

        parse_time_match = re.search(parse_time_regex, line)
        if parse_time_match:
            parse_time = float(parse_time_match.group(1))
            parse_times.append(parse_time)
            continue

        result_length_match = re.search(result_length_regex, line)
        if result_length_match:
            result_length = int(result_length_match.group(1))
            result_lengths.append(result_length)
            continue

        finish_reason_match = re.search(finish_reason_regex, line)
        if finish_reason_match:
            finish_reason = finish_reason_match.group(1)
            finish_reasons[finish_reason] = finish_reasons.get(finish_reason, 0) + 1
            continue

    results = {
        'request_count': request_count,
        'invalid_json_count': invalid_json_count,
        'timeout_count': timeout_count,
        'finish_reasons': finish_reasons,
    }

    if parse_times:
        parse_time_stats = {
            'min': min(parse_times),
            'max': max(parse_times),
            'mean': sum(parse_times) / len(parse_times)
        }
        results['parse_time_stats'] = parse_time_stats
        results['parse_times'] = parse_times

    if result_lengths:
        result_length_stats = {
            'min': min(result_lengths),
            'max': max(result_lengths),
            'mean': sum(result_lengths) / len(result_lengths)
        }
        results['result_length_stats'] = result_length_stats
        results['result_lengths'] = result_lengths

    print(json.dumps(results, indent=2))


def parse_args(args):
    parser = argparse.ArgumentParser(description='Process batch job log file to harvest info')

    parser.add_argument('--log_file', help='The log file to parse. Can be a local path or an S3 URL.')

    return parser.parse_args(args)
