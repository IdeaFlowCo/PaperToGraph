# Architecture Overview

## Tech Stack

| Component | Technology |
|-----------|------------|
| Web Framework | Quart (async Flask-like) |
| Database | Neo4j Graph Database |
| AI/ML | OpenAI GPT API, Llama 2 (SageMaker) |
| Storage | AWS S3 |
| Document Sources | Google Drive API |
| Semantic Search | Simon (PostgreSQL + Elasticsearch) |
| Error Tracking | Sentry |
| Token Counting | tiktoken |
| Document Conversion | markitdown |

## Project Structure

```
PaperToGraph/
├── app.py                    # Main Quart application server
├── parse.py                  # Text parsing orchestration
├── save.py                   # Neo4j saving utilities
├── merge.py                  # GPT-based merge logic (legacy)
├── simon_client.py           # Simon search integration
├── search.py                 # Document search (local/GDrive)
├── tasks.py                  # Async task management
├── run_script.py             # Script runner framework
│
├── gpt/                      # GPT integration module
│   ├── common.py             # OpenAI API wrapper, rate limiting
│   ├── parse.py              # Entity extraction prompts
│   ├── text.py               # Text splitting utilities
│   ├── ent_types.py          # Entity type classification
│   ├── rel_types.py          # Relationship type classification
│   ├── merge.py              # Merging parse results (legacy)
│   ├── data_prep.py          # Training data generation
│   └── ft_models.py          # Fine-tuned model querying
│
├── neo/                      # Neo4j database module
│   ├── common.py             # Entity/relationship normalization
│   ├── ent_data.py           # EntityRecord data model
│   └── write.py              # Neo4j write operations
│
├── aws/                      # AWS S3 integration
│   ├── common.py             # S3 client initialization
│   ├── read.py               # S3 file reading
│   ├── write.py              # S3 file writing
│   └── uri.py                # S3 URI utilities
│
├── batch/                    # Batch job processing
│   ├── common.py             # Job thread management
│   ├── parse.py              # Batch parsing jobs
│   └── save.py               # Batch Neo4j save jobs
│
├── utils/                    # General utilities
│   ├── environment.py        # Configuration loading
│   ├── logging.py            # Centralized logging
│   └── server.py             # HTTP response helpers
│
├── gdrive/                   # Google Drive integration
│   ├── common.py             # OAuth flow, credentials
│   └── files.py              # File access/retrieval
│
├── llama/                    # Llama 2 integration
│   ├── common.py             # SageMaker endpoint invocation
│   ├── query.py              # Llama 2 query execution
│   └── data_prep.py          # Training data preparation
│
├── scripts/                  # Utility scripts
│   ├── run_batch_parse_job.py
│   ├── run_batch_save_job.py
│   ├── enrich_entity_types.py
│   ├── enrich_relationship_types.py
│   └── cleanup_graph_sources.py
│
├── templates/                # HTML templates
├── static/                   # Frontend assets
└── simon/                    # Git submodule (Simon library)
```

## Module Responsibilities

### Core Application (`app.py`)
- HTTP request handling via Quart
- Route definitions for all endpoints
- Application mode configuration
- Before-serving hooks for initialization

### Parse Module (`parse.py`)
- Orchestrates text-to-entities pipeline
- Coordinates chunking and parallel processing
- Implements heartbeat streaming for long requests

### Save Module (`save.py`)
- Orchestrates entity-to-Neo4j pipeline
- Handles source attribution
- Manages input text storage to S3

### GPT Module (`gpt/`)
- OpenAI API communication
- Rate limiting and retry logic
- Text chunking and token management
- Entity extraction prompts
- Entity/relationship type classification

### Neo4j Module (`neo/`)
- Database driver management
- Entity and relationship CRUD operations
- Data normalization (names, relationships)
- EntityRecord data model

### AWS Module (`aws/`)
- S3 client initialization
- File read/write operations
- URI format handling (s3://, https://, console URLs)
- IAM role support

### Batch Module (`batch/`)
- Background job threading
- Job status tracking via files
- Parse and save job implementations
- Cancellation support

### Utils Module (`utils/`)
- Configuration loading from multiple sources
- Thread-aware logging
- HTTP streaming helpers

## High-Level Data Flow

```
┌─────────────────┐
│  Input Sources  │
│  (Text/PDF/S3)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Text Extraction │
│  (markitdown)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Text Chunking  │
│  (token-based)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   GPT Parsing   │
│ (parallel reqs) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Entity/Rel JSON │
│    Extraction   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Neo4j Storage  │
│ (MERGE queries) │
└─────────────────┘
```

## Key Architectural Patterns

### Async Processing with Heartbeats
Long-running HTTP requests use chunked transfer encoding with periodic heartbeat characters to keep connections alive.

### Task Chunking for Rate Limits
GPT requests are chunked and rate-limited based on model-specific limits with exponential backoff.

### Entity Normalization
All entity names are lowercased for consistent matching. Relationship names are converted to snake_case.

### Source Attribution
Every entity and relationship maintains a list of source URIs (HTTP format) for provenance tracking.

### Thread-based Batch Jobs
Background jobs run in separate threads with file-based IPC for status tracking and cancellation.

### Configuration Hierarchy
Settings load from: CLI args > environment variables > .env file

## Cross-References

- See `dataflow.md` for detailed data pipeline documentation
- See `components.md` for in-depth module documentation
- See `api_reference.md` for HTTP endpoint details
- See `configuration.md` for environment variable reference
