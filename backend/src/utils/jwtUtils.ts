// backend/src/utils/jwtUtils.ts
import crypto from 'crypto';

export const generateJwtSecret = () => {
    return crypto.randomBytes(32).toString('hex');
};