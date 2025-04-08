import { db } from '../database.js';
import bcrypt from 'bcryptjs';

export async function loginUser(
  email: string,
  password: string
): Promise<any> {

  const user = await db.get('SELECT * FROM users WHERE email = ?', [email]);
  if (!user) {
    throw new Error('Invalid email or password.');
  }
  
  // Compare the provided plaintext password with the stored bcrypt hash.
  const isMatch = await bcrypt.compare(password, user.passwordhash);
  if (!isMatch) {
    throw new Error('Invalid email or password.');
  }
  
  return user;
}