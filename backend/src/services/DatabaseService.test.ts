import { DatabaseService, User } from './DatabaseService.js';
import { StorageService } from './StorageService.js';
import { expect } from 'chai';
import { join } from 'path';
import { writeFile, rm } from 'fs/promises';
import { v4 as uuidv4 } from 'uuid';

describe('DatabaseService - Materials', () => {
  let db: DatabaseService;
  let storage: StorageService;
  let projectId: string;

  beforeEach(async () => {
    db = new DatabaseService();
    storage = new StorageService();
    await storage.initialize();

    // Create a test project
    projectId = await db.createProject({
      name: 'Test Project',
      description: 'Test project for materials',
      modelName: 'test-model',
      promptTemplateId: 'test-template',
      configuration: { language: 'en', gradeLevel: '5', subject: 'test' }
    });
  });

  afterEach(async () => {
    // Clean up test files
    await rm(storage.getConfig().rootDir, { recursive: true, force: true });
  });

  describe('material management', () => {
    it('should create and retrieve material', async () => {
      const materialId = await db.createMaterial({
        projectId,
        title: 'Test Material',
        content: 'Test content',
        focusArea: 'Test focus',
        metadata: { key: 'value' }
      });

      const material = await db.getMaterial(materialId);
      expect(material.title).to.equal('Test Material');
      expect(material.content).to.equal('Test content');
      expect(material.status).to.equal('pending');
      expect(material.metadata).to.deep.equal({ key: 'value' });
    });

    it('should list project materials', async () => {
      // Create multiple materials
      await db.createMaterial({
        projectId,
        title: 'Material 1',
        content: 'Content 1',
        focusArea: 'Focus 1'
      });

      await db.createMaterial({
        projectId,
        title: 'Material 2',
        content: 'Content 2',
        focusArea: 'Focus 2'
      });

      const materials = await db.getProjectMaterials(projectId);
      expect(materials).to.have.length(2);
      const titles = materials.map(m => m.title);
      expect(titles).to.include('Material 1');
      expect(titles).to.include('Material 2');
    });

    it('should update material status', async () => {
      const materialId = await db.createMaterial({
        projectId,
        title: 'Test Material',
        content: 'Test content',
        focusArea: 'Test focus'
      });

      await db.updateMaterialStatus(materialId, 'completed');
      
      const material = await db.getMaterial(materialId);
      expect(material.status).to.equal('completed');
    });

    it('should delete material and its files', async () => {
      // Create a test file
      const testFile = join(storage.getConfig().rootDir, 'test.txt');
      await writeFile(testFile, 'test content');

      const materialId = await db.createMaterial({
        projectId,
        title: 'Test Material',
        content: 'Test content',
        focusArea: 'Test focus',
        filePath: testFile
      });

      await db.deleteMaterial(materialId);

      try {
        await db.getMaterial(materialId);
        expect.fail('Material should have been deleted');
      } catch (error) {
        expect(error.message).to.include('not found');
      }
    });
  });
}); 

describe('DatabaseService - User Management', () => {
  let db: DatabaseService;

  beforeEach(() => {
    db = new DatabaseService();
  });

  it('should create a user', async () => {
    const userId = uuidv4();
    const userData = {
      id: userId,
      username: 'testuser',
      email: 'test@example.com',
      password_hash: 'hashed_password', // In real scenarios, this would be a bcrypt hash
      position: 'student',
    };

    await db.createUser(userData);    
    const retrievedUser = await db.getUserByEmail('test@example.com');

    
    expect(retrievedUser).to.not.be.null;
    expect(retrievedUser?.username).to.equal('testuser');
    expect(retrievedUser?.email).to.equal('test@example.com');
    expect(retrievedUser?.password_hash).to.equal('hashed_password');
    expect(retrievedUser?.position).to.equal('student');
    expect(retrievedUser?.created_at).to.not.be.null;

    await db.deleteUserById(userId); // Clean up after test
  });

  it('should get a user by email', async () => {
    const userId = uuidv4();
    const userData = {
      id: userId,
      username: 'testuser2',
      email: 'test2@example.com',
      password_hash: 'hashed_password2',
      position: 'teacher',
      created_at: new Date().toISOString()
    };

    await db.createUser(userData);
    const user = await db.getUserByEmail('test2@example.com');

    expect(user).to.not.be.null;
    expect(user?.username).to.equal('testuser2');
    expect(user?.email).to.equal('test2@example.com');
    expect(user?.password_hash).to.equal('hashed_password2');
    expect(user?.position).to.equal('teacher');
    expect(user?.created_at).to.not.be.null;

    await db.deleteUserById(userId); // Clean up after test  
  });

  it('should return null if user not found', async () => {
    const user = await db.getUserByEmail('nonexistent@example.com');
    expect(user).to.be.null;
  });

  it('should handle duplicate email', async () => {
    const userId1 = uuidv4();
    const userData1 = {
        id: userId1,
        username: 'user1',
        email: 'duplicate@example.com',
        password_hash: 'hashed1',
        position: 'student',
        created_at: new Date().toISOString()
    };
    await db.createUser(userData1);

    const userId2 = uuidv4();
    const userData2 = {
        id: userId2,
        username: 'user2',
        email: 'duplicate@example.com',
        password_hash: 'hashed2',
        position: 'teacher',
        created_at: new Date().toISOString()
    };

    try {
        await db.createUser(userData2);
        expect.fail('Expected createUser to throw an error');
    } catch (error: any) {
        expect(error.message).to.include('UNIQUE constraint failed'); // Adjust this to match your DB error message
    }

    await db.deleteUserById(userId1); // Clean up after test  
    await db.deleteUserById(userId2); // Clean up after test  
});

it('should handle duplicate username', async () => {
    const userId1 = uuidv4();
    const userData1 = {
        id: userId1,
        username: 'duplicateuser',
        email: 'user1@example.com',
        password_hash: 'hashed1',
        position: 'student',
        created_at: new Date().toISOString()
    };
    await db.createUser(userData1);

    const userId2 = uuidv4();
    const userData2 = {
        id: userId2,
        username: 'duplicateuser',
        email: 'user2@example.com',
        password_hash: 'hashed2',
        position: 'teacher',
        created_at: new Date().toISOString()
    };

    try {
        await db.createUser(userData2);
        expect.fail('Expected createUser to throw an error');
    } catch (error: any) {
        expect(error.message).to.include('UNIQUE constraint failed'); // Adjust this to match your DB error message
    }

    await db.deleteUserById(userId1); // Clean up after test  
    await db.deleteUserById(userId2); // Clean up after test  
  });
});