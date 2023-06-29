'''
Functions for saving parsed data to Neo4j.
'''

import hashlib
import json

import aws
import neo
from utils import log_msg, log_warn, log_error


def save_dict_of_entities(neo_driver, data, source=None, timestamp=None):
    if not timestamp:
        timestamp = neo.make_timestamp()

    for ent_name, ent_data in data.items():
        if not isinstance(ent_name, str):
            log_warn(
                f'Unexpected key in entity dict. Expected string, got: {type(ent_name)}')
            log_warn(ent_name)
            log_warn("Won't be saving this entity.")
            continue
        if not isinstance(ent_data, dict):
            log_warn(
                f'Unexpected value in entity dict for "{ent_name}". Expected dict, got: {type(ent_data)}')
            log_warn(ent_data)
            log_warn("Won't be saving this entity.")
            continue
        ent = neo.EntityData.from_json_entry(
            ent_name, ent_data, source, timestamp)
        ent.save_to_neo(neo_driver)
        ent.save_relationships_to_neo(neo_driver)


def save_json_data(json_str, source_uri=None, neo_config=None):
    if not source_uri:
        raise ValueError('Must provide')
    # Ensure save input URI is an HTTP URL for easy access from Neo4j
    source_uri = aws.s3_uri_to_http(source_uri)

    # Create a Neo4j driver instance
    driver = neo.get_neo4j_driver(neo_config)

    # Use a single timestamp for marking creation/modification time of all entities and relationships in this run
    timestamp = neo.make_timestamp()

    try:
        parsed = json.loads(json_str)
        if isinstance(parsed, dict):
            save_dict_of_entities(
                driver, parsed, source=source_uri, timestamp=timestamp)
        elif isinstance(parsed, list):
            for obj in parsed:
                save_dict_of_entities(
                    driver, obj, source=source_uri, timestamp=timestamp)
        else:
            log_error(
                f'Unexpected input type. Expected JSON-encoded object or array, got: {type(parsed)}')
            log_error(f'Exact string received: "{json_str}"')
            log_error(f'Parsed as: {parsed}')
            raise Exception(
                f'Unexpected input: "{json_str}"', f'Parsed as: {parsed}')
    except json.JSONDecodeError as err:
        log_error('Provided input is not valid JSON.')
        log_error(f'Exact string received: "{json_str}"')
        raise err
    finally:
        driver.close()


WEB_SUBMISSIONS_URI = 's3://paper2graph-parse-inputs/web-submissions/'
HASH_SLUG_LENGTH = 12


def save_input_text(text):
    hash_slug = hashlib.sha256(text.encode('utf-8')).hexdigest()
    hash_slug = hash_slug[:HASH_SLUG_LENGTH]
    output_uri = f'{WEB_SUBMISSIONS_URI.rstrip("/")}/{hash_slug}.txt'
    log_msg(f'Saving input text to {output_uri}')
    # This call will raise Exception if any issue, but just let that bubble up:
    aws.write_file_to_s3(output_uri, text)
    return output_uri
