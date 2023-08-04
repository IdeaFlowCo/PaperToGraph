import asyncio
import json
import os
import subprocess
import sys
import time

import aws
from utils import log_msg, log_debug


def search_docs(query, papers_dir=None):
    find_cmd = ['find', papers_dir, '-type', 'f', '-name', '*.txt']
    grep_cmd = ['parallel', '-k', '-j8', '-m', f'LC_ALL=C fgrep -Hic "{query}" {{}}']

    grep_st = time.time()
    find_process = subprocess.Popen(find_cmd, stdout=subprocess.PIPE, text=True)
    grep_process = subprocess.Popen(grep_cmd, stdin=find_process.stdout, stdout=subprocess.PIPE, text=True)

    # Allow find_process to receive a SIGPIPE if grep_process exits.
    find_process.stdout.close()

    output, error = grep_process.communicate()
    grep_et = time.time()
    log_msg(f'Parallelized grep search for {query} in {papers_dir} completed in {(grep_et - grep_st):.2f} seconds')
    # log_msg(output)
    # log_msg(error)

    # log_msg(f'grep_process.returncode: {grep_process.returncode}')
    # if grep_process.returncode != 0:
    #     print("Grep process failed.")
    #     return []

    # output = output.decode('utf-8').strip().splitlines()
    output = output.strip().splitlines()
    files_with_matches = [line.split(':')[0] for line in output if int(line.split(':')[1]) > 0]
    log_debug(f'Files with matches: {files_with_matches}')

    structured_result = [
        {'title': os.path.basename(f).rstrip('.txt'), 'path': f} for f in files_with_matches
    ]
    return structured_result


async def asearch_docs(query, papers_dir=None):
    log_msg(f'Running async search for "{query}" in {papers_dir}')
    search_results = await asyncio.to_thread(lambda: search_docs(query, papers_dir=papers_dir))
    log_msg(search_results)
    return {'files': search_results}


def upload_batch_set(files, base_dir='s3://paper2graph-parse-inputs/web-search-sets'):
    # Remove any potential duplicates
    files = list(set(files))

    missing_files = [f for f in files if not os.path.isfile(f)]

    if missing_files:
        log_msg(f'Request to create new batch set with unknown files: {missing_files}')
        return {'error': 'Unknown files', 'detail': missing_files}

    try:
        new_batch_set_uri = aws.create_new_batch_set_dir(base_dir_uri=base_dir)
    except Exception as e:
        log_msg(f'Error creating folder for new batch set: {e}')
        return {'error': f'Error creating folder for new batch set: {e}'}

    for f in files:
        try:
            file_name = os.path.basename(f)
            new_file_uri = new_batch_set_uri + '/' + file_name
            aws.upload_to_s3(new_file_uri, f)
        except Exception as e:
            log_msg(f'Error uploading file {f} to batch set {new_batch_set_uri}: {e}')
            return {'error': f'Error uploading file {f} to batch set {new_batch_set_uri}: {e}'}

    return {'uri': new_batch_set_uri}


async def aupload_batch_set(files, base_dir='s3://paper2graph-parse-inputs/web-search-sets'):
    log_msg(f'Running async upload_batch_set with {len(files)} files')
    result = await asyncio.to_thread(lambda: upload_batch_set(files, base_dir=base_dir))
    log_msg(result)
    return result
