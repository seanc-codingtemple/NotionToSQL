# How It Works: Notion Schema to PostgreSQL DDL

_Author: Lead Software Engineering Manager_

## Overview

This repository provides a streamlined, modular pipeline to:

1. **Retrieve** a Notion database schema via the official Notion API.  
2. **Normalize** and **serialize** that schema to a concise JSON file.  
3. **Generate** PostgreSQL DDL (Data Definition Language) statements to create tables that mirror the Notion schema, plus a metadata table capturing full property details.

The pipeline consists of three main scripts:

- `index.py` – orchestration script, reads your Notion integration token & database ID, and writes `sample_output.json`.  
- `notion_utils.py` – utility module handling API calls, property parsing, error handling, and metadata extraction.  
- `sql_generator.py` – takes `sample_output.json` and produces `sample_output.sql`, containing DDL for your main table and a companion `__schema` table.

A Python virtual environment (`.venv`) and `requirements.txt` ensure you install only the Notion client and dependencies locally.

---

## Tool 1: notion_utils.py

### Responsibilities

- **Retrieve** the raw database object from Notion (`databases.retrieve`).  
- **Parse** each property definition into a normalized Python dict with:
  - `type` (the Notion property type)  
  - `property_id` (immutable UUID assigned by Notion)  
  - Type-specific metadata (e.g. formula expression, rollup configuration, select options).  
- **Error handling** and logging: unsupported types, API failures, malformed schemas.

### Key Techniques & Challenges

- **Dynamic schemas**: Notion databases can have arbitrarily-named properties of many types. We use a `SUPPORTED_TYPES` set and pattern-match each type.
- **Stable identifiers**: Users can rename a column in the UI, which changes its `name` but not its `id`. We capture `property_id` to reliably link data ↔ metadata.
- **Nested objects**: Relation and rollup properties embed database IDs, relation property names, and function names. We unwrap these to flat JSON fields.
- **API rate-limits & errors**: Wrapped API calls in try/catch, logging failures without halting the entire schema mapping.

---

## Tool 2: index.py

### Responsibilities

- Read your **Notion integration token** (`NOTION_TOKEN` env var) and an optional **database ID** (CLI argument).  
- Instantiate the Notion client (`@notionhq/client`).  
- Call `map_database_schema` from `notion_utils` to build a JSON-friendly representation.  
- **Persist** the schema to `sample_output.json` for downstream processing.

### Rationale

- Keeps all side-effects (file writes) at the top level.  
- Makes the schema export fully repeatable: rerun after schema changes in Notion to regenerate JSON.

---

## Tool 3: sql_generator.py

### Responsibilities

- **Read** `sample_output.json`.  
- **Generate** SQL DDL:
  1. **Main table** (`db_<ID>`) with columns for every property:
     - `id UUID PRIMARY KEY` – we add an explicit primary key using Notion’s page IDs.  
     - Non-relation columns: mapped by type (e.g. `TEXT`, `NUMERIC`, `TIMESTAMPTZ`).  
     - **Relation** columns: stored as `UUID[]` arrays of foreign page IDs.  
     - **Rollup** columns: scalar aggregates become `INTEGER` or `NUMERIC`; others default to `JSONB`.  
  2. **Metadata table** (`db_<ID>__schema`) capturing full property definitions:
     - `property_id` (UUID) – stable key.  
     - `property_name` (original label), `column_name` (slugified SQL).  
     - `type` and raw `metadata` JSONB blob.
- **Write** the combined DDL to `sample_output.sql`.

### Rationale & Best Practices

- **Array columns** for relations keep the import simple. If you later need a true many-to-many join table, you can generate it from the metadata table without changing the ingestion logic.
- **Scalar vs JSONB for rollups**: storing numeric aggregates in typed columns optimizes for filtering and aggregation in SQL; fall back to JSONB for free-form rollups.
- **Schema metadata table** acts as a “dictionary” for your ETL and migrations—don’t rely on human-readable names, use `property_id`.

---

## Notion API Nuances

1. **Property Objects** are polymorphic: each has a `type` field and a nested block containing type-specific settings.  
2. **Properties** are defined at the database level; each page (row) then has analogous **PropertyValue** objects.  
3. **Relations** store page IDs of linked pages. Under the hood, these are many-to-many.  
4. **Rollups** compute over those related pages, but Notion does not expose raw aggregates directly in the page objects—only in the schema of the database.  
5. **Formulas** use a custom expression language; we capture the raw string so you can re-implement or inspect it.

---

## Challenges & Solutions

- **Changing column names**: We capture `property_id` to decouple schema from labels.  
- **Huge formulas**: We store expressions as JSONB metadata rather than embedding them in VARCHAR columns.  
- **Evolving schemas**: By regenerating JSON and re-running SQL DDL, you can migrate safely.
- **Rate-limits**: You can batch or cache related database requests in `notion_utils` if you have large numbers of relations.

---

## Next Steps & Extensions

- **Data Ingestion**: Write an ETL that reads Notion page data (`query` vs `retrieve`) and loads it into the SQL tables. Use the metadata to map column names and types.  
- **Join Table Generation**: Enable optional generation of many-to-many join tables for relations, based on metadata flags.  
- **Select / Multi-select options**: Extend the metadata table to store select option lists and colors, then create PostgreSQL ENUM types.  
- **Versioned Schemas**: Introduce a `schema_version` table and retain historical schema snapshots.

By modularizing schema mapping and SQL generation, you maintain a clear separation of concerns, minimize brittle string-manipulation errors, and leverage Notion’s API primitives effectively. Enjoy a robust, repeatable workflow for bridging Notion and PostgreSQL!  
