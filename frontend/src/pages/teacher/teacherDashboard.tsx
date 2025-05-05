import React, { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { api } from "src/services/api";

// Define class type
type Class = {
  id: string;
  name: string;
};

const TeacherDashboard: React.FC = () => {
  const [teacherName, setTeacherName] = useState("Teacher");
  const [classes, setClasses] = useState<Class[]>([]);
  const navigate = useNavigate();
  const location = useLocation();
  const successMessage = location.state?.successMessage || "";
  const [showSuccess, setShowSuccess] = useState(!!successMessage);

  useEffect(() => {
    const fetchTeacherData = async () => {
      try {
        const profile = await api.getProfile();
        setTeacherName(`${profile.firstname} ${profile.lastname}`);
      } catch (err) {
        console.error("Failed to fetch teacher data:", err);
      }
    };

    const fetchTeacherClasses = async () => {
      try {
        const token = localStorage.getItem("token");
        const userId = localStorage.getItem("userId"); 
    
        const response = await fetch(`http://localhost:3001/api/classrooms/users/${userId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
    
        if (!response.ok) {
          throw new Error("Failed to fetch classes");
        }
    
        const data = await response.json();
        setClasses(data.map((cls: any) => ({
          id: cls.id,
          name: cls.name,
        })));
      } catch (err) {
        console.error("Failed to fetch teacher classes:", err);
      }
    };    

    fetchTeacherData();
    fetchTeacherClasses();
  }, []);

  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => {
        setShowSuccess(false);
      }, 3000); // 5 seconds

      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  const handleLogout = () => {
    navigate("/");
  };

  const handleCreateClass = () => {
    navigate("/dashboard/teacher/create-class");
  };

  const handleManageClass = (classId: string) => {
    navigate(`/dashboard/teacher/manage-class/${classId}`);
  };
  const handleGradeClass = (classId: String) => {
    navigate(`/dashboard/teacher/grade/${classId}`);
  }
  

  return (
    <div className="container-fluid">
      <header className="bg-primary text-white p-3 mb-4">
        <div className="d-flex justify-content-between align-items-center">
          <h1 className="h4 mb-0">
            <i className="bi bi-braces"></i> EdgePrompt <span className="text-white">| Teacher Dashboard</span>
          </h1>
          <nav className="ms-auto d-flex align-items-center gap-3">
            <button className="btn btn-light btn-sm" onClick={() => navigate("/")}>
              Home
            </button>
            <button className="btn btn-light btn-sm" onClick={() => navigate("/profile")}>
              Profile
            </button>
            <button className="btn btn-outline-light btn-sm" onClick={handleLogout}>
              <i className="bi bi-box-arrow-right me-1"></i> Logout
            </button>
          </nav>
        </div>
      </header>
  
      <h2 className="mb-4">Welcome, {teacherName}!</h2>
      {showSuccess && (
        <div className="alert alert-success" role="alert">
          {successMessage}
        </div>
      )}
  
      <div className="row">
        <div className="col-md-9">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h4>Your Classes</h4>
            <button className="btn btn-primary btn-sm" onClick={handleCreateClass}>
              <i className="bi bi-plus-lg me-1"></i> Create Class
            </button>
          </div>
  
          <div className="row g-3">
            {classes.map((cls) => (
              <div className="col-md-6 col-lg-4" key={cls.id}>
                <div className="card shadow-sm h-100">
                  <div className="card-body text-center">
                    <h5 className="card-title">{cls.name}</h5>
                    <div className="d-flex justify-content-center gap-2 mt-2 flex-wrap">
                      <button
                        className="btn btn-outline-primary btn-sm"
                        onClick={() => navigate(`/dashboard/teacher/class/${cls.id}`)}
                      >
                        View Materials
                      </button>
                      <button
                        className="btn btn-outline-primary btn-sm"
                        onClick={() => handleManageClass(cls.id)}
                      >
                        Manage
                      </button>
                      <button
                       className="btn btn-outline-primary btn-sm"
                       onClick={() => handleGradeClass(cls.id)}
                      >
                        
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {classes.length === 0 && (
              <div className="col-12 text-center text-muted mt-3">
                No classes yet. Create your first class!
              </div>
            )}
          </div>
        </div>
  
        <div className="col-md-3">
          <div className="card shadow-sm">
            <div className="card-header bg-light">
              <h5 className="mb-0">
                <i className="bi bi-megaphone me-1"></i> Class Management
              </h5>
            </div>
            <div className="card-body">
              <p className="text-muted">This section will include announcements and tools in future.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );  
};

export default TeacherDashboard;