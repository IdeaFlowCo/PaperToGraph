# API Reference

## Overview

PaperToGraph exposes a REST API via Quart (async Flask). All endpoints are defined in `app.py`.

## Core Parsing Endpoints

### POST /raw-parse

Parse text and extract entities/relationships using GPT.

**Request**:
```json
{
  "text": "string",           // Required: text to parse
  "gpt_model": "string",      // Optional: model to use (default: gpt-3.5-turbo)
  "skip_on_error": true,      // Optional: skip chunks on error (default: true)
  "prompt_override": "string" // Optional: custom system prompt
}
```

**Response**: Streaming JSON with heartbeats
```json
{
  "translation": [
    {
      "Entity Name": {
        "relationship": ["target1", "target2"],
        "_ENTITY_TYPE": "Drug"
      }
    }
  ],
  "source_uri": "s3://..."
}
```

**Notes**:
- Uses chunked transfer encoding with heartbeats
- Long-running request (may take minutes for large texts)
- Input text saved to S3 for source attribution

### GET /parse-prompt

Get the default GPT parse prompt.

**Response**:
```json
{
  "prompt": "string"
}
```

### POST /save-to-neo

Save parsed JSON data to Neo4j.

**Request**:
```json
{
  "data": {},                 // Required: parsed entity JSON
  "source_uri": "string"      // Required: source document URI
}
```

**Response**:
```json
{
  "message": "Saved # entities and # relationships to Neo4j"
}
```

---

## Batch Processing Endpoints

### GET /batch

Render batch processing page (HTML).

### GET /batch-status

Get current batch job status.

**Response**:
```json
{
  "status": "NOT_STARTED" | "RUNNING" | "COMPLETED" | "CANCELED",
  "job_type": "parse" | "save" | null
}
```

### POST /new-batch-job

Start a new batch processing job.

**Request**:
```json
{
  "job_type": "parse" | "save",   // Required
  "data_source": "s3://...",      // Required: input S3 URI
  "output_uri": "s3://...",       // Required for parse jobs
  "gpt_model": "string",          // Optional for parse jobs
  "prompt_override": "string",    // Optional for parse jobs
  "dry_run": false                // Optional: simulation mode
}
```

**Response**:
```json
{
  "message": "Started batch job",
  "output_dir": "s3://..."        // For parse jobs
}
```

### POST /cancel-batch-job

Cancel a running batch job.

**Response**:
```json
{
  "message": "Canceled batch job"
}
```

### GET /batch-log

Stream batch job log via Server-Sent Events (SSE).

**Response**: EventSource stream
```
data: Log line 1
data: Log line 2
...
```

---

## Search and Query Endpoints

### GET /query

Render Simon search query page (HTML).

### POST /query-simon

Execute a Simon semantic search query.

**Request**:
```json
{
  "query": "string"           // Required: search query
}
```

**Response**:
```json
{
  "result": "string"          // Search result text
}
```

### GET /search

Render document search page (HTML).

### POST /doc-search

Search documents by query.

**Request**:
```json
{
  "query": "string"           // Required: search query
}
```

**Response**:
```json
{
  "results": [
    {
      "file": "string",
      "snippet": "string",
      "metadata": {}          // If metadata file configured
    }
  ]
}
```

---

## File Upload Endpoints

### POST /new-doc-set

Upload a batch of files to S3.

**Request**: multipart/form-data
- `files[]`: File uploads

**Response**:
```json
{
  "message": "Uploaded # files",
  "batch_uri": "s3://..."
}
```

---

## Google Drive Endpoints

### GET /gdrive

Render Google Drive page (HTML).

### GET /gdrive-auth

Initiate Google OAuth flow.

**Response**: Redirect to Google OAuth consent screen

### GET /google-oauth

OAuth callback handler.

**Query Parameters**:
- `code`: Authorization code from Google
- `state`: CSRF state token

**Response**: Redirect to /gdrive with credentials stored

### GET /gdrive-revoke

Revoke Google OAuth credentials.

**Response**: Redirect to /gdrive

### POST /gdrive-search

Search Google Drive files.

**Request**:
```json
{
  "query": "string"           // Required: search query
}
```

**Response**:
```json
{
  "files": [
    {
      "id": "string",
      "name": "string",
      "mimeType": "string"
    }
  ]
}
```

### POST /gdrive-ingest

Ingest Google Drive files into Simon.

**Request**:
```json
{
  "files": [                  // Required: files to ingest
    {
      "id": "string",
      "name": "string"
    }
  ]
}
```

**Response**:
```json
{
  "message": "Ingested # files"
}
```

---

## LLM Query Endpoints

### GET /hackathon

Render hackathon page (HTML) - used in rarediseaseguru mode.

### POST /ask-llm

Query Llama or fine-tuned GPT model.

**Request**:
```json
{
  "query": "string",          // Required: query text
  "model": "llama" | "gpt"    // Optional: model to use
}
```

**Response**:
```json
{
  "response": "string"
}
```

---

## Utility Endpoints

### GET /neo4j

Redirect to Neo4j browser console.

**Response**: Redirect to Neo4j URI from configuration

### GET /

Home page - renders based on APP_MODE:
- `paper2graph`: Full application home
- `querymydrive`: Query interface
- `rarediseaseguru`: Hackathon page

---

## Error Responses

All endpoints may return error responses:

```json
{
  "error": "Error message",
  "details": "Additional details"  // Optional
}
```

**HTTP Status Codes**:
- `400`: Bad request (missing/invalid parameters)
- `401`: Unauthorized (missing credentials)
- `404`: Not found
- `500`: Internal server error

---

## Authentication

Most endpoints require no authentication. Google Drive endpoints use OAuth tokens stored in session.

## Rate Limiting

No server-side rate limiting. GPT calls are rate-limited per OpenAI API limits (see `dataflow.md`).

## Streaming Responses

Long-running endpoints use chunked transfer encoding:
- `POST /raw-parse`: Heartbeats during parsing
- `GET /batch-log`: SSE stream

**Headers for streaming responses**:
```
Content-Type: application/json
Transfer-Encoding: chunked
X-Accel-Buffering: no
```

---

## Cross-References

- See `components.md` for implementation details
- See `dataflow.md` for data processing pipelines
- See `configuration.md` for environment setup
