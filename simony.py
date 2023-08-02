import json
import sys
import time

from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings

from elasticsearch import Elasticsearch

from simon import AgentContext, Assistant, KnowledgeBase
from simon import environment

from utils import log_msg


async def query_simon(query):
    log_msg(f'Querying Simon with query: {query}')

    log_msg(f'Initializing Simon...')
    env_vars = environment.get_env_vars()
    KEY = env_vars.get("OPENAI_KEY")
    ES_CONFIG = env_vars.get('ES_CONFIG')

    llm = ChatOpenAI(openai_api_key=KEY, model_name="gpt-4", temperature=0)
    # llm = OpenAI(openai_api_key=KEY, model_name="gpt-4")
    embedding = OpenAIEmbeddings(openai_api_key=KEY, model="text-embedding-ada-002")

    # db
    es = Elasticsearch(**ES_CONFIG)
    # UID = "test-uid"
    # UID = "test-uid-alt"
    UID = 'paper2graph'

    # # serialize all of the above together
    context = AgentContext(llm, embedding, es, UID)

    # provision our data sources (knowledgebase is provided by default
    # but initialized here for debug)
    kb = KnowledgeBase(context)
    providers = []

    # create assistant
    assistant = Assistant(context, providers, verbose=True)

    log_msg(f'Simon initialized. Querying Simon...')

    a = time.time()
    assistant_result = assistant(query)
    b = time.time()
    res_for_logs = json.dumps(assistant_result, sort_keys=True, indent=2)
    log_msg(f'Simon query completed in {(a-b):.2f} seconds. Result:\n{res_for_logs}')

    return assistant_result


if __name__ == '__main__':
    sys.path.insert(0, '/home/phillip/Code/simon')

    env_vars = environment.get_env_vars()
    KEY = env_vars.get("OPENAI_KEY")
    ES_CONFIG = env_vars.get('ES_CONFIG')

    llm = ChatOpenAI(openai_api_key=KEY, model_name="gpt-4", temperature=0)
    # llm = OpenAI(openai_api_key=KEY, model_name="gpt-4")
    embedding = OpenAIEmbeddings(openai_api_key=KEY, model="text-embedding-ada-002")

    # db
    es = Elasticsearch(**ES_CONFIG)
    # UID = "test-uid"
    # UID = "test-uid-alt"
    UID = 'ingest_files'

    # # serialize all of the above together
    context = AgentContext(llm, embedding, es, UID)

    # provision our data sources (knowledgebase is provided by default
    # but initialized here for debug)
    kb = KnowledgeBase(context)
    providers = []

    # create assistant
    assistant = Assistant(context, providers, verbose=True)

    a = time.time()
    assistant_result = assistant("What do I know about vestibular migraines?")
    b = time.time()
    print(json.dumps(assistant_result, sort_keys=True, indent=4))

    print(b - a)
