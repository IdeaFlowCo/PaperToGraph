import argparse
import asyncio
import json
import logging
import os
import time

import sentry_sdk

from flask import Flask, request, jsonify, render_template, Response
from sentry_sdk.integrations.flask import FlaskIntegration

import batch
import parse
import save
import utils
from utils import log_msg


# sentry_sdk.init(
#     dsn="https://4226949e3a1d4812b5c26d55888d470d@o461205.ingest.sentry.io/4505326108999680",
#     integrations=[
#         FlaskIntegration(),
#     ],

#     # Set traces_sample_rate to 1.0 to capture 100%
#     # of transactions for performance monitoring.
#     # Sentry recommends adjusting this value in production.
#     traces_sample_rate=1.0
# )


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


def __create_parse_response(message:str, model:str, prompt_override=None):
    model = utils.sanitize_gpt_model_choice(model)
    iter = iter_over_async(parse.async_parse_with_heartbeat(message, model=model, prompt_override=prompt_override))
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
        return __create_parse_response(post['text'], post['model'], prompt_override=post.get('prompt_override', None))
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


@app.route('/batch-status')
def batch_status():
    if batch.is_batch_job_running():
        return jsonify({'status': 'running'})
    else:
        return jsonify({'status': 'idle'})


@app.route('/new-batch-job', methods=["POST"])
def new_batch_job():
    post = request.get_json()
    log_msg('POST request to /new-batch-job endpoint')
    __log_args(post)

    if batch.is_batch_job_running():
        return jsonify({'status': 'error', 'message': 'batch job already running'}), 400
    
    required_args = ['job_type', 'data_source']
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(__wrong_payload_response(), 400)
    
    if post['job_type'] == 'parse':
        batch.make_and_run_parse_job(post)
        return jsonify({'status': 'success', 'message': 'New job started'}), 200
    elif post['job_type'] == 'save':
        neo_config = app.config.get('NEO4J_CREDENTIALS')
        batch.make_and_run_save_job(post, neo_config)
        return jsonify({'status': 'success', 'message': 'New job started'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'invalid job_type'}), 400


@app.route('/cancel-batch-job', methods=["POST"])
def cancel_batch_job():
    log_msg('POST request to /cancel-batch-job endpoint')
    batch.cancel_batch_job()
    return jsonify({'status': 'success', 'message': 'Batch job cancel requested'}), 200


@app.route('/batch-log', methods=["GET"])
def batch_log():
    def response_generator(file_path):
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                # Yield last 20 lines as context
                for line in lines[-20:]:
                    yield f'data:{line}\n\n'
                # Watch for new lines and yield them as they are added
                while batch.is_batch_job_running():
                    current_position = file.tell()
                    line = file.readline().rstrip()
                    if line:
                        yield f'data:{line}\n\n'
                        continue
                    else:
                        yield f'data:nodata\n\n'
                        file.seek(current_position)
                        time.sleep(0.25)
                yield f'data:done\n\n'
        except GeneratorExit:
            log_msg('Client connection closed')

    return Response(response_generator(batch.LOG_FILE), mimetype= 'text/event-stream')


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

    log_msg('Starting server...')
    if args.local:
        utils.setup_logger()
        # utils.setup_logger(level=logging.DEBUG)
        app.run(host="127.0.0.1", port=5001, debug=True)
    else:
        utils.setup_logger()
        app.run_server(debug=True, use_reloader=False )
