'''
Functions for interacting with Neo4j.
'''

from re import sub

from neo4j import GraphDatabase
from neo4j.time import DateTime

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


def get_timestamp():
    return DateTime.now()


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
        log_msg(f'Entity for "{name}" created or updated')


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
        log_msg(f'Relationship "{relationship_name}" created or updated between "{ent1_name}" and "{ent2_name}"')


def find_entities_with_abbreviation(driver, abbreviation):
    with driver.session() as session:
        n_abbrev = normalize_entity_name(abbreviation)
        result = session.run(
            "MATCH (ent:Entity {normalized_name: $n_abbrev}) "
            "MATCH (m)-[r:abbreviation]->(n) "
            "RETURN m, r",
            n_abbrev=n_abbrev,
        )
        return result


def get_driver_for_config(neo_config):
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
