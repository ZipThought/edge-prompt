import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import dotenv from 'dotenv';

dotenv.config();

const jwtSecret = 'your-secret-key'; // Replace with your actual secret key

declare module 'express-serve-static-core' {
    interface Request {
      user?: any; // Or a more specific type if you have one
    }
}

export function authMiddleware(req: Request, res: Response, next: NextFunction) {
    const authHeader = req.headers.authorization;

    if (authHeader) {
        const token = authHeader.split(' ')[1]; // Extract token from "Bearer <token>"

        try {
            const decoded = jwt.verify(token, jwtSecret);
            req.user = decoded; // Attach user data to the request
            next();
        } catch (error) {
            res.status(401).json({ message: 'Invalid token' });
        }
    } else {
        res.status(401).json({ message: 'No token provided' });
    }
}