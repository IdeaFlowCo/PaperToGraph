'''
Shared utility functions frequently used when working with Neo4j.
'''

import json
from re import sub

from neo4j import GraphDatabase
from neo4j.time import DateTime

from utils import log_msg


def normalize_entity_name(ent_name):
    # Just convert to lowercase for now
    return ent_name.lower()


def sanitize_relationship_name(relationship):
    # Replace illegal chars with _
    relationship = relationship.replace('/', '_').replace('.', '_').replace('%', '_')
    # Replace - with a space
    relationship = relationship.replace('-', ' ')
    # Transform remainder to snake case (NamedThing or 'Named Thing' to named_thing, etc)
    return '_'.join(
        sub('([A-Z][a-z]+)', r' \1',
            sub('([A-Z]+)', r' \1',
                relationship)).split()).lower()


def make_timestamp():
    return DateTime.now()


def get_neo4j_driver(neo_config):
    if not neo_config:
        neo_config = {}

    # Ignore any config values that are None or empty strings
    neo_config = {k: v for k, v in neo_config.items() if v}

    uri = neo_config.get('uri', 'neo4j+s://20d077bf.databases.neo4j.io')
    user = neo_config.get('user', 'neo4j')
    password = neo_config.get('password', 'VNfVHsSRzfTZlRRDTDluxFvi6PfLtwkO_5JTxJCV3Mc')

    params_for_log = {
        'uri': uri,
        'user': user,
        'password': 'DEFAULT' if 'password' not in neo_config else password[:3] + '...' + password[-3:]
    }
    log_msg(f'Connecting to Neo4j database with the following parameters:\n{json.dumps(params_for_log, indent=2)}')

    # Create a Neo4j driver instance
    return GraphDatabase.driver(uri, auth=(user, password))
