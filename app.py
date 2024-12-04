import asyncio
import json
import os

import google.oauth2.credentials

import sentry_sdk
from sentry_sdk.integrations.quart import QuartIntegration

from quart import (
    Quart,
    request,
    session,
    jsonify,
    render_template,
    make_response,
    redirect,
    url_for,
)

import batch
import gdrive
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
SENTRY_DSN = os.environ.get("SENTRY_DSN", None)
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            QuartIntegration(),
        ],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # Sentry recommends adjusting this value in production.
        traces_sample_rate=1.0,
    )


app = Quart(__name__)
config = utils.load_config()
app.config.update(config)
app.config.update(ENV="development")
app.config.update(SECRET_KEY="878as7d8f7997dfaewrwv8asdf8)(dS&A&*d78(*&ASD08A")


def _log_args(args):
    to_log = args.copy()
    if "text" in to_log:
        if len(to_log["text"]) > 150:
            to_log["text"] = to_log["text"][:150] + "..."
    to_log = json.dumps(to_log, indent=2)
    log_msg(f"Request arguments: \n{to_log}")


def _wrong_payload_response(message="wrong payload"):
    return {"translation": message}


async def _render_template(template, **kwargs):
    kwargs["app_title"] = app.config.get("APP_TITLE", "Paper2Graph")
    kwargs["nav_links"] = app.config.get("nav_links", [])
    kwargs["active_page"] = request.path

    # Only include the Sentry reporting JS if server is configured to report backend errors
    kwargs["include_sentry_js"] = not not SENTRY_DSN

    return await render_template(template, **kwargs)


def _url_for(page, external=False):
    if not external:
        return url_for(page)

    if app.config.get("DEV_SERVER"):
        return url_for(page, _external=True)
    else:
        return url_for(page, _external=True, _scheme="https")


@app.route("/")
async def home():
    app_mode = app.config.get("APP_MODE", "paper2graph")
    if app_mode == "querymydrive":
        return await _render_template("query.html")
    elif app_mode == "rarediseaseguru":
        return await _render_template("hackathon.html")
    return await _render_template("translate.html")


@app.route("/raw-parse", methods=["POST"])
async def raw_parse():
    post = await request.get_json()
    log_msg("POST request to /raw-parse endpoint")
    _log_args(post)

    required_args = ["text"]
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    text = post.get("text")
    model = gpt.sanitize_gpt_model_choice(post.get("model"))
    prompt_override = post.get("prompt_override", None)
    response = await make_response(
        parse.async_parse_with_heartbeat(
            text, model=model, prompt_override=prompt_override
        ),
        {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Transfer-Encoding": "chunked",
        },
    )
    response.timeout = None
    return response


@app.route("/parse-prompt")
async def get_parse_prompt():
    log_msg("GET request to /parse-prompt endpoint")
    prompt = gpt.get_default_parse_prompt()
    return jsonify({"prompt": prompt})


@app.route("/save-to-neo", methods=["POST"])
async def save_to_neo():
    post = await request.get_json()
    log_msg("POST request to /save-to-neo endpoint")
    _log_args(post)

    required_args = ["data", "input_text"]
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    try:
        # Make sure data is valid JSON
        data = json.loads(post["data"])
    except json.JSONDecodeError:
        return jsonify(
            {"status": "error", "message": "data provided not valid JSON"}
        ), 400

    log_msg("Saving input text to S3...")
    saved_input_uri = save.save_input_text_to_s3(post["input_text"])

    log_msg("Saving data to Neo4j...")
    save.save_data_to_neo4j(
        data, source_uri=saved_input_uri, neo_config=app.config.get("neo4j_config")
    )

    return jsonify({"status": "success"})


@app.route("/batch")
async def batch_page():
    return await _render_template("batch.html")


@app.route("/batch-status")
async def batch_status():
    if batch.is_batch_job_running():
        return jsonify({"status": "running"})
    else:
        return jsonify({"status": "idle"})


@app.route("/new-batch-job", methods=["POST"])
async def new_batch_job():
    post = await request.get_json()
    log_msg("POST request to /new-batch-job endpoint")
    _log_args(post)

    if batch.is_batch_job_running():
        return jsonify({"status": "error", "message": "batch job already running"}), 400

    required_args = ["job_type", "data_source"]
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    if post["job_type"] == "parse":
        batch.make_and_run_parse_job(post)
        return jsonify({"status": "success", "message": "New job started"}), 200
    elif post["job_type"] == "save":
        neo_config = app.config.get("neo4j")
        batch.make_and_run_save_job(post, neo_config)
        return jsonify({"status": "success", "message": "New job started"}), 200
    else:
        return jsonify({"status": "error", "message": "invalid job_type"}), 400


@app.route("/cancel-batch-job", methods=["POST"])
async def cancel_batch_job():
    log_msg("POST request to /cancel-batch-job endpoint")
    batch.cancel_batch_job()
    return jsonify({"status": "success", "message": "Batch job cancel requested"}), 200


@app.route("/batch-log", methods=["GET"])
async def batch_log():
    async def tail_log(file_path):
        with open(file_path, "r") as file:
            lines = file.readlines()
            # Yield last 20 lines as context
            for line in lines[-20:]:
                yield f"data:{line}\n\n"
            # Watch for new lines and yield them as they are added
            while batch.is_batch_job_running():
                current_position = file.tell()
                line = file.readline().rstrip()
                if line:
                    yield f"data:{line}\n\n"
                    continue
                else:
                    yield f"data:nodata\n\n"
                    file.seek(current_position)
                    await asyncio.sleep(1)

            # Yield any remaining lines
            line = file.readline().rstrip()
            while line:
                yield f"data:{line}\n\n"
                line = file.readline().rstrip()

            yield f"data:done\n\n"

    response = await make_response(
        tail_log(batch.LOG_FILE),
        {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Transfer-Encoding": "chunked",
        },
    )
    response.timeout = None
    return response


@app.route("/query")
async def query_page():
    # show_kb_options = not not app.config.get('DEV_SERVER')
    show_kb_options = True
    return await _render_template("query.html", show_kb_options=show_kb_options)


@app.route("/query-simon", methods=["POST"])
async def query_simon():
    post = await request.get_json()
    log_msg("POST request to /query-simon endpoint")
    _log_args(post)

    required_args = ["query"]
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    app_mode = app.config.get("APP_MODE", "paper2graph")
    kb = post.get("kb", None)
    if app_mode == "querymydrive" or kb == "querymydrive":
        simon_client = app.gdrive_simon_client
    else:
        simon_client = app.simon_client

    query = post.get("query")
    return await utils.make_response_with_heartbeat(
        simon_client.query_simon(query), log_label="simon query"
    )


@app.route("/search")
async def search_page():
    paper_count = "{:,}".format(app.search_config["paper_count"])
    return await _render_template("search.html", paper_count=paper_count)


@app.route("/doc-search", methods=["POST"])
async def doc_search():
    post = await request.get_json()
    log_msg("POST request to /doc-search endpoint")
    _log_args(post)

    if not app.search_config:
        return jsonify({"status": "error", "message": "PAPERS_DIR not configured"}), 500

    required_args = ["query"]
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    query = post.get("query")
    papers_dir = app.search_config["papers_dir"]
    metadata_file = app.search_config["metadata_file"]
    return await utils.make_response_with_heartbeat(
        search.asearch_docs(query, papers_dir=papers_dir, metadata_file=metadata_file),
        log_label="Doc search",
    )


@app.route("/new-doc-set", methods=["POST"])
async def make_new_doc_set():
    post = await request.get_json()
    log_msg("POST request to /doc-search endpoint")
    _log_args(post)

    required_args = ["files"]
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    files = post.get("files")

    # Get Google Drive credentials if they exist in the session
    gdrive_creds = None
    if gdrive.CREDS_SESSION_KEY in session:
        gdrive_creds = google.oauth2.credentials.Credentials(
            **session[gdrive.CREDS_SESSION_KEY]
        )

    return await utils.make_response_with_heartbeat(
        search.aupload_batch_set(files, gdrive_creds=gdrive_creds),
        log_label="Upload new batch set",
    )


@app.route("/gdrive")
async def gdrive_page():
    if gdrive.CREDS_SESSION_KEY not in session:
        return redirect(_url_for("gdrive_auth"))

    file_types = [
        {"label": "Plain Text", "value": gdrive.FileType.PLAIN_TEXT},
        {"label": "PDF", "value": gdrive.FileType.PDF},
        {"label": "Google Doc", "value": gdrive.FileType.GOOGLE_DOC},
    ]
    return await _render_template("gdrive.html", file_types=file_types)


@app.route("/gdrive-auth")
async def gdrive_auth():
    flow = gdrive.build_oauth_flow()

    # The URI created here must exactly match one of the authorized redirect URIs
    # for the OAuth 2.0 client, which you configured in the API Console. If this
    # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
    # error.
    flow.redirect_uri = _url_for("google_oauth_callback", external=True)

    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type="offline",
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes="true",
    )

    # Store the state so the callback can verify the auth server response.
    session["state"] = state

    return redirect(authorization_url)


@app.route("/google-oauth")
async def google_oauth_callback():
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = session["state"]

    flow = gdrive.build_oauth_flow(state=state)
    flow.redirect_uri = _url_for("google_oauth_callback", external=True)

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    # Store credentials in the session.
    credentials = flow.credentials
    session[gdrive.CREDS_SESSION_KEY] = gdrive.credentials_to_dict(credentials)

    return redirect(_url_for("gdrive_page"))


@app.route("/gdrive-revoke")
async def gdrive_revoke():
    if gdrive.CREDS_SESSION_KEY in session:
        credentials = google.oauth2.credentials.Credentials(
            **session[gdrive.CREDS_SESSION_KEY]
        )
        gdrive.revoke_credentials(credentials)
        del session[gdrive.CREDS_SESSION_KEY]
    return redirect(_url_for("gdrive_page"))


@app.route("/gdrive-search", methods=["POST"])
async def gdrive_search():
    post = await request.get_json()
    log_msg("POST request to /gdrive-search endpoint")
    _log_args(post)

    if gdrive.CREDS_SESSION_KEY not in session:
        return jsonify(
            {"status": "error", "message": "Google OAuth credentials not in session"}
        ), 400

    required_args = ["query", "mime_type"]
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    query = post.get("query")
    mime_type = post.get("mime_type")
    credentials = google.oauth2.credentials.Credentials(
        **session[gdrive.CREDS_SESSION_KEY]
    )
    return await utils.make_response_with_heartbeat(
        gdrive.asearch_files(
            credentials=credentials, file_name=query, file_type=mime_type
        ),
        log_label="Doc search",
    )


@app.route("/gdrive-ingest", methods=["POST"])
async def ingest_from_gdrive():
    post = await request.get_json()
    log_msg("POST request to /gdrive-ingest endpoint")
    _log_args(post)

    if gdrive.CREDS_SESSION_KEY not in session:
        return jsonify(
            {"status": "error", "message": "Google OAuth credentials not in session"}
        ), 400

    required_args = ["files"]
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    files = post.get("files")
    credentials = google.oauth2.credentials.Credentials(
        **session[gdrive.CREDS_SESSION_KEY]
    )
    return await utils.make_response_with_heartbeat(
        app.gdrive_simon_client.ingest_gdrive_file_set(credentials, files),
        log_label="Simon ingest from Google Drive",
    )


@app.route("/hackathon")
async def hackathon():
    return await _render_template("hackathon.html")


@app.route("/ask-llm", methods=["POST"])
async def ask_llm():
    post = await request.get_json()
    log_msg("POST request to /ask-llm endpoint")
    _log_args(post)

    required_args = ["query", "llm"]
    if post is None or not all(arg in post for arg in required_args):
        return jsonify(_wrong_payload_response()), 400

    query = post.get("query")
    llm_choice = post.get("llm")

    if llm_choice == "llama-2023-08-14":
        return await utils.make_response_with_heartbeat(
            llama.aask_llama(query), log_label="Llama query"
        )
    elif llm_choice == "davinci-2023-08-14":
        return await utils.make_response_with_heartbeat(
            gpt.ask_ft_gpt(query, model="davinci:ft-ideaflow-2023-08-14-01-33-40"),
            log_label="Fine-tuned GPT query",
        )
    else:
        return jsonify({"status": "error", "message": "invalid llm choice"}), 400


NEO4J_CONSOLE_URL = "https://workspace-preview.neo4j.io/?connectURL=neo4j%2Bs%3A%2F%2Fneo4j%4020d077bf.databases.neo4j.io%3A7687&instanceName=Paper2Graph&ntid=auth0%7C6482ae0be0fef058d606edfb&_ga=2.164858559.108545494.1687387686-1365613772.1686597025"


@app.route("/neo4j")
async def neo4j_page():
    return redirect(NEO4J_CONSOLE_URL)


def _setup_nav_links(app_mode="paper2graph"):
    if app_mode == "querymydrive":
        app.config["nav_links"] = [
            {"name": "Home", "url": "/"},
            {"name": "Ingest", "url": "/gdrive"},
        ]
        return
    elif app_mode == "rarediseaseguru":
        app.config["nav_links"] = [
            {"name": "Home", "url": "/"},
        ]
        return

    nav_links = [
        {"name": "Home", "url": "/"},
        {"name": "Batch Processing", "url": "/batch"},
        {"name": "Query", "url": "/query"},
        {"name": "Ingest", "url": "/gdrive"},
        {"name": "Neo4j", "url": "/neo4j"},
    ]
    if app.config.get("PAPERS_DIR"):
        nav_links.insert(3, {"name": "Search", "url": "/search"})

    app.config["nav_links"] = nav_links


@app.before_serving
async def server_setup():
    utils.setup_logger(**app.config["logger"])
    log_msg("Logger initialized")
    utils.log_config_vars(app.config)

    app_mode = app.config.get("APP_MODE", "paper2graph")
    _setup_nav_links(app_mode=app_mode)


@app.before_serving
async def openai_setup():
    gpt.init_module(app.config)


@app.before_serving
async def batch_job_setup():
    batch.setup_status_file()


@app.before_serving
async def simon_setup():
    app.simon_client = simon_client.SimonClient(app.config)


@app.before_serving
async def gdrive_ingest_setup():
    app.gdrive_simon_client = simon_client.SimonClient(
        app.config, uid_override="querymydrive"
    )


@app.before_serving
async def search_setup():
    papers_dir = app.config.get("PAPERS_DIR", None)
    if not papers_dir:
        log_msg("PAPERS_DIR not configured, /search will not be available")
        return

    # Walk papers_dir and count all .txt files
    # Only do this once, at server startup, because it may be slow for very large numbers of files
    log_msg(f"Counting papers in {papers_dir} that will be available for /search...")
    paper_count = 0
    for _, _, files in os.walk(papers_dir):
        paper_count += len(
            [file for file in files if os.path.splitext(file)[1] == ".txt"]
        )
    log_msg(f"{paper_count:,} papers found!")

    app.search_config = {
        "papers_dir": papers_dir,
        "paper_count": paper_count,
        "metadata_file": app.config.get("PAPERS_METADATA_FILE", None),
    }
    log_msg(f"Search config: {app.search_config}")


if __name__ == "__main__":
    print("Starting server...")
    if app.config.get("DEV_SERVER"):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        app.run(host="127.0.0.1", port=5001, debug=True)
    else:
        app.run_server(use_reloader=False)
