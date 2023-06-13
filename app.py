import argparse
import asyncio
import json
import os

import sentry_sdk

from flask import Flask, request, jsonify, render_template
from sentry_sdk.integrations.flask import FlaskIntegration

import parse
import save
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
    if model not in ['gpt-3.5-turbo', 'gpt-4']:
        model = 'gpt-3.5-turbo'
    
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
    
    if post is None or 'data' not in post:
        return jsonify(__wrong_payload_response(), 400)
    
    try:
        save.save_json_array(post['data'], neo_config=app.config['NEO4J_CREDENTIALS'])
        return jsonify({'status': 'success'}, 200)
    except json.JSONDecodeError:
        return jsonify({'status': 'error', 'message': 'data provided not valid JSON'}), 400


def __handle_neo_credential_override(args):
    uri_override = args.neo_uri if args.neo_uri is not None else os.environ.get('NEO_URI')
    user_override = args.neo_user if args.neo_user is not None else os.environ.get('NEO_USER')
    pass_override = args.neo_pass if args.neo_pass is not None else os.environ.get('NEO_PASS')
    neo_credentials = {
        'uri': uri_override,
        'user': user_override,
        'password': pass_override
    }
    # Ignore any override values that are None or empty strings
    neo_credentials = {k: v for k, v in neo_credentials.items() if v}
    log_msg(f'Neo4j credential overrides: {neo_credentials}')
    app.config.update(NEO4J_CREDENTIALS=neo_credentials)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()

    argparser.add_argument('--local', dest='local', action='store_true')

    argparser.add_argument('--neo_uri', action='store', default=None, help='Specify URI for Neo4j database')
    argparser.add_argument('--neo_user', action='store', default=None, help='Specify username for Neo4j database')
    argparser.add_argument('--neo_pass', action='store', default=None, help='Specify password for Neo4j database')

    args = argparser.parse_args()

    __handle_neo_credential_override(args)

    log_msg('Starting server...')
    if args.local:
        app.run(host="127.0.0.1", port=5001, debug=True)
    else:
        app.run_server(debug=True, use_reloader=False )
