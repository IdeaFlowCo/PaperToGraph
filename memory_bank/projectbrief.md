# Project Brief: PaperToGraph

## Overview

PaperToGraph is a Python/Quart web application that extracts entities and relationships from scientific papers using GPT, stores them in a Neo4j graph database, and provides various interfaces for batch processing, search, and querying.

## Core Purpose

Transform unstructured scientific literature into a structured knowledge graph by:
1. Extracting named entities (Drugs, Diseases, Other) from text
2. Identifying relationships between entities
3. Storing the knowledge graph in Neo4j for querying and analysis

## Problem Statement

Scientific literature contains vast amounts of knowledge locked in unstructured text. Researchers need efficient ways to:
- Extract key entities (drugs, diseases, genes, etc.) from papers
- Understand relationships between entities
- Query accumulated knowledge across multiple papers
- Build knowledge graphs from document collections

## Target Users

- Researchers analyzing scientific literature
- Data scientists building biomedical knowledge graphs
- Organizations needing to extract structured data from document collections
- Teams working on drug discovery, disease research, or similar domains

## Application Modes

PaperToGraph supports three operational modes via the `APP_MODE` environment variable:

### 1. paper2graph (Default)
Full-featured entity extraction and knowledge graph building:
- Text parsing with GPT
- Batch processing from S3
- Neo4j graph storage
- Document search and semantic query
- Google Drive integration

### 2. querymydrive
Focused on searching and querying Google Drive documents:
- Google Drive OAuth integration
- Document ingestion to Simon semantic search
- Simplified UI for document querying

### 3. rarediseaseguru
Specialized mode for rare disease information:
- Targeted interface for rare disease queries
- Hackathon template UI
- Limited functionality subset

## Key Features

- **Entity Extraction**: GPT-powered extraction of named entities from text
- **Relationship Mapping**: Automatic identification of relationships between entities
- **Batch Processing**: Process large document sets from S3
- **Knowledge Graph**: Neo4j storage with entity and relationship tracking
- **Semantic Search**: Simon-powered semantic search over ingested documents
- **Multi-Format Support**: Handle PDF, DOCX, TXT, and Google Docs
- **Source Attribution**: Track source documents for all extracted data

## Integration Points

- **OpenAI API**: GPT models for entity extraction
- **Neo4j**: Graph database storage
- **AWS S3**: Document storage and batch job I/O
- **Google Drive**: Document source and OAuth
- **Simon**: Semantic search backend (PostgreSQL + Elasticsearch)
- **Sentry**: Error tracking and monitoring

## Success Criteria

- Accurately extract entities and relationships from scientific text
- Build queryable knowledge graphs from document collections
- Support scalable batch processing of large document sets
- Maintain source attribution for all extracted data
- Provide intuitive interfaces for search and query
