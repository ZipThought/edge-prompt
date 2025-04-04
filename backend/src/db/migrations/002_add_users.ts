import { DatabaseService } from '../../services/DatabaseService.js';
import { StorageService } from '../../services/StorageService.js';

export async function up() {
    const db = new DatabaseService();
    const storage = new StorageService();

    // Initialize storage
    await storage.initialize();

    await db.exec(`
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            position TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    `);
}

export async function down() {
    const db = new DatabaseService();
    await db.exec(`
        DROP TABLE IF EXISTS users;
    `);
}