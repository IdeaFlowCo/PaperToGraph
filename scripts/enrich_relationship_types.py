import argparse
import csv
import re
import threading

import gpt
import neo
import utils
from utils import log_msg, log_debug, log_warn


RELATIONSHIP_TYPES = {
    "Promotes",
    "Inhibits",
    "Associated With",
    "Disconnected From",
    "Other",
}

CSV_FIELDS = ["rel_name", "type"]


def _get_all_relationship_names(neo4j_driver):
    with neo4j_driver.session() as session:
        query = (
            "MATCH ()-[r]-() "
            "WITH type(r) AS relationshipType, COUNT(r) AS count "
            "RETURN relationshipType "
            "ORDER BY count DESC"
        )
        result = session.run(query)
        return [record["relationshipType"] for record in result]


def _get_rel_types_from_file(source_file):
    pairs = []
    with open(source_file, "r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            if row["type"] not in RELATIONSHIP_TYPES:
                log_warn(
                    f'Source file line [{i}]: relationship type "{row["type"]}" not recognized, skipping'
                )
                continue
            nt_pair = (row["rel_name"], row["type"])
            pairs.append(nt_pair)
    return pairs


async def _get_rel_types_from_gpt(relationship_names, gpt_model):
    name_type_pairs = []
    max_input_tokens = gpt.rel_types.get_input_token_limit(gpt_model)
    tries = 0
    # GPT output might be invalid, so we'll potentially try up to 3 times to get valid output
    while relationship_names and tries < 3:
        rel_name_chunks = gpt.split_input_list_to_chunks(
            relationship_names, max_input_tokens, model=gpt_model
        )
        for chunk in rel_name_chunks:
            log_debug(chunk)
            result_str = await gpt.fetch_relationship_types(chunk, model=gpt_model)
            log_debug(result_str)

            # Results should be in the form
            # ("relationship name", "relationship type")
            name_type_pattern = r'\("(.*?)"\s*,\s*"(.*?)"\)'
            re_results = re.findall(name_type_pattern, result_str)

            for result in re_results:
                name, ent_type = result
                # Only want to include results where the entity type is in our list of valid types
                if ent_type in RELATIONSHIP_TYPES:
                    name_type_pairs.append((name, ent_type))
                elif name in RELATIONSHIP_TYPES:
                    # Sometimes GPT gets the tuple order confused; if the name is a valid type, swap the order
                    name_type_pairs.append((ent_type, name))

        mapped_names = [pair[0] for pair in name_type_pairs]
        relationship_names = [
            name for name in relationship_names if name not in mapped_names
        ]
        tries += 1

    log_debug(name_type_pairs)
    return name_type_pairs


def _get_rel_types_from_log(log_file):
    name_type_pairs = []
    seen_names = set()
    with open(log_file, "r") as f:
        contents = f.read()
        # Results should be in the form
        # ("relationship name", "relationship type")
        name_type_pattern = r'\("(.*?)"\s*,\s*"(.*?)"\)'
        re_results = re.findall(name_type_pattern, contents)
        for result in re_results:
            name, ent_type = result
            # Only want to include results where the entity type is in our list of valid types
            if ent_type in RELATIONSHIP_TYPES and name not in seen_names:
                name_type_pairs.append((name, ent_type))
                seen_names.add(name)
            elif name in RELATIONSHIP_TYPES and ent_type not in seen_names:
                # Sometimes GPT gets the tuple order confused; if the name is a valid type, swap the order
                name_type_pairs.append((ent_type, name))
                seen_names.add(name)
    return name_type_pairs


def _write_typings_to_file(name_type_pairs, output_file):
    with open(output_file, "w") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for nt_pair in name_type_pairs:
            data_dict = {"rel_name": nt_pair[0], "type": nt_pair[1]}
            writer.writerow(data_dict)


def _update_relationship_types(neo4j_driver, rel_name_type_pairs):
    update_count = 0
    mod_timestamp = neo.make_timestamp()
    # Update in chunks of 500 to avoid session timeouts
    for i in range(0, len(rel_name_type_pairs), 500):
        update_chunk = rel_name_type_pairs[i : i + 500]
        log_msg(
            f"Updating {len(update_chunk)} of {len(rel_name_type_pairs)} relationships..."
        )
        with neo4j_driver.session() as session:
            for rel_name, rel_type in update_chunk:
                result = session.run(
                    "MATCH ()-[r]-() "
                    "WHERE type(r) = $rel_name "
                    "SET "
                    "  r._INHIBITS_PROMOTES_OR_OTHER = $rel_type, "
                    "  r.last_modified = datetime($timestamp) "
                    "RETURN r",
                    rel_name=rel_name,
                    rel_type=rel_type,
                    timestamp=mod_timestamp,
                )
                if result.peek() is not None:
                    update_count += 1
    return update_count


async def main(args):
    thread_name = utils.REL_TYPES_THREAD_NAME
    threading.current_thread().setName(thread_name)

    config = utils.environment.load_config(cl_args=args)
    utils.setup_logger(name=thread_name, **config["logger"])
    log_msg("Logger initialized")

    gpt.init_module(config)

    try:
        if args.source_file:
            log_msg(f"Reading name/type pairs from file {args.recover_previous}")
            name_type_pairs = _get_rel_types_from_file(args.source_file)
            log_msg(f"Loaded {len(name_type_pairs)} name/type pairs.")
        elif args.recover_previous:
            log_msg(f"Recovering name/type pairs from log file {args.recover_previous}")
            name_type_pairs = _get_rel_types_from_log(args.recover_previous)
            log_msg(
                f"Recovered {len(name_type_pairs)} name/type pairs from previous run's log file."
            )
        else:
            driver = neo.get_neo4j_driver(config["neo4j"])
            relationship_names = _get_all_relationship_names(driver)
            log_msg(f"Loaded {len(relationship_names)} relationships from Neo4j.")

            if args.top_n:
                relationship_names = relationship_names[: args.top_n]
                log_msg(
                    f"--top_n set to {args.top_n}, retrieving types for {len(relationship_names)} relationships."
                )

            log_msg("Fetching name/type pairs from GPT...")
            name_type_pairs = await _get_rel_types_from_gpt(
                relationship_names, args.gpt_model
            )
            log_msg(f"Received {len(name_type_pairs)} name/type pairs from GPT.")

        if args.output_file:
            log_msg(f"Writing name/type pairs to {args.output_file}")
            _write_typings_to_file(name_type_pairs, args.output_file)
        else:
            log_msg("Updating relationship types in Neo4j...")
            driver = neo.get_neo4j_driver(config["neo4j"])
            num_updated = _update_relationship_types(driver, name_type_pairs)
            log_msg(f"Set types on {num_updated} relationships.")

        log_msg("Done!")
    finally:
        driver.close()


def parse_args(args):
    parser = argparse.ArgumentParser(description="Enrich entity types with GPT")

    parser.add_argument(
        "--gpt_model",
        default="gpt-4o-mini",
        help="Name of the GPT model to use for relationship typing",
    )
    parser.add_argument(
        "--top_n",
        type=int,
        default=0,
        help="Only retrieve types for the top N most occuring relationship types; if 0, will fetch all",
    )
    parser.add_argument(
        "--output_file",
        default=None,
        help="Specify a file to write name/type pairs to instead of saving them directly in Neo4j",
    )
    parser.add_argument(
        "--source_file",
        default=None,
        help="Specify file to read name/type pairs from instead of asking GPT to do typing",
    )
    parser.add_argument(
        "--recover_previous",
        default=None,
        help="Specify a log file from a previous run to recover mapped types from instead of using GPT",
    )
    utils.add_logger_args(parser)
    utils.add_neo_credential_override_args(parser)

    return parser.parse_args(args)
