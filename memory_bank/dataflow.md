# Data Flow Documentation

## Overview

This document describes the core data pipelines in PaperToGraph, from input text to knowledge graph storage.

## Single Document Parse Flow

### 1. Text Input
```
User submits text via POST /raw-parse
    │
    ▼
parse.py: parse_with_gpt() or parse_with_gpt_multitask()
```

### 2. Text Chunking
```
gpt/text.py: split_to_token_size(text, token_limit, model)
    │
    ├── Split by paragraphs (double newlines)
    ├── Split oversized paragraphs by token boundaries
    └── Recombine undersized chunks to meet token limit
    │
    ▼
List of text chunks (each within model token limit)
```

### 3. Parallel GPT Requests
```
tasks.py: create_and_run_tasks()
    │
    ├── Maintains max concurrent tasks (rate limiting)
    ├── gpt/common.py: async_fetch_from_openai()
    │       ├── Rate limit backoff (exponential)
    │       ├── Timeout retry (2 attempts)
    │       └── JSON validation
    │
    ▼
List of JSON parse results per chunk
```

### 4. Entity Extraction
```
gpt/parse.py: Parse Prompt
    │
    ├── Step 1: Extract Named Entities (Drug, Disease, Other)
    ├── Step 2: Map Relationships between entities
    ├── Step 3: Handle Abbreviations
    └── Step 4: Format as JSON
    │
    ▼
JSON Output Format:
{
  "Entity Name": {
    "relationship_name": ["target1", "target2"],
    "_ENTITY_TYPE": "Drug"
  }
}
```

### 5. Optional Neo4j Save
```
POST /save-to-neo with JSON data
    │
    ▼
save.py: save_data_to_neo4j(data, source_uri, neo_config)
    │
    ├── Create EntityRecord from each JSON entry
    ├── Convert source URI to HTTP format
    └── Write to Neo4j with timestamp
```

## Batch Parse Flow

### 1. Job Initialization
```
POST /new-batch-job (job_type="parse")
    │
    ▼
batch/common.py: make_and_run_parse_job()
    │
    ├── Create BatchJobThread
    ├── Initialize status file (/tmp/p2g/)
    └── Start background thread
```

### 2. Input File Discovery
```
batch/parse.py: BatchParseJob.run()
    │
    ▼
aws/read.py: get_objects_at_s3_uri(data_source)
    │
    ├── List all objects recursively
    ├── Filter empty files
    └── Return list of s3://bucket/key URIs
```

### 3. Per-File Processing
```
For each input file:
    │
    ├── aws/read.py: read_file_from_s3(uri)
    │       └── Auto-detect binary vs text
    │
    ├── doc_convert.convert_to_text()  (PDF, DOCX, etc.)
    │
    ├── gpt/text.py: split_to_token_size()
    │
    └── gpt/parse.py: async_fetch_parse() per chunk
```

### 4. Output Writing
```
aws/write.py: create_output_dir_for_job()
    │
    ▼
Output Structure:
{output_uri}/{timestamp}-{input_name}-output/
├── source.txt                  # Original input file
├── output_1.source.txt         # Input chunk 1
├── output_1.json               # Parse result for chunk 1
├── output_2.source.txt
├── output_2.json
├── ...
├── job_args.json               # Job configuration
└── job_log.txt                 # Execution log
```

## Batch Save Flow

### 1. Job Initialization
```
POST /new-batch-job (job_type="save")
    │
    ▼
batch/common.py: make_and_run_save_job()
```

### 2. Input Discovery
```
batch/save.py: _find_input_files(data_source)
    │
    ▼
aws/read.py: get_objects_by_folder_at_s3_uri()
    │
    └── Return dict: {folder_name: [file_uris]}
```

### 3. Source Matching
```
For each folder:
    │
    ├── Find output_*.json files
    ├── Find *.source.txt files
    │
    ▼
Matching Logic:
├── If one source.txt: Use for all outputs
├── If multiple sources: Match output_N.json to output_N.source.txt
└── If no sources: Use output file URI as source
```

### 4. Neo4j Writing
```
For each output file:
    │
    ├── aws/read.py: read_file_from_s3()
    ├── Parse JSON content
    │
    ▼
save.py: save_data_to_neo4j()
    │
    ├── neo/ent_data.py: EntityRecord.from_json_entry()
    ├── neo/write.py: create_or_update_entity()
    └── neo/write.py: create_or_update_relationship()
```

## EntityRecord Data Model

### Class Definition
```python
class EntityRecord:
    name: str                      # Entity name (required)
    normalized_name: str           # Lowercase version
    type: str                      # "Drug", "Disease", "Other"
    source: str                    # HTTP URL of source
    _source_s3: str                # S3 URI format
    _source_http: str              # HTTP URL format
    timestamp: DateTime            # Creation/modification time
    relationships: dict            # {rel_name: [targets]}
```

### JSON Input Format
```json
{
  "Aspirin": {
    "treats": "pain",
    "inhibits": ["COX-1", "COX-2"],
    "_ENTITY_TYPE": "Drug"
  }
}
```

### Processing Steps
1. `_ENTITY_TYPE` field extracted and removed
2. Remaining keys become relationship names
3. Values normalized to lists of strings
4. Relationship names sanitized to snake_case

### Neo4j Output

**Entity Node** (`:Entity`):
```
{
  name: "Aspirin",
  normalized_name: "aspirin",
  type: "Drug",
  created_at: DateTime,
  last_modified: DateTime,
  sources: ["https://bucket.s3.amazonaws.com/..."]
}
```

**Relationship Edge**:
```
(aspirin)-[:treats {sources: [...], created_at, last_modified}]->(pain)
```

## Neo4j Query Patterns

### Entity Creation/Update (MERGE)
```cypher
MERGE (e:Entity {normalized_name: $normalized_name})
ON CREATE SET
  e.name = $name,
  e.created_at = $timestamp,
  e.last_modified = $timestamp,
  e.sources = [$source]
ON MATCH SET
  e.last_modified = $timestamp,
  e.sources = CASE
    WHEN $source IN e.sources THEN e.sources
    ELSE e.sources + $source
  END
```

### Relationship Creation
```cypher
MATCH (e1:Entity {normalized_name: $ent1_norm})
MATCH (e2:Entity {normalized_name: $ent2_norm})
MERGE (e1)-[r:relationship_name]->(e2)
ON CREATE SET r.sources = [$source], r.created_at = $ts
ON MATCH SET r.sources = r.sources + $source
```

## Token Management

### Context Window Calculation
```
max_input_tokens = context_window
                 - system_message_tokens
                 - output_reservation
                 - margin_of_error (200)
```

### Model-Specific Limits

| Model | Context Window | Output Reserve | Timeout |
|-------|---------------|----------------|---------|
| gpt-3.5-turbo | 4,096 | 1,600 | 60s |
| gpt-3.5-turbo-16k | 16,384 | 8,000 | 120s |
| gpt-4 | 8,192 | 2,400 | 180s |
| gpt-4-32k | 32,768 | 16,000 | 300s |
| gpt-4o | 128,000 | 16,000 | 180s |
| gpt-4o-mini | 128,000 | 16,000 | 120s |

## Rate Limiting Strategy

### Per-Model Limits
```
gpt-4o:         500 RPM, 300k TPM
gpt-4o-mini:    750 RPM, 400k TPM
gpt-4:          200 RPM, 40k TPM
gpt-4-32k:      200 RPM, 80k TPM
gpt-3.5-turbo:  60 RPM, 60k TPM
```

### Backoff Algorithm
```python
backoff_time = 2^(error_count) * base_delay * (1 + random())
```

### Implementation
- Track concurrent requests per model
- Implement exponential backoff on rate limit errors
- Add jitter to prevent thundering herd
- Up to 5 retries for rate limits
- Up to 2 retries for timeouts

## Cross-References

- See `components.md` for detailed module documentation
- See `api_reference.md` for endpoint specifications
- See `architecture.md` for system overview
