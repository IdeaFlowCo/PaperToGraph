import asyncio
import csv
import json
import os
import subprocess
import sys
import time
import tempfile

import aws
import gdrive
from utils import log_msg, log_debug


def search_docs(query, papers_dir=None):
    find_cmd = ["find", papers_dir, "-type", "f", "-name", "*.txt"]
    grep_cmd = ["parallel", "-k", "-j8", "-m", f'LC_ALL=C fgrep -Hic "{query}" {{}}']

    grep_st = time.time()
    find_process = subprocess.Popen(find_cmd, stdout=subprocess.PIPE, text=True)
    grep_process = subprocess.Popen(
        grep_cmd, stdin=find_process.stdout, stdout=subprocess.PIPE, text=True
    )

    # Allow find_process to receive a SIGPIPE if grep_process exits.
    find_process.stdout.close()

    output, error = grep_process.communicate()
    grep_et = time.time()
    log_msg(
        f"Parallelized grep search for {query} in {papers_dir} completed in {(grep_et - grep_st):.2f} seconds"
    )

    # TODO: Figure out why return code is always 12 for some reason (probably related to use of `parallel`` ?)
    # log_msg(f'grep_process.returncode: {grep_process.returncode}')
    # if grep_process.returncode != 0:
    #     print("Grep process failed.")
    #     return []

    output = output.strip().splitlines()
    files_with_matches = [
        line.split(":")[0] for line in output if int(line.split(":")[1]) > 0
    ]
    log_debug(f"Files with matches: {files_with_matches}")

    structured_result = [
        {"pmc_id": os.path.basename(f).rstrip(".txt"), "path": f}
        for f in files_with_matches
    ]
    return structured_result


def load_metadata_as_dict(metadata_file):
    log_msg(f"Loading paper metadata from {metadata_file}")
    paper_metadata = {}
    with open(metadata_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            paper_metadata[row["pmc_id"]] = {
                "title": row.get("article_title", None),
                "article_type": row.get("article_type", None),
                "doi": row.get("doi", None),
            }
    return paper_metadata


def add_metadata_to_docs_list(docs, metadata_file):
    metadata = load_metadata_as_dict(metadata_file)
    for doc in docs:
        doc_md = metadata.get(doc["pmc_id"], None)
        if not doc_md:
            log_msg(f'No metadata found for {doc["pmc_id"]}')
            continue
        # Filter out empty values
        doc_md = {k: v for k, v in doc_md.items() if v}
        doc.update(doc_md)
    return docs


async def asearch_docs(query, papers_dir=None, metadata_file=None):
    log_msg(f'Running async search for "{query}" in {papers_dir}')
    search_st = time.time()
    search_results = await asyncio.to_thread(
        lambda: search_docs(query, papers_dir=papers_dir)
    )
    search_et = time.time()
    log_msg(f"search_docs call completed in {(search_et - search_st):.2f} seconds")

    if metadata_file:
        metadata_st = time.time()
        search_results = await asyncio.to_thread(
            lambda: add_metadata_to_docs_list(search_results, metadata_file)
        )
        metadata_et = time.time()
        log_msg(
            f"Added metadata for {len(search_results)} search results in {(metadata_et - metadata_st):.2f} seconds"
        )
    else:
        log_msg(f"No metadata file provided, skipping metadata lookup")

    log_debug(search_results)
    return {"files": search_results}


async def _process_single_gdrive_file(
    gdrive_creds, file_id, temp_dir, new_batch_set_uri, file_index, total_files
):
    try:
        file = await gdrive.aget_file(credentials=gdrive_creds, file_id=file_id)
        if file is None:
            log_msg(f"File {file_id} not found in Google Drive")
            return {"error": "File not found", "file_id": file_id}

        # Save the file content to a temporary file
        file_name = file["metadata"]["name"]
        temp_file_path = os.path.join(temp_dir, file_name)
        with open(temp_file_path, "w", encoding="utf-8") as f:
            f.write(file["content"])

        # Upload to S3
        new_file_uri = new_batch_set_uri + "/" + file_name
        log_msg(
            f"Uploading file {file_name} to {new_file_uri} ({file_index+1}/{total_files})"
        )
        await asyncio.to_thread(aws.upload_to_s3, new_file_uri, temp_file_path)
        return {"success": True, "file_id": file_id}
    except Exception as e:
        log_msg(f"Error processing file {file_id}: {e}")
        return {"error": str(e), "file_id": file_id}


async def _process_single_local_file(
    file_path, new_batch_set_uri, file_index, total_files
):
    try:
        if not os.path.isfile(file_path):
            log_msg(f"File {file_path} not found")
            return {"error": "File not found", "file_path": file_path}

        file_name = os.path.basename(file_path)
        new_file_uri = new_batch_set_uri + "/" + file_name
        log_msg(
            f"Uploading file {file_name} to {new_file_uri} ({file_index+1}/{total_files})"
        )
        await asyncio.to_thread(aws.upload_to_s3, new_file_uri, file_path)
        return {"success": True, "file_path": file_path}
    except Exception as e:
        log_msg(f"Error processing file {file_path}: {e}")
        return {"error": str(e), "file_path": file_path}


async def upload_batch_set(
    files, gdrive_creds=None, base_dir="s3://paper2graph-parse-inputs/web-search-sets"
):
    # Remove any potential duplicates
    files = list(set(files))

    try:
        new_batch_set_uri = await asyncio.to_thread(
            aws.create_new_batch_set_dir, base_dir_uri=base_dir
        )
        new_batch_set_uri = new_batch_set_uri.rstrip("/")
    except Exception as e:
        log_msg(f"Error creating folder for new batch set: {e}")
        return {"error": f"Error creating folder for new batch set: {e}"}

    if gdrive_creds:
        # Create a temporary directory to store downloaded files
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks = [
                _process_single_gdrive_file(
                    gdrive_creds, file_id, temp_dir, new_batch_set_uri, i, len(files)
                )
                for i, file_id in enumerate(files)
            ]
            results = await asyncio.gather(*tasks)

            # Check for any errors
            errors = [r for r in results if "error" in r]
            if errors:
                missing_files = [
                    e["file_id"] for e in errors if e.get("error") == "File not found"
                ]
                if missing_files:
                    log_msg(
                        f"Request to create new batch set with unknown files: {missing_files}"
                    )
                    return {"error": "Unknown files", "detail": missing_files}
                return {"error": "Error processing files", "detail": errors}

            return {"uri": new_batch_set_uri}
    else:
        # Handle local files
        tasks = [
            _process_single_local_file(f, new_batch_set_uri, i, len(files))
            for i, f in enumerate(files)
        ]
        results = await asyncio.gather(*tasks)

        # Check for any errors
        errors = [r for r in results if "error" in r]
        if errors:
            missing_files = [
                e["file_path"] for e in errors if e.get("error") == "File not found"
            ]
            if missing_files:
                log_msg(
                    f"Request to create new batch set with unknown files: {missing_files}"
                )
                return {"error": "Unknown files", "detail": missing_files}
            return {"error": "Error processing files", "detail": errors}

        return {"uri": new_batch_set_uri}


async def aupload_batch_set(
    files, gdrive_creds=None, base_dir="s3://paper2graph-parse-inputs/web-search-sets"
):
    log_msg(f"Running async upload_batch_set with {len(files)} files")
    result = await upload_batch_set(files, gdrive_creds=gdrive_creds, base_dir=base_dir)
    log_msg(result)
    return result
