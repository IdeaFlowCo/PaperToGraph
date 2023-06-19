'''
Functions for saving parsed data to Neo4j.
'''

import hashlib
import json
from re import sub

from neo4j import GraphDatabase
from neo4j.time import DateTime

import aws
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



# Function to create an entity in the database if it doesn't exist
def create_or_update_entity(driver, name, source, timestamp):
    with driver.session() as session:
        normalized_name = normalize_entity_name(name)
        session.run(
            "MERGE (ent:Entity {normalized_name: $normalized_name}) "
            "ON CREATE set ent.name = $name, ent.created_at = datetime($created_at), ent.sources = [$source] "
            "ON MATCH SET ent.sources = CASE "
            "   WHEN ent.sources IS NULL THEN [$source] "
            "   ELSE CASE "
            "       WHEN NOT $source IN ent.sources THEN ent.sources + [$source] "
            "       ELSE ent.sources "
            "   END "
            "END "
            "RETURN ent",
            normalized_name=normalized_name,
            name=name,
            source=source,
            created_at=timestamp,
        )
        # TODO: Check result for any extra logging or error handling logic
        log_msg('Entity created or updated')


# Function to create a named relationship between two entities if it doesn't exist
def create_or_update_relationships(driver, ent1_name, relationship_name, ent2_name, source, timestamp):
    with driver.session() as session:
        n_ent1_name = normalize_entity_name(ent1_name)
        n_ent2_name = normalize_entity_name(ent2_name)
        session.run(
            "MATCH (e1:Entity {normalized_name: $ent1_name}) "
            "MATCH (e2:Entity {normalized_name: $ent2_name}) "
            "MERGE (e1)-[r:%s]->(e2) "
            "ON CREATE SET r.sources = [$source], r.created_at = datetime($created_at) "
            "ON MATCH SET r.sources = CASE "
            "   WHEN r.sources IS NULL THEN [$source] "
            "   ELSE CASE "
            "       WHEN NOT $source IN r.sources THEN r.sources + [$source] "
            "       ELSE r.sources "
            "   END "
            "END "
            "RETURN r"
            % (relationship_name),
            ent1_name=n_ent1_name,
            ent2_name=n_ent2_name,
            source=source,
            created_at=timestamp,
        )
        # TODO: Check result for any extra logging or error handling logic
        log_msg('Relationship created or updated')


def __get_neo4j_driver(neo_config):
    if not neo_config:
        neo_config = {}

    # Ignore any config values that are None or empty strings
    neo_config = {k: v for k, v in neo_config.items() if v}

    uri = neo_config.get('uri', 'neo4j+s://20d077bf.databases.neo4j.io')
    user = neo_config.get('user', 'neo4j')
    password = neo_config.get('password', 'VNfVHsSRzfTZlRRDTDluxFvi6PfLtwkO_5JTxJCV3Mc')

    log_msg('Connecting to Neo4j database with the following parameters:')
    log_msg(f'uri: {uri}')
    log_msg(f'user: {user}')
    if password == 'VNfVHsSRzfTZlRRDTDluxFvi6PfLtwkO_5JTxJCV3Mc':
        log_msg(f'password: DEFAULT')
    else:
        log_msg(f'password: {password[:3]}...{password[-3:]}')

    # Create a Neo4j driver instance
    return GraphDatabase.driver(uri, auth=(user, password))


def save_dict_of_entities(neo_driver, data, source=None, created_ts=None):
    if not created_ts:
        created_ts = DateTime.now()

    for name, relationships in data.items():
        create_or_update_entity(neo_driver, name, source, created_ts)
        if not isinstance(relationships, dict):
            # We expect every top level value to be a dict of relationships for the named key.
            # If that's not the case for some reason, just skip it for now
            continue
        for relationship_name, target in relationships.items():
            # Relationship name is valid if it's a string
            valid_relationship = isinstance(relationship_name, str)
            # Target is valid if it's a string or a list of strings
            valid_target = isinstance(target, str) or (isinstance(target, list) and all(isinstance(t, str) for t in target))
            if not valid_relationship or not valid_target:
                # We expect all of these to be str -> str pairs.
                # If that's not the case, just skip for now.
                continue
            relationship_name = sanitize_relationship_name(relationship_name)
            if not isinstance(target, list):
                target = [target]
            for t in target:
                create_or_update_entity(neo_driver, t, source, created_ts)
                create_or_update_relationships(neo_driver, name, relationship_name, t, source, created_ts)


def save_json_data(json_str, saved_input_uri=None, neo_config=None):
    # Create a Neo4j driver instance
    driver = __get_neo4j_driver(neo_config)

    # Use a single timestamp for marking creation time of all entities/relationships in this run
    created_ts = DateTime.now()

    try:
        parsed = json.loads(json_str)
        if isinstance(parsed, dict):
            save_dict_of_entities(driver, parsed, source=saved_input_uri, created_ts=created_ts)
        elif isinstance(parsed, list):
            for obj in parsed:
                save_dict_of_entities(driver, obj, source=saved_input_uri, created_ts=created_ts)
        else:
            log_msg('Unexpected input type. Expected JSON object or array.')
            log_msg(f'Received: {json_str}')
            log_msg(f'Parsed as: {parsed}')
            raise Exception(f'Unexpected input: {json_str}', f'Parsed as: {parsed}')
    except json.JSONDecodeError as err:
        log_msg('Provided input is not valid JSON.')
        log_msg(f'Received: {json_str}')
        raise err
    finally:
        driver.close()


WEB_SUBMISSIONS_URI = 's3://paper2graph-parse-inputs/web-submissions/'
HASH_SLUG_LENGTH = 12

def save_input_text(text):
    hash_slug = hashlib.sha256(text.encode('utf-8')).hexdigest()[:HASH_SLUG_LENGTH]
    output_uri = f'{WEB_SUBMISSIONS_URI.rstrip("/")}/{hash_slug}.txt'
    log_msg(f'Saving input text to {output_uri}')
    # This call will raise Exception if any issue, but just let that bubble up:
    aws.write_file_to_s3(output_uri, text)
    return output_uri
