import { DatabaseService } from '../services/DatabaseService.js';
import { StorageService } from '../services/StorageService.js';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function migrate() {
  console.log('Starting database migration...');
  
  try {
    const db = new DatabaseService();
    const storage = new StorageService();
    const schema = readFileSync(join(__dirname, 'schema.sql'), 'utf8');
    
    // Initialize storage
    await storage.initialize();

    // Run migrations in a transaction
    await db.transaction(async () => {
      // Create tables if they don't exist
      await db.exec(schema);
      console.log('Schema initialized');
    
      // Initialize roles
    await db.exec(`
      INSERT INTO roles (id, name, description)
      SELECT 'role_admin', 'Administrator', 'Has full access to the system'
      WHERE NOT EXISTS (SELECT 1 FROM roles WHERE id = 'role_admin');

      INSERT INTO roles (id, name, description)
      SELECT 'role_teacher', 'Teacher', 'Can create and manage materials and projects'
      WHERE NOT EXISTS (SELECT 1 FROM roles WHERE id = 'role_teacher');

      INSERT INTO roles (id, name, description)
      SELECT 'role_student', 'Student', 'Can view materials and submit responses'
      WHERE NOT EXISTS (SELECT 1 FROM roles WHERE id = 'role_student');
    `);
    console.log('Roles initialized');

    // Initialize permissions (using named permissions)
    await db.exec(`
      INSERT INTO permissions (id, name, description)
      SELECT 'perm_create_project', 'create_project', 'Allows creating new projects'
      WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE name = 'create_project');

      INSERT INTO permissions (id, name, description)
      SELECT 'perm_edit_material', 'edit_material', 'Allows editing existing materials'
      WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE name = 'edit_material');

      INSERT INTO permissions (id, name, description)
      SELECT 'perm_view_user_data', 'view_user_data', 'Allows viewing user data'
      WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE name = 'view_user_data');

      INSERT INTO permissions (id, name, description)
      SELECT 'perm_download_file', 'download_file', 'Allows downloading files'
      WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE name = 'download_file');

      INSERT INTO permissions (id, name, description)
      SELECT 'perm_generate_question', 'generate_question', 'Allows generating questions'
      WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE name = 'generate_question');

      INSERT INTO permissions (id, name, description)
      SELECT 'perm_validate_response', 'validate_response', 'Allows validating student responses'
      WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE name = 'validate_response');

      INSERT INTO permissions (id, name, description)
      SELECT 'perm_view_project', 'view_project', 'Allows viewing project details'
      WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE name = 'view_project');
  `);
  console.log('Permissions initialized');



    // Initialize role_permissions (Role Assignments)
    await db.exec(`
      INSERT INTO role_permissions (role_id, permission_id)
      SELECT 'role_admin', 'perm_create_project'
      WHERE NOT EXISTS (SELECT 1 FROM role_permissions WHERE role_id = 'role_admin' AND permission_id = 'perm_create_project');

      INSERT INTO role_permissions (role_id, permission_id)
      SELECT 'role_admin', 'perm_edit_material'
      WHERE NOT EXISTS (SELECT 1 FROM role_permissions WHERE role_id = 'role_admin' AND permission_id = 'perm_edit_material');

      INSERT INTO role_permissions (role_id, permission_id)
      SELECT 'role_admin', 'perm_view_user_data'
      WHERE NOT EXISTS (SELECT 1 FROM role_permissions WHERE role_id = 'role_admin' AND permission_id = 'perm_view_user_data');

      INSERT INTO role_permissions (role_id, permission_id)
      SELECT 'role_admin', 'perm_download_file'
      WHERE NOT EXISTS (SELECT 1 FROM role_permissions WHERE role_id = 'role_admin' AND permission_id = 'perm_download_file');

      INSERT INTO role_permissions (role_id, permission_id)
      SELECT 'role_admin', 'perm_generate_question'
      WHERE NOT EXISTS (SELECT 1 FROM role_permissions WHERE role_id = 'role_admin' AND permission_id = 'perm_generate_question');

      INSERT INTO role_permissions (role_id, permission_id)
      SELECT 'role_admin', 'perm_validate_response'
      WHERE NOT EXISTS (SELECT 1 FROM role_permissions WHERE role_id = 'role_admin' AND permission_id = 'perm_validate_response');

      INSERT INTO role_permissions (role_id, permission_id)
      SELECT 'role_admin', 'perm_view_project'
      WHERE NOT EXISTS (SELECT 1 FROM role_permissions WHERE role_id = 'role_admin' AND permission_id = 'perm_view_project');

      INSERT INTO role_permissions (role_id, permission_id)
      SELECT 'role_teacher', 'perm_create_project'
      WHERE NOT EXISTS (SELECT 1 FROM role_permissions WHERE role_id = 'role_teacher' AND permission_id = 'perm_create_project');

      INSERT INTO role_permissions (role_id, permission_id)
      SELECT 'role_teacher', 'perm_edit_material'
      WHERE NOT EXISTS (SELECT 1 FROM role_permissions WHERE role_id = 'role_teacher' AND permission_id = 'perm_edit_material');

      INSERT INTO role_permissions (role_id, permission_id)
      SELECT 'role_teacher', 'download_file'
      WHERE NOT EXISTS (SELECT 1 FROM role_permissions WHERE role_id = 'role_teacher' AND permission_id = 'download_file');

      INSERT INTO role_permissions (role_id, permission_id)
      SELECT 'role_teacher', 'perm_generate_question'
      WHERE NOT EXISTS (SELECT 1 FROM role_permissions WHERE role_id = 'role_teacher' AND permission_id = 'perm_generate_question');

      INSERT INTO role_permissions (role_id, permission_id)
      SELECT 'role_teacher', 'perm_validate_response'
      WHERE NOT EXISTS (SELECT 1 FROM role_permissions WHERE role_id = 'role_teacher' AND permission_id = 'perm_validate_response');

      INSERT INTO role_permissions (role_id, permission_id)
      SELECT 'role_teacher', 'perm_view_project'
      WHERE NOT EXISTS (SELECT 1 FROM role_permissions WHERE role_id = 'role_teacher' AND permission_id = 'perm_view_project');
      
      INSERT INTO role_permissions (role_id, permission_id)
      SELECT 'role_student', 'perm_view_user_data'
      WHERE NOT EXISTS (SELECT 1 FROM role_permissions WHERE role_id = 'role_student' AND permission_id = 'perm_view_user_data');
    `);
    console.log('Role permissions initialized');


      // Add default prompt template if none exists
      const templates = await db.getPromptTemplates();
      if (templates.length === 0) {
        await db.createPromptTemplate({
          name: 'Basic Question Generator',
          version: '1.0',
          type: 'question_generation',
          content: `Given the following context and focus area, generate a question that:
1. Tests understanding of the key concepts
2. Encourages critical thinking
3. Is relevant to the focus area

Context: {context}
Focus Area: {focusArea}

Generate a single question that meets these criteria.`,
          description: 'Default template for generating basic comprehension questions'
        });
        console.log('Created default prompt template');
      }
    });
    
    console.log('Migration completed successfully');
  } catch (error) {
    console.error('Migration failed:', error);
    process.exit(1);
  }
}

migrate(); 