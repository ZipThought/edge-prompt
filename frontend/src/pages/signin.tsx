import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export const LoginPage: React.FC = () => {
  // State variables to handle form inputs, errors, and loading state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
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
      // Simulating an API call with a delay
      await new Promise((resolve) => setTimeout(resolve, 1500));
      // Navigate to the home page on successful login
      navigate("/");
      // Clear input fields after successful login
      setEmail("");
      setPassword("");
    } catch (err) {
      // Handle login failure
      setError("Login failed. Please try again.");
    } finally {
      // Stop the loading state after process completion
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
