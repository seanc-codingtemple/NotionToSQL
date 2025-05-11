# How It Works: Notion to PostgreSQL Workflow

This pipeline bridges Notion and PostgreSQL through three clear, modular steps:

1. **export_schema.py** – pull your Notion database schema into JSON.
2. **generate_sql_ddl.py** – turn that JSON schema into SQL DDL.
3. **import_page_to_sql.py** – fetch individual Notion pages and build insert scripts.

Each tool writes well‐named files so you can inspect, version, and extend your data flow.

---

## 1. Schema Extraction (export_schema.py)

High‐level:
Retrieves your Notion database definition and writes it to `database_schema.json`.

Usage:
```shell
export NOTION_TOKEN=<your_notion_token>
export NOTION_DATABASE_ID=<your_database_uuid>
python3 export_schema.py
# → database_schema.json
```

Details:
- Reads `NOTION_TOKEN` and `DATABASE_ID` (env var or CLI arg).
- Uses `notion_client` + `schema_mapper.map_database_schema` to normalize properties:
  - Captures `property_id`, types, and metadata (options, formulas, relations).
- Saves the output in **database_schema.json**.

---

## 2. DDL Generation (generate_sql_ddl.py)

High‐level:
Consumes **database_schema.json** and writes table‐creation SQL to `database_schema.sql`.

Usage:
```shell
python3 generate_sql_ddl.py \
  --input database_schema.json \
  [--table-name custom_table_name] \
  --output database_schema.sql
# → database_schema.sql
```
If you omit `--table-name`, the script defaults to a slug based on your Notion database’s title, falling back to `db_<DATABASE_ID>`.

Details:
- Maps Notion types to Postgres types (`TEXT`, `NUMERIC`, `UUID[]`, etc.).
- Slugifies property names into SQL‐safe column identifiers.
- Table naming logic:
  1. Use `--table-name` override if provided.
  2. Otherwise, slugify the Notion database title from `database_schema.json`.
  3. If title is blank, use `db_<DATABASE_ID>`.
- Produces two CREATE statements:
  1. **Main table** (named per above) with a UUID primary key and one column per property.
  2. **Metadata table** (append `__schema` suffix) listing each property’s ID, name, column, and JSONB metadata.

---

## 3. Data Import Simulation (import_page_to_sql.py)

High‐level:
Fetches a single Notion page and writes:
- A JSON file with the cleaned row (`<table>_<page_id>_page.json`).
- An INSERT SQL script (`<table>_<page_id>_insert.sql`).

Usage:
```shell
PAGE_ID=<32‐hex_page_uuid>
python3 import_page_to_sql.py \
  --page-id $PAGE_ID \
  --schema database_schema.json \
  --table db_<DATABASE_ID>
# → db_<DATABASE_ID>_<PAGE_ID>_page.json
# → db_<DATABASE_ID>_<PAGE_ID>_insert.sql
```

Details:
- Reads the JSON schema to map Notion property names → column names.
- Calls `notion.pages.retrieve(page_id)` to fetch the page.
- Normalizes each value:
  - **Text** → string
  - **Number / Boolean** → numeric or boolean
  - **Date / Timestamp** → ISO date string
  - **Select / Multi‐select** → string/list of strings
  - **Relation** → list of page IDs
  - **Formula / Rollup** → pick primitive result or cleaned array
  - **People** → list of user IDs
  - **Files** → list of file URLs
- Writes two files:
  1. **`<table>_<page_id>_page.json`**: the raw row dict.
  2. **`<table>_<page_id>_insert.sql`**: the INSERT statement with a commented JSON of values.
- Optionally, add `--db-url <POSTGRES_URL>` to connect via `psycopg2` and execute the insert directly.

---

## 4. (Optional) JS Exporter (export_schema_node.js)

High‐level:
A Node.js version of schema export—prints property names and types to stdout.

Usage:
```shell
export NOTION_TOKEN=<your_notion_token>
node export_schema_node.js [DATABASE_ID]
```

Redirect or pipe its output into a `.json` file if desired.

---

### Notion → Postgres Type Map

| Notion Type            | Mapped Value                     |
|------------------------|----------------------------------|
| title / rich_text      | plain string                     |
| number                 | Python numeric                   |
| select                 | selected option name             |
| multi_select           | list of option names             |
| date                   | ISO date/time string             |
| checkbox               | boolean                          |
| url / email / phone    | string                           |
| people                 | list of user IDs                 |
| files                  | list of URLs                     |
| relation               | list of page UUIDs               |
| formula / rollup       | primitive (num, bool, string, date) or cleaned list |
| status                 | status name                      |
| created_time / last_edited_time | ISO timestamp          |
| created_by / last_edited_by     | user ID                 |

For full schema details, see Notion’s Property Object docs: https://developers.notion.com/reference/property-object

---

By separating schema export, DDL generation, and page import, you get a transparent, repeatable pipeline. Feel free to add ETL steps, join‐table generators, or migration scripts as your project grows.