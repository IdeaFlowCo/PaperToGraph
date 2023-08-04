import argparse
import csv
from datetime import datetime
import re
import threading

import neo
import utils
from utils import log_msg


def load_source_dates(dates_file):
    source_dates = {}
    counter = 0
    with open(dates_file, 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            try:
                update_ts = datetime.strptime(row[1], "%Y %b %d")
            except ValueError:
                continue
            # split the path by '/' and get the last element (article name)
            article_file_name = row[0].split('/')[-1]
            source_dates[article_file_name] = update_ts
            counter += 1
            if counter % 100000 == 0:
                log_msg(f'Loaded {counter} source dates')
    log_msg('Source dates loaded')
    return source_dates


def exract_article_id_from_source(source_url):
    pattern = r'PMC\d+\.txt'
    match = re.search(pattern, source_url)
    if match:
        return match.group(0)
    else:
        return None


def update_node_source_dates(neo4j_driver, source_dates):
    mod_timestamp = neo.make_timestamp()
    with neo4j_driver.session() as session:
        nodes_to_update = session.run(
            "MATCH (n:Entity)"
            "WHERE "
            "n._EARLIEST_SOURCE_DATE IS NULL AND "
            "n.sources IS NOT NULL "
            "RETURN n.normalized_name, n.sources"
        )
        num_updated = 0

        nodes_with_date = []
        nodes_without_date = []
        for record in nodes_to_update:
            normalized_name = record['n.normalized_name']
            sources = record['n.sources']
            earliest_source_date = None
            for source in sources:
                source_id = exract_article_id_from_source(source)
                source_date = source_dates.get(source_id, None)
                if source_date is not None:
                    if earliest_source_date is None or source_date < earliest_source_date:
                        earliest_source_date = source_date
            if earliest_source_date is not None:
                nodes_with_date.append((normalized_name, earliest_source_date))
            else:
                nodes_without_date.append(normalized_name)
            if len(nodes_with_date) + len(nodes_without_date) >= 15000:
                nodes_with_date_data = [
                    {"name": normalized_name, "date": earliest_source_date}
                    for normalized_name, earliest_source_date in nodes_with_date
                ]
                session.run(
                    "UNWIND $nodes_data as node "
                    "MATCH (n:Entity {normalized_name: node.name}) "
                    "SET "
                    '  n._EARLIEST_SOURCE_DATE = "UNKNOWN",'
                    "  n.last_modified = datetime($timestamp)",
                    nodes_data=nodes_with_date_data,
                    timestamp=mod_timestamp)
                num_updated += len(nodes_with_date)
                log_msg(f'Updated {num_updated} nodes')
                nodes_without_date_data = [
                    {"name": normalized_name}
                    for normalized_name in nodes_without_date
                ]
                session.run(
                    "UNWIND $nodes_data as node "
                    "MATCH (n:Entity {normalized_name: node.name}) "
                    "SET "
                    '  n._EARLIEST_SOURCE_DATE = "UNKNOWN",'
                    "  n.last_modified = datetime($timestamp)",
                    nodes_data=nodes_without_date_data,
                    timestamp=mod_timestamp)
                num_updated += len(nodes_without_date)
                log_msg(f'Updated {num_updated} nodes')
                nodes_with_date = []
                nodes_without_date = []

        nodes_with_date_data = [
            {"name": normalized_name, "date": earliest_source_date}
            for normalized_name, earliest_source_date in nodes_with_date
        ]
        session.run(
            "UNWIND $nodes_data as node "
            "MATCH (n:Entity {normalized_name: node.name}) "
            "SET "
            '  n._EARLIEST_SOURCE_DATE = "UNKNOWN",'
            "  n.last_modified = datetime($timestamp)",
            nodes_data=nodes_with_date_data,
            timestamp=mod_timestamp)
        num_updated += len(nodes_with_date)
        log_msg(f'Updated {num_updated} nodes')
        nodes_without_date_data = [
            {"name": normalized_name}
            for normalized_name in nodes_without_date
        ]
        session.run(
            "UNWIND $nodes_data as node "
            "MATCH (n:Entity {normalized_name: node.name}) "
            "SET "
            '  n._EARLIEST_SOURCE_DATE = "UNKNOWN",'
            "  n.last_modified = datetime($timestamp)",
            nodes_data=nodes_without_date_data,
            timestamp=mod_timestamp)
        num_updated += len(nodes_without_date)
        log_msg(f'Updated {num_updated} nodes')


def update_relationship_source_dates(neo4j_driver, source_dates):
    mod_timestamp = neo.make_timestamp()
    with neo4j_driver.session() as session:
        relationships_to_update = session.run(
            "MATCH ()-[r]-()"
            "WHERE "
            # "r._EARLIEST_SOURCE_DATE IS NULL AND "
            "r.sources IS NOT NULL "
            "RETURN ID(r), r.sources"
        )
        num_updated = 0
        relationships_with_date = []
        relationships_without_date = []
        for record in relationships_to_update:
            relationship_id = record['ID(r)']
            sources = record['r.sources']
            earliest_source_date = None
            for source in sources:
                source_id = exract_article_id_from_source(source)
                source_date = source_dates.get(source_id, None)
                if source_date is not None:
                    if earliest_source_date is None or source_date < earliest_source_date:
                        earliest_source_date = source_date
            if earliest_source_date is not None:
                relationships_with_date.append((relationship_id, earliest_source_date))
            else:
                relationships_without_date.append(relationship_id)
            if len(relationships_with_date) + len(relationships_without_date) >= 15000:
                session.run(
                    "UNWIND $rels_data as rel "
                    "MATCH ()-[r]-() "
                    "WHERE ID(r) = rel.id "
                    "SET "
                    "  r._EARLIEST_SOURCE_DATE = datetime(rel.date),"
                    "  r.last_modified = datetime($timestamp)",
                    rels_data=[{"id": rel_id, "date": earliest_source_date} for rel_id,
                               earliest_source_date in relationships_with_date],
                    timestamp=mod_timestamp)
                num_updated += len(relationships_with_date)
                log_msg(f'Updated {num_updated} relationships')
                session.run(
                    "UNWIND $rels_data as rel "
                    "MATCH ()-[r]-() "
                    "WHERE ID(r) = rel.id "
                    "SET "
                    '  r._EARLIEST_SOURCE_DATE = "UNKNOWN",'
                    "  r.last_modified = datetime($timestamp)",
                    rels_data=[{"id": rel_id} for rel_id in relationships_without_date],
                    timestamp=mod_timestamp)
                num_updated += len(relationships_without_date)
                log_msg(f'Updated {num_updated} relationships')
                relationships_with_date = []
                relationships_without_date = []
        session.run(
            "UNWIND $rels_data as rel "
            "MATCH ()-[r]-() "
            "WHERE ID(r) = rel.id "
            "SET "
            "  r._EARLIEST_SOURCE_DATE = datetime(rel.date),"
            "  r.last_modified = datetime($timestamp)",
            rels_data=[{"id": rel_id, "date": earliest_source_date} for rel_id,
                       earliest_source_date in relationships_with_date],
            timestamp=mod_timestamp)
        num_updated += len(relationships_with_date)
        log_msg(f'Updated {num_updated} relationships')
        session.run(
            "UNWIND $rels_data as rel "
            "MATCH ()-[r]-() "
            "WHERE ID(r) = rel.id "
            "SET "
            '  r._EARLIEST_SOURCE_DATE = "UNKNOWN",'
            "  r.last_modified = datetime($timestamp)",
            rels_data=[{"id": rel_id} for rel_id in relationships_without_date],
            timestamp=mod_timestamp)
        num_updated += len(relationships_without_date)
        log_msg(f'Updated {num_updated} relationships')


async def main(args):
    thread_name = utils.ENT_TYPES_THREAD_NAME
    threading.current_thread().setName(thread_name)

    config = utils.environment.load_config(cl_args=args)
    utils.setup_logger(name=thread_name, **config['logger'])
    log_msg('Logger initialized')

    source_dates = load_source_dates(args.dates_file)

    driver = neo.get_neo4j_driver(config['neo4j'])

    try:
        update_node_source_dates(driver, source_dates)
        update_relationship_source_dates(driver, source_dates)

        log_msg('Done!')
    finally:
        driver.close()


def parse_args(args):
    parser = argparse.ArgumentParser(description='Enrich source dates in Neo4j')

    parser.add_argument(
        '--debug',
        action='store_true',
        default=False,
        help='Enable debug logging'
    )
    parser.add_argument(
        '--log_file',
        default=None,
        help='Mirror logs to a file in addition to stdout'
    )
    parser.add_argument(
        '--dates_file',
        default=None,
        help='File containing dates for source articles'
    )
    utils.add_neo_credential_override_args(parser)

    return parser.parse_args(args)
