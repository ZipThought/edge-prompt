import React, { useEffect, useState } from "react";
 import { useNavigate, useParams } from "react-router-dom";
 import { api } from "../../services/api";
 import { Project } from "../../types";
 import { ProjectForm } from '../../components/project/ProjectForm'; // Import ProjectForm

 const TeacherGradeClassPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [classData, setClassData] = useState<any>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false); // New state to control form visibility

  useEffect(() => {
    const fetchClassData = async () => {
      try {
        const data = await api.getClassById(id!);
        setClassData(data);
      } catch (error) {
        console.error("Failed to fetch class data", error);
      } finally {
        setLoading(false);
      }
    };

    const fetchProjects = async () => {
      try {
        const classProjects = await api.getProjectsForClass(id!);
        setProjects(classProjects);
      } catch (error) {
        console.error("Failed to fetch modules:", error);
        setError("Failed to load modules for this class.");
      }
    };

    fetchClassData();
    fetchProjects();
  }, [id]);

  const handleCreateModule = () => {
    setShowCreateForm(true); // Show the form instead of navigating
  };

  const handleProjectCreated = () => {
    setShowCreateForm(false); // Hide the form after creation
    api.getProjectsForClass(id!).then(setProjects); // Refresh the list after creation
  };

  const handleViewModule = (moduleId: string) => {
    navigate(`/dashboard/teacher/project/${moduleId}`);
  };

  const handleBack = () => {
    navigate("/dashboard/teacher");
  };

  if (loading) {
    return (
      <div className="container text-center mt-5">
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
        <p className="mt-2">Loading class data...</p>
      </div>
    );
  }

  if (!classData) {
    return (
      <div className="container mt-5">
        <div className="alert alert-danger">Class not found</div>
        <button className="btn btn-secondary" onClick={() => navigate("/dashboard/teacher")}>
          Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="container-fluid">
      <header className="bg-primary text-white p-3 mb-4">
        <div className="d-flex justify-content-between align-items-center">
          <h1 className="h4 mb-0">
            <i className="bi bi-braces"></i> EdgePrompt | Class: {classData.className}
          </h1>
          <nav className="ms-auto d-flex align-items-center gap-3">
            <button className="btn btn-light btn-sm" onClick={() => navigate("/dashboard/teacher")}>
              <i className="bi bi-arrow-left me-1"></i> Back to Dashboard
            </button>
            <button
              className="btn btn-outline-light btn-sm"
              onClick={() => navigate("/")}
            >
              <i className="bi bi-box-arrow-right me-1"></i> Logout
            </button>
          </nav>
        </div>
      </header>

      <div className="row">
        <div className="col-12">
          <div className="d-flex justify-content-between align-items-center mb-4">
            <h2>Modules</h2>
            <button className="btn btn-primary" onClick={handleCreateModule}>
              <i className="bi bi-plus-circle me-2"></i> Create Module
            </button>
          </div>

          {showCreateForm && (
            <div className="mb-4">
              <ProjectForm
                onSuccess={handleProjectCreated}
                onClose={() => setShowCreateForm(false)}
                classroom_id={id}
              />
            </div>
          )}

          {projects.length === 0 ? (
            <div className="alert alert-info">
              No modules available for this class.
            </div>
          ) : (
            <div className="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
              {projects.map((module) => (
                <div className="col" key={module.id}>
                  <div className="card h-100">
                    <div className="card-body">
                      <h5 className="card-title">{module.name}</h5>
                      <p className="card-text">{module.description}</p>
                      <button
                        onClick={() => handleViewModule(module.id)}
                        className="btn btn-secondary"
                      >
                        View Module
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
 };

 export default TeacherGradeClassPage;