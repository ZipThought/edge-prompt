import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

export const LoginPage: React.FC = () => {
  // State variables to handle form inputs, errors, and loading state.
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Hook for navigating to different routes.
  const navigate = useNavigate();

  // Handles form submission by calling the login API.
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    // Basic validation to ensure both fields are filled.
    if (!email || !password) {
      setError("Please enter both email and password");
      setIsLoading(false);
      return;
    }

    try {
      // Call the signin API endpoint via your api service.
      // It is assumed that api.signin sends a POST request to /api/signin.
      const response = await api.signin({ email, password });
      
      // Store the token (if using JWT) in localStorage, context, or similar.
      localStorage.setItem("token", response.token);

      // Clear the input fields and navigate to the home page.
      setEmail("");
      setPassword("");
      navigate("/");
    } catch (err: any) {
      // Update error state with the message received from the API call.
      setError(`Login failed: ${err.response?.data?.message || err.message}`);
    } finally {
      // End the loading state.
      setIsLoading(false);
    }
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
              <label htmlFor="password" className="form-label">
                Password
              </label>
              <input
                type="password"
                className="form-control"
                id="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <div className="d-grid">
              <button type="submit" className="btn btn-primary" disabled={isLoading}>
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
