import argparse
import re
import threading

import gpt
import neo
import utils
from utils import log_msg


ENTITY_TYPES = {
    'Drug',
    'Disease',
    'Other',
}


def get_all_entity_names(neo4j_driver):
    with neo4j_driver.session() as session:
        result = session.run("MATCH (n:Entity) WHERE n.type IS NULL RETURN n.name LIMIT 400")
        return [record['n.name'] for record in result]


async def get_entity_types_from_gpt(entity_names, gpt_model):
    result_str = await gpt.fetch_entity_types(entity_names, model=gpt_model)

    # Results should be in the form
    # ("entity name", "entity type")
    name_type_pattern = r'\("(.*?)"\s*,\s*"(.*?)"\)'
    results = re.findall(name_type_pattern, result_str)

    # Only include results where the entity type is in our list of valid types
    results = [(name, ent_type) for name, ent_type in results if ent_type in ENTITY_TYPES]

    return results


def update_entity_types(neo4j_driver, ent_name_type_pairs):
    update_count = 0
    mod_timestamp = neo.make_timestamp()
    with neo4j_driver.session() as session:
        for ent_name, ent_type in ent_name_type_pairs:
            n_ent_name = neo.normalize_entity_name(ent_name)
            result = session.run(
                "MATCH (n:Entity {normalized_name: $normalized_name}) "
                "SET "
                "  n.type = $ent_type, "
                "  n.last_modified = datetime($timestamp) "
                "RETURN n",
                normalized_name=n_ent_name,
                ent_type=ent_type,
                timestamp=mod_timestamp)
            if result.peek() is not None:
                update_count += 1
    return update_count


async def main(args):
    thread_name = utils.ENT_TYPES_THREAD_NAME
    threading.current_thread().setName(thread_name)
    utils.setup_logger(name=thread_name)
    log_msg('Logger initialized')

    neo_config = utils.neo_config_from_args_or_env(args)
    driver = neo.get_neo4j_driver(neo_config)

    try:
        entity_names = get_all_entity_names(driver)
        while entity_names:
            log_msg(f'Loaded {len(entity_names)} entities to tag with types.')

            log_msg('Using GPT to get entity types for each...')
            name_type_pairs = await get_entity_types_from_gpt(entity_names, args.gpt_model)
            log_msg(f'Received {len(name_type_pairs)} name/type pairs from GPT.')

            log_msg('Updating entity types in Neo4j...')
            num_updated = update_entity_types(driver, name_type_pairs)
            log_msg(f'Set types on {num_updated} entities.')

            entity_names = get_all_entity_names(driver)

        log_msg('Done!')
    finally:
        driver.close()


def parse_args():
    parser = argparse.ArgumentParser(description='Enrich entity types with GPT')

    parser.add_argument(
        '--gpt-model',
        default='gpt-3.5-turbo',
        help='Name of the GPT model to use'
    )
    utils.add_neo_credential_override_args(parser)

    return parser