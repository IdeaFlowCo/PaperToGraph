# Progress Tracker

This file tracks the development progress of PaperToGraph.

## What Works

<!-- Features and functionality that are complete and working -->

- Core entity extraction via GPT
- Batch parsing from S3
- Batch saving to Neo4j
- Web UI for parse/save operations
- Google Drive OAuth integration
- Simon semantic search integration
- Entity type classification (Drug/Disease/Other)
- Relationship type classification
- Source attribution tracking
- Multiple GPT model support (3.5-turbo through 4o)
- Document format support (PDF, DOCX, TXT)

## What Is In Progress

<!-- Features currently under development -->

## What Is Planned

<!-- Features planned for future development -->

## Known Issues

<!-- Bugs and problems that need to be fixed -->

## Technical Debt

<!-- Areas that need refactoring or improvement -->

- `merge.py` and `gpt/merge.py` are legacy code (GPT merge doesn't work well)
- Some scripts may need updates for newer GPT models

## Performance Notes

<!-- Observations about system performance -->

- Rate limiting implemented per GPT model
- Batch jobs run in background threads
- Heartbeat streaming keeps long connections alive

## Dependencies to Watch

<!-- External dependencies that may need updates -->

- OpenAI API changes
- Neo4j driver updates
- Simon library updates
- AWS SDK updates
