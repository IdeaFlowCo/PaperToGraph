import argparse
import threading

import aws
import neo
import utils
from utils import log_msg


def update_source_uri(source_uri):
    return aws.s3_uri_to_http(source_uri)


def update_nodes(tx, update_function):
    update_count = 0
    timestamp = neo.make_timestamp()
    result = tx.run("MATCH (n) WHERE n.sources IS NOT NULL RETURN n")
    for record in result:
        node = record['n']
        new_sources = [update_function(source) for source in node['sources']]
        tx.run(
            "MATCH (n) "
            "WHERE id(n) = $id "
            "SET "
            "  n.sources = $sources, "
            "  n.last_modified = datetime($timestamp) "
            "RETURN n",
            id=node.id,
            sources=new_sources,
            timestamp=timestamp
        )
        if result.peek() is not None:
            update_count += 1
        if update_count % 500 == 0:
            log_msg(f'{update_count} nodes updated so far...')
    log_msg(f'Updated {update_count} nodes.')


def update_relationships(tx, update_function):
    update_count = 0
    timestamp = neo.make_timestamp()
    result = tx.run("MATCH ()-[r]-() WHERE r.sources IS NOT NULL RETURN r")
    for record in result:
        relationship = record['r']
        new_sources = [update_function(source) for source in relationship['sources']]
        tx.run(
            "MATCH ()-[r]-() "
            "WHERE id(r) = $id "
            "SET "
            "  r.sources = $sources, "
            "  r.last_modified = datetime($timestamp) "
            "RETURN r",
            id=relationship.id,
            sources=new_sources,
            timestamp=timestamp
        )
        if result.peek() is not None:
            update_count += 1
        if update_count % 500 == 0:
            log_msg(f'{update_count} relationships updated so far...')
    log_msg(f'Updated {update_count} relationships.')


def update_sources(neo4j_driver=None):
    with neo4j_driver.session() as session:
        session.execute_write(update_nodes, update_source_uri)
        session.execute_write(update_relationships, update_source_uri)


def main(args):
    thread_name = utils.GRAPH_SOURCES_THREAD_NAME
    threading.current_thread().setName(thread_name)
    utils.setup_logger(name=thread_name)
    log_msg('Logger initialized')

    neo_config = utils.neo_config_from_args_or_env(args)
    driver = neo.get_neo4j_driver(neo_config)

    try:
        update_sources(driver)
    finally:
        driver.close()


def parse_args():
    parser = argparse.ArgumentParser(description='Correct source URIs in the graph')

    utils.add_neo_credential_override_args(parser)

    return parser
