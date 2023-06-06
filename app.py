import argparse
import os

from flask import Flask, session, request, jsonify, render_template
import openai


openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
app.config.update(ENV='development')
app.config.update(SECRET_KEY='878as7d8f7997dfaewrwv8asdf8)(dS&A&*d78(*&ASD08A')

SESSION_KEY = "json"


PROMPT_TEMPLATE = (
    "Extract the named entities and relations between them in subsequent queries as per the following format. "
    "Specifically list the named entities, then sub-bullets showing each of their relationships after a colon. "
    "Don't forget newlines between entries."
    "Input: "
    "\"Tom Currier is a great guy who built lots of communities after he studied at Stanford and Harvard. He also won the Thiel fellowship\""
    "Output: "
    "Tom Currier\n "
    "\n- studied at: Stanford, Harvard "
    "\n- winner of: Thiel Fellowship \n"
    "\n------\n"
    "Query: \n"
)

def __fetch_gpt_response(message:str):
    new_prompt = PROMPT_TEMPLATE + message

    result = openai.Completion.create(
        model="text-davinci-003",
        prompt=new_prompt,
        max_tokens=3000,
        temperature=1.2
    )
    print(result)
    return {"translation": result["choices"][0]["text"]}


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
    response = jsonify(__fetch_gpt_response(text), 200)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response # For some reason the response comes back with leading \n's; trimming in js for now


@app.route("/post", methods=["POST"])
def post():
    post = request.get_json()
    print(post)
    
    if post is not None:
        session[SESSION_KEY] = post
        return jsonify(__fetch_gpt_response(post["text"]), 201)
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
