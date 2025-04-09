import express from 'express';
import cors from 'cors';
import { ValidationService } from './services/ValidationService.js';
import { LMStudioService } from './services/LMStudioService.js';
import { MaterialProcessor } from './services/MaterialProcessor.js';
import multer from 'multer';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { mkdirSync } from 'fs';
import { MaterialSource } from './types/index.js';
import fs from 'fs/promises';
import { DatabaseService } from './services/DatabaseService.js';
import { StorageService } from './services/StorageService.js';
import { v4 as uuid } from 'uuid';
import { registerUser, loginUser } from './services/AuthenticationService.js';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import dotenv from 'dotenv';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();

app.use(cors());
app.use(express.json());

// Create uploads directory if it doesn't exist
const uploadsDir = join(dirname(__dirname), 'uploads');
mkdirSync(uploadsDir, { recursive: true });

const lmStudio = new LMStudioService();
const validator = new ValidationService(lmStudio);
const materialProcessor = new MaterialProcessor(lmStudio);
const db = new DatabaseService();
const storage = new StorageService();
await storage.initialize();

// Configure multer for file uploads
const storageMulter = multer.diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, uploadsDir);
  },
  filename: (_req, file, cb) => {
    cb(null, `${Date.now()}-${path.basename(file.originalname)}`);
  }
});

const upload = multer({ storage: storageMulter });

app.post('/api/signup', async (req, res) => {
  const { firstname, lastname, email, passwordhash, dob } = req.body;
  const hashedPassword = await bcrypt.hash(passwordhash, 10);
  const id = uuid();

  try {
    await registerUser(id, firstname, lastname, email, hashedPassword, dob);
    res.status(201).json({ message: 'User created successfully' });
  } catch (err: any) {
    res.status(500).json({ error: 'User creation failed', details: err.message });
  }
});

// SIGNIN (Login) Endpoint
app.post('/api/signin', async (req, res) => {
  const { email, password } = req.body;

  if (!email || !password) {
    return res.status(400).json({ message: 'Email and password are required.' });
  }

  try {
    // Authenticate the user using the new loginUser function.
    const user = await loginUser(email, password);

    // Generate a JWT token upon successful authentication.
    const token = jwt.sign(
      { id: user.id, email: user.email },
      process.env.JWT_SECRET || 'supersecret',
      { expiresIn: '1h' }
    );

    return res.status(200).json({ token });
  } catch (error: any) {
    console.error('Signin error:', error);
    return res.status(401).json({ message: 'Invalid email or password.' });
  }
});

// ---------------- Existing Endpoints Below ---------------- //

app.post('/api/validate', async (req, res) => {
  try {
    const { questionId, answer } = req.body;
    
    if (!questionId || !answer) {
      res.status(400).json({ 
        error: 'Missing required fields',
        details: {
          questionId: !questionId,
          answer: !answer
        }
      });
      return;
    }

    // Retrieve the question from database
    const question = await db.getQuestion(questionId);
    if (!question) {
      res.status(404).json({ error: 'Question not found' });
      return;
    }
    
    // Get the prompt template using the ID from the question
    const promptTemplate = await db.getPromptTemplate(question.promptTemplateId);
    if (!promptTemplate) {
      res.status(404).json({ error: 'Prompt template not found' });
      return;
    }

    // Validate the answer using the retrieved data and prompt template
    const result = await validator.validateResponse(
      question.question,
      answer,
      promptTemplate
    );
    
    res.json(result);
  } catch (error) {
    console.error('Validation error:', error);
    res.status(500).json({ 
      error: 'Validation failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

app.post('/api/generate', async (req, res) => {
  try {
    const { materialId, promptTemplateId, templateIndex, useSourceLanguage } = req.body;
    
    if (!materialId || !promptTemplateId || templateIndex === undefined) {
      res.status(400).json({ 
        error: 'Missing required fields',
        details: {
          materialId: !materialId,
          promptTemplateId: !promptTemplateId,
          templateIndex: templateIndex === undefined
        }
      });
      return;
    }

    // Retrieve material from database
    const material = await db.getMaterial(materialId);
    if (!material) {
      res.status(404).json({ error: 'Material not found' });
      return;
    }
    
    // Retrieve prompt template from database
    const promptTemplate = await db.getPromptTemplate(promptTemplateId);
    if (!promptTemplate) {
      res.status(404).json({ error: 'Prompt template not found' });
      return;
    }
    
    // Get the question template from the material's metadata
    const questionTemplate = material.metadata?.templates?.[templateIndex];
    if (!questionTemplate) {
      res.status(404).json({ error: 'Question template not found at specified index' });
      return;
    }

    // Generate question using the material's content and templates
    const questionText = await materialProcessor.generateQuestion(
      questionTemplate, 
      material.content,
      promptTemplate,
      useSourceLanguage
    );
    
    // Generate appropriate rules based on the prompt template
    const rubric = await materialProcessor.generateRubric(
      questionText,
      questionTemplate,
      promptTemplate
    );
    
    // Generate a UUID for the question
    const questionId = uuid();
    
    // Save to database
    await db.createQuestion({
      materialId,
      promptTemplateId,
      question: questionText,
      template: JSON.stringify(questionTemplate),
      rules: JSON.stringify(rubric),
      metadata: {
        generatedAt: new Date().toISOString(),
        templateIndex,
        validationStages: ['content_relevance', 'vocabulary_appropriateness', 'detailed_criteria_evaluation']
      }
    });
    
    // Return the complete question with its ID
    res.json({ 
      id: questionId,
      materialId,
      promptTemplateId,
      question: questionText,
      template: questionTemplate,
      rubric,
      metadata: {
        generatedAt: new Date().toISOString(),
        templateIndex,
        validationStages: ['content_relevance', 'vocabulary_appropriateness', 'detailed_criteria_evaluation']
      }
    });
  } catch (error) {
    console.error('Generation error:', error);
    res.status(500).json({ 
      error: 'Failed to generate question',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

app.get('/api/health', async (_req, res) => {
  try {
    const isLMStudioAvailable = await lmStudio.isAvailable();
    res.json({ 
      status: 'ok',
      lmStudio: isLMStudioAvailable 
    });
  } catch (error) {
    console.error('Health check error:', error);
    res.status(500).json({ 
      status: 'error',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

app.post('/api/materials/process', async (req, res) => {
  const { material, projectId } = req.body;
  
  if (!projectId) {
    res.status(400).json({ error: 'Project ID is required' });
    return;
  }
  
  try {
    // Extract content if not already provided
    const content = typeof material.content === 'string' && !material.content.startsWith('/') 
      ? material.content 
      : await materialProcessor.extractContent(material);
    
    // Generate objectives and templates
    const objectives = await materialProcessor.extractLearningObjectives(
      content, 
      material.metadata.focusArea,
      material.metadata.useSourceLanguage
    );
    
    const templates = await materialProcessor.suggestQuestionTemplates(
      content, 
      objectives, 
      material.metadata.focusArea,
      material.metadata.useSourceLanguage
    );
    
    // Create database record for the material
    const materialId = await db.createMaterial({
      projectId,
      title: material.metadata.title || 'Untitled Material',
      content: content,
      focusArea: material.metadata.focusArea,
      metadata: {
        ...material.metadata,
        learningObjectives: objectives,
        templates: templates,
        wordCount: content.split(/\s+/).length,
        processedAt: new Date().toISOString()
      }
    });
    
    // Update material status to completed
    await db.updateMaterialStatus(materialId, 'completed');
    
    res.json({
      id: materialId,
      objectives,
      templates,
      wordCount: content.split(/\s+/).length,
      status: 'success'
    });
  } catch (error) {
    console.error('Material processing error:', error);
    res.status(500).json({ 
      error: 'Failed to process material',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

app.post('/api/materials/upload', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      res.status(400).json({ error: 'No file uploaded' });
      return;
    }

    // Get file extension without the dot
    const fileType = path.extname(req.file.originalname).toLowerCase().substring(1);
    
    if (!['txt', 'pdf', 'doc', 'docx', 'md'].includes(fileType)) {
      res.status(400).json({ 
        error: 'Unsupported file type', 
        details: `File type ${fileType} is not supported. Supported types: txt, pdf, doc, docx, md` 
      });
      return;
    }

    const metadata = JSON.parse(req.body.metadata || '{}');
    const projectId = metadata.projectId || null;
    
    if (!projectId) {
      res.status(400).json({ error: 'Project ID is required' });
      return;
    }

    // Extract content from file
    const material: MaterialSource = {
      type: fileType,
      content: req.file.path,
      metadata
    };
    
    // Process file to extract content
    const content = await materialProcessor.extractContent(material);
    
    // Generate objectives and templates
    const objectives = await materialProcessor.extractLearningObjectives(
      content, 
      metadata.focusArea,
      metadata.useSourceLanguage
    );
    
    const templates = await materialProcessor.suggestQuestionTemplates(
      content, 
      objectives, 
      metadata.focusArea,
      metadata.useSourceLanguage
    );

    // Create database record for the material
    const materialId = await db.createMaterial({
      projectId,
      title: metadata.title || 'Untitled Material',
      content: content,
      focusArea: metadata.focusArea,
      filePath: req.file.path,
      fileType,
      fileSize: req.file.size,
      metadata: {
        ...metadata,
        learningObjectives: objectives,
        templates: templates,
        wordCount: content.split(/\s+/).length,
        processedAt: new Date().toISOString()
      }
    });
    
    // Update material status to completed
    await db.updateMaterialStatus(materialId, 'completed');
    
    res.json({
      id: materialId,
      content,
      objectives,
      templates,
      wordCount: content.split(/\s+/).length,
      status: 'success'
    });
  } catch (error) {
    if (req.file) {
      await fs.unlink(req.file.path).catch(() => {});
    }
    
    console.error('Material upload error:', error);
    res.status(500).json({ 
      error: 'Failed to process uploaded material',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Project endpoints
app.get('/api/projects', async (_req, res) => {
  try {
    const projects = await db.getProjects();
    res.json(projects);
  } catch (error) {
    console.error('Failed to get projects:', error);
    res.status(500).json({ error: 'Failed to get projects' });
  }
});

app.post('/api/projects', async (req, res) => {
  try {
    const projectId = await db.createProject(req.body);
    const project = await db.getProject(projectId);
    res.json(project);
  } catch (error) {
    console.error('Failed to create project:', error);
    res.status(500).json({ error: 'Failed to create project' });
  }
});

app.put('/api/projects/:id', async (req, res) => {
  try {
    await db.updateProject(req.params.id, req.body);
    const project = await db.getProject(req.params.id);
    res.json(project);
  } catch (error) {
    console.error('Failed to update project:', error);
    res.status(500).json({ error: 'Failed to update project' });
  }
});

app.delete('/api/projects/:id', async (req, res) => {
  try {
    await db.deleteProject(req.params.id);
    res.json({ success: true });
  } catch (error) {
    console.error('Failed to delete project:', error);
    res.status(500).json({ error: 'Failed to delete project' });
  }
});

// Prompt template endpoints
app.get('/api/prompt-templates', async (_req, res) => {
  try {
    const templates = await db.getPromptTemplates();
    res.json(templates);
  } catch (error) {
    console.error('Failed to get prompt templates:', error);
    res.status(500).json({ error: 'Failed to get prompt templates' });
  }
});

app.post('/api/prompt-templates', async (req, res) => {
  try {
    const templateId = await db.createPromptTemplate(req.body);
    const template = await db.getPromptTemplate(templateId);
    res.json(template);
  } catch (error) {
    console.error('Failed to create prompt template:', error);
    res.status(500).json({ error: 'Failed to create prompt template' });
  }
});

// Add materials endpoints
app.get('/api/materials', async (req, res) => {
  try {
    const projectId = req.query.projectId as string;
    if (!projectId) {
      res.status(400).json({ error: 'Missing projectId parameter' });
      return;
    }
    
    const materials = await db.getProjectMaterials(projectId);
    res.json(materials);
  } catch (error) {
    console.error('Failed to get materials:', error);
    res.status(500).json({ 
      error: 'Failed to get materials',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

app.get('/api/materials/:id', async (req, res) => {
  try {
    const id = req.params.id;
    const material = await db.getMaterial(id);
    res.json(material);
  } catch (error) {
    console.error('Failed to get material:', error);
    res.status(500).json({ 
      error: 'Failed to get material',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

app.delete('/api/materials/:id', async (req, res) => {
  try {
    const id = req.params.id;
    await db.deleteMaterial(id);
    res.json({ success: true });
  } catch (error) {
    console.error('Failed to delete material:', error);
    res.status(500).json({ 
      error: 'Failed to delete material',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Add question endpoints
app.get('/api/questions', async (req, res) => {
  try {
    const { materialId } = req.query;
    
    if (!materialId) {
      res.status(400).json({ error: 'Material ID is required' });
      return;
    }
    
    const questions = await db.getQuestionsByMaterial(materialId as string);
    res.json(questions.map(q => ({
      id: q.id,
      materialId: q.materialId,
      promptTemplateId: q.promptTemplateId,
      question: q.question,
      template: q.template,
      rubric: q.rubric,
      metadata: q.metadata
    })));
  } catch (error) {
    console.error('Failed to get questions:', error);
    res.status(500).json({ 
      error: 'Failed to get questions',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

app.post('/api/questions', async (req, res) => {
  try {
    const { materialId, promptTemplateId, question, metadata } = req.body;
    
    if (!materialId || !promptTemplateId || !question) {
      res.status(400).json({
        error: 'Missing required fields',
        details: {
          materialId: !materialId,
          promptTemplateId: !promptTemplateId,
          question: !question
        }
      });
      return;
    }
    
    const questionId = await db.createQuestion({
      materialId,
      promptTemplateId,
      question,
      template: JSON.stringify({}),
      rules: JSON.stringify({}),
      metadata
    });
    
    res.json({
      id: questionId,
      materialId,
      promptTemplateId,
      question,
      metadata: metadata || {}
    });
  } catch (error) {
    console.error('Error saving question:', error);
    res.status(500).json({
      error: 'Failed to save question',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Add response endpoints
app.get('/api/responses', async (req, res) => {
  try {
    const questionId = req.query.questionId as string;
    if (!questionId) {
      res.status(400).json({ error: 'Missing questionId parameter' });
      return;
    }
    
    const responses = await db.getQuestionResponses(questionId);
    res.json(responses);
  } catch (error) {
    console.error('Failed to get responses:', error);
    res.status(500).json({ 
      error: 'Failed to get responses',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

app.post('/api/responses', async (req, res) => {
  try {
    const { questionId, response, score, feedback, metadata } = req.body;
    
    if (!questionId || !response) {
      res.status(400).json({ 
        error: 'Missing required fields',
        details: {
          questionId: !questionId,
          response: !response
        }
      });
      return;
    }
    
    const responseId = await db.createResponse({
      questionId,
      response,
      score,
      feedback,
      metadata: metadata || {}
    });
    
    const createdResponse = await db.getResponse(responseId);
    res.json(createdResponse);
  } catch (error) {
    console.error('Failed to create response:', error);
    res.status(500).json({ 
      error: 'Failed to create response',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Add endpoint for material content updates
app.patch('/api/materials/:id/content', async (req, res) => {
  try {
    const { id } = req.params;
    const { content } = req.body;
    
    if (!content) {
      res.status(400).json({ error: 'Content is required' });
      return;
    }
    
    await db.updateMaterialContent(id, content);
    const updatedMaterial = await db.getMaterial(id);
    res.json(updatedMaterial);
  } catch (error) {
    console.error('Error updating material content:', error);
    res.status(500).json({ 
      error: 'Failed to update material content',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Endpoint to update material title
app.patch('/api/materials/:id/title', async (req, res) => {
  try {
    const { id } = req.params;
    const { title } = req.body;
    
    if (!title) {
      res.status(400).json({ error: 'Title is required' });
      return;
    }
    
    await db.updateMaterialTitle(id, title);
    const updatedMaterial = await db.getMaterial(id);
    res.json(updatedMaterial);
  } catch (error) {
    console.error('Error updating material title:', error);
    res.status(500).json({ 
      error: 'Failed to update material title',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Endpoint to reprocess a material
app.post('/api/materials/:id/reprocess', upload.single('file'), async (req, res) => {
  try {
    const { id } = req.params;
    
    if (!req.file) {
      res.status(400).json({ error: 'No file uploaded' });
      return;
    }
    
    const originalMaterial = await db.getMaterial(id);
    if (!originalMaterial) {
      res.status(404).json({ error: 'Material not found' });
      return;
    }
    
    const fileType = path.extname(req.file.originalname).toLowerCase().substring(1);
    
    if (!['txt', 'pdf', 'doc', 'docx', 'md'].includes(fileType)) {
      res.status(400).json({ 
        error: 'Unsupported file type', 
        details: `File type ${fileType} is not supported. Supported types: txt, pdf, doc, docx, md` 
      });
      return;
    }
    
    const material = {
      type: fileType,
      content: req.file.path,
      metadata: {
        ...originalMaterial.metadata,
        focusArea: originalMaterial.focusArea,
        projectId: originalMaterial.projectId
      }
    };
    
    const content = await materialProcessor.extractContent(material);
    
    const objectives = await materialProcessor.extractLearningObjectives(
      content, 
      originalMaterial.focusArea,
      originalMaterial.metadata?.useSourceLanguage
    );
    
    const templates = await materialProcessor.suggestQuestionTemplates(
      content, 
      objectives, 
      originalMaterial.focusArea,
      originalMaterial.metadata?.useSourceLanguage
    );
    
    await db.updateMaterialReprocessed({
      id,
      content,
      filePath: req.file.path,
      fileType,
      fileSize: req.file.size,
      metadata: {
        ...originalMaterial.metadata,
        learningObjectives: objectives,
        templates: templates,
        wordCount: content.split(/\s+/).length,
        processedAt: new Date().toISOString()
      }
    });
    
    await db.updateMaterialStatus(id, 'completed');
    
    const updatedMaterial = await db.getMaterial(id);
    res.json({
      id,
      content,
      objectives,
      templates,
      wordCount: content.split(/\s+/).length,
      status: 'success'
    });
  } catch (error) {
    if (req.file) {
      await fs.unlink(req.file.path).catch(() => {});
    }
    
    console.error('Material reprocessing error:', error);
    res.status(500).json({ 
      error: 'Failed to reprocess material',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Debug info logging function
function logServerConfiguration() {
  console.log('\n----- EdgePrompt Server Configuration -----');
  console.log(`\n🌐 Server running on port: ${PORT}`);
  console.log(`🔗 API Base URL: http://localhost:${PORT}/api`);
  const llmConfig = lmStudio.getConfig();
  console.log('\n🤖 LLM Service Configuration:');
  console.log(`   - API URL: ${llmConfig.apiUrl}`);
  console.log(`   - Model: ${llmConfig.model || 'Not specified'}`);
  console.log(`   - Temperature: ${llmConfig.temperature || 'Default'}`);
  console.log(`   - Max Tokens: ${llmConfig.maxTokens || 'Default'}`);
  console.log('\n💾 Database Configuration:');
  console.log(`   - Database Path: ${db.getDatabasePath()}`);
  console.log(`   - Uploads Directory: ${uploadsDir}`);
  try {
    if (storage && typeof storage.getConfig === 'function') {
      console.log(`   - Storage Root: ${storage.getConfig().rootDir}`);
    } else {
      console.log(`   - Storage: Not initialized`);
    }
  } catch (error) {
    console.log(`   - Storage: Error accessing configuration`);
  }
  
  console.log('\n📡 Registered API Endpoints:');
  const routes: string[] = [];
  
  function extractRoutes(app: any, basePath = '') {
    if (!app._router || !app._router.stack) return;
    app._router.stack.forEach((layer: any) => {
      if (layer.route) {
        const methods = Object.keys(layer.route.methods)
          .filter(method => layer.route.methods[method])
          .map(method => method.toUpperCase())
          .join(', ');
        routes.push(`   ${methods} ${basePath}${layer.route.path}`);
      } else if (layer.name === 'router' && layer.handle.stack) {
        const routerPath = layer.regexp.toString()
          .replace('\\/?(?=\\/|$)', '')
          .replace('?', '')
          .replace(/\\/g, '')
          .replace(/\^|\$/g, '')
          .replace(/\(\?:\(\[\^\\\/\]\+\?\)\)/g, ':param');
        layer.handle.stack.forEach((stackItem: any) => {
          if (stackItem.route) {
            const methods = Object.keys(stackItem.route.methods)
              .filter(method => stackItem.route.methods[method])
              .map(method => method.toUpperCase())
              .join(', ');
            routes.push(`   ${methods} ${basePath}${routerPath}${stackItem.route.path}`);
          }
        });
      }
    });
  }
  
  extractRoutes(app);
  const apiRoutes = routes
    .filter(route => route.includes('/api'))
    .sort((a, b) => {
      const methodA = a.trim().split(' ')[0];
      const methodB = b.trim().split(' ')[0];
      const pathA = a.trim().split(' ')[1];
      const pathB = b.trim().split(' ')[1];
      if (pathA === pathB) {
        return methodA.localeCompare(methodB);
      }
      return pathA.localeCompare(pathB);
    });
  apiRoutes.forEach(route => console.log(route));
  console.log('\n------------------------------------------\n');
}

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  logServerConfiguration();
});
