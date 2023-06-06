import argparse
import os

from flask import Flask, session, request, jsonify, render_template
import openai

import parser


openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
app.config.update(ENV='development')
app.config.update(SECRET_KEY='878as7d8f7997dfaewrwv8asdf8)(dS&A&*d78(*&ASD08A')

SESSION_KEY = "json"


def __build_parsed_response(message:str):
    result = parser.parse_with_gpt(message)
    print(result)
    return {"translation": result}


def __wrong_payload_response(message="wrong payload"):
    return {"translation": message}


@app.route('/')
def home():
   return render_template("indexExtractor.html")


@app.route('/extractor')
def extractor():
   return render_template("indexExtractor.html")

@app.route("/translate", methods=["GET"])
def get():
    # get = session.get(SESSION_KEY)
    text = request.args.get("text")
    response = jsonify(__build_parsed_response(text), 200)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response # For some reason the response comes back with leading \n's; trimming in js for now


@app.route("/post", methods=["POST"])
def post():
    post = request.get_json()
    print(post)
    
    if post is not None:
        session[SESSION_KEY] = post
        return jsonify(__build_parsed_response(post["text"]), 201)
    else:
        return jsonify(__wrong_payload_response(), 400)



if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--local', dest='local', action='store_true')
    args = argparser.parse_args()

    if args.local:
        app.run(host="127.0.0.1", port=5001, debug=True)
    else:
        app.run_server(debug=True, use_reloader=False )
