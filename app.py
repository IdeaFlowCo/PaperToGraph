import argparse
import asyncio
from datetime import datetime
import json

from flask import Flask, request, jsonify, render_template

import parser
import saver


app = Flask(__name__)
app.config.update(ENV='development')
app.config.update(SECRET_KEY='878as7d8f7997dfaewrwv8asdf8)(dS&A&*d78(*&ASD08A')


def __log_msg(msg:str):
    ts = datetime.now().isoformat(timespec='seconds')
    print(f'[{ts}] {msg}')


def __log_args(args):
    to_log = args.copy()
    if 'text' in to_log:
        if len(to_log['text']) > 150:
            to_log['text'] = to_log['text'][:150] + '...'
    to_log = json.dumps(to_log, indent=2)
    __log_msg(f'Request arguments: \n{to_log}')


def iter_over_async(ait, loop):
    '''
    Make an async generator behave as if it's syncronous.
    
    Need this for Flask streaming response.
    '''
    ait = ait.__aiter__()
    async def get_next():
        try: obj = await ait.__anext__(); return False, obj
        except StopAsyncIteration: return True, None
    while True:
        done, obj = loop.run_until_complete(get_next())
        if done: break
        yield obj


def __parsed_response_generator(message:str, model:str):
    if model not in ['gpt-3.5-turbo', 'gpt-4']:
        model = 'gpt-3.5-turbo'
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    iter = iter_over_async(parser.async_parse_with_gpt(message, model=model), loop)
    return app.response_class(iter, mimetype='application/json')


def __raw_parse_response_generator(message:str, model:str):
    if model not in ['gpt-3.5-turbo', 'gpt-4']:
        model = 'gpt-3.5-turbo'
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    iter = iter_over_async(parser.async_parse_without_merging(message, model=model), loop)
    return app.response_class(iter, mimetype='application/json')


def __wrong_payload_response(message="wrong payload"):
    return {"translation": message}


@app.route('/')
def home():
   return render_template("index.html")


@app.route('/extractor')
def extractor():
   return render_template("index.html")


@app.route("/translate", methods=["POST"])
def post():
    post = request.get_json()
    __log_msg('POST request to /translate endpoint')
    __log_args(post)
    
    if post is not None:
        return __parsed_response_generator(post['text'], post['model'])
    else:
        return jsonify(__wrong_payload_response(), 400)



@app.route("/raw-parse", methods=["POST"])
def raw_parse():
    post = request.get_json()
    __log_msg('POST request to /raw-parse endpoint')
    __log_args(post)
    
    if post is not None:
        return __raw_parse_response_generator(post['text'], post['model'])
    else:
        return jsonify(__wrong_payload_response(), 400)


@app.route("/save-to-neo", methods=["POST"])
def save_to_neo():
    post = request.get_json()
    __log_msg('POST request to /save-to-neo endpoint')
    __log_args(post)
    
    if post is not None and 'data' in post:
        saver.save_json_array(post['data'])
        return jsonify({'status': 'success'}, 200)
    else:
        return jsonify(__wrong_payload_response(), 400)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--local', dest='local', action='store_true')
    args = argparser.parse_args()

    __log_msg('Starting server...')
    if args.local:
        app.run(host="127.0.0.1", port=5001, debug=True)
    else:
        app.run_server(debug=True, use_reloader=False )
