import Database from 'better-sqlite3';
import { v4 as uuid } from 'uuid';
import { Project, ProjectConfiguration } from '../types/index.js';
import { StorageService } from './StorageService.js';
import { Material, MaterialStatus } from '../types/index.js';
import { rm } from 'fs/promises';

export interface User {
  id: string;
  firstname: string;
  lastname: string;
  email: string;
  passwordhash: string;
  dob: string;
  created_at?: string;
}

interface ProjectRow {
  id: string;
  name: string;
  description: string | null;
  model_name: string;
  prompt_template_id: string;
  configuration: string;
  created_at: string;
}

interface ColumnInfo {
  cid: number;
  name: string;
  type: string;
  notnull: number;
  dflt_value: string | null;
  pk: number;
}

export class DatabaseService {
  private db: Database.Database;
  private storage: StorageService;

  constructor() {
    this.db = new Database('research.db');
    this.db.pragma('journal_mode = WAL'); // Better concurrency
    this.db.pragma('foreign_keys = ON');  // Enforce foreign key constraints
    this.storage = new StorageService();
  }

  // Add method to get a prepared statement
  private prepareStatement(sql: string): Database.Statement {
    return this.db.prepare(sql);
  }

  // Update material with file info
  async updateMaterialFile(
    materialId: string,
    content: string,
    filePath: string | null,
    fileType: string | null,
    fileSize: number | null,
    status: MaterialStatus
  ): Promise<void> {
    const stmt = this.prepareStatement(`
      UPDATE materials 
      SET content = ?, file_path = ?, file_type = ?, file_size = ?, status = ?
      WHERE id = ?
    `);

    stmt.run(
      content,
      filePath,
      fileType,
      fileSize,
      status,
      materialId
    );
  }

  // Add transaction support
  transaction<T>(fn: () => T): T {
    try {
      this.db.prepare('BEGIN').run();
      const result = fn();
      this.db.prepare('COMMIT').run();
      return result;
    } catch (error) {
      this.db.prepare('ROLLBACK').run();
      throw error;
    }
  }

  exec(sql: string) {
    return this.db.exec(sql);
  }

  // Project methods
  getProjects(): Project[] {
    const stmt = this.db.prepare('SELECT * FROM projects ORDER BY created_at DESC');
    const projects = stmt.all() as ProjectRow[];
    
    return projects.map(project => ({
      id: project.id,
      name: project.name,
      description: project.description || '',
      modelName: project.model_name,
      promptTemplateId: project.prompt_template_id,
      configuration: JSON.parse(project.configuration) as ProjectConfiguration,
      createdAt: project.created_at
    }));
  }

  getProject(id: string): Project {
    const stmt = this.db.prepare('SELECT * FROM projects WHERE id = ?');
    const project = stmt.get(id) as ProjectRow | undefined;
    
    if (!project) {
      throw new Error(`Project not found: ${id}`);
    }

    return {
      id: project.id,
      name: project.name,
      description: project.description || '',
      modelName: project.model_name,
      promptTemplateId: project.prompt_template_id,
      configuration: JSON.parse(project.configuration) as ProjectConfiguration,
      createdAt: project.created_at
    };
  }

  async createProject(params: {
    name: string;
    description?: string;
    modelName: string;
    promptTemplateId: string;
    configuration: any;
  }) {
    const stmt = this.db.prepare(`
      INSERT INTO projects (id, name, description, model_name, prompt_template_id, configuration)
      VALUES (?, ?, ?, ?, ?, ?)
    `);

    const id = uuid();
    stmt.run(
      id,
      params.name,
      params.description || null,
      params.modelName,
      params.promptTemplateId,
      JSON.stringify(params.configuration)
    );
    return id;
  }

  async updateProject(id: string, params: {
    name: string;
    description?: string;
    modelName: string;
    promptTemplateId: string;
    configuration: any;
  }) {
    const stmt = this.db.prepare(`
      UPDATE projects 
      SET name = ?, description = ?, model_name = ?, 
          prompt_template_id = ?, configuration = ?
      WHERE id = ?
    `);

    stmt.run(
      params.name,
      params.description || null,
      params.modelName,
      params.promptTemplateId,
      JSON.stringify(params.configuration),
      id
    );
  }

  async deleteProject(id: string) {
    const stmt = this.db.prepare('DELETE FROM projects WHERE id = ?');
    stmt.run(id);
  }

  // Prompt template methods
  async getPromptTemplates() {
    return this.db.prepare('SELECT * FROM prompt_templates ORDER BY name, version').all();
  }

  async getPromptTemplate(id: string) {
    return this.db.prepare('SELECT * FROM prompt_templates WHERE id = ?').get(id);
  }

  async createPromptTemplate(params: {
    name: string;
    version: string;
    type: string;
    content: string;
    description?: string;
  }) {
    const stmt = this.db.prepare(`
      INSERT INTO prompt_templates (id, name, version, type, content, description)
      VALUES (?, ?, ?, ?, ?, ?)
    `);

    const id = uuid();
    stmt.run(
      id,
      params.name,
      params.version,
      params.type,
      params.content,
      params.description || null
    );
    return id;
  }

  // Material management methods
  async createMaterial(params: {
    projectId: string;
    title: string;
    content: string;
    focusArea: string;
    filePath?: string;
    fileType?: string;
    fileSize?: number;
    metadata?: any;
  }): Promise<string> {
    const stmt = this.db.prepare(`
      INSERT INTO materials (
        id, project_id, title, content, focus_area, 
        file_path, file_type, file_size, metadata, status
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    const id = uuid();
    stmt.run(
      id,
      params.projectId,
      params.title,
      params.content,
      params.focusArea,
      params.filePath || null,
      params.fileType || null,
      params.fileSize || null,
      params.metadata ? JSON.stringify(params.metadata) : null,
      'pending' as MaterialStatus
    );

    return id;
  }

  async getMaterial(id: string): Promise<Material> {
    const stmt = this.db.prepare(`
      SELECT m.*, p.name as project_name 
      FROM materials m
      JOIN projects p ON m.project_id = p.id
      WHERE m.id = ?
    `);
    
    const material = stmt.get(id) as any;
    if (!material) {
      throw new Error(`Material not found: ${id}`);
    }

    return {
      id: material.id,
      projectId: material.project_id,
      projectName: material.project_name,
      title: material.title,
      content: material.content,
      focusArea: material.focus_area,
      filePath: material.file_path,
      fileType: material.file_type,
      fileSize: material.file_size,
      status: material.status as MaterialStatus,
      metadata: material.metadata ? JSON.parse(material.metadata) : null,
      createdAt: material.created_at
    };
  }

  async getProjectMaterials(projectId: string): Promise<Material[]> {
    const stmt = this.db.prepare(`
      SELECT m.*, p.name as project_name 
      FROM materials m
      JOIN projects p ON m.project_id = p.id
      WHERE m.project_id = ?
      ORDER BY m.created_at DESC
    `);
    
    const materials = stmt.all(projectId) as any[];
    return materials.map(material => ({
      id: material.id,
      projectId: material.project_id,
      projectName: material.project_name,
      title: material.title,
      content: material.content,
      focusArea: material.focus_area,
      filePath: material.file_path,
      fileType: material.file_type,
      fileSize: material.file_size,
      status: material.status as MaterialStatus,
      metadata: material.metadata ? JSON.parse(material.metadata) : null,
      createdAt: material.created_at
    }));
  }

  async updateMaterialStatus(id: string, status: MaterialStatus): Promise<void> {
    const stmt = this.db.prepare(`
      UPDATE materials 
      SET status = ?
      WHERE id = ?
    `);

    stmt.run(status, id);
  }

  async deleteMaterial(id: string): Promise<void> {
    const material = await this.getMaterial(id);
    
    // Delete original file if it exists
    if (material.filePath) {
      await rm(material.filePath, { force: true });
    }

    const stmt = this.db.prepare('DELETE FROM materials WHERE id = ?');
    stmt.run(id);
  }

  getTableInfo(tableName: string): ColumnInfo[] {
    const stmt = this.db.prepare(`PRAGMA table_info(${tableName})`);
    return stmt.all() as ColumnInfo[];
  }

  // Question methods
  async getMaterialQuestions(materialId: string) {
    const stmt = this.db.prepare(`
      SELECT * FROM generated_questions 
      WHERE material_id = ?
      ORDER BY created_at DESC
    `);
    
    const questions = stmt.all(materialId) as any[];
    return questions.map(q => ({
      id: q.id,
      materialId: q.material_id,
      promptTemplateId: q.prompt_template_id,
      question: q.question,
      constraints: JSON.parse(q.constraints || '{}'),
      metadata: JSON.parse(q.metadata || '{}'),
      createdAt: q.created_at
    }));
  }

  async getQuestion(id: string) {
    const stmt = this.db.prepare(`
      SELECT * FROM generated_questions 
      WHERE id = ?
    `);
    
    const q = stmt.get(id) as any;
    if (!q) {
      throw new Error(`Question not found: ${id}`);
    }
    
    return {
      id: q.id,
      materialId: q.material_id,
      promptTemplateId: q.prompt_template_id,
      question: q.question,
      constraints: JSON.parse(q.constraints || '{}'),
      metadata: JSON.parse(q.metadata || '{}'),
      createdAt: q.created_at
    };
  }

  async createQuestion(params: {
    materialId: string;
    promptTemplateId: string;
    question: string;
    template: string;
    rules: string;
    metadata?: any;
  }) {
    const stmt = this.prepareStatement(`
      INSERT INTO generated_questions (
        id, material_id, prompt_template_id, question, constraints, metadata
      )
      VALUES (?, ?, ?, ?, ?, ?)
    `);

    const id = uuid();
    stmt.run(
      id,
      params.materialId,
      params.promptTemplateId,
      params.question,
      params.template,
      params.metadata ? JSON.stringify({
        ...params.metadata,
        rules: params.rules
      }) : null
    );
    
    return id;
  }

  async getQuestionsByMaterial(materialId: string) {
    const stmt = this.db.prepare(`
      SELECT id, material_id, prompt_template_id, question, constraints, metadata
      FROM generated_questions 
      WHERE material_id = ?
      ORDER BY created_at DESC
    `);
    
    const questions = stmt.all(materialId) as any[];
    
    return questions.map(q => {
      // Parse metadata to get the rules field (which contains our rubric)
      let metadata = {};
      let rubric = {};
      
      try {
        metadata = JSON.parse(q.metadata || '{}');
        // The rules are stored in metadata.rules in our database schema
        if (metadata.rules) {
          rubric = JSON.parse(metadata.rules);
          delete metadata.rules; // Remove from metadata to avoid duplication
        }
      } catch (e) {
        console.warn(`Failed to parse metadata for question ${q.id}`, e);
      }
      
      // Parse template constraints
      let template = {};
      try {
        template = JSON.parse(q.constraints || '{}');
      } catch (e) {
        console.warn(`Failed to parse constraints for question ${q.id}`, e);
      }
      
      return {
        id: q.id,
        materialId: q.material_id,
        promptTemplateId: q.prompt_template_id,
        question: q.question,
        template,
        rubric,  // Include the parsed rubric
        metadata
      };
    });
  }

  // Response methods
  async getQuestionResponses(questionId: string) {
    const stmt = this.db.prepare(`
      SELECT * FROM responses 
      WHERE question_id = ?
      ORDER BY created_at DESC
    `);
    
    const responses = stmt.all(questionId) as any[];
    return responses.map(r => ({
      id: r.id,
      questionId: r.question_id,
      response: r.response,
      score: r.score,
      feedback: r.feedback,
      metadata: JSON.parse(r.metadata || '{}'),
      createdAt: r.created_at
    }));
  }

  async getResponse(id: string) {
    const stmt = this.db.prepare(`
      SELECT * FROM responses 
      WHERE id = ?
    `);
    
    const r = stmt.get(id) as any;
    if (!r) {
      throw new Error(`Response not found: ${id}`);
    }
    
    return {
      id: r.id,
      questionId: r.question_id,
      response: r.response,
      score: r.score,
      feedback: r.feedback,
      metadata: JSON.parse(r.metadata || '{}'),
      createdAt: r.created_at
    };
  }

  async createResponse(params: {
    questionId: string;
    response: string;
    score?: number;
    feedback?: string;
    metadata?: any;
  }) {
    const stmt = this.db.prepare(`
      INSERT INTO responses (
        id, question_id, response, score, feedback, metadata
      )
      VALUES (?, ?, ?, ?, ?, ?)
    `);

    const id = uuid();
    stmt.run(
      id,
      params.questionId,
      params.response,
      params.score || null,
      params.feedback || null,
      params.metadata ? JSON.stringify(params.metadata) : null
    );
    
    return id;
  }

  getDatabasePath() {
    return this.db.name || 'research.db';
  }

  async updateMaterialMetadata(materialId: string, metadata: any): Promise<void> {
    const stmt = this.prepareStatement(`
      UPDATE materials 
      SET metadata = ?
      WHERE id = ?
    `);

    stmt.run(
      JSON.stringify(metadata),
      materialId
    );
  }

  async updateMaterialContent(materialId: string, content: string): Promise<void> {
    const stmt = this.prepareStatement(`
      UPDATE materials 
      SET content = ?
      WHERE id = ?
    `);

    stmt.run(
      content,
      materialId
    );
  }

  async updateMaterialTitle(materialId: string, title: string): Promise<void> {
    const stmt = this.prepareStatement(`
      UPDATE materials 
      SET title = ?
      WHERE id = ?
    `);

    stmt.run(
      title,
      materialId
    );
  }

  async updateMaterialReprocessed(params: {
    id: string;
    content: string;
    filePath: string;
    fileType: string;
    fileSize: number;
    metadata: any;
  }): Promise<void> {
    const stmt = this.prepareStatement(`
      UPDATE materials 
      SET 
        content = ?,
        file_path = ?,
        file_type = ?,
        file_size = ?,
        metadata = ?,
        status = 'completed'
      WHERE id = ?
    `);

    stmt.run(
      params.content,
      params.filePath,
      params.fileType,
      params.fileSize,
      JSON.stringify(params.metadata),
      params.id
    );
  }

  //DatabseService function to accomodate sign in and update database
  async registerUser(user: Omit<User, 'created_at'>): Promise<void> {
    const stmt = await this.db.prepare(`
      INSERT INTO users (id, firstname, lastname, email, passwordhash, dob)
      VALUES (?, ?, ?, ?, ?, ?)
    `);
      stmt.run(user.id, user.firstname, user.lastname, user.email, user.passwordhash, user.dob);
  }

    // Function to delete a user by email
  async deleteUserByEmail(email: string): Promise<void> {
    try {
      const stmt = await this.db.prepare(`
        DELETE FROM users
        WHERE email = ?
      `);
      await stmt.run(email);
    } catch (error) {
      console.error('Error deleting user:', error);
      throw error; // Re-throw the error to be handled by the caller
    }
  }
  
    // Function to get a user by email
  async getUserByEmail(email: string): Promise<User | null> { // Changed return type
    try {
      const stmt = await this.db.prepare(`
        SELECT id, firstname, lastname, email, dob, passwordhash, created_at 
        FROM users
        WHERE email = ?
      `);
      const user = await stmt.get(email) as User | undefined; // Explicitly cast
      return user || null; //  Return undefined if not found
    } catch (error) {
      console.error('Error in getUserByEmail:', error);
      throw error; // Propagate the error to the caller
    }
  }

  //Function to get user's information when logged in
  async getUserById(userId: string): Promise<User | null> {
    try {
      const stmt = this.prepareStatement(`
        SELECT id, firstname, lastname, email, passwordhash, dob, created_at
        FROM users
        WHERE id = ?
      `);
      const user = stmt.get(userId) as User | undefined;
      return user || null;
    } catch (error) {
      console.error('Error in getUserById:', error);
      throw error;
    }
  }  
  async deleteUserById(userId: string): Promise<void> {
    await this.exec(`DELETE FROM users WHERE id = ?`, [userId]);
  }
    
  //From here on, we are adding the role and permission management functions

  //Function to create new role
  async createRole(role: { id: string; name: string; description?: string }): Promise<void> {
    const stmt = this.prepareStatement(`
        INSERT INTO roles (id, name, description) VALUES (?, ?, ?)
    `);
    await stmt.run(role.id, role.name, role.description);
  }

  //Functino to get role by role name
  async getRoleByName(roleName: string): Promise<{ id: string } | undefined> {
    const stmt = this.prepareStatement(`SELECT id FROM roles WHERE name = ?`);
    return stmt.get(roleName) as { id: string } | undefined;
  }

  //Function to assign role to user
  async assignRoleToUser(userId: string, roleId: string): Promise<void> {
      const stmt = this.prepareStatement(`
          INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)
      `);
      await stmt.run(userId, roleId);
  }

  //Function to get user role by user.id
  async getUserRoles(userId: string): Promise<string[]> {
    const stmt = this.prepareStatement(`
        SELECT r.name FROM user_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.user_id = ?
    `);
    const result = await stmt.all(userId) as any[];
    return result.map(row => row.name);
  }

  //Function to get users by roles
  async getUsersByRole(roleName: string): Promise<{ id: string; firstname: string; lastname: string; email: string }[]> {
    const stmt = this.prepareStatement(`
      SELECT u.id, u.firstname, u.lastname, u.email
      FROM users u
      JOIN user_roles ur ON u.id = ur.user_id
      JOIN roles r ON ur.role_id = r.id
      WHERE LOWER(r.name) = LOWER(?)
    `);
    return stmt.all(roleName);
  }

  //Function to achieve user permissions
  async getUserPermissions(userId: string): Promise<string[]> {
      const stmt = this.prepareStatement(`
          SELECT p.name 
          FROM users u
          JOIN user_roles ur ON u.id = ur.user_id
          JOIN roles r ON ur.role_id = r.id
          JOIN role_permissions rp ON r.id = rp.role_id
          JOIN permissions p ON rp.permission_id = p.id
          WHERE u.id = ?
      `);
      const result = await stmt.all(userId);
      return result.map((row: any) => row.name);
  }

  //Function to achieve role permissions
  async getRolePermissions(roleId: string): Promise<string[]> {
      const stmt = this.prepareStatement(`
          SELECT p.name
          FROM roles r
          JOIN role_permissions rp ON r.id = rp.role_id
          JOIN permissions p ON rp.permission_id = p.id
          WHERE r.id = ?
      `);
      const result = await stmt.all(roleId);
      return result.map((row: any) => row.name);
  }

  // Classrom functions
  async createClassroom(name: string, description?: string): Promise<string> {
    const stmt = this.prepareStatement(`
        INSERT INTO classrooms (id, name, description) VALUES (?, ?, ?)
    `);
    const id = uuid();
    await stmt.run(id, name, description);
    return id;
  }

  async getClassroom(id: string): Promise<any> {
      const stmt = this.prepareStatement(`
          SELECT * FROM classrooms WHERE id = ?
      `);
      return stmt.get(id);
  }

  async getClassroomWithDetailsById(classId: string): Promise<any> {
    const stmt = this.prepareStatement(`
      SELECT id as classId, name as className
      FROM classrooms
      WHERE id = ?
    `);
  
    const classData = stmt.get(classId);
    if (!classData) return null;
  
    const materialStmt = this.prepareStatement(`
      SELECT id, title FROM materials WHERE classroom_id = ?
    `);
    const learningMaterials = materialStmt.all(classId);
  
    return {
      ...classData,
      subjectName: classData.className, 
      learningMaterials,
    };
  }

  async getClassroomsForTeacher(userId: string): Promise<any[]> {
      const stmt = this.prepareStatement(`
          SELECT c.* FROM classrooms c
          JOIN classroom_teachers ct ON c.id = ct.classroom_id
          WHERE ct.user_id = ?
      `);
      return stmt.all(userId);
  }

  async addTeacherToClassroom(classroomId: string, userId: string): Promise<void> {
      const stmt = this.prepareStatement(`
          INSERT INTO classroom_teachers (classroom_id, user_id) VALUES (?, ?)
      `);
      await stmt.run(classroomId, userId);
  }

  async addStudentToClassroom(classroomId: string, userId: string): Promise<void> {
      const stmt = this.prepareStatement(`
          INSERT INTO classroom_students (classroom_id, user_id) VALUES (?, ?)
      `);
      await stmt.run(classroomId, userId);
  }

  async getStudentsInClassroom(classroomId: string): Promise<any[]> {
      const stmt = this.prepareStatement(`
          SELECT u.* FROM users u
          JOIN classroom_students cs ON u.id = cs.user_id
          WHERE cs.classroom_id = ?
      `);
      return stmt.all(classroomId);
  }

  async getMaterialsForClassroom(classroomId: string): Promise<any[]> {
      const stmt = this.prepareStatement(`
          SELECT * FROM materials WHERE classroom_id = ?
      `);
      return stmt.all(classroomId);
  }

  async getStudentClasses(userId: string): Promise<any[]> {

    const stmt = this.prepareStatement(`
      SELECT c.id, c.name
      FROM classrooms c
      JOIN classroom_students cs ON c.id = cs.classroom_id
      WHERE cs.user_id = ?
    `);
    return stmt.all(userId);
  }
  
  
  close() {
    this.db.close();
  }
} 