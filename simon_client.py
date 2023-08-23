import asyncio
import json
import sys
import time

from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings

from elasticsearch import Elasticsearch

# Add submodule dir to path to allow imports
sys.path.append('./simon')
from simon import AgentContext, Search

import utils
from utils import log_msg


class SimonClient:
    def __init__(self, config):
        self.config = config
        self._search_client = self._search_client_from_config(config)

    def _search_client_from_config(self, config):
        openai_api_key = config['OPENAI_API_KEY']
        llm = ChatOpenAI(openai_api_key=openai_api_key, model_name="gpt-3.5-turbo", temperature=0)
        reason_llm = ChatOpenAI(openai_api_key=openai_api_key, model_name="gpt-4", temperature=0)
        embedding = OpenAIEmbeddings(openai_api_key=openai_api_key, model="text-embedding-ada-002")

        es = Elasticsearch(**config['elastic'])
        uid = 'paper2graph'

        context = AgentContext(llm, reason_llm, embedding, es, uid)
        return Search(context)

    async def query_simon(self, query):
        log_msg(f'Querying Simon with query: "{query}"')
        a = time.time()
        result = await asyncio.to_thread(lambda: self._search_client.query(query))
        b = time.time()
        res_for_logs = json.dumps(result, indent=2)
        log_msg(f'Simon query completed in {(a-b):.2f} seconds. Result:\n{res_for_logs}')

        return result


if __name__ == '__main__':
    config = utils.environment.load_config()
    utils.setup_logger(**config['logger'])
    log_msg('Logger initialized')

    client = SimonClient(config)

    start_time = time.time()
    result = asyncio.run(client.query_simon("What do I know about vestibular migraines?"))
    end_time = time.time()
    print(f'Simon query completed in {end_time - start_time:.2f} seconds')
    print(f'Query result:\n{json.dumps(result, indent=2)}')
