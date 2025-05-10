// backend/src/utils/jwtUtils.ts
import crypto from 'crypto';

let jwtSecret: string | undefined = undefined;

export const generateJwtSecret = () => {
    console.log("generateJwtSecret called");
    if (!jwtSecret) {
        jwtSecret = crypto.randomBytes(32).toString('hex');
        console.log(`generateJwtSecret: Generated new secret: ${jwtSecret}`);
    } else {
        console.log(`generateJwtSecret: Returning existing secret: ${jwtSecret}`);
    }
    return jwtSecret;
};

export const getJwtSecret = () => {
    console.log("getJwtSecret called");
    if (!jwtSecret) {
        jwtSecret = crypto.randomBytes(32).toString('hex');
        console.log(`getJwtSecret: Generated new secret: ${jwtSecret}`);
    } else {
        console.log(`getJwtSecret: Returning existing secret: ${jwtSecret}`);
    }
    return jwtSecret;
};