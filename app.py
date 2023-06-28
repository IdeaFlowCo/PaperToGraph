import argparse
import asyncio
import json

import sentry_sdk
from sentry_sdk.integrations.quart import QuartIntegration

from quart import Quart, request, jsonify, render_template, Response, make_response

import batch
import parse
import save
import utils
from utils import log_msg


sentry_sdk.init(
    dsn="https://4226949e3a1d4812b5c26d55888d470d@o461205.ingest.sentry.io/4505326108999680",
    integrations=[
        QuartIntegration(),
    ],

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # Sentry recommends adjusting this value in production.
    traces_sample_rate=1.0
)


app = Quart(__name__)
app.config.from_prefixed_env('P2G')
app.config.update(ENV='development')
app.config.update(SECRET_KEY='878as7d8f7997dfaewrwv8asdf8)(dS&A&*d78(*&ASD08A')



def __log_args(args):
    to_log = args.copy()
    if 'text' in to_log:
        if len(to_log['text']) > 150:
            to_log['text'] = to_log['text'][:150] + '...'
    to_log = json.dumps(to_log, indent=2)
    log_msg(f'Request arguments: \n{to_log}')


def __create_parse_response(message:str, model:str, prompt_override=None):
    model = utils.sanitize_gpt_model_choice(model)
    return app.response_class(
        parse.async_parse_with_heartbeat(message, model=model, prompt_override=prompt_override),
        mimetype='application/json'
    )


def __wrong_payload_response(message="wrong payload"):
    return {"translation": message}


@app.route('/')
async def home():
   return await render_template("index.html")


@app.route('/extractor')
async def extractor():
   return await render_template("index.html")


@app.route("/raw-parse", methods=["POST"])
async def raw_parse():
    post = await request.get_json()
    log_msg('POST request to /raw-parse endpoint')
    __log_args(post)
    
    if post is not None:
        return __create_parse_response(post['text'], post['model'], prompt_override=post.get('prompt_override', None))
    else:
        return jsonify(__wrong_payload_response(), 400)


@app.route("/save-to-neo", methods=["POST"])
async def save_to_neo():
    post= await request.get_json()
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
async def batch_page():
   return await render_template("batch.html")


@app.route('/batch-status')
async def batch_status():
    if batch.is_batch_job_running():
        return jsonify({'status': 'running'})
    else:
        return jsonify({'status': 'idle'})


@app.route('/new-batch-job', methods=["POST"])
async def new_batch_job():
    post = await request.get_json()
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
async def cancel_batch_job():
    log_msg('POST request to /cancel-batch-job endpoint')
    batch.cancel_batch_job()
    return jsonify({'status': 'success', 'message': 'Batch job cancel requested'}), 200


async def batch_log_response_generator(file_path):
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
                await asyncio.sleep(0.5)
        yield f'data:done\n\n'


@app.route('/batch-log', methods=["GET"])
async def batch_log():
    async def tail_log(file_path):
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
                    await asyncio.sleep(0.5)
            yield f'data:done\n\n'

    response = await make_response(
        tail_log(batch.LOG_FILE),
         {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Transfer-Encoding': 'chunked',
        },
    )
    response.timeout = None
    return response


def __handle_neo_credential_overrides():
    neo_credentials = app.config.get('NEO4J_CREDENTIALS', {})
    neo_cred_overrides = utils.get_neo_config_from_env()
    # Ignore any override values that are None or empty strings
    neo_cred_overrides = {k: v for k, v in neo_cred_overrides.items() if v}

    if not neo_cred_overrides:
        log_msg('No Neo4j credential overrides from environment variables')
        return
    
    log_msg(f'Neo4j credential overrides from environment variables: {neo_cred_overrides}')
    neo_credentials.update(neo_cred_overrides)
    app.config.update(NEO4J_CREDENTIALS=neo_credentials)


if __name__ == '__main__':
    if app.config.get('LOG_LEVEL'):
        utils.setup_logger(level=app.config.get('LOG_LEVEL'))
    else:
        utils.setup_logger()
    log_msg('Logger initialized') 

    __handle_neo_credential_overrides()

    log_msg('Starting server...')
    if app.config.get('DEV_SERVER'):
        app.run(host="127.0.0.1", port=5001, debug=True)
    else:
        app.run_server(use_reloader=False )
