'''
Model class for entity data
'''

import aws
from utils import log_msg, log_warn

from .common import make_timestamp, normalize_entity_name, sanitize_relationship_name
from .write import create_or_update_entity, create_or_update_entity_by_name, create_or_update_relationship


class EntityRecord:
    def __init__(self, name, relationships=None, ent_type=None, timestamp=None, source=None):
        if not name:
            raise ValueError('Entity name must be supplied')
        self.name = name
        self.normalized_name = normalize_entity_name(name)

        if not source:
            raise ValueError('Entity source must be supplied')
        if not aws.is_valid_s3_uri(source):
            raise ValueError(f'Invalid entity source URI: {source}')
        self._source_s3, self._source_http = (
            aws.source_uri_to_s3_and_http(source))
        # Use HTTP format for source because that's what we're always saving to the database
        self.source = self._source_http

        self.type = ent_type

        self.timestamp = timestamp or make_timestamp()

        self.relationships = relationships or {}
        if self.relationships:
            self.__sanitize_relationships()

    def __str__(self):
        # Use S3 format of source here because this is only for logging/debugging and S3 URI is easier to read
        return f'Entity(name="{self.name}", source="{self._source_s3}", timestamp="{self.timestamp}")'

    def __sanitize_relationships(self):
        sanitized_relationships = {}
        for relationship_name, target in self.relationships.items():
            if not isinstance(relationship_name, str):
                log_warn(
                    f'Unexpected key in entity relationships dict for "{self.name}". Expected string, got: {type(relationship_name)}')
                log_warn(relationship_name)
                log_warn('Pruning this relationship from the entity data.')
                continue
            relationship_name = sanitize_relationship_name(relationship_name)
            target = self.__sanitize_relationship_target(target)
            if target:
                sanitized_relationships[relationship_name] = target
        self.relationships = sanitized_relationships

    def __sanitize_relationship_target(self, target):
        if isinstance(target, str):
            return [target]
        elif isinstance(target, list):
            valid_targets = []
            for t in target:
                if not isinstance(t, str):
                    log_warn(
                        f'Unexpected target in entity relationships dict for "{self.name}". '
                        f'Expected all target list values to be strings, got: {type(t)}')
                    log_warn(t)
                    log_warn("Won't be saving this target.")
                    continue
                valid_targets.append(t)
            return valid_targets
        else:
            log_warn(
                f'Invalid relationship target for entity "{self.name}". Expected string or list of strings, got: {type(target)}')
            log_warn(target)
            return None

    @staticmethod
    def from_json_entry(name, values_dict, source=None, timestamp=None):
        ent_type = values_dict.pop('_ENTITY_TYPE', None)
        # All leftover data assumed to be relationships
        relationships = values_dict

        return EntityRecord(name, relationships=relationships, ent_type=ent_type, source=source, timestamp=timestamp)

    def has_data_to_save(self):
        # If there are no relationships, we shouldn't bother saving this stub of an entity.
        return bool(self.relationships)

    def save_to_neo(self, neo_driver):
        log_msg(f'Saving entity "{self.name}"')
        create_or_update_entity(neo_driver, self)

    def save_relationships_to_neo(self, neo_driver):
        log_msg(f'Saving relationships for entity "{self.name}"')
        for relationship_name, target_list in self.relationships.items():
            for target in target_list:
                # Ensure target entity exists in Neo4j
                create_or_update_entity_by_name(
                    neo_driver, target, self.source, self.timestamp)
                # Create relationship between this entity and the target
                create_or_update_relationship(
                    neo_driver, self.name, relationship_name, target, self.source, self.timestamp)
