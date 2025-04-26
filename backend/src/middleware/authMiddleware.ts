import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { DatabaseService } from '../services/DatabaseService.js';

declare module 'express-serve-static-core' {
    interface Request {
      user?: any; // Or a more specific type if you have one
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
    '/api/classrooms/:id': 'view_classroom',
    '/api/classrooms/users/:userId': 'view_classrooms_for_teacher',
    '/api/classrooms/:classroom_id/teachers/:user_id': 'add_teacher_to_classroom',
    '/api/classrooms/:classroom_id/students/:user_id': 'add_student_to_classroom',
    '/api/classrooms/:classroom_id/students': 'view_classroom_students',
    '/api/classrooms/:classroom_id/materials': 'view_classroom_materials'
};

   // Function to extract the base path (without parameters)
function getBasePath(path: string): string {
    const parts = path.split('/');
    if (parts.length > 2 && parts[2].includes(':')) {
        return `/${parts[1]}/${parts[2].split('/')[0]}`;
    }
    return `/${parts[1]}`;
}

export function authMiddleware(req: Request, res: Response, next: NextFunction) {
    const authHeader = req.headers.authorization;

    if (authHeader) {
        const token = authHeader.split(' ')[1]; // Extract token from "Bearer <token>"

        try {
            const decoded = jwt.verify(token, jwtSecret);
            req.user = {
                userId: (decoded as any).id,
                email: (decoded as any).email,
                role: (decoded as any).role
              };
            next();

            // Determine the required permission
            const basePath = getBasePath(req.path);
            const fullPath = req.path;
            let requiredPermission = routePermissions[fullPath] || routePermissions[basePath] ;

            if (requiredPermission) {
                const db = new DatabaseService();
                db.getUserPermissions(decoded.userId)
                    .then(userPermissions => {
                        if (userPermissions.includes(requiredPermission)) {
                            next();
                        } else {
                            res.status(403).json({ message: 'Unauthorized' });
                        }
                    })
                    .catch(err => {
                        console.error("Database error checking permissions:", err);
                        res.status(500).json({ message: 'Internal server error' });
                    });
            } else {
                next(); // No specific permission required
            }

        } catch (error) {
            res.status(401).json({ message: 'Invalid token' });
        }
    } else {
        res.status(401).json({ message: 'No token provided' });
    }
}