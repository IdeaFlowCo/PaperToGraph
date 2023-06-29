'''
Functions for writing data to Neo4j.
'''

from utils import log_msg

from .common import make_timestamp, normalize_entity_name


CREATE_OR_UPDATE_ENT_QUERY = (
    "MERGE (ent:Entity {normalized_name: $normalized_name}) "
    "ON CREATE SET "
    "   ent.name = $name, "
    "   ent.created_at = datetime($timestamp), "
    "   ent.last_modified = datetime($timestamp), "
    "   ent.sources = [$source] "
    "ON MATCH SET "
    "   ent.sources = CASE "
    "      WHEN ent.sources IS NULL THEN [$source] "
    "      ELSE CASE "
    "          WHEN NOT $source IN ent.sources THEN ent.sources + [$source] "
    "          ELSE ent.sources "
    "      END "
    "   END, "
    "   ent.last_modified = datetime($timestamp)"
    "RETURN ent"
)

CREATE_OR_UPDATE_ENT_WITH_TYPE_QUERY = (
    "MERGE (ent:Entity {normalized_name: $normalized_name}) "
    "ON CREATE SET "
    "   ent.name = $name, "
    "   ent.created_at = datetime($timestamp), "
    "   ent.last_modified = datetime($timestamp), "
    "   ent.sources = [$source], "
    "   ent.type = $type "
    "ON MATCH SET "
    "   ent.sources = CASE "
    "      WHEN ent.sources IS NULL THEN [$source] "
    "      ELSE CASE "
    "          WHEN NOT $source IN ent.sources THEN ent.sources + [$source] "
    "          ELSE ent.sources "
    "      END "
    "   END, "
    "   ent.type = CASE "
    "      WHEN ent.type IS NULL THEN $type "
    "   END, "
    "   ent.last_modified = datetime($timestamp)"
    "RETURN ent"
)


def create_or_update_entity(driver, ent_data):
    timestamp = ent_data.timestamp or make_timestamp()
    with driver.session() as session:
        if ent_data.type:
            session.run(
                CREATE_OR_UPDATE_ENT_WITH_TYPE_QUERY,
                normalized_name=ent_data.normalized_name,
                name=ent_data.name,
                source=ent_data.source,
                type=ent_data.type,
                timestamp=timestamp,
            )
        else:
            session.run(
                CREATE_OR_UPDATE_ENT_QUERY,
                normalized_name=ent_data.normalized_name,
                name=ent_data.name,
                source=ent_data.source,
                timestamp=timestamp,
            )
        # TODO: Check result for any extra logging or error handling logic
        log_msg(f'Entity for "{ent_data.name}" created or updated')


# Function to create an entity in the database if it doesn't exist
def create_or_update_entity_by_name(driver, name, source, timestamp):
    with driver.session() as session:
        normalized_name = normalize_entity_name(name)
        session.run(
            CREATE_OR_UPDATE_ENT_QUERY,
            normalized_name=normalized_name,
            name=name,
            source=source,
            timestamp=timestamp,
        )
        # TODO: Check result for any extra logging or error handling logic
        log_msg(f'Entity for "{name}" created or updated')


# Function to create a named relationship between two entities if it doesn't exist
def create_or_update_relationship(driver, ent1_name, relationship_name, ent2_name, source, timestamp):
    with driver.session() as session:
        n_ent1_name = normalize_entity_name(ent1_name)
        n_ent2_name = normalize_entity_name(ent2_name)
        query = (
            "MATCH (e1:Entity {normalized_name: $ent1_name}) "
            "MATCH (e2:Entity {normalized_name: $ent2_name}) "
            "MERGE (e1)-[r:%s]->(e2) "
            "ON CREATE SET "
            "   r.created_at = datetime($timestamp), "
            "   r.last_modified = datetime($timestamp), "
            "   r.sources = [$source] "
            "ON MATCH SET "
            "   r.sources = CASE "
            "      WHEN r.sources IS NULL THEN [$source] "
            "      ELSE CASE "
            "          WHEN NOT $source IN r.sources THEN r.sources + [$source] "
            "          ELSE r.sources "
            "      END "
            "   END, "
            "   r.last_modified = datetime($timestamp) "
            "RETURN r"
        ) % relationship_name
        session.run(
            query,
            ent1_name=n_ent1_name,
            ent2_name=n_ent2_name,
            source=source,
            timestamp=timestamp,
        )
        # TODO: Check result for any extra logging or error handling logic
        log_msg(
            f'Relationship "{relationship_name}" created or updated between "{ent1_name}" and "{ent2_name}"')
