# /Users/seancurrie/Desktop/MCP/NotionToSQL/notion_utils.py
"""
Utility functions for mapping Notion database schemas into a consistent JSON structure.

This module handles:
  - Retrieving database definitions
  - Parsing property types (title, rich_text, number, select, multi_select, date,
    people, files, checkbox, url, email, phone_number, formula, relation, rollup,
    created_time, last_edited_time, status, created_by, last_edited_by)
  - Error handling and validation
  - Fetching related database metadata (ID + title)

For full details, see the Notion API docs:
https://developers.notion.com/reference/property-object
"""

import logging
from notion_client import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supported property types based on Notion API
SUPPORTED_TYPES = {
    "title", "rich_text", "number", "select", "multi_select", "date",
    "people", "files", "checkbox", "url", "email", "phone_number",
    "formula", "relation", "rollup", "created_time", "last_edited_time",
    "status", "created_by", "last_edited_by"
}


def retrieve_database(notion: Client, database_id: str) -> dict:
    """
    Retrieve a database schema from Notion, with error handling.

    Raises:
      ValueError on invalid ID or if API returns an error.
    """
    try:
        db = notion.databases.retrieve(database_id=database_id)
        return db
    except Exception as e:
        logger.error(f"Failed to retrieve database {database_id}: {e}")
        raise ValueError(f"Cannot retrieve Notion database: {database_id}")


def parse_property(notion: Client, db_props: dict, name: str, prop: dict) -> dict:
    """
    Parse a single property definition into a normalized dict entry.

    Returns a dict with at least `type`, plus type-specific metadata.
    """
    ptype = prop.get("type")
    if ptype not in SUPPORTED_TYPES:
        logger.warning(f"Unsupported property type '{ptype}' for '{name}', skipping.")
        return {"type": ptype}

    # Include the immutable Notion property ID to tie metadata to data columns
    entry = {"type": ptype, "property_id": prop.get("id")}

    if ptype == "relation":
        rid = prop.get("relation", {}).get("database_id")
        entry.update(_fetch_related_db(notion, rid))

    elif ptype == "rollup":
        rc = prop.get("rollup", {})
        rel_prop_name = rc.get("relation_property_name")
        rp = db_props.get(rel_prop_name, {})
        rid = rp.get("relation", {}).get("database_id")
        entry.update(_fetch_related_db(notion, rid))
        entry.update({
            "rollup_property_name": rc.get("rollup_property_name"),
            "rollup_function": rc.get("function")
        })

    elif ptype == "formula":
        entry["formula_expression"] = prop.get("formula", {}).get("expression")

    # other Notion types can include extra metadata if desired
    # for example, `select` has `options`, `number` has `format`, etc.

    return entry


def _fetch_related_db(notion: Client, database_id: str) -> dict:
    """
    Helper to fetch title for related databases.
    Returns a dict with `relation_database_id` and `relation_database_title`.
    """
    info = {"relation_database_id": database_id, "relation_database_title": None}
    if not database_id:
        return info

    try:
        rd = notion.databases.retrieve(database_id=database_id)
        title_rich = rd.get("title", [])
        title = "".join([t.get("plain_text", "") for t in title_rich])
        info["relation_database_title"] = title
    except Exception as e:
        logger.warning(f"Could not fetch related database title for {database_id}: {e}")
    return info


def map_database_schema(notion: Client, database_id: str) -> dict:
    """
    Retrieve and map the entire database schema to a JSON-friendly dict.
    """
    db = retrieve_database(notion, database_id)
    props = db.get("properties", {})
    mapped = {}
    for name, prop in props.items():
        try:
            mapped[name] = parse_property(notion, props, name, prop)
        except Exception as e:
            logger.error(f"Error parsing property '{name}': {e}")
            mapped[name] = {"type": prop.get("type"), "error": str(e)}

    # also capture the human-readable database title
    title_rich = db.get("title", [])
    title = "".join([t.get("plain_text", "") for t in title_rich])
    return {"database_id": database_id, "database_title": title, "properties": mapped}
