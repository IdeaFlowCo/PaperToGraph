'''
Functions for saving parsed data to Neo4j.
'''

import hashlib
import json

import aws
import neo
from utils import log_msg, log_warn, log_error


def _save_dict_of_entities(neo_driver, data, source=None, timestamp=None):
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
                f'Unexpected value in entity dict for "{ent_name}". Expected dict of relationships -> targets, got: {type(ent_data)}')
            log_warn(ent_data)
            log_warn("Won't be saving this entity.")
            continue
        ent = neo.EntityRecord.from_json_entry(
            ent_name, ent_data, source, timestamp)
        if ent.has_data_to_save():
            ent.save_to_neo(neo_driver)
            ent.save_relationships_to_neo(neo_driver)


def save_data_to_neo4j(data, source_uri=None, neo_config=None):
    if not source_uri:
        raise ValueError('Must provide a source URI for the input data.')
    # Ensure save input URI is an HTTP URL for easy access from Neo4j
    source_uri = aws.s3_uri_to_http(source_uri)

    # Create a Neo4j driver instance
    driver = neo.get_neo4j_driver(neo_config)

    # Use a single timestamp for marking creation/modification time of all entities and relationships in this run
    timestamp = neo.make_timestamp()

    try:
        if isinstance(data, dict):
            _save_dict_of_entities(
                driver, data, source=source_uri, timestamp=timestamp)
        elif isinstance(data, list):
            for obj in data:
                _save_dict_of_entities(
                    driver, obj, source=source_uri, timestamp=timestamp)
        else:
            log_error(
                f'Unexpected input type. Expected dict or list, got: {type(data)}')
            log_error(f'Exact string received: "{data}"')
            log_error(f'Parsed as: {data}')
            raise Exception(
                f'Unexpected input: {data}')
    finally:
        driver.close()


WEB_SUBMISSIONS_URI = 's3://paper2graph-parse-inputs/web-submissions/'
HASH_SLUG_LENGTH = 12


def save_input_text_to_s3(text):
    hash_slug = hashlib.sha256(text.encode('utf-8')).hexdigest()
    hash_slug = hash_slug[:HASH_SLUG_LENGTH]
    output_uri = f'{WEB_SUBMISSIONS_URI.rstrip("/")}/{hash_slug}.txt'
    log_msg(f'Saving input text to {output_uri}')
    # This call will raise Exception if any issue, but just let that bubble up:
    aws.write_to_s3_file(output_uri, text)
    return output_uri
