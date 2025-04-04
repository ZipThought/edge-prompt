import jwt from 'jsonwebtoken';
import { expect } from 'chai';
import request from 'supertest';
import express from 'express';
// The authMiddleware function (as in your code)
import { authMiddleware } from './authMiddleware.js'; // Adjust the path

describe('authMiddleware', () => {
    let app: express.Express;
    let server: any;
    const jwtSecret = 'your-secret-key'; // Use a consistent test secret

    before((done) => {
        app = express();
        app.use(express.json());

        // A simple protected route for testing
        app.get('/protected', authMiddleware, (req, res) => {
            res.status(200).json({ message: 'Protected', user: req.user });
        });

        server = app.listen(0, done);
    });

    after((done) => {
        server.close(done);
    });

    it('should attach decoded user to req.user with a valid token', async () => {
        const userPayload = { userId: '123', username: 'testuser' };
        const token = jwt.sign(userPayload, jwtSecret);

        const response = await request(app)
            .get('/protected')
            .set('Authorization', `Bearer ${token}`);

        expect(response.status).to.equal(200);
        expect(response.body).to.have.property('user');
        expect(response.body.user).to.have.property('userId', userPayload.userId);
        expect(response.body.user).to.have.property('username', userPayload.username);
    });

    it('should return 401 if no token is provided', async () => {
        const response = await request(app)
            .get('/protected');

        expect(response.status).to.equal(401);
        expect(response.body).to.deep.equal({ message: 'No token provided' });
    });

    it('should return 401 if token is invalid', async () => {
        const response = await request(app)
            .get('/protected')
            .set('Authorization', 'Bearer invalid-token');

        expect(response.status).to.equal(401);
        expect(response.body).to.deep.equal({ message: 'Invalid token' });
    });

    it('should handle JWT verification errors', async () => {
        // Simulate a token that would cause verification to fail (e.g., wrong secret)
        const tamperedToken = jwt.sign({ userId: '123' }, 'wrong-secret');

        const response = await request(app)
            .get('/protected')
            .set('Authorization', `Bearer ${tamperedToken}`);

        expect(response.status).to.equal(401);
        expect(response.body).to.deep.equal({ message: 'Invalid token' });
    });
});