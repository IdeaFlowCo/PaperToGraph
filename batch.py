import asyncio
import threading


import batch_parse_job
import batch_save_job
import utils
from utils import log_msg


STATUS_FILE = '/tmp/p2g_batch_job_status.txt'
LOG_FILE = 'logs/batch-job.log'

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
    parse_job = batch_parse_job.BatchParseJob(gpt_model=gpt_model, dry_run=dry_run)

    data_source = job_args['data_source']
    output_uri = job_args.get('output_uri', 's3://paper2graph-parse-results')
    work_fn = lambda: parse_job.run(data_source, output_uri)

    utils.setup_logger(name=thread_name, log_file=LOG_FILE)
    
    batch_job_thread = BatchJobThread(thread_name, work_fn)
    batch_job_thread.start()


def make_and_run_save_job(neo_config, job_args):
    thread_name = utils.BATCH_SAVE_THREAD_NAME
    
    data_source = job_args['data_source']
    if 'neo_uri' in job_args:
        neo_config['uri'] = job_args['neo_uri']
    if 'neo_user' in job_args:
        neo_config['user'] = job_args['neo_user']
    if 'neo_password' in job_args:
        neo_config['password'] = job_args['neo_password']

    work_fn = lambda: batch_save_job.save_to_neo4j(data_source, neo_config)

    utils.setup_logger(name=thread_name, log_file=LOG_FILE)

    batch_job_thread = BatchJobThread(thread_name, work_fn)
    batch_job_thread.start()
