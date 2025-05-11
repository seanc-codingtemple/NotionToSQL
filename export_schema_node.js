// /Users/seancurrie/Desktop/MCP/NotionToSQL/index.js

/* 
  A simple script that retrieves a Notion database's properties and their types
  Usage:
    1. npm install @notionhq/client
    2. set NOTION_TOKEN=your_integration_token
    3. node index.js [DATABASE_ID] or set NOTION_DATABASE_ID environment variable
*/

const { Client } = require('@notionhq/client');

// Read your integration token from environment variable
const notion = new Client({ auth: process.env.NOTION_TOKEN });

async function main() {
  // Accept database ID from the first CLI argument or from NOTION_DATABASE_ID env var
  const databaseId = process.argv[2] || process.env.NOTION_DATABASE_ID;
  if (!databaseId) {
    console.error('Error: Please provide DATABASE_ID as an argument or set NOTION_DATABASE_ID environment variable.');
    process.exit(1);
  }

  try {
    const response = await notion.databases.retrieve({ database_id: databaseId });
    console.log(`Database ID: ${databaseId}`);
    console.log('Properties and types:');

    const properties = response.properties;
    for (const [name, prop] of Object.entries(properties)) {
      console.log(`- ${name}: ${prop.type}`);
    }
  } catch (error) {
    console.error('Error retrieving database:', error);
    process.exit(1);
  }
}

main();
