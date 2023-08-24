import asyncio
from enum import StrEnum
import io
import logging

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from .common import build_api_client


class FileType(StrEnum):
    PLAIN_TEXT = 'text/plain'
    # HTML = 'text/html'
    PDF = 'application/pdf'
    GOOGLE_DOC = 'application/vnd.google-apps.document'


def search_files(credentials=None, file_name=None, file_type='_ALL_'):
    """Search for files with a specified mime type in Google Drive
    """
    drive_api = build_api_client(credentials)
    query_parts = []
    if file_name:
        query_parts.append(f"name contains '{file_name}'")
    if file_type != '_ALL_':
        query_parts.append(f"mimeType = '{file_type}'")
    else:
        mime_types = []
        for ft in FileType:
            mime_types.append(f"mimeType = '{ft}'")
        query_parts.append(f"({' or '.join(mime_types)})")
    query = ' and '.join(query_parts)
    logging.info(f'Searching Google Drive with query: "{query}"')
    try:
        files = []
        page_token = None
        while True:
            # pylint: disable=maybe-no-member
            response = drive_api.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, '
                'files(id, name)',
                pageToken=page_token
            ).execute()
            logging.debug(response)
            files.extend(response.get('files', []))
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
    except HttpError as error:
        logging.error(F'Error while searching Google Drive files: {error}')
        files = None

    return files


async def asearch_files(**kwargs):
    # logging.info(f'Running async search_files request for {file_type}')
    files = await asyncio.to_thread(lambda: search_files(**kwargs))
    logging.info(files)
    return {'files': files}


def get_file(credentials=None, file_id=None):
    """Get file metadata from Google Drive
    """
    drive_api = build_api_client(credentials)
    try:
        # pylint: disable=maybe-no-member
        file_metadata = drive_api.files().get(
            fileId=file_id,
            fields='id, name, mimeType'
        ).execute()
        logging.debug(file_metadata)
        mime_type = file_metadata.get('mimeType', None)
        if mime_type == FileType.PLAIN_TEXT:
            # pylint: disable=maybe-no-member
            request = drive_api.files().get_media(fileId=file_id)
        elif mime_type == FileType.GOOGLE_DOC:
            # pylint: disable=maybe-no-member
            request = drive_api.files().export_media(
                fileId=file_id,
                mimeType=FileType.PLAIN_TEXT
            )
        elif mime_type == FileType.PDF:
            logging.warning('PDF files are not supported yet, returning None')
            return None
        else:
            logging.warning(F'Unsupported file type: {mime_type}')
            return None

        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            logging.debug(F'Google Drive download {int(status.progress() * 100)}.')

        return {'metadata': file_metadata, 'content': file.getvalue().decode('utf-8')}
    except HttpError as error:
        logging.error(F'Error while getting Google Drive file: {error}')
        return None


async def aget_file(**kwargs):
    file = await asyncio.to_thread(lambda: get_file(**kwargs))
    return file


if __name__ == '__main__':
    search_files(file_type=FileType.PLAIN_TEXT)
