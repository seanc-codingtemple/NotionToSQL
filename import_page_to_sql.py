#!/usr/bin/env python3
"""
import_data.py

Retrieve a single Notion page and prepare an INSERT statement for Postgres.

Usage:
  export NOTION_TOKEN=<your_token>
  python import_page_to_sql.py \
    --page-id <NOTION_PAGE_ID> \
    --schema database_schema.json \
    --table db_<DATABASE_ID> [--db-url <POSTGRES_CONNECTION_URL>]

If --db-url is provided, the script will attempt to connect and execute the INSERT.
Otherwise, it will just print the SQL and values.
"""
import os
import sys
import json
import argparse
import logging

try:
    import psycopg2
except ImportError:
    psycopg2 = None

from notion_client import Client
from generate_sql_ddl import slugify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_value(prop: dict):
    """Extract a Python value from a Notion property value object."""
    ptype = prop.get('type')
    # title and rich_text
    if ptype in ('title', 'rich_text'):
        texts = prop.get(ptype) or []
        return ''.join([t.get('plain_text', '') for t in texts]) or None
    # number
    if ptype == 'number':
        return prop.get('number')
    # select
    if ptype == 'select':
        sel = prop.get('select')
        return sel.get('name') if sel else None
    # multi_select
    if ptype == 'multi_select':
        return [opt.get('name') for opt in prop.get('multi_select', [])]
    # date
    if ptype == 'date':
        d = prop.get('date')
        return d.get('start') if d else None
    # checkbox
    if ptype == 'checkbox':
        return prop.get('checkbox')
    # url, email, phone_number
    if ptype in ('url', 'email', 'phone_number'):
        return prop.get(ptype)
    # people: return list of user IDs
    if ptype == 'people':
        return [u.get('id') for u in prop.get('people', [])]

    # files: return list of URLs
    if ptype == 'files':
        urls = []
        for f in prop.get('files', []):
            file_info = f.get('file') or f.get('external') or {}
            url = file_info.get('url')
            if url:
                urls.append(url)
        return urls
    # relation: list of page IDs
    if ptype == 'relation':
        return [r.get('id') for r in prop.get('relation', [])]
    # formula: pick primitive type, for date return the start string; empty strings -> None
    if ptype == 'formula':
        f = prop.get('formula', {})
        # number
        if f.get('number') is not None:
            return f.get('number')
        # string
        if f.get('string') is not None:
            s = f.get('string')
            return s if s else None
        # boolean
        if f.get('boolean') is not None:
            return f.get('boolean')
        # date returns an object
        if f.get('date'):
            return f.get('date', {}).get('start')
        return None
    # status: return the status name
    if ptype == 'status':
        s = prop.get('status')
        return s.get('name') if s else None

    # created_by / last_edited_by: return user id
    if ptype in ('created_by', 'last_edited_by'):
        u = prop.get(ptype)
        return u.get('id') if u else None

    # rollup: pick primitive if available; otherwise parse each array element and filter None
    if ptype == 'rollup':
        r = prop.get('rollup', {})
        # number
        if r.get('number') is not None:
            return r.get('number')
        # date returns an object
        if r.get('date'):
            return r.get('date', {}).get('start')
        # string
        if r.get('string') is not None:
            s = r.get('string')
            return s if s else None
        # boolean
        if r.get('boolean') is not None:
            return r.get('boolean')
        # array fallback
        arr = r.get('array', [])
        items = [parse_value(item) for item in arr]
        return [i for i in items if i is not None]
    # created_time, last_edited_time
    if ptype in ('created_time', 'last_edited_time'):
        return prop.get(ptype)
    # fallback: return raw
    return prop.get(ptype)


def main():
    parser = argparse.ArgumentParser(description='Import a Notion page into PostgreSQL')
    parser.add_argument('--page-id', '-p', required=True, help='Notion page ID to retrieve')
    parser.add_argument('--schema', '-s', required=True, help='JSON schema file (from index.py)')
    parser.add_argument('--table', '-t', required=True, help='Target SQL table name')
    parser.add_argument('--db-url', '-d', help='Postgres connection URL (optional)')
    args = parser.parse_args()

    token = os.getenv('NOTION_TOKEN')
    if not token:
        logger.error('Please set NOTION_TOKEN environment variable')
        sys.exit(1)

    # load schema mapping
    try:
        with open(args.schema, 'r', encoding='utf-8') as f:
            schema = json.load(f)
    except Exception as e:
        logger.error(f'Error loading schema file: {e}')
        sys.exit(1)

    # build property -> column map
    prop_defs = schema.get('properties', {})
    col_map = {name: slugify(name) for name in prop_defs.keys()}

    # retrieve page
    notion = Client(auth=token)
    try:
        page = notion.pages.retrieve(page_id=args.page_id)
    except Exception as e:
        logger.error(f'Error retrieving page {args.page_id}: {e}')
        sys.exit(1)

    # extract properties
    props = page.get('properties', {})
    row = {}
    # always include page id as primary key
    row['id'] = page.get('id')
    for name, meta in prop_defs.items():
        col = col_map.get(name)
        prop_value = props.get(name)
        if prop_value is None:
            row[col] = None
        else:
            row[col] = parse_value(prop_value)

    # write raw row data to JSON for inspection
    raw_file = f"{args.table}_{args.page_id}_data.json"
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(row, f, indent=2)
    print(f"Raw row JSON written to {raw_file}")

    # build SQL
    columns = list(row.keys())
    placeholders = ', '.join(['%s'] * len(columns))
    col_list = ', '.join([f'"{c}"' for c in columns])
    sql = f'INSERT INTO "{args.table}" ({col_list}) VALUES ({placeholders});'
    values = [row[c] for c in columns]

    # write SQL and values to a .sql file
    out_file = f"{args.table}_{args.page_id}_insert.sql"
    with open(out_file, 'w', encoding='utf-8') as f:
        # write the INSERT statement
        f.write(sql + '\n\n')
        # append the values as a commented JSON blob
        f.write('-- Values: ' + json.dumps(values) + '\n')
    print(f"SQL + values written to {out_file}")

    # optional execution
    if args.db_url:
        if not psycopg2:
            logger.error('psycopg2 not installed; cannot connect to DB')
            sys.exit(1)
        try:
            conn = psycopg2.connect(args.db_url)
            cur = conn.cursor()
            cur.execute(sql, values)
            conn.commit()
            logger.info('Row inserted successfully')
            cur.close()
            conn.close()
        except Exception as e:
            logger.error(f'Error executing SQL: {e}')
            sys.exit(1)


if __name__ == '__main__':
    main()
