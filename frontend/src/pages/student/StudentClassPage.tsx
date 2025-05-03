import React, { useEffect, useState } from "react";
 import { useNavigate, useParams } from "react-router-dom";
 import { api } from "../../services/api";
 import { Project } from "../../types";

 type Class = {
  id: string;
  name: string;
 };

 type LearningMaterial = {
  id: string;
  title: string;
 };

 const StudentClassPage: React.FC = () => {
  const { classId } = useParams<{ classId: string }>();
  const navigate = useNavigate();

  const [classData, setClassData] = useState<Class | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [studentName, setStudentName] = useState("Student");

  useEffect(() => {
    const fetchClassData = async () => {
      try {
        const token = localStorage.getItem("token");
        const response = await fetch(
          `http://localhost:3001/api/classrooms/${classId}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) throw new Error("Class fetch failed");

        const data = await response.json();
        setClassData({
          id: data.id,
          name: data.name,
        });
      } catch (err) {
        console.error("Failed to fetch class data:", err);
      }
    };

    const fetchModules = async () => {
      try {
        const modules = await api.getProjectsForClass(classId!);
        setProjects(modules);
      } catch (error) {
        console.error("Failed to fetch modules:", error);
      }
    };

    const fetchStudentProfile = async () => {
      try {
        const token = localStorage.getItem("token");
        const response = await api.getProfile();
        setStudentName(`${response.firstname} ${response.lastname}`);
      } catch (err) {
        console.error("Failed to fetch student profile:", err);
      }
    };

    fetchStudentProfile();
    fetchClassData();
    fetchModules();
  }, [classId]);

  const handleModuleClick = (moduleId: string) => {
    navigate(`/dashboard/student/project/${moduleId}`); // This line is the focus
  };

  const handleBack = () => {
    navigate("/dashboard/student");
  };

  const handleLogout = () => {
    navigate("/");
  };

  const handleProfile = () => {
    navigate("/profile");
  };

  if (!classData) return <div>Loading class data...</div>;

  return (
    <div className="container-fluid">
      <header className="bg-primary text-white p-3 mb-4">
        <div className="d-flex justify-content-between align-items-center">
          <h1 className="h4 mb-0">
            <i className="bi bi-braces"></i> EdgePrompt | Class: {classData.name}
          </h1>
          <nav className="ms-auto d-flex align-items-center gap-3">
            <button className="btn btn-light btn-sm" onClick={handleBack}>
              <i className="bi bi-arrow-left me-1"></i> Dashboard
            </button>
            <button className="btn btn-light btn-sm" onClick={handleProfile}>
              <i className="bi bi-person-circle me-1"></i> Profile
            </button>
            <button
              className="btn btn-outline-light btn-sm"
              onClick={handleLogout}
            >
              <i className="bi bi-box-arrow-right me-1"></i> Logout
            </button>
          </nav>
        </div>
      </header>

      <div className="row">
        <div className="col-12">
          <h2>Modules</h2>
          {projects.length === 0 ? (
            <div className="alert alert-info">
              No modules available for this class.
            </div>
          ) : (
            <div className="row row-cols-1 row-cols-md-2 g-4">
              {projects.map((module) => (
                <div className="col" key={module.id}>
                  <div className="card h-100">
                    <div className="card-body">
                      <h5 className="card-title">{module.name}</h5>
                      <p className="card-text">{module.description}</p>
                      <button
                        onClick={() => handleModuleClick(module.id)}
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

 export default StudentClassPage;