'''
Functions for saving parsed data to Neo4j.
'''

import json
from re import sub

from neo4j import GraphDatabase
from neo4j.time import DateTime

from utils import log_msg


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
def create_entity_if_not_exists(driver, name, timestamp):
    with driver.session() as session:
        result = session.run("MATCH (ent:Entity {name: $name}) RETURN count(ent) AS count", name=name)
        count = result.single()["count"]
        if count == 0:
            session.run(
                # Note: have to call datetime() on created_at here to avoid getting localdatetime types by default
                "CREATE (:Entity {name: $name, created_at: datetime($created_at)})", 
                name=name,
                created_at=timestamp,
            )
            log_msg(f"Entity '{name}' created in the database.")
        else:
            log_msg(f"Entity '{name}' already exists in the database.")


# Function to create a named relationship between two entities if it doesn't exist
def create_relationship_if_not_exists(driver, ent1_name, relationship_name, ent2_name, timestamp):
    with driver.session() as session:
        result = session.run(
            "MATCH (ent1:Entity {name: $ent1_name})-[r:%s]->(ent2:Entity {name: $ent2_name}) RETURN count(r) AS count"
            % (relationship_name),
            ent1_name=ent1_name,
            ent2_name=ent2_name,
        )
        count = result.single()["count"]
        if count == 0:
            session.run(
                "MATCH (ent1:Entity {name: $ent1_name}), (ent2:Entity {name: $ent2_name}) "
                # Note: have to call datetime() on created_at here to avoid getting localdatetime types by default
                "CREATE (ent1)-[r:%s {created_at: datetime($created_at)}]->(ent2)" % (relationship_name),
                ent1_name=ent1_name,
                ent2_name=ent2_name,
                created_at=timestamp,
            )
            log_msg(f"Relationship '{relationship_name}' created between '{ent1_name}' and '{ent2_name}'.")
        else:
            log_msg(f"Relationship '{relationship_name}' already exists between '{ent1_name}' and '{ent2_name}'.")


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


def save_dict_of_entities(neo_driver, data, created_ts=None):
    if not created_ts:
        created_ts = DateTime.now()

    for name, relationships in data.items():
        create_entity_if_not_exists(neo_driver, name, created_ts)
        if not isinstance(relationships, dict):
            # We expect every top level value to be a dict of relationships for the named key.
            # If that's not the case for some reason, just skip it for now
            continue
        for relationship_name, target in relationships.items():
            if not isinstance(relationship_name, str) or not isinstance(target, str):
                # We expect all of these to be str -> str pairs.
                # If that's not the case, just skip for now.
                continue
            create_entity_if_not_exists(neo_driver, target, created_ts)
            relationship_name = sanitize_relationship_name(relationship_name)
            create_relationship_if_not_exists(neo_driver, name, relationship_name, target, created_ts)


def save_json_data(json_str, neo_config=None):
    # Create a Neo4j driver instance
    driver = __get_neo4j_driver(neo_config)

    # Use a single timestamp for marking creation time of all entities/relationships in this run
    created_ts = DateTime.now()

    try:
        parsed = json.loads(json_str)
        if isinstance(parsed, dict):
            save_dict_of_entities(driver, parsed, created_ts=created_ts)
        elif isinstance(parsed, list):
            for obj in parsed:
                save_dict_of_entities(driver, obj, created_ts=created_ts)
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
    
