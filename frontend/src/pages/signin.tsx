import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from '../services/api';
import DOMPurify from "dompurify";

export const LoginPage: React.FC = () => {
  // State variables to handle form inputs, errors, and loading state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const [passwordVisible, setPasswordVisible] = useState(false);
  const togglePasswordVisibility = () => {
    setPasswordVisible(!passwordVisible);
  };
  
  // Hook for navigating to different routes
  const navigate = useNavigate();
  // Handles form submission for login.
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    // Basic validation to ensure fields are not empty
    if (!email || !password) {
      setError("Please enter both email and password");
      setIsLoading(false);
      return;
    }

    try {
      const userToSubmit = {
        email: DOMPurify.sanitize(email),
        password: DOMPurify.sanitize(password),
      }

      const response = await api.signin(userToSubmit);
      
      // Navigate to the home page on successful login
      if (response && response.token) {
        //  Assuming the backend sends a 'token' property
        localStorage.setItem("authToken", response.token); //  Securely store the token
        navigate("/"); // Navigate to the home page
      } else {
      setError("Login failed. Please try again."); //  Generic error
      }
      // Clear input fields after successful login
      setEmail("");
      setPassword("");
    } catch (err:any) {
      //  Handle specific API errors
      if (err.message === 'Invalid credentials') {
        setError('Invalid email or password.');
      } else if (err.message === 'User not found') {
        setError('User with this email not found.');
      } else {
        setError(err.message || "Login failed due to an unexpected error.");
      }
    } finally {
      // Stop the loading state after process completion
      setIsLoading(false);
    }
  };

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setPassword(event.target.value);
  };
  return (
    <div className="container d-flex justify-content-center align-items-center vh-100">
      <div className="card" style={{ width: "100%", maxWidth: "400px" }}>
        <div className="card-header bg-primary text-white text-center">
          <h4 className="mb-0">
            <i className="bi bi-braces me-2"></i>
            EdgePrompt Login
          </h4>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            {error && (
              <div className="alert alert-danger">
                <i className="bi bi-exclamation-triangle me-2"></i>
                {error}
              </div>
            )}

            <div className="mb-3">
              <label htmlFor="email" className="form-label">
                Email address
              </label>
              <input
                type="email"
                className="form-control"
                id="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="mb-3">
            <label htmlFor="passwordhash" className="form-label">
              Password
            </label>
            <div className="input-group">
              <input
                type={passwordVisible ? "text" : "password"}
                className="form-control"
                id="password"
                name="password"
                value={password}
                onChange={handleInputChange}
                required
              />
              <button
                type="button"
                className="btn btn-outline-secondary"
                onClick={togglePasswordVisibility}
              >
                {passwordVisible ? "Hide" : "Show"}
              </button>
            </div>
          </div>

            <div className="d-grid">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2" />
                    Logging in...
                  </>
                ) : (
                  <>
                    <i className="bi bi-box-arrow-in-right me-2"></i>
                    Login
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
        <div className="card-footer text-center">
          <small className="text-muted">
            Don't have an account? <a href="/signup">Sign up</a>
          </small>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
