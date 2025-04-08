import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from "react-router-dom";
import { ErrorBoundary } from './components/ErrorBoundary';
import { ProjectForm } from './components/project/ProjectForm';
import PromptEngineeringTool from './components/tools/PromptEngineeringTool';
import { MaterialDetailView } from './components/teacher/MaterialDetailView';
import { PromptTemplateManager } from './components/prompt/PromptTemplateManager';
import { SimplifiedMaterialUploader } from './components/teacher/SimplifiedMaterialUploader';
import { ProjectProvider, useProject } from './contexts/ProjectContext';
import { api } from './services/api';
import { Material } from './types';
import SignUpPage from "./pages/signup"; 
import { LoginPage } from "./pages/signin";


// Main content wrapper that uses the project context
const MainContent: React.FC = () => {
  const { projects, activeProject, setActiveProject } = useProject();
  const [activeTab, setActiveTab] = useState<
    "generator" | "templates" | "promptTools"
  >("generator");
  const [autoSelectDisabled, setAutoSelectDisabled] = useState(false);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [isLoadingMaterials, setIsLoadingMaterials] = useState(false);
  const [selectedMaterialId, setSelectedMaterialId] = useState<string | null>(
    null
  );
  const [showCreateProject, setShowCreateProject] = useState(false);
  const navigate = useNavigate();

  // Auto-select first project if none selected
  useEffect(() => {
    if (!activeProject && projects.length > 0 && !autoSelectDisabled) {
      setActiveProject(projects[0]);
    }
  }, [projects, activeProject, setActiveProject, autoSelectDisabled]);

  // Load materials when active project changes
  useEffect(() => {
    const loadMaterials = async () => {
      if (!activeProject) return;
      setIsLoadingMaterials(true);
      try {
        const projectMaterials = await api.getMaterials(activeProject.id);
        setMaterials(projectMaterials);
      } catch (error) {
        console.error("Error loading materials:", error);
      } finally {
        setIsLoadingMaterials(false);
      }
    };

    loadMaterials();
  }, [activeProject]);

  // Handle material upload completion
  const handleMaterialUploaded = async () => {
    if (!activeProject) return;

    try {
      const projectMaterials = await api.getMaterials(activeProject.id);
      setMaterials(projectMaterials);
    } catch (error) {
      console.error("Error refreshing materials:", error);
    }
  };

  // Handle back to projects
  const handleBackToProjects = () => {
    setAutoSelectDisabled(true);
    setActiveProject(null);
  };

  // Get main content based on tab and selection
  const getMainContent = () => {
    if (!activeProject) {
      return (
        <div className="alert alert-info">
          <i className="bi bi-info-circle me-2"></i>
          Please select a project to begin
        </div>
      );
    }

    if (activeTab === "generator") {
      if (selectedMaterialId) {
        return (
          <MaterialDetailView
            materialId={selectedMaterialId}
            onBack={() => setSelectedMaterialId(null)}
            onRefresh={handleMaterialUploaded}
          />
        );
      } else {
        return (
          <div className="text-center p-5 bg-light rounded border">
            <i className="bi bi-file-earmark-text display-1 text-muted"></i>
            <h4 className="mt-3">Select a Material</h4>
            <p className="text-muted">
              Click on a material from the list on the left,
              <br />
              or upload a new material to begin.
            </p>
          </div>
        );
      }
    } else if (activeTab === "templates") {
      return <PromptTemplateManager />;
    } else {
      return <PromptEngineeringTool />;
    }
  };

  return (
    <div className="container-fluid">
      <header className="bg-primary text-white p-3 mb-4">
        <div className="d-flex justify-content-between align-items-center">
          <h1 className="h4 mb-0">
            <i className="bi bi-braces"></i> EdgePrompt
          </h1>
          <div className="ms-auto d-flex align-items-center">
            <button className="btn btn-info me-3" onClick={() => navigate("/signup")}>
              <i className="bi bi-person-plus"></i> Sign Up
            </button>
            <button className="btn btn-info me-3" onClick={() => navigate("/login")}>
              <i className="bi bi-person me-2"></i> Login
            </button>

            {activeProject ? (
              <div className="badge bg-light text-primary">
                {activeProject.name} ({activeProject.modelName})
              </div>
            ) : (
              <div className="badge bg-warning text-dark">
                <i className="bi bi-exclamation-triangle-fill me-1"></i>
                No project selected
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="row">
        {/* Left Sidebar */}
        <div className="col-md-3">
          {/* Projects Section */}
          <div className="card mb-3">
            <div className="card-header bg-light">
              <h5 className="mb-0">Projects</h5>
            </div>
            <div className="card-body p-0">
              {projects.length === 0 ? (
                <div className="text-center py-3">
                  <p className="text-muted">No projects found</p>
                  <button
                    className="btn btn-sm btn-primary"
                    onClick={() => setShowCreateProject(true)}
                  >
                    <i className="bi bi-plus-circle me-1"></i>
                    Create Project
                  </button>
                </div>
              ) : (
                <div className="list-group list-group-flush">
                  {projects.map((project) => (
                    <button
                      key={project.id}
                      className={`list-group-item list-group-item-action ${
                        activeProject?.id === project.id ? "active" : ""
                      }`}
                      onClick={() => setActiveProject(project)}
                    >
                      <div className="d-flex w-100 justify-content-between">
                        <h6 className="mb-0">{project.name}</h6>
                        <small>{project.modelName}</small>
                      </div>
                      <small
                        className="text-truncate d-block"
                        style={{ maxWidth: "100%" }}
                      >
                        {project.description}
                      </small>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Upload Material Section (only when project is selected) */}
          {activeProject && (
            <>
              <SimplifiedMaterialUploader
                onMaterialUploaded={handleMaterialUploaded}
              />

              {/* Materials List */}
              <div className="card">
                <div className="card-header bg-light d-flex justify-content-between align-items-center">
                  <h5 className="mb-0">
                    <i className="bi bi-journal-text me-1"></i>
                    Materials
                  </h5>
                </div>
                <div className="card-body p-0">
                  {isLoadingMaterials ? (
                    <div className="text-center py-3">
                      <div
                        className="spinner-border spinner-border-sm"
                        role="status"
                      >
                        <span className="visually-hidden">Loading...</span>
                      </div>
                      <p className="small mt-2 mb-0">Loading materials...</p>
                    </div>
                  ) : materials.length === 0 ? (
                    <div className="text-center py-3">
                      <p className="text-muted small mb-0">
                        No materials found
                      </p>
                    </div>
                  ) : (
                    <div className="list-group list-group-flush">
                      {materials.map((material) => (
                        <button
                          key={material.id}
                          className={`list-group-item list-group-item-action ${
                            selectedMaterialId === material.id ? "active" : ""
                          }`}
                          onClick={() => setSelectedMaterialId(material.id)}
                        >
                          <div className="d-flex justify-content-between">
                            <span
                              className="fw-semibold text-truncate"
                              style={{ maxWidth: "180px" }}
                            >
                              {material.title || "Untitled Material"}
                            </span>
                            <span
                              className={`badge bg-${getBadgeColor(
                                material.status
                              )}`}
                            >
                              {material.status}
                            </span>
                          </div>
                          <small
                            className="text-truncate d-block"
                            style={{ maxWidth: "100%" }}
                          >
                            {material.focusArea}
                          </small>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Main Content Area */}
        <div className="col-md-9">
          {activeProject && (
            <ul className="nav nav-tabs mb-4">
              <li className="nav-item">
                <button
                  className={`nav-link ${
                    activeTab === "generator" ? "active" : ""
                  }`}
                  onClick={() => {
                    setActiveTab("generator");
                  }}
                >
                  <i className="bi bi-file-text me-1"></i>
                  Content Generator
                </button>
              </li>
              <li className="nav-item">
                <button
                  className={`nav-link ${
                    activeTab === "templates" ? "active" : ""
                  }`}
                  onClick={() => {
                    setActiveTab("templates");
                    setSelectedMaterialId(null);
                  }}
                >
                  <i className="bi bi-file-earmark-text me-1"></i>
                  Prompt Templates
                </button>
              </li>
              <li className="nav-item">
                <button
                  className={`nav-link ${
                    activeTab === "promptTools" ? "active" : ""
                  }`}
                  onClick={() => {
                    setActiveTab("promptTools");
                    setSelectedMaterialId(null);
                  }}
                >
                  <i className="bi bi-tools me-1"></i>
                  Prompt Engineering Tools
                </button>
              </li>
            </ul>
          )}

          {getMainContent()}
        </div>
      </div>

      {showCreateProject && (
        <div
          className="modal show d-block"
          tabIndex={-1}
          style={{ backgroundColor: "rgba(0,0,0,0.5)" }}
        >
          <div className="modal-dialog modal-lg">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Create New Project</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowCreateProject(false)}
                ></button>
              </div>
              <div className="modal-body">
                <ProjectForm
                  onSuccess={() => {
                    setShowCreateProject(false);
                    // Refresh projects list
                    api.getProjects().then((projectsData) => {
                      if (projectsData.length > 0) {
                        setActiveProject(projectsData[0]);
                      }
                    });
                  }}
                  onClose={() => setShowCreateProject(false)}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Helper function for badge colors
function getBadgeColor(status: string): string {
  switch (status) {
    case "completed":
      return "success";
    case "pending":
      return "warning";
    case "processing":
      return "primary";
    case "error":
      return "danger";
    default:
      return "secondary";
  }
}

const App: React.FC = () => {
  return (
    <ProjectProvider>
    <Router>
      <Routes>
        {/* Signup page route - connected to signup.tsx */}
        <Route path="/signup" element={<SignUpPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element ={<MainContent/>} />
      </Routes>
    </Router>
    </ProjectProvider>
    
  );
};

export default App;
