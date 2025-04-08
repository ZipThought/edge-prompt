import sqlite3 from 'sqlite3';
import { open } from 'sqlite';

// interface for a user
export interface User {
  id: number;
  email: string;
  password: string; 
}

const dbPromise = open({
  filename: './edge-prompt/backend/src/db/database.sqlite3',
  driver: sqlite3.Database
});

// Utility function to get a user by email.
export async function getUserByEmail(email: string): Promise<User | null> {
  const db = await dbPromise;
  const user = await db.get<User>(
    `SELECT id, email, password FROM users WHERE email = ?`,
    email
  );
  return user || null;
}
