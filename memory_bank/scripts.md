# Scripts Reference

## Overview

Utility scripts are located in the `scripts/` directory and run via the `run_script.py` framework.

## Script Runner

**Usage**:
```bash
python run_script.py <script_name> [arguments]
```

**Script Requirements**:
- Must have a `main(args)` function
- Optionally define `parse_args(sys_args)` for CLI argument parsing

---

## Batch Processing Scripts

### run_batch_parse_job.py

CLI alternative to the web UI batch parse.

**Usage**:
```bash
python run_script.py run_batch_parse_job \
  --data_source=s3://bucket/input/ \
  --output_uri=s3://bucket/output/ \
  [--gpt_model=gpt-4o] \
  [--dry_run]
```

**Arguments**:

| Argument | Description | Required |
|----------|-------------|----------|
| `--data_source` | S3 URI of input files | Yes |
| `--output_uri` | S3 URI for output directory | Yes |
| `--gpt_model` | GPT model to use | No |
| `--prompt_override` | Custom parse prompt | No |
| `--dry_run` | Simulation mode (no writes) | No |
| `--neo-uri` | Override Neo4j URI | No |
| `--neo-user` | Override Neo4j user | No |
| `--neo-pass` | Override Neo4j password | No |

**Output Structure**:
```
{output_uri}/{timestamp}-{input_name}-output/
├── source.txt
├── output_1.source.txt
├── output_1.json
├── output_2.source.txt
├── output_2.json
├── job_args.json
└── job_log.txt
```

### run_batch_save_job.py

CLI alternative to the web UI batch save.

**Usage**:
```bash
python run_script.py run_batch_save_job \
  --data_source=s3://bucket/parse-output/
```

**Arguments**:

| Argument | Description | Required |
|----------|-------------|----------|
| `--data_source` | S3 URI of parse output | Yes |
| `--neo-uri` | Override Neo4j URI | No |
| `--neo-user` | Override Neo4j user | No |
| `--neo-pass` | Override Neo4j password | No |

**Expected Input Structure**:
```
{data_source}/
├── folder1/
│   ├── source.txt
│   ├── output_1.json
│   └── output_2.json
└── folder2/
    ├── source.txt
    └── output_1.json
```

---

## Entity Enrichment Scripts

### enrich_entity_types.py

Tag entities in Neo4j with type classification (Drug, Disease, Other).

**Usage**:
```bash
python run_script.py enrich_entity_types \
  [--neo-uri=...] \
  [--neo-user=...] \
  [--neo-pass=...]
```

**Process**:
1. Query Neo4j for entities without `type` property (batch of 300)
2. Send entity names to GPT for classification
3. Update entities with type in Neo4j
4. Repeat until all entities are classified

**GPT Prompt**: Classify each entity as:
- `Drug` - medication names
- `Disease` - medical conditions
- `Other` - genes, proteins, etc.

**Output Format**: `("entity_name", "type")`

**Thread Name**: `p2g-ent-types`

### enrich_relationship_types.py

Categorize relationships in Neo4j.

**Usage**:
```bash
python run_script.py enrich_relationship_types \
  [--neo-uri=...] \
  [--neo-user=...] \
  [--neo-pass=...]
```

**Process**:
1. Query unique relationship types from Neo4j
2. Classify each relationship type via GPT
3. Update relationship metadata in Neo4j

**Categories**:
- `Promotes` - positive relationship
- `Inhibits` - negative relationship
- `Associated With` - neutral connection
- `Disconnected From` - negative connection
- `Other` - uncategorized

**Thread Name**: `p2g-rel-types`

### enrich_source_dates.py

Extract and enrich publication dates from source URIs.

**Usage**:
```bash
python run_script.py enrich_source_dates
```

**Process**:
1. Walk entities with source URIs
2. Parse source text for publication dates
3. Update entities with date metadata

---

## Graph Maintenance Scripts

### cleanup_graph_sources.py

Normalize source URIs to HTTP format.

**Usage**:
```bash
python run_script.py cleanup_graph_sources \
  [--neo-uri=...] \
  [--neo-user=...] \
  [--neo-pass=...]
```

**Process**:
1. Query entities with S3 URI format sources
2. Convert `s3://bucket/key` to `https://bucket.s3.amazonaws.com/key`
3. Update source arrays in Neo4j

**Thread Name**: `p2g-graph-sources`

### fix_source_strings.py

Correct malformed source strings.

**Usage**:
```bash
python run_script.py fix_source_strings
```

**Process**:
1. Query entities with malformed sources
2. Apply corrections
3. Update Neo4j

---

## Data Preparation Scripts

### papers_to_training_data.py

Generate Q&A training data from scientific papers.

**Usage**:
```bash
python run_script.py papers_to_training_data \
  --input_dir=/path/to/papers \
  --output_file=/path/to/output.jsonl
```

**Process**:
1. Read papers from input directory
2. Extract text content
3. Generate Q&A pairs via GPT
4. Write to JSONL format

**Output Format**:
```json
{"question": "What is...", "answer": "..."}
```

### extract_q_and_a_data.py

Extract Q&A pairs from paper text.

**Usage**:
```bash
python run_script.py extract_q_and_a_data
```

### extract_article_metadata_from_xml.py

Extract metadata from XML article files.

**Usage**:
```bash
python run_script.py extract_article_metadata_from_xml \
  --input_dir=/path/to/xml/files
```

---

## Log Analysis Scripts

### analyze_parse_job_log.py

Analyze batch parse job logs for statistics and errors.

**Usage**:
```bash
python run_script.py analyze_parse_job_log \
  --log_file=/path/to/job_log.txt
```

**Output**:
- Total files processed
- Success/failure counts
- Error breakdown
- Timing statistics

---

## Common CLI Arguments

All scripts support these configuration overrides:

| Argument | Description |
|----------|-------------|
| `--neo-uri` | Neo4j connection URI |
| `--neo-user` | Neo4j username |
| `--neo-pass` | Neo4j password |
| `--log-level` | Logging level |
| `--log-file` | Log file path |

---

## Running Scripts as Background Jobs

Scripts can be run as background jobs via the web UI for:
- `enrich_entity_types`
- `enrich_relationship_types`
- `cleanup_graph_sources`

These use the same BatchJobThread infrastructure as batch parse/save jobs.

---

## Cross-References

- See `configuration.md` for environment variables
- See `components.md` for module documentation
- See `dataflow.md` for data processing details
