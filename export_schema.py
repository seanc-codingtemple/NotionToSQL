#!/usr/bin/env python3
"""
A simple script that maps a Notion database schema into a clean JSON using Python and a virtual environment.

Setup and usage:
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  export NOTION_TOKEN=<your_notion_token>
  python export_schema.py [DATABASE_ID]

If DATABASE_ID is omitted, supply it via the NOTION_DATABASE_ID environment variable.
"""

import os
import sys
import json

from notion_client import Client
from schema_mapper import map_database_schema


def main():
    token = os.getenv("NOTION_TOKEN")
    if not token:
        print("Error: Please set NOTION_TOKEN environment variable.")
        sys.exit(1)

database_id = sys.argv[1] if len(sys.argv) > 1 else os.getenv("NOTION_DATABASE_ID")
if not database_id:
    print("Error: Please provide DATABASE_ID as an argument or set NOTION_DATABASE_ID environment variable.")
    sys.exit(1)

    notion = Client(auth=token)

    try:
        schema = map_database_schema(notion, database_id)
        # Write schema to database_schema.json for downstream processing
        output_file = 'database_schema.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(schema, indent=2))
        print(f"Schema written to {output_file}")
    except Exception as e:
        print("Error mapping database schema:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
