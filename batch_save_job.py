import argparse
import asyncio

import save



TEST_INPUT = '''
[
  {
    "Trifluoperazine": {
      "may treat": "Wilms' Tumor",
      "antagonizes": "CALM1"
    },
    "CALM1": {
      "regulated by": "Trifluoperazine",
      "regulates": "IL-6"
    },
    "IL-6": {
      "associated with": "Wilms' Tumor",
      "regulated by": "CALM1"
    }
  }
]
'''

async def __load_input(data_source):
    return TEST_INPUT


async def save_to_neo4j(data_source, neo_uri):
    input = await __load_input(data_source)
    save.save_json_array(input)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--data_source', help="The URI for the data to be ingested, like an S3 bucket location.")
    parser.add_argument(
        '--neo_uri', help="The URI for the Neo4j instance to save loaded data to.")
    args = parser.parse_args()

    asyncio.run(
        save_to_neo4j(args.data_source, args.neo_uri)
    )
