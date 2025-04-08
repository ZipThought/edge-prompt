import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Ensures __dirname works in ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Correct paths based on current file location
const dbDir = path.resolve(__dirname, 'db');
const dbFilePath = path.join(dbDir, 'database.sqlite3');
const schemaPath = path.join(dbDir, 'schema.sql');

// Ensure db directory exists
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true });
}

// Open SQLite database
export const db = await open({
  filename: dbFilePath,
  driver: sqlite3.Database,
});

// Load schema and initialize tables
const schema = fs.readFileSync(schemaPath, 'utf8');
await db.exec(schema);
