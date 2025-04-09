// edge-prompt/backend/src/services/AuthenticationService.ts

import { DatabaseService } from './DatabaseService.js';
import bcrypt from 'bcryptjs';

// Create a shared instance of DatabaseService.
// (This means that this module will have its own DB connection.
// Alternatively, you could pass the instance from index.ts if you need a single shared instance.)
const dbService = new DatabaseService();

/**
 * Registers a new user in the database.
 *
 * @param id - Unique user ID.
 * @param firstname - User's first name.
 * @param lastname - User's last name.
 * @param email - User's email.
 * @param passwordhash - User's hashed password.
 * @param dob - User's date of birth.
 * @throws Error if a user with the given email already exists.
 */
export async function registerUser(
  id: string,
  firstname: string,
  lastname: string,
  email: string,
  passwordhash: string,
  dob: string
): Promise<void> {
  // Prepare a statement to check if the user already exists.
  const stmtSelect = dbService['db'].prepare('SELECT * FROM users WHERE email = ?');
  const existingUser = stmtSelect.get(email);
  if (existingUser) {
    throw new Error('User already exists');
  }

  // Insert the new user into the users table.
  const stmtInsert = dbService['db'].prepare(`
    INSERT INTO users (id, firstname, lastname, email, passwordhash, dob)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  stmtInsert.run(id, firstname, lastname, email, passwordhash, dob);
}

/**
 * Authenticates a user by verifying their email and password.
 *
 * @param email - The email address provided during login.
 * @param password - The plain text password provided during login.
 * @returns The user object on successful authentication.
 * @throws Error if the authentication fails.
 */
export async function loginUser(
  email: string,
  password: string
): Promise<any> {
  // Prepare a statement to retrieve the user by email.
  const stmtSelect = dbService['db'].prepare('SELECT * FROM users WHERE email = ?');
  const user = stmtSelect.get(email);
  if (!user) {
    throw new Error('Invalid email or password.');
  }
  
  // Compare the provided plain text password with the stored hash.
  const isMatch = bcrypt.compareSync(password, user.passwordhash);
  if (!isMatch) {
    throw new Error('Invalid email or password.');
  }
  
  return user;
}
