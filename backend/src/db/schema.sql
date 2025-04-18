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

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_materials_project ON materials(project_id);
CREATE INDEX IF NOT EXISTS idx_questions_material ON generated_questions(material_id);
CREATE INDEX IF NOT EXISTS idx_responses_question ON responses(question_id);
CREATE INDEX IF NOT EXISTS idx_materials_status ON materials(status); 
