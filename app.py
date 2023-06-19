import argparse
import asyncio
import json
from threading import Event, Thread

import sentry_sdk

from flask import Flask, request, jsonify, render_template, Response
from sentry_sdk.integrations.flask import FlaskIntegration

import batch_parse_job
import batch_save_job
import parse
import save
import time
import utils
from utils import log_msg


sentry_sdk.init(
    dsn="https://4226949e3a1d4812b5c26d55888d470d@o461205.ingest.sentry.io/4505326108999680",
    integrations=[
        FlaskIntegration(),
    ],

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # Sentry recommends adjusting this value in production.
    traces_sample_rate=1.0
)


app = Flask(__name__)
app.config.update(ENV='development')
app.config.update(SECRET_KEY='878as7d8f7997dfaewrwv8asdf8)(dS&A&*d78(*&ASD08A')



def __log_args(args):
    to_log = args.copy()
    if 'text' in to_log:
        if len(to_log['text']) > 150:
            to_log['text'] = to_log['text'][:150] + '...'
    to_log = json.dumps(to_log, indent=2)
    log_msg(f'Request arguments: \n{to_log}')


def iter_over_async(ait):
    '''
    Make an async generator behave as if it's syncronous.
    
    Need this for Flask streaming response.
    '''
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    ait = ait.__aiter__()
    async def get_next():
        try: obj = await ait.__anext__(); return False, obj
        except StopAsyncIteration: return True, None
    while True:
        done, obj = loop.run_until_complete(get_next())
        if done: break
        yield obj


def __create_parse_response(message:str, model:str):
    model = utils.sanitize_gpt_model_choice(model)
    iter = iter_over_async(parse.async_parse_with_heartbeat(message, model=model))
    return app.response_class(iter, mimetype='application/json')


def __wrong_payload_response(message="wrong payload"):
    return {"translation": message}


@app.route('/')
def home():
   return render_template("index.html")


@app.route('/extractor')
def extractor():
   return render_template("index.html")


@app.route("/raw-parse", methods=["POST"])
def raw_parse():
    post = request.get_json()
    log_msg('POST request to /raw-parse endpoint')
    __log_args(post)
    
    if post is not None:
        return __create_parse_response(post['text'], post['model'])
    else:
        return jsonify(__wrong_payload_response(), 400)


@app.route("/save-to-neo", methods=["POST"])
def save_to_neo():
    post = request.get_json()
    log_msg('POST request to /save-to-neo endpoint')
    __log_args(post)
    
    required_args = ['data', 'input_text']
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(__wrong_payload_response(), 400)
    
    try:
        # Make sure data is valid JSON
        json.loads(post['data'])
        log_msg('About to save input text')
        saved_input_uri = save.save_input_text(post['input_text'])
        log_msg('Saved input text')
        save.save_json_data(post['data'], saved_input_uri=saved_input_uri, neo_config=app.config.get('NEO4J_CREDENTIALS'))
        return jsonify({'status': 'success'}, 200)
    except json.JSONDecodeError:
        return jsonify({'status': 'error', 'message': 'data provided not valid JSON'}, 400)


@app.route('/batch')
def batch_page():
   return render_template("batch.html")


batch_running = Event()


@app.route('/batch-status')
def batch_status():
    global batch_running
    return jsonify({'status': 'running' if batch_running.is_set() else 'idle'})


def __run_job_as_thread(thread_name, job):
    global batch_running
    if batch_running.is_set():
        raise Exception('batch job already running')
    
    def thread_target():
        global batch_running
        batch_running.set()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(job())
        loop.close()
        batch_running.clear()

    job_thread = Thread(name=thread_name, target=thread_target)
    job_thread.start()


BATCH_JOB_LOG_FILE = 'logs/batch-job.log'


@app.route('/new-batch-job', methods=["POST"])
def new_batch_job():
    post = request.get_json()
    log_msg('POST request to /new-batch-job endpoint')
    __log_args(post)

    global batch_running
    if batch_running.is_set():
        return jsonify({'status': 'error', 'message': 'batch job already running'}), 400
    
    required_args = ['job_type', 'data_source']
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(__wrong_payload_response(), 400)
    
    if post['job_type'] == 'parse':
        thread_name = utils.BATCH_PARSE_THREAD_NAME
        utils.setup_logger(name=thread_name, log_file=BATCH_JOB_LOG_FILE)
        gpt_model = utils.sanitize_gpt_model_choice(post.get('gpt_model', 'any'))
        dry_run = post.get('dry_run', False)
        parse_job = batch_parse_job.BatchParseJob(gpt_model=gpt_model, dry_run=dry_run)

        data_source = post['data_source']
        output_uri = post.get('output_uri', 's3://paper2graph-parse-results')
        __run_job_as_thread(thread_name, lambda: parse_job.run(data_source, output_uri))
        return jsonify({'status': 'success', 'message': 'New job started'}), 200
    elif post['job_type'] == 'save':
        thread_name = utils.BATCH_SAVE_THREAD_NAME
        utils.setup_logger(name=thread_name, log_file=BATCH_JOB_LOG_FILE)
        data_source = post['data_source']
        neo_config = app.config.get('NEO4J_CREDENTIALS')
        if 'neo_uri' in post:
            neo_config['uri'] = post['neo_uri']
        if 'neo_user' in post:
            neo_config['user'] = post['neo_user']
        if 'neo_password' in post:
            neo_config['password'] = post['neo_password']
        __run_job_as_thread(thread_name, lambda: batch_save_job.save_to_neo4j(data_source, neo_config))
        return jsonify({'status': 'success', 'message': 'New job started'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'invalid job_type'}), 400


@app.route('/batch-log', methods=["GET"])
def batch_log():
    def log_tail(file_path):
        with open(file_path, 'r') as file:
            lines = file.readlines()
            # Yield last 20 lines as context
            for line in lines[-20:]:
                yield f'data:{line}\n\n'
            # Watch for new lines and yield them as they are added
            while True:
                current_position = file.tell()
                line = file.readline().rstrip()
                if line:
                    yield f'data:{line}\n\n'
                else:
                    file.seek(current_position)
                    time.sleep(0.25)
    return Response(log_tail(BATCH_JOB_LOG_FILE), mimetype= 'text/event-stream')


def __handle_neo_credential_override(args):
    neo_credentials = utils.neo_config_from_args_or_env(args)
    # Ignore any override values that are None or empty strings
    neo_credentials = {k: v for k, v in neo_credentials.items() if v}
    log_msg(f'Neo4j credential overrides: {neo_credentials}')
    app.config.update(NEO4J_CREDENTIALS=neo_credentials)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()

    argparser.add_argument('--local', dest='local', action='store_true')

    utils.add_neo_credential_override_args(argparser)

    args = argparser.parse_args()

    __handle_neo_credential_override(args)

    utils.setup_logger()

    log_msg('Starting server...')
    if args.local:
        app.run(host="127.0.0.1", port=5001, debug=True)
    else:
        app.run_server(debug=True, use_reloader=False )
