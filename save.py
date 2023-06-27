'''
Functions for saving parsed data to Neo4j.
'''

import hashlib
import json

import aws
import neo
from utils import log_msg



def save_dict_of_entities(neo_driver, data, source=None, created_ts=None):
    if not created_ts:
        created_ts = neo.get_timestamp()

    for name, relationships in data.items():
        neo.create_or_update_entity(neo_driver, name, source, created_ts)
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
            relationship_name = neo.sanitize_relationship_name(relationship_name)
            if not isinstance(target, list):
                target = [target]
            for t in target:
                neo.create_or_update_entity(neo_driver, t, source, created_ts)
                neo.create_or_update_relationships(neo_driver, name, relationship_name, t, source, created_ts)


def save_json_data(json_str, saved_input_uri=None, neo_config=None):
    # Create a Neo4j driver instance
    driver = neo.get_driver_for_config(neo_config)

    # Use a single timestamp for marking creation time of all entities/relationships in this run
    created_ts = neo.get_timestamp()

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
