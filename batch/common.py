import asyncio
import os
import threading

import utils
from utils import log_msg

from . import parse
from . import save


STATUS_FILE = '/tmp/p2g/p2g_batch_job_status.txt'
LOG_FILE = '/tmp/p2g/batch-job.log'

NOT_STARTED = 'Not started'
RUNNING = 'Running'
CANCELING = 'Canceling'
CANCELED = 'Canceled'
COMPLETED = 'Completed'


class BatchJobThread(threading.Thread):
    def __init__(self, name, work_fn, interval=1):
        super().__init__(name=name)
        self._work_fn = work_fn
        self.interval = interval
        self._cancel_flag = threading.Event()

    def run(self):
        self._write_status_to_file(RUNNING)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._run_work_fn())
        if self._cancel_flag.is_set():
            self._write_status_to_file(CANCELED)
        else:
            self._write_status_to_file(COMPLETED)
        loop.close()

    async def _run_work_fn(self):
        work_task = asyncio.create_task(self._work_fn())
        while not self._cancel_flag.is_set():
            if work_task.done():
                log_msg('Batch job completed.')
                break

            if self._cancel_requested():
                log_msg('Cancel requested. Stopping batch job.')
                work_task.cancel()
                self.cancel()
                break

            await asyncio.sleep(self.interval)

    def _cancel_requested(self):
        with open(STATUS_FILE, "r") as f:
            status = f.read()

        return status == CANCELING

    def _write_status_to_file(self, status):
        with open(STATUS_FILE, "w") as f:
            f.write(status)

    def cancel(self):
        self._cancel_flag.set()


def setup_status_file():
    # Make intermediate directories if necessary
    if os.path.dirname(STATUS_FILE):
        os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    # Clear any previous contents
    open(STATUS_FILE, 'w').close()


def cancel_batch_job():
    with open(STATUS_FILE, "w") as f:
        f.write(CANCELING)


def is_batch_job_running():
    try:
        with open(STATUS_FILE, "r") as f:
            status = f.read()
        return status == RUNNING
    except FileNotFoundError:
        with open(STATUS_FILE, "w") as f:
            f.write(NOT_STARTED)
        return False


def make_and_run_parse_job(job_args):
    thread_name = utils.BATCH_PARSE_THREAD_NAME

    gpt_model = utils.sanitize_gpt_model_choice(job_args.get('model', 'any'))
    dry_run = job_args.get('dry_run', False)
    prompt = job_args.get('prompt', None)
    parse_job = parse.BatchParseJob(
        gpt_model=gpt_model,
        dry_run=dry_run,
        prompt_override=prompt,
        log_file=LOG_FILE
    )

    data_source = job_args['data_source']
    output_uri = job_args.get('output_uri', 's3://paper2graph-parse-results')
    def work_fn(): return parse_job.run(data_source, output_uri)

    utils.setup_logger(name=thread_name, log_file=LOG_FILE)

    batch_job_thread = BatchJobThread(thread_name, work_fn)
    batch_job_thread.start()


def make_and_run_save_job(job_args, neo_config):
    thread_name = utils.BATCH_SAVE_THREAD_NAME

    data_source = job_args['data_source']
    if 'neo_uri' in job_args:
        neo_config['uri'] = job_args['neo_uri']
    if 'neo_user' in job_args:
        neo_config['user'] = job_args['neo_user']
    if 'neo_password' in job_args:
        neo_config['password'] = job_args['neo_password']

    def work_fn(): return save.save_to_neo4j(data_source, neo_config)

    utils.setup_logger(name=thread_name, log_file=LOG_FILE)

    batch_job_thread = BatchJobThread(thread_name, work_fn)
    batch_job_thread.start()
