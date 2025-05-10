import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { DatabaseService } from '../services/DatabaseService.js';
import dotenv from 'dotenv';
import { getJwtSecret } from '../utils/jwtUtils.js';

dotenv.config();

export const jwtSecret = process.env.JWT_SECRET || 'your-secret-key'; // Use getJwtSecret()

declare module 'express-serve-static-core' {
    interface Request {
      user?: {
        userId: string;
        email: string;
        role: string;
      };
    }
  }

// Define your route to permission mapping
const routePermissions: Record<string, string> = {
    '/api/projects': 'create_project',  // Example: POST /api/projects
    '/api/projects/:id': 'view_project', // Example: GET /api/projects/:id
    '/api/materials': 'view_materials', // Example: GET /api/materials
    '/api/materials/upload': 'upload_file', // Example: POST /api/materials/upload
    '/api/materials/:id': 'edit_material', // Example: GET, PUT, DELETE /api/materials/:id
    '/api/generate': 'generate_question', // Example: POST /api/generate
    '/api/validate': 'validate_response', // Example: POST /api/validate
    '/api/files/:projectId/:materialId/:filename': 'download_file', // Example: GET /api/files/...
    // Classroom permissions
    '/api/classrooms': 'create_classroom',
    // '/api/classrooms/:id': 'view_classroom',
    '/api/classrooms/users/:userId': 'view_classrooms_for_teacher',
    '/api/classrooms/:classroom_id/teachers/:user_id': 'add_teacher_to_classroom',
    // '/api/classrooms/:classroom_id/students/:user_id': 'add_student_to_classroom',
    '/api/classrooms/:classroom_id/students': 'view_classroom_students',
    '/api/classrooms/:classroom_id/materials': 'view_classroom_materials',
    '/api/classrooms/users/:userId/classes': 'view_classrooms_for_student',
    '/api/classrooms/:id': 'manage_classroom',
    '/api/classrooms/:classroom_id/students/:user_id': 'manage_classroom_students',
    '/api/classrooms/:classroom_id/students/available': 'manage_classroom_students',
    '/api/classrooms/:id/students': 'view_classroom_students'

};

   // Function to extract the base path (without parameters)
   function getBasePath(path: string): string {
    const parts = path.split('/');
    if (parts.length > 2 && parts[2].includes(':')) {
      return `/${parts[1]}/${parts[2].split('/')[0]}`;
    }
    return `/${parts[1]}`;
  }
  
  export async function authMiddleware(req: Request, res: Response, next: NextFunction) {
    const authHeader = req.headers.authorization;
  
    if (!authHeader) {
      return res.status(401).json({ message: 'No token provided' });
    }
  
    const token = authHeader.split(' ')[1];
  
    try {
      const decoded = jwt.verify(token, jwtSecret) as any;
  
      req.user = {
        userId: decoded.userId,
        email: decoded.email,
        role: decoded.role
      };
  
      const fullPath = req.path;
      const basePath = getBasePath(fullPath);
      const requiredPermission = routePermissions[fullPath] || routePermissions[basePath];
  
      if (!requiredPermission) {
        return next(); // No permission restriction for this route
      }
  
      const db = new DatabaseService();
      const userPermissions = await db.getUserPermissions(decoded.userId);
  
      if (userPermissions.includes(requiredPermission)) {
        return next(); // Permission granted
      } else {
        return res.status(403).json({ message: 'Unauthorized: insufficient permissions' });
      }
    } catch (err) {
      console.error('JWT verification error:', err);
      return res.status(401).json({ message: 'Invalid token' });
    }
  }
