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
    uri = neo_config['uri']
    user = neo_config['user']
    password = neo_config['password']

    def mask_password(pwd):
        if not pwd:
            return '***'
        if len(pwd) <= 6:
            return '*' * len(pwd)
        return pwd[:2] + '...' + pwd[-2:]

    params_for_log = {
        'uri': uri,
        'user': user,
        'password': mask_password(password),
        'password_length': len(password) if password else 0
    }
    log_msg(f'Connecting to Neo4j database with parameters:\n{json.dumps(params_for_log, indent=2)}')

    # Create a Neo4j driver instance
    return GraphDatabase.driver(uri, auth=(user, password))
