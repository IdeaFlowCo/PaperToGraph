import asyncio
import json
import os

import sentry_sdk
from sentry_sdk.integrations.quart import QuartIntegration

from quart import Quart, request, jsonify, render_template, make_response

import aws
import batch
import gpt
import llama
import parse
import save
import search
import simon_client
import utils
from utils import log_msg

# Unlike other config values, SENTRY_DSN is only ever set via environment variable
# (mainly because it's annoying to have Sentry exception intercept/reporting running locally)
SENTRY_DSN = os.environ.get('SENTRY_DSN', None)
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            QuartIntegration(),
        ],

        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # Sentry recommends adjusting this value in production.
        traces_sample_rate=1.0
    )


app = Quart(__name__)
config = utils.load_config()
app.config.update(config)
app.config.update(ENV='development')
app.config.update(SECRET_KEY='878as7d8f7997dfaewrwv8asdf8)(dS&A&*d78(*&ASD08A')


def _log_args(args):
    to_log = args.copy()
    if 'text' in to_log:
        if len(to_log['text']) > 150:
            to_log['text'] = to_log['text'][:150] + '...'
    to_log = json.dumps(to_log, indent=2)
    log_msg(f'Request arguments: \n{to_log}')


def _wrong_payload_response(message="wrong payload"):
    return {"translation": message}


async def _render_template(template, **kwargs):
    nav_links = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Batch Processing', 'url': '/batch'},
        {'name': 'Query', 'url': '/query'},
    ]
    if app.config.get('PAPERS_DIR'):
        nav_links.append({'name': 'Search', 'url': '/search'})
    kwargs['nav_links'] = nav_links
    kwargs['active_page'] = request.path

    # Only include the Sentry reporting JS if server is configured to report backend errors
    kwargs['include_sentry_js'] = not not SENTRY_DSN

    return await render_template(template, **kwargs)


@app.route('/')
async def home():
    return await _render_template("index.html")


@app.route('/hackathon')
async def hackathon():
    return await _render_template("hackathon.html")


@app.route('/ask-llama', methods=["POST"])
async def ask_llama():
    post = await request.get_json()
    log_msg('POST request to /ask-llama endpoint')
    _log_args(post)

    required_args = ['query']
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    query = post.get('query')
    return await utils.make_response_with_heartbeat(
        llama.aask_llama(query),
        log_label='Llama query'
    )


@app.route('/extractor')
async def extractor():
    return await _render_template("index.html")


@app.route("/raw-parse", methods=["POST"])
async def raw_parse():
    post = await request.get_json()
    log_msg('POST request to /raw-parse endpoint')
    _log_args(post)

    required_args = ['text']
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    text = post.get('text')
    model = gpt.sanitize_gpt_model_choice(post.get('model'))
    prompt_override = post.get('prompt_override', None)
    response = await make_response(
        parse.async_parse_with_heartbeat(text, model=model, prompt_override=prompt_override),
        {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            'Transfer-Encoding': 'chunked',
        },
    )
    response.timeout = None
    return response


@app.route('/parse-prompt')
async def get_parse_prompt():
    log_msg('GET request to /parse-prompt endpoint')
    prompt = gpt.get_default_parse_prompt()
    return jsonify({'prompt': prompt})


@app.route("/save-to-neo", methods=["POST"])
async def save_to_neo():
    post = await request.get_json()
    log_msg('POST request to /save-to-neo endpoint')
    _log_args(post)

    required_args = ['data', 'input_text']
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    try:
        # Make sure data is valid JSON
        data = json.loads(post['data'])
    except json.JSONDecodeError:
        return jsonify({'status': 'error', 'message': 'data provided not valid JSON'}), 400

    log_msg('Saving input text to S3...')
    saved_input_uri = save.save_input_text_to_s3(post['input_text'])

    log_msg('Saving data to Neo4j...')
    save.save_data_to_neo4j(
        data,
        source_uri=saved_input_uri,
        neo_config=app.config.get('neo4j_config')
    )

    return jsonify({'status': 'success'})


@app.route('/batch')
async def batch_page():
    return await _render_template("batch.html")


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
    _log_args(post)

    if batch.is_batch_job_running():
        return jsonify({'status': 'error', 'message': 'batch job already running'}), 400

    required_args = ['job_type', 'data_source']
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    if post['job_type'] == 'parse':
        batch.make_and_run_parse_job(post)
        return jsonify({'status': 'success', 'message': 'New job started'}), 200
    elif post['job_type'] == 'save':
        neo_config = app.config.get('neo4j')
        batch.make_and_run_save_job(post, neo_config)
        return jsonify({'status': 'success', 'message': 'New job started'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'invalid job_type'}), 400


@app.route('/cancel-batch-job', methods=["POST"])
async def cancel_batch_job():
    log_msg('POST request to /cancel-batch-job endpoint')
    batch.cancel_batch_job()
    return jsonify({'status': 'success', 'message': 'Batch job cancel requested'}), 200


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
                    await asyncio.sleep(1)

            # Yield any remaining lines
            line = file.readline().rstrip()
            while line:
                yield f'data:{line}\n\n'
                line = file.readline().rstrip()

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


@app.route('/query')
async def query_page():
    return await _render_template("query.html")


@app.route('/query-simon', methods=["POST"])
async def query_simon():
    post = await request.get_json()
    log_msg('POST request to /query-simon endpoint')
    _log_args(post)

    required_args = ['query']
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    query = post.get('query')
    return await utils.make_response_with_heartbeat(
        app.simon_client.query_simon(query),
        log_label='simon query'
    )


@app.route('/search')
async def search_page():
    paper_count = '{:,}'.format(app.search_config['paper_count'])
    return await _render_template("search.html", paper_count=paper_count)


@app.route('/doc-search', methods=["POST"])
async def doc_search():
    post = await request.get_json()
    log_msg('POST request to /doc-search endpoint')
    _log_args(post)

    if not app.search_config:
        return jsonify({'status': 'error', 'message': 'PAPERS_DIR not configured'}), 500

    required_args = ['query']
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    query = post.get('query')
    papers_dir = app.search_config['papers_dir']
    metadata_file = app.search_config['metadata_file']
    return await utils.make_response_with_heartbeat(
        search.asearch_docs(query, papers_dir=papers_dir, metadata_file=metadata_file),
        log_label='Doc search'
    )


@app.route('/new-doc-set', methods=["POST"])
async def make_new_doc_set():
    post = await request.get_json()
    log_msg('POST request to /doc-search endpoint')
    _log_args(post)

    required_args = ['files']
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    files = post.get('files')
    return await utils.make_response_with_heartbeat(
        search.aupload_batch_set(files),
        log_label='Upload new batch set'
    )


@app.before_serving
async def server_setup():
    utils.setup_logger(**app.config['logger'])
    log_msg('Logger initialized')
    utils.log_config_vars(app.config)


@app.before_serving
async def batch_job_setup():
    batch.setup_status_file()


@app.before_serving
async def simon_setup():
    app.simon_client = simon_client.SimonClient(app.config)


@app.before_serving
async def search_setup():
    papers_dir = app.config.get('PAPERS_DIR', None)
    if not papers_dir:
        log_msg('PAPERS_DIR not configured, /search will not be available')
        return

    # Walk papers_dir and count all .txt files
    # Only do this once, at server startup, because it may be slow for very large numbers of files
    log_msg(f'Counting papers in {papers_dir} that will be available for /search...')
    paper_count = 0
    for _, _, files in os.walk(papers_dir):
        paper_count += len([file for file in files if os.path.splitext(file)[1] == ".txt"])
    log_msg(f'{paper_count:,} papers found!')

    app.search_config = {
        'papers_dir': papers_dir,
        'paper_count': paper_count,
        'metadata_file': app.config.get('PAPERS_METADATA_FILE', None)
    }
    log_msg(f'Search config: {app.search_config}')


if __name__ == '__main__':
    print('Starting server...')
    if app.config.get('DEV_SERVER'):
        app.run(host="127.0.0.1", port=5001, debug=True)
    else:
        app.run_server(use_reloader=False)
