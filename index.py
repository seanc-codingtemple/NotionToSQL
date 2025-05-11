#!/usr/bin/env python3
"""
A simple script that maps a Notion database schema into a clean JSON using Python and a virtual environment.

Setup and usage:
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  export NOTION_TOKEN=<your_notion_token>
  python index.py [DATABASE_ID]

If DATABASE_ID is omitted, it defaults to 5ae98e91b6c1427c8e9e01552e05d3c5
"""

import os
import sys
import json

from notion_client import Client
from notion_utils import map_database_schema


def main():
    token = os.getenv("NOTION_TOKEN")
    if not token:
        print("Error: Please set NOTION_TOKEN environment variable.")
        sys.exit(1)

    database_id = sys.argv[1] if len(sys.argv) > 1 else "5ae98e91b6c1427c8e9e01552e05d3c5"

    notion = Client(auth=token)

    try:
        schema = map_database_schema(notion, database_id)
        # Write schema to sample_output.json for downstream processing
        output_file = 'sample_output.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(schema, indent=2))
        print(f"Schema written to {output_file}")
    except Exception as e:
        print("Error mapping database schema:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
