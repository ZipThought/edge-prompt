import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from '../services/api';
import  bcrypt from 'bcryptjs';
import DOMPurify from "dompurify";

const SignUpPage: React.FC = () => {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    firstname: "",
    lastname: "",
    email: "",
    password: "",
    dob: "",
    role: ""
  });

  const [passwordVisible, setPasswordVisible] = useState(false);

  const [message, setMessage] = useState('');

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const togglePasswordVisibility = () => {
    setPasswordVisible(!passwordVisible);
  };

  // Handle form submission - connected to api.ts
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const signupData = {
        firstname: DOMPurify.sanitize(formData.firstname),
        lastname: DOMPurify.sanitize(formData.lastname),
        email: DOMPurify.sanitize(formData.email),
        password: DOMPurify.sanitize(formData.password),
        dob: DOMPurify.sanitize(formData.dob),
      }
      const response = await api.signup(signupData);
      if (response && response.token) {
        //  Assuming the backend sends a 'token' property
        localStorage.setItem("authToken", response.token); //  Securely store the token
        navigate("/"); // Navigate to the home page
      }
      setMessage('Account created successfully!');
      setFormData({
        firstname: "",
        lastname: "",
        email: "",
        password: "",
        dob: "",
        role: ""
      });
    } catch (error: any) {
      setMessage(`Signup failed: ${error.response?.data?.error || error.message}`);
    }
  };

  return (
    <div className="container d-flex justify-content-center align-items-center vh-100">
      <div className="card shadow-lg p-4 rounded" style={{ width: "400px" }}>
        <h2 className="text-center mb-4 text-primary">
          <i className="bi bi-person-plus"></i> Sign Up
        </h2>
        <form onSubmit={handleSubmit}>

          <div className="mb-3">
            <label htmlFor="firstname" className="form-label">
              First Name
            </label>
            <input
              type="text"
              className="form-control"
              id="firstname"
              name="firstname"
              value={formData.firstname}
              onChange={handleInputChange}
              required
            />
          </div>

          <div className="mb-3">
            <label htmlFor="lastname" className="form-label">
              Last Name
            </label>
            <input
              type="text"
              className="form-control"
              id="lastname"
              name="lastname"
              value={formData.lastname}
              onChange={handleInputChange}
              required
            />
          </div>

          <div className="mb-3">
            <label htmlFor="email" className="form-label">
              Email
            </label>
            <input
              type="email"
              className="form-control"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
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
                value={formData.password}
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

          <div className="mb-3">
            <label htmlFor="dob" className="form-label">
              Date of Birth
            </label>
            <input
              type="date"
              className="form-control"
              id="dob"
              name="dob"
              value={formData.dob}
              onChange={handleInputChange}
              required
            />
          </div>

          {/* New Role Selection Section */}
          <div className="mb-3">
            <label htmlFor="role" className="form-label">
              Role
            </label>
            <select
              className="form-select"
              id="role"
              name="role"
              value={formData.role}
              onChange={handleInputChange}
              required
            >
              <option value="student">Student</option>
              <option value="teacher">Teacher</option>
            </select>
          </div>

          <button type="submit" className="btn btn-primary w-100">
            Sign Up
          </button>
        </form>

        <p className="text-center mt-3">
          Already have an account?{" "}
        </p>
      </div>
    </div>
  );
};

export default SignUpPage;
