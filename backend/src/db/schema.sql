-- Core research tables
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  model_name TEXT NOT NULL,
  prompt_template_id TEXT NOT NULL,
  configuration JSON NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompt_templates (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  type TEXT NOT NULL,
  content TEXT NOT NULL,
  description TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Data collection tables
CREATE TABLE IF NOT EXISTS materials (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  title TEXT,
  content TEXT NOT NULL,
  focus_area TEXT NOT NULL,
  metadata JSON,
  file_path TEXT,
  file_type TEXT,
  file_size INTEGER,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'error')),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS generated_questions (
  id TEXT PRIMARY KEY,
  material_id TEXT NOT NULL,
  prompt_template_id TEXT NOT NULL,
  question TEXT NOT NULL,
  constraints JSON,
  metadata JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(material_id) REFERENCES materials(id),
  FOREIGN KEY(prompt_template_id) REFERENCES prompt_templates(id)
);

CREATE TABLE IF NOT EXISTS responses (
  id TEXT PRIMARY KEY,
  question_id TEXT NOT NULL,
  response TEXT NOT NULL,
  score REAL,
  feedback TEXT,
  metadata JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(question_id) REFERENCES generated_questions(id)
);


CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  firstname TEXT NOT NULL,
  lastname TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  passwordhash TEXT NOT NULL,
  dob TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

--Creating role TABLE
CREATE TABLE IF NOT EXISTS roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,  -- e.g., 'teacher', 'student', 'admin'
    description TEXT
);

--Creating permissions TABLE
CREATE TABLE IF NOT EXISTS permissions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,  -- e.g., 'create_project', 'edit_material', 'view_user_data'
    description TEXT
);

--Junction table to associate roles with permissions
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id TEXT NOT NULL,
    permission_id TEXT NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (permission_id) REFERENCES permissions(id)
);

--Junction table to associate users with roles
CREATE TABLE IF NOT EXISTS user_roles (
    user_id TEXT NOT NULL,
    role_id TEXT NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- Initiate the database with some default roles and permissions
INSERT INTO roles (id, name, description) VALUES
('role_admin', 'Administrator', 'Has full access to the system'),
('role_teacher', 'Teacher', 'Can create and manage materials and projects'),
('role_student', 'Student', 'Can view materials and submit responses');

INSERT INTO permissions (id, name, description) VALUES
('perm_create_project', 'create_project', 'Allows creating new projects'),
('perm_edit_material', 'edit_material', 'Allows editing existing materials'),
('perm_view_user_data', 'view_user_data', 'Allows viewing user data');

INSERT INTO role_permissions (role_id, permission_id) VALUES
('role_admin', 'perm_create_project'),
('role_admin', 'perm_edit_material'),
('role_admin', 'perm_view_user_data'),
('role_teacher', 'perm_create_project'),
('role_teacher', 'perm_edit_material'),
('role_student', 'perm_view_user_data');  

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_materials_project ON materials(project_id);
CREATE INDEX IF NOT EXISTS idx_questions_material ON generated_questions(material_id);
CREATE INDEX IF NOT EXISTS idx_responses_question ON responses(question_id);
CREATE INDEX IF NOT EXISTS idx_materials_status ON materials(status); 
