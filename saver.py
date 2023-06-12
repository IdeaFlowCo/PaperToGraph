import json
from re import sub

from neo4j import GraphDatabase

def snake_case(s):
  # Replace illegal chars with _
  s = s.replace('/', '_')
  # Replace . and - with a space
  s = s.replace('-', ' ').replace('.', ' ')
  # Do rest of snake case transformation (NamedThing to named_thing, etc)
  return '_'.join(
    sub('([A-Z][a-z]+)', r' \1',
    sub('([A-Z]+)', r' \1',
    s)).split()).lower()

# Function to create an object in the database if it doesn't exist
def create_object_if_not_exists(driver, name):
    with driver.session() as session:
        result = session.run("MATCH (obj:Object {name: $name}) RETURN count(obj) AS count", name=name)
        count = result.single()["count"]
        if count == 0:
            session.run("CREATE (:Object {name: $name})", name=name)
            print(f"Object '{name}' created in the database.")
        else:
            print(f"Object '{name}' already exists in the database.")


# Function to create a named relationship between two objects if it doesn't exist
def create_relationship_if_not_exists(driver, obj1_name, relationship_name, obj2_name):
    with driver.session() as session:
        result = session.run(
            "MATCH (obj1:Object {name: $obj1_name})-[r:%s]->(obj2:Object {name: $obj2_name}) RETURN count(r) AS count"
            % (relationship_name),
            obj1_name=obj1_name,
            obj2_name=obj2_name,
        )
        count = result.single()["count"]
        if count == 0:
            session.run(
                "MATCH (obj1:Object {name: $obj1_name}), (obj2:Object {name: $obj2_name}) "
                "CREATE (obj1)-[:%s]->(obj2)" % (relationship_name),
                obj1_name=obj1_name,
                obj2_name=obj2_name,
            )
            print(f"Relationship '{relationship_name}' created between '{obj1_name}' and '{obj2_name}'.")
        else:
            print(f"Relationship '{relationship_name}' already exists between '{obj1_name}' and '{obj2_name}'.")


def save_json_array(json_arr_str):
    # Create a Neo4j driver instance
    driver = GraphDatabase.driver("neo4j+s://20d077bf.databases.neo4j.io", auth=("neo4j", "VNfVHsSRzfTZlRRDTDluxFvi6PfLtwkO_5JTxJCV3Mc"))

    try:
        parsed_arr = json.loads(json_arr_str)
        for obj in parsed_arr:
            for name, relationships in obj.items():
                create_object_if_not_exists(driver, name)
                if not isinstance(relationships, dict):
                    # We expect every top level value to be a dict of relationships for the named key.
                    # If that's not the case for some reason, just skip it for now
                    continue
                for relationship_name, target in relationships.items():
                    if not isinstance(relationship_name, str) or not isinstance(target, str):
                        # We expect all of these to be str -> str pairs.
                        # If that's not the case, just skip for now.
                        continue
                    create_object_if_not_exists(driver, target)
                    relationship_name = snake_case(relationship_name)
                    create_relationship_if_not_exists(driver, name, relationship_name, target)
    finally:
        # Close the Neo4j driver
        driver.close()
