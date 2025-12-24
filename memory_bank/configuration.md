# Configuration Reference

## Overview

PaperToGraph configuration is loaded from multiple sources with the following priority (highest to lowest):

1. Command-line arguments (uppercase)
2. Shell environment variables
3. `.env` file values

Configuration loading is handled by `utils/environment.py`.

## Environment Variables

### Core Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key for GPT calls | Yes | - |
| `APP_MODE` | Application mode | No | `paper2graph` |
| `APP_TITLE` | Custom application title | No | Mode-specific |
| `DEV_SERVER` | Enable development server features | No | `False` |

### Logging

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `LOG_LEVEL` | Logging level | No | `INFO` |
| `LOG_FILE` | Path to log file | No | None (stdout only) |

**Valid log levels**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### AWS Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `AWS_USE_IAM_ROLE` | Use IAM role instead of credentials | No | `False` |
| `AWS_ACCESS_KEY_ID` | AWS access key | If not using IAM | - |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | If not using IAM | - |
| `AWS_SESSION_TOKEN` | AWS session token | No | - |

**Note**: Set `AWS_USE_IAM_ROLE=true` when running on EC2 with IAM role.

### Neo4j Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `NEO_URI` | Neo4j connection URI | Yes | - |
| `NEO_USER` | Neo4j username | Yes | - |
| `NEO_PASS` | Neo4j password | Yes | - |

**URI Format**: `neo4j+s://hostname:port` or `neo4j://hostname:port`

### Document Search

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `PAPERS_DIR` | Directory containing paper files | No | - |
| `PAPERS_METADATA_FILE` | CSV with paper metadata | No | - |

### Simon/Elasticsearch Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ELASTIC_URL` | Elasticsearch URL | Conditional | - |
| `ELASTIC_CLOUD_ID` | Elastic Cloud ID | Conditional | - |
| `ELASTIC_USER` | Elasticsearch username | If using Simon | - |
| `ELASTIC_PASSWORD` | Elasticsearch password | If using Simon | - |

**Note**: Use either `ELASTIC_URL` or `ELASTIC_CLOUD_ID`, not both.

### PostgreSQL (Simon Backend)

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `POSTGRES_HOST` | PostgreSQL host | If using Simon | - |
| `POSTGRES_PORT` | PostgreSQL port | If using Simon | `5432` |
| `POSTGRES_DB` | PostgreSQL database | If using Simon | - |
| `POSTGRES_USER` | PostgreSQL username | If using Simon | - |
| `POSTGRES_PASSWORD` | PostgreSQL password | If using Simon | - |

### Error Tracking

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SENTRY_DSN` | Sentry DSN for error tracking | No | - |

### Google Services

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_MAPS_KEY` | Google Maps API key | No | - |
| `GOOGLE_CLIENT_ID` | OAuth client ID | If using GDrive | - |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret | If using GDrive | - |

---

## Configuration Structure

The `load_config()` function returns a dictionary with nested structure:

```python
{
    'logger': {
        'log_file': str | None,
        'level': str  # 'INFO', 'DEBUG', etc.
    },
    'aws': {
        'aws_use_iam_role': bool,
        'aws_access_key_id': str | None,
        'aws_secret_access_key': str | None,
        'aws_session_token': str | None
    },
    'neo4j': {
        'uri': str,
        'user': str,
        'password': str
    },
    'postgres': {
        'host': str,
        'port': int,
        'db': str,
        'user': str,
        'password': str
    },
    'elastic': {
        'url': str | None,
        'cloud_id': str | None,
        'user': str,
        'password': str
    },
    'OPENAI_API_KEY': str,
    'APP_MODE': str,
    'PAPERS_DIR': str | None,
    'PAPERS_METADATA_FILE': str | None,
    # ... other top-level vars
}
```

---

## Application Modes

### paper2graph (Default)

Full-featured entity extraction and knowledge graph building.

**Navigation Links**:
- Home
- Batch Processing
- Query
- Ingest
- Neo4j

**Available Features**:
- Text parsing
- Batch processing
- Neo4j storage
- Document search
- Google Drive integration
- Simon semantic search

### querymydrive

Google Drive document querying mode.

**Navigation Links**:
- Home
- Ingest

**Available Features**:
- Google Drive OAuth
- Document ingestion
- Simon semantic search

**Special Configuration**:
- Uses separate SimonClient instance
- UID override: `"querymydrive"`

### rarediseaseguru

Specialized rare disease information mode.

**Navigation Links**:
- Home only

**Available Features**:
- Hackathon template UI
- Limited functionality

---

## CLI Arguments

Scripts in `scripts/` can accept CLI arguments that override configuration.

### Common Arguments

```bash
--neo-uri       # Override NEO_URI
--neo-user      # Override NEO_USER
--neo-pass      # Override NEO_PASS
--log-level     # Override LOG_LEVEL
--log-file      # Override LOG_FILE
```

### Script-Specific Arguments

**run_batch_parse_job.py**:
```bash
--data_source   # S3 URI of input files
--output_uri    # S3 URI for output
--gpt_model     # GPT model to use
--dry_run       # Simulation mode
```

**run_batch_save_job.py**:
```bash
--data_source   # S3 URI of parse output
```

---

## .env File Example

```bash
# Core
OPENAI_API_KEY=sk-...
APP_MODE=paper2graph

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/paper2graph.log

# AWS (option 1: credentials)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# AWS (option 2: IAM role)
# AWS_USE_IAM_ROLE=true

# Neo4j
NEO_URI=neo4j+s://xxx.databases.neo4j.io
NEO_USER=neo4j
NEO_PASS=...

# Document Search (optional)
PAPERS_DIR=/path/to/papers
PAPERS_METADATA_FILE=/path/to/metadata.csv

# Simon/Elasticsearch (optional)
ELASTIC_URL=http://localhost:9200
ELASTIC_USER=elastic
ELASTIC_PASSWORD=...

# PostgreSQL for Simon (optional)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=simon
POSTGRES_USER=postgres
POSTGRES_PASSWORD=...

# Error tracking (optional)
SENTRY_DSN=https://...@sentry.io/...

# Google Drive (optional)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

---

## Security Considerations

### Secret Masking

Secrets are masked in logs using `secret_to_log_str()`:
- Shows first 4 and last 4 characters
- Masks middle with asterisks
- Example: `sk-a***key` for `sk-abcdefghijkey`

### Sensitive Variables

These variables contain secrets and should never be logged in full:
- `OPENAI_API_KEY`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN`
- `NEO_PASS`
- `POSTGRES_PASSWORD`
- `ELASTIC_PASSWORD`
- `GOOGLE_CLIENT_SECRET`
- `SENTRY_DSN`

---

## File Locations

| File | Purpose |
|------|---------|
| `.env` | Environment configuration |
| `.env.example` | Configuration template |
| `/tmp/p2g/` | Batch job status and logs |
| `/tmp/p2g/p2g_batch_job_status.txt` | Job status file |
| `/tmp/p2g/batch-job.log` | Job log file |

---

## Cross-References

- See `architecture.md` for system overview
- See `scripts.md` for CLI script usage
- See `api_reference.md` for endpoint configuration
