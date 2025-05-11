// /Users/seancurrie/Desktop/MCP/NotionToSQL/index.js

/* 
  A simple script that retrieves a Notion database's properties and their types
  Usage:
    1. npm install @notionhq/client
    2. set NOTION_TOKEN=your_integration_token
    3. node index.js [DATABASE_ID]
*/

const { Client } = require('@notionhq/client');

// Read your integration token from environment variable
const notion = new Client({ auth: process.env.NOTION_TOKEN });

async function main() {
  // Accept database ID from the first CLI argument, otherwise use default
  const databaseId = process.argv[2] || '5ae98e91b6c1427c8e9e01552e05d3c5';

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
