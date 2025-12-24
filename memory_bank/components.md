# Component Documentation

## GPT Module (`gpt/`)

### gpt/common.py - OpenAI Integration

**Purpose**: Core wrapper for OpenAI API calls with rate limiting and retry logic.

**Valid Models**:
```python
VALID_GPT_MODELS = [
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
    "gpt-4",
    "gpt-4-32k",
    "gpt-4o",
    "gpt-4o-mini"
]
DEFAULT_GPT_MODEL = "gpt-3.5-turbo"
```

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `init_module(config)` | Set OpenAI API key |
| `sanitize_gpt_model_choice(model)` | Validate model selection |
| `async_fetch_from_openai(messages, ...)` | Main API call with retries |
| `get_token_length(text, model)` | Token counting via tiktoken |
| `split_input_list_to_chunks(input_list, max_tokens, model)` | Chunk splitting |
| `get_context_window_size(model)` | Context window limits |
| `get_max_requests_per_minute(model)` | Rate limits per model |
| `get_rl_backoff_time(model)` | Backoff delay with jitter |
| `clean_json(response)` | Clean JSON, remove empty values |

**Rate Limit Configuration**:
```python
# Requests per minute
RPM = {
    "gpt-4o": 500,
    "gpt-4o-mini": 750,
    "gpt-4": 200,
    "gpt-4-32k": 200,
    "gpt-3.5-turbo": 60,
    "gpt-3.5-turbo-16k": 60
}

# Tokens per minute
TPM = {
    "gpt-4o": 300000,
    "gpt-4o-mini": 400000,
    "gpt-4": 40000,
    "gpt-4-32k": 80000,
    "gpt-3.5-turbo": 60000,
    "gpt-3.5-turbo-16k": 120000
}
```

### gpt/parse.py - Entity Extraction

**Purpose**: GPT prompts and logic for extracting entities and relationships.

**Parse Prompt Template** (simplified):
```
Step 1: Extract Named Entities
- Drug: medication names
- Disease: medical conditions
- Other: genes, proteins, etc.

Step 2: Map Relationships
- Identify connections between entities

Step 3: Handle Abbreviations
- Create "abbreviation_of" relationships

Step 4: Format as JSON
{
  "Entity": {
    "relationship": ["target1", "target2"],
    "_ENTITY_TYPE": "Drug"
  }
}
```

**Special Markers**:
- `NO_ENTITIES_FOUND`: Skip marker for empty results

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `get_text_token_limit(model)` | Max input tokens |
| `get_text_size_limit(model)` | Max input characters |
| `get_output_reservation(model)` | Reserved output tokens |
| `get_timeout_limit(model)` | Request timeout |
| `get_default_parse_prompt()` | Default system message |
| `async_fetch_parse(text, model, ...)` | Main parse function |

### gpt/text.py - Text Processing

**Purpose**: Text splitting and tokenization utilities.

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `is_text_oversized(text)` | Check if > 6000 chars |
| `normalize_line_endings(text)` | CRLF/CR to LF |
| `split_to_size(text, limit)` | Split by paragraphs/sentences |
| `get_token_length(text, model)` | Token count |
| `split_to_token_size(text, limit, model)` | Token-aware splitting |

**Splitting Algorithm**:
1. Split by double newlines (paragraphs)
2. Split oversized paragraphs by token boundaries
3. Recombine undersized chunks to meet limit

### gpt/ent_types.py - Entity Classification

**Purpose**: Classify entities as Drug, Disease, or Other.

**Output Format**: `("entity_name", "type")`

**Key Functions**:
- `get_output_reservation(model)` - 2000-10000 tokens
- `get_input_token_limit(model)` - Calculate max input
- `fetch_entity_types(input, model, prompt_override)` - Main function

### gpt/rel_types.py - Relationship Classification

**Purpose**: Categorize relationships.

**Categories**:
- Promotes
- Inhibits
- Associated With
- Disconnected From
- Other

**Output Format**: `("relationship_name", "category")`

---

## Neo4j Module (`neo/`)

### neo/common.py - Utilities

**Purpose**: Entity/relationship normalization and driver setup.

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `normalize_entity_name(name)` | Convert to lowercase |
| `sanitize_relationship_name(rel)` | Convert to snake_case |
| `make_timestamp()` | Create Neo4j DateTime |
| `get_neo4j_driver(config)` | Initialize driver |

**Relationship Sanitization**:
- Replace `/`, `.`, `%` with `_`
- Replace `-` with space
- Convert camelCase to snake_case

### neo/ent_data.py - EntityRecord

**Purpose**: Data model for entities extracted from text.

**Class Definition**:
```python
class EntityRecord:
    name: str                      # Required
    normalized_name: str           # Lowercase
    type: str                      # Drug/Disease/Other
    source: str                    # HTTP URL
    _source_s3: str                # Internal
    _source_http: str              # Internal
    timestamp: DateTime            # Creation time
    relationships: dict            # {rel_name: [targets]}
```

**Key Methods**:

| Method | Purpose |
|--------|---------|
| `from_json_entry(name, values, source, ts)` | Factory from parsed JSON |
| `has_data_to_save()` | Check for relationships |
| `save_to_neo(driver)` | Write entity node |
| `save_relationships_to_neo(driver)` | Create relationship edges |

### neo/write.py - Database Writes

**Purpose**: Neo4j write operations for entities and relationships.

**Cypher Queries**:

1. **CREATE_OR_UPDATE_ENT_QUERY**:
   - MERGE on normalized_name
   - ON CREATE: Set name, timestamps, sources
   - ON MATCH: Append source, update timestamp

2. **CREATE_OR_UPDATE_ENT_WITH_TYPE_QUERY**:
   - Same as above + type field

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `create_or_update_entity(driver, ent_data)` | Write EntityRecord |
| `create_or_update_entity_by_name(driver, name, source, ts)` | Write by name |
| `create_or_update_relationship(driver, e1, rel, e2, source, ts)` | Create edge |

---

## AWS Module (`aws/`)

### aws/common.py - Client Initialization

**Purpose**: AWS client setup with credential handling.

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `check_for_env_vars(throw)` | Validate credentials |
| `get_s3_client(cl_args)` | Create S3 client |
| `get_sagemaker_client(cl_args)` | Create SageMaker client |

**Credential Options**:
- Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- IAM role: `AWS_USE_IAM_ROLE=true`

### aws/uri.py - URI Utilities

**Purpose**: Parse and convert S3 URI formats.

**Supported Formats**:
1. `s3://bucket/key`
2. `https://bucket.s3.amazonaws.com/key`
3. AWS Console URLs

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `parse_s3_uri(uri)` | Parse to (bucket, key) |
| `s3_uri_to_http(uri)` | Convert to HTTPS |
| `http_to_s3_uri(url)` | Convert to S3 URI |
| `is_valid_s3_uri(uri)` | Validate |
| `source_uri_to_s3_and_http(uri)` | Get both formats |

### aws/read.py - Read Operations

**Purpose**: Read files and list objects from S3.

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `get_objects_at_s3_uri(uri)` | List all objects recursively |
| `get_objects_by_folder_at_s3_uri(uri)` | List by folder structure |
| `read_file_from_s3(uri)` | Read file (auto-detect binary) |

### aws/write.py - Write Operations

**Purpose**: Write files and create directories in S3.

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `create_output_dir_for_job(source, output, dry_run)` | Timestamped job dir |
| `create_output_dir_for_file(output, filename, dry_run)` | Per-file subdir |
| `write_to_s3_file(output, data)` | Write string/bytes |
| `upload_to_s3(output, filepath)` | Upload local file |
| `create_new_batch_set_dir(base)` | Timestamped batch dir |

---

## Batch Module (`batch/`)

### batch/common.py - Job Management

**Purpose**: Thread management and status tracking for batch jobs.

**Status File**: `/tmp/p2g/p2g_batch_job_status.txt`
**Log File**: `/tmp/p2g/batch-job.log`

**Job States**:
```
NOT_STARTED → RUNNING → COMPLETED | CANCELED
```

**Thread Names**:
- `p2g-batch-parse` - Parse jobs
- `p2g-batch-save` - Save jobs
- `p2g-ent-types` - Entity enrichment
- `p2g-rel-types` - Relationship enrichment
- `p2g-graph-sources` - Source cleanup

**BatchJobThread Class**:
- Extends `threading.Thread`
- Runs async work via `asyncio`
- Monitors cancel flag
- Updates status file

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `setup_status_file()` | Initialize tracking |
| `is_batch_job_running()` | Check status |
| `cancel_batch_job()` | Request cancellation |
| `make_and_run_parse_job(args)` | Start parse thread |
| `make_and_run_save_job(args, neo_config)` | Start save thread |

### batch/parse.py - Parse Jobs

**Purpose**: Batch parsing of documents from S3.

**BatchParseJob Class**:
```python
class BatchParseJob:
    gpt_model: str           # Model to use
    dry_run: bool            # Simulation mode
    prompt_override: str     # Custom prompt
    log_file: str            # Log path
    job_output_uri: str      # S3 output dir
    output_tasks: set        # Async write tasks
```

**Workflow**:
1. Find input files at S3 path
2. Create timestamped output directory
3. For each file:
   - Fetch and convert to text
   - Parse with GPT in chunks
   - Write results to S3
4. Write job metadata and log

**Output Structure**:
```
{timestamp}-{input}-output/
├── source.txt
├── output_1.source.txt
├── output_1.json
├── output_2.source.txt
├── output_2.json
├── job_args.json
└── job_log.txt
```

### batch/save.py - Save Jobs

**Purpose**: Batch saving of parse results to Neo4j.

**Workflow**:
1. Find input folders at S3 path
2. For each folder:
   - Locate output JSON files
   - Match source files
   - Save to Neo4j with attribution

**Source Matching Logic**:
- One `source.txt` → use for all outputs
- Multiple sources → match by number
- No sources → use output URI

---

## Utils Module (`utils/`)

### utils/environment.py - Configuration

**Purpose**: Load configuration from multiple sources.

**Priority** (highest first):
1. Command-line arguments
2. Environment variables
3. `.env` file

**Configuration Structure**:
```python
{
  'logger': {'log_file': str, 'level': str},
  'aws': {'aws_use_iam_role': bool, ...},
  'neo4j': {'uri': str, 'user': str, 'password': str},
  'OPENAI_API_KEY': str,
  'APP_MODE': str,
  ...
}
```

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `load_config(cl_args)` | Load all config sources |
| `add_neo_credential_override_args(parser)` | Add Neo4j CLI args |
| `add_logger_args(parser)` | Add logging CLI args |
| `secret_to_log_str(secret)` | Mask secrets |
| `log_config_vars(config)` | Log config safely |

### utils/logging.py - Logging System

**Purpose**: Thread-aware logging with file and console output.

**Logger Names by Thread**:
- `p2g-batch-parse`, `p2g-batch-save` → Batch loggers
- `p2g-ent-types`, `p2g-rel-types` → Script loggers
- `paper2graph` → Default logger

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `get_logger()` | Get thread-appropriate logger |
| `log_msg(msg, level)` | Main logging function |
| `log_debug(msg)` | Debug level |
| `log_warn(msg)` | Warning level |
| `log_error(msg)` | Error level |
| `setup_logger(name, file, level)` | Create logger |

### utils/server.py - HTTP Helpers

**Purpose**: Streaming response helpers for long-running requests.

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `gen_result_with_heartbeat(fn, label, interval)` | Generator with heartbeats |
| `make_response_with_heartbeat(fn, label)` | HTTP response wrapper |

**Heartbeat Pattern**:
- Run async work in background
- Yield heartbeat spaces every N seconds
- Yield final result when complete
- Cancel on client disconnect

---

## Simon Client (`simon_client.py`)

**Purpose**: Wrapper for Simon semantic search library.

**SimonClient Class**:
- LLM: `ChatOpenAI(gpt-3.5-turbo)`
- Reasoning LLM: `ChatOpenAI(gpt-4)`
- Embeddings: `OpenAIEmbeddings(text-embedding-ada-002)`
- Backend: PostgreSQL

**Key Methods**:

| Method | Purpose |
|--------|---------|
| `query_simon(query)` | Execute search query |
| `ingest_gdrive_file(creds, file_id)` | Ingest single file |
| `ingest_gdrive_file_set(creds, files)` | Batch ingest |

---

## Google Drive Module (`gdrive/`)

### gdrive/common.py - OAuth

**Purpose**: Google OAuth flow and credential management.

### gdrive/files.py - File Access

**Purpose**: Fetch files from Google Drive.

**File Types**:
```python
class FileType:
    PLAIN_TEXT = "text/plain"
    PDF = "application/pdf"
    GOOGLE_DOC = "application/vnd.google-apps.document"
```

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `aget_file(credentials, file_id)` | Async fetch file |

**Google Docs Handling**:
- Export as text
- Return content with metadata

---

## Llama Module (`llama/`)

**Purpose**: Llama 2 integration via SageMaker.

### llama/query.py

**Endpoint**: `jumpstart-ftc-meta-textgeneration-llama-2-7b`

**Parameters**:
- max_tokens: 256
- temperature: 0.2
- top_p: 0.9

**Key Functions**:

| Function | Purpose |
|--------|---------|
| `ask_llama(query)` | Synchronous query |
| `aask_llama(query)` | Async wrapper |

---

## Cross-References

- See `architecture.md` for system overview
- See `dataflow.md` for data pipeline details
- See `api_reference.md` for endpoint documentation
- See `scripts.md` for utility script documentation
