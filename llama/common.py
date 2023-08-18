import json

import boto3

FINE_TUNED_ENDPOINT = 'jumpstart-ftc-meta-textgeneration-llama-2-7b'


def fetch_response(payload, endpoint_name=FINE_TUNED_ENDPOINT):
    client = boto3.client("sagemaker-runtime", region_name="us-east-1")
    response = client.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType="application/json",
        Body=json.dumps(payload),
        CustomAttributes="accept_eula=true",
    )
    response = response["Body"].read().decode("utf8")
    response = json.loads(response)
    return response
