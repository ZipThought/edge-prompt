import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../../services/api";
import { Material, Project } from "../../types";

interface QuestionWithAnswer extends Omit<any, 'id'> {
  id: string;
  studentAnswer: string;
}

const StudentModulePage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [project, setProject] = useState<Project | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [questions, setQuestions] = useState<QuestionWithAnswer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMaterial, setSelectedMaterial] = useState<Material | null>(null);
  const [activeTab, setActiveTab] = useState<'material' | 'questions'>('material');
  const [submissionSuccess, setSubmissionSuccess] = useState(false);
  const [validationErrors, setValidationErrors] = useState<{ [questionId: string]: string }>({});

  const fetchResponse = useCallback(async (questionId: string) => {
    try {
      const response = await api.getResponses(questionId);
      return response ? response[0] : null;
    } catch (error) {
      console.error(`Failed to fetch response for question ${questionId}:`, error);
      return null;
    }
  }, []);

  useEffect(() => {
    const fetchProjectData = async () => {
      setLoading(true);
      setError(null);
      try {
        const projectData = await api.getProject(projectId!);
        setProject(projectData);
        const allProjects = await api.getProjects();
        setProjects(allProjects);
      } catch (err) {
        console.error("Failed to fetch project:", err);
        setError("Failed to load project.");
      }
    };

    const fetchMaterialsData = async () => {
      try {
        const materialsData = await api.getMaterials(projectId!);
        setMaterials(materialsData);
      } catch (err) {
        console.error("Failed to fetch materials:", err);
        setError("Failed to load materials.");
      } finally {
        setLoading(false);
      }
    };

    fetchProjectData();
    fetchMaterialsData();
  }, [projectId]);

  useEffect(() => {
    const fetchQuestionsAndResponses = async () => {
      if (selectedMaterial) {
        setLoading(true);
        setError(null);
        try {
          const questionsData = await api.getQuestions(selectedMaterial.id);
          const initialResponses: { [questionId: string]: any } = {};
          for (const question of questionsData) {
            const response = await fetchResponse(question.id);
            if (response) {
              initialResponses[question.id] = response;
            }
          }
          setQuestions(questionsData.map(q => ({
            ...q,
            studentAnswer: initialResponses[q.id]?.response || '',
          })));
          const hasExistingResponses = Object.values(initialResponses).some(res => res?.response?.trim());
          setSubmissionSuccess(hasExistingResponses);
        } catch (error) {
          console.error("Failed to fetch questions and responses:", error);
          setError("Failed to load questions and responses.");
        } finally {
          setLoading(false);
        }
      } else {
        setQuestions([]);
      }
    };

    fetchQuestionsAndResponses();
  }, [selectedMaterial, fetchResponse]);

  const handleSubmitAllAnswers = async () => {
    const newErrors: { [questionId: string]: string } = {};
    let hasError = false;
    let firstInvalidId: string | null = null;

    questions.forEach(q => {
      if (!q.studentAnswer.trim()) {
        newErrors[q.id] = "Please answer this question.";
        if (!firstInvalidId) firstInvalidId = q.id;
        hasError = true;
      }
    });

    setValidationErrors(newErrors);
    if (hasError && firstInvalidId) {
      const el = document.getElementById(`question-${firstInvalidId}`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    if (hasError) return;

    try {
      await Promise.all(
        questions.map(q =>
          api.saveResponse({
            questionId: q.id,
            response: q.studentAnswer,
          })
        )
      );
      setSubmissionSuccess(true);
    } catch (error) {
      console.error("Failed to submit responses:", error);
      alert("There was an error submitting your responses.");
    }
  };

  const handleProjectClick = (projectId: string) => navigate(`/dashboard/student/project/${projectId}`);
  const handleBack = () => navigate(`/dashboard/student`);
  const handleLogout = () => navigate("/");
  const handleProfile = () => navigate("/profile");

  const handleAnswerChange = (questionId: string, answer: string) => {
    setQuestions(prev => prev.map(q => q.id === questionId ? { ...q, studentAnswer: answer } : q));
    setValidationErrors(prev => ({ ...prev, [questionId]: "" }));
  };

  if (loading) return (<div className="container text-center mt-5"><div className="spinner-border" role="status" /><p className="mt-2">Loading project...</p></div>);
  if (error) return (<div className="container mt-5"><div className="alert alert-danger">{error}</div><button className="btn btn-secondary" onClick={handleBack}>Back to Dashboard</button></div>);
  if (!project) return (<div className="container mt-5"><div className="alert alert-warning">Project not found.</div><button className="btn btn-secondary" onClick={handleBack}>Back to Dashboard</button></div>);

  return (
    <div className="container-fluid">
      <header className="bg-primary text-white p-3 mb-4">
        <div className="d-flex justify-content-between align-items-center">
          <h1 className="h4 mb-0"><i className="bi bi-braces"></i> EdgePrompt | Module: {project.name}</h1>
          <nav className="ms-auto d-flex align-items-center gap-3">
            <button className="btn btn-light btn-sm" onClick={handleBack}><i className="bi bi-arrow-left me-1"></i> Back to Class</button>
            <button className="btn btn-light btn-sm" onClick={handleProfile}><i className="bi bi-person-circle me-1"></i> Profile</button>
            <button className="btn btn-outline-light btn-sm" onClick={handleLogout}><i className="bi bi-box-arrow-right me-1"></i> Logout</button>
          </nav>
        </div>
      </header>

      <div className="row">
        <div className="col-md-4 col-lg-3">
          <div className="card shadow-sm mb-4">
            <div className="card-header bg-light"><h5 className="mb-0">Modules</h5></div>
            <div className="card-body">
              {projects.length === 0 ? <div className="alert alert-info">No projects available for this class.</div> : (
                <div className="list-group list-group-flush">
                  {projects.map(p => (
                    <button
                      key={p.id}
                      className={`list-group-item list-group-item-action ${p.id === projectId ? 'active' : ''}`}
                      onClick={() => handleProjectClick(p.id)}
                    >
                      {p.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-md-8 col-lg-9">
          <div className="card shadow-sm">
            <div className="card-body">
              <h2 className="card-title">{project.name}</h2>
              {project.description && <p className="card-text">{project.description}</p>}
              <h4>Materials</h4>
              {materials.length === 0 ? <div className="alert alert-info">No materials available for this project.</div> : (
                <div className="list-group">
                  {materials.map(material => (
                    <button key={material.id} className={`list-group-item list-group-item-action ${selectedMaterial?.id === material.id ? 'active' : ''}`} onClick={() => { setSelectedMaterial(material); setActiveTab('material'); }}>{material.title}</button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {selectedMaterial && (
            <>
              <ul className="nav nav-tabs mt-4">
                <li className="nav-item">
                  <button className={`nav-link ${activeTab === 'material' ? 'active' : ''}`} onClick={() => setActiveTab('material')}>Material</button>
                </li>
                <li className="nav-item">
                  <button className={`nav-link ${activeTab === 'questions' ? 'active' : ''}`} onClick={() => setActiveTab('questions')}>Questions</button>
                </li>
              </ul>

              {activeTab === 'material' && (
                <div className="card shadow-sm mt-3">
                  <div className="card-body">
                    <h5 className="card-title">{selectedMaterial.title}</h5>
                    <p className="card-text">{selectedMaterial.content}</p>
                  </div>
                </div>
              )}

              {activeTab === 'questions' && (
                <div className="card shadow-sm mt-3">
                  <div className="card-body">
                    <h5 className="card-title">Teacher Questions</h5>
                    <form onSubmit={(e) => { e.preventDefault(); handleSubmitAllAnswers(); }}>
                      {questions.length > 0 && !submissionSuccess ? (
                        questions.map((question) => (
                          <div key={question.id} id={`question-${question.id}`} className="mb-4">
                            <p className="fw-bold">{question.question}</p>
                            <textarea
                              className="form-control"
                              rows={4}
                              value={question.studentAnswer}
                              onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                              placeholder="Your answer here..."
                            ></textarea>
                            {validationErrors[question.id] && (
                              <div className="text-danger mt-1">{validationErrors[question.id]}</div>
                            )}
                          </div>
                        ))
                      ) : questions.length === 0 && !submissionSuccess ? (
                        <div className="alert alert-info">No questions yet for this material.</div>
                      ) : null
                    }
                      {questions.length > 0 && !submissionSuccess && (
                        <button type="submit" className="btn btn-success">Submit</button>
                      )}
                    </form>
                    {submissionSuccess && (
                      <div className="alert alert-success mt-3">
                        Your responses have been submitted for review.
                      </div>
                    )}
                    {submissionSuccess && (
                      <div className="mt-4">
                        <h6 className="fw-bold">Teacher Feedback</h6>
                        <p className="text-muted">Coming soon...</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default StudentModulePage;
