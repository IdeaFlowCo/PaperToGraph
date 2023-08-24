
import google_auth_oauthlib
from googleapiclient.discovery import build

import requests


# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
CLIENT_SECRETS_FILE = 'oauth_client_secrets.json'

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly',
          'https://www.googleapis.com/auth/drive.metadata.readonly']
API_SERVICE_NAME = 'drive'
API_VERSION = 'v3'


CREDS_SESSION_KEY = 'g-oauth-creds'


def build_api_client(credentials):
    client = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
    return client


def build_oauth_flow(state=None):
    '''
    Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    '''
    if state:
        return google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)

    return google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)


def revoke_credentials(credentials):
    requests.post('https://oauth2.googleapis.com/revoke',
                  params={'token': credentials.token},
                  headers={'content-type': 'application/x-www-form-urlencoded'})
    # TODO: maybe check status code here and do some error handling


def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}
