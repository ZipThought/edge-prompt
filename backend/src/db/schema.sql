-- Core research tables
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  classroom_id TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  model_name TEXT NOT NULL,
  prompt_template_id TEXT NOT NULL,
  configuration JSON NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(classroom_id) REFERENCES classrooms(id)
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
  classroom_id TEXT,
  title TEXT,
  content TEXT NOT NULL,
  focus_area TEXT NOT NULL,
  metadata JSON,
  file_path TEXT,
  file_type TEXT,
  file_size INTEGER,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'error')),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(project_id) REFERENCES projects(id),
  FOREIGN KEY(classroom_id) REFERENCES classrooms(id)
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

--Creating classroom TABLE
CREATE TABLE IF NOT EXISTS classrooms (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

--Junction table to associate classrooms with teachers
CREATE TABLE IF NOT EXISTS classroom_teachers (
    classroom_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    PRIMARY KEY (classroom_id, user_id),
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

--Junction table to associate classrooms with students
CREATE TABLE IF NOT EXISTS classroom_students (
    classroom_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    PRIMARY KEY (classroom_id, user_id),
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

--Creating question TABLE
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    class_id TEXT NOT NULL,
    teacher_id TEXT NOT NULL,
    question_text TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES classrooms(id),
    FOREIGN KEY (teacher_id) REFERENCES users(id)
);

--Creating response TABLE
CREATE TABLE IF NOT EXISTS responses (
    id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    class_id TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(id),
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (class_id) REFERENCES classrooms(id)
);

--Creating rubric TABLE
CREATE TABLE IF NOT EXISTS rubrics (
    id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL,
    rubric_text TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(id)
);

--Creating feedback TABLE
CREATE TABLE IF NOT EXISTS feedback (
    id TEXT PRIMARY KEY,
    response_id TEXT NOT NULL,
    teacher_id TEXT NOT NULL,
    feedback_text TEXT NOT NULL,
    score REAL,
    given_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (response_id) REFERENCES responses(id),
    FOREIGN KEY (teacher_id) REFERENCES users(id)
);



-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_materials_project ON materials(project_id);
CREATE INDEX IF NOT EXISTS idx_questions_material ON generated_questions(material_id);
CREATE INDEX IF NOT EXISTS idx_responses_question ON responses(question_id);
CREATE INDEX IF NOT EXISTS idx_materials_status ON materials(status); 
CREATE INDEX IF NOT EXISTS idx_classroom_teachers ON classroom_teachers(classroom_id, user_id);
CREATE INDEX IF NOT EXISTS idx_classroom_students ON classroom_students(classroom_id, user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles ON user_roles(user_id, role_id);