import argparse
import os
import re
import threading

import aws
import neo
import utils
from utils import log_msg


def load_source_strings(sources_path):
    sources = aws.get_objects_at_s3_uri(sources_path)
    sources_by_filename = {}
    for s in sources:
        name = os.path.basename(s)
        sources_by_filename[name] = aws.s3_uri_to_http(s)

    log_msg(f'Loaded {len(sources_by_filename)} source strings')

    return sources_by_filename


def exract_article_id_from_source(source_url):
    pattern = r'PMC\d+\.txt'
    match = re.search(pattern, source_url)
    if match:
        return match.group(0)
    else:
        return None


def update_node_sources(neo4j_driver, sources_by_filename):
    mod_timestamp = neo.make_timestamp()
    with neo4j_driver.session() as session:
        nodes_with_json_sources = list(session.run(
            'MATCH (n:Entity) '
            'WHERE ANY('
            'source in n.sources WHERE source ENDS WITH ".json"'
            ') '
            'RETURN ID(n), n.sources'
        ))
        log_msg(f'Found {len(nodes_with_json_sources)} nodes with JSON sources')

        nodes_to_update = []
        for record in nodes_with_json_sources:
            node_id = record['ID(n)']
            sources = record['n.sources']
            fixed_sources = []
            changed_any = False
            for source in sources:
                if not source.endswith('.json'):
                    fixed_sources.append(source)
                    continue

                source_id = exract_article_id_from_source(source)
                fixed_source = sources_by_filename.get(source_id, None)
                if fixed_source is not None:
                    fixed_sources.append(fixed_source)
                    changed_any = True
                else:
                    fixed_sources.append(source)
            if changed_any:
                nodes_to_update.append((node_id, fixed_sources))

        log_msg(f'Found total of {len(nodes_to_update)} nodes to update')
        for i in range(0, len(nodes_to_update), 500):
            nodes_data = [
                {"id": node_id, "sources": sources}
                for node_id, sources in nodes_to_update[i:i + 500]
            ]
            session.run(
                "UNWIND $nodes_data as node "
                "MATCH (n:Entity) "
                "WHERE ID(n) = node.id "
                "SET "
                '  n.sources = node.sources,'
                "  n.last_modified = datetime($timestamp)",
                nodes_data=nodes_data,
                timestamp=mod_timestamp)
            log_msg(f'Updated {i + len(nodes_data)} nodes')


def update_relationship_sources(neo4j_driver, sources_by_filename):
    mod_timestamp = neo.make_timestamp()
    with neo4j_driver.session() as session:
        rels_with_json_sources = list(session.run(
            'MATCH ()-[r]-() '
            'WHERE ANY('
            'source in r.sources WHERE source ENDS WITH ".json"'
            ') '
            'RETURN ID(r), r.sources'
        ))
        log_msg(f'Found {len(rels_with_json_sources)} relationships with JSON sources')

        rels_to_update = []
        for record in rels_with_json_sources:
            relationship_id = record['ID(r)']
            sources = record['r.sources']
            fixed_sources = []
            changed_any = False
            for source in sources:
                if not source.endswith('.json'):
                    fixed_sources.append(source)
                    continue

                source_id = exract_article_id_from_source(source)
                fixed_source = sources_by_filename.get(source_id, None)
                if fixed_source is not None:
                    fixed_sources.append(fixed_source)
                    changed_any = True
                else:
                    fixed_sources.append(source)
            if changed_any:
                rels_to_update.append((relationship_id, fixed_sources))

        log_msg(f'Found total of {len(rels_to_update)} relationships to update')
        for i in range(0, len(rels_to_update), 500):
            rels_data = [
                {"id": rel_id, "sources": sources}
                for rel_id, sources in rels_to_update[i:i + 500]
            ]
            session.run(
                "UNWIND $rels_data as rel "
                "MATCH ()-[r]-() "
                "WHERE ID(r) = rel.id "
                "SET "
                '  r.sources = rel.sources,'
                "  r.last_modified = datetime($timestamp)",
                rels_data=rels_data,
                timestamp=mod_timestamp)
            log_msg(f'Updated {i + len(rels_data)} relationships')


async def main(args):
    thread_name = utils.ENT_TYPES_THREAD_NAME
    threading.current_thread().setName(thread_name)

    config = utils.environment.load_config(cl_args=args)
    utils.setup_logger(name=thread_name, **config['logger'])
    log_msg('Logger initialized')

    sources_by_filename = load_source_strings(args.sources_dir)

    driver = neo.get_neo4j_driver(config['neo4j'])

    try:
        update_node_sources(driver, sources_by_filename)
        update_relationship_sources(driver, sources_by_filename)

        log_msg('Done!')
    finally:
        driver.close()


def parse_args(args):
    parser = argparse.ArgumentParser(description='Fix source strings in Neo4j')

    parser.add_argument(
        '--sources_dir',
        default=None,
        help='Path to canonical sources'
    )
    utils.add_logger_args(parser)
    utils.add_neo_credential_override_args(parser)

    return parser.parse_args(args)
