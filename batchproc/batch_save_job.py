import argparse


def save_to_neo4j(data_source, neo_uri):
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--data_source', help="The URI for the data to be ingested, like an S3 bucket location.")
    parser.add_argument(
        '--neo_uri', help="The URI for the Neo4j instance to save loaded data to.")
    args = parser.parse_args()

    save_to_neo4j(args.data_source, args.neo_uri)
