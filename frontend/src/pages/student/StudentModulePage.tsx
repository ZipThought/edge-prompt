import React, { useEffect, useState, useCallback } from "react";
 import { useParams, useNavigate } from "react-router-dom";
 import { api } from "../../services/api";
 import { Material, Project } from "../../types";
 import { GeneratedQuestion } from '../../types/edgeprompt';
 // Import GeneratedQuestion type
 

 interface Class {
  id: string;
  name: string;
 }
 

 interface QuestionWithAnswer extends Omit<any, 'id'> {
  id: string;
  studentAnswer: string;
  feedback?: string;
  score?: number;
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
  const [submissionStatus, setSubmissionStatus] = useState<
  { [questionId: string]: 'idle' | 'submitting' | 'success' | 'error' }
  >({});
  const [submissionErrors, setSubmissionErrors] = useState<
  { [questionId: string]: string }
  >({});
  const [submissionConfirmation, setSubmissionConfirmation] = useState<
  { [questionId: string]: boolean }
  >({});
  const [responses, setResponses] = useState<
  { [questionId: string]: any }
  >({});
  const [editMode, setEditMode] = useState<{ [questionId: string]: boolean }>({});
  const [activeTab, setActiveTab] = useState<'content' | 'questions'>('content');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [allSubmitted, setAllSubmitted] = useState(false);
  const [showFinalSubmitConfirmation, setShowFinalSubmitConfirmation] = useState(false);
  const [isMaterialFinallySubmitted, setIsMaterialFinallySubmitted] = useState(false);
 

  // Function to fetch response for a single question
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
 

          setResponses(initialResponses);
          setQuestions(questionsData.map(q => ({
            ...q,
            studentAnswer: initialResponses[q.id]?.response || '',
            feedback: initialResponses[q.id]?.feedback,
            score: initialResponses[q.id]?.score,
          })));
          setEditMode(questionsData.reduce((acc, q) => ({ ...acc, [q.id]: !initialResponses[q.id] }), {}));
 

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
 

  useEffect(() => {
    const checkFinalSubmission = async () => {
      if (selectedMaterial) {
        try {
          console.log("Checking final submission status for material:", selectedMaterial.id);
          const response = await api.isMaterialFinallySubmitted(selectedMaterial.id);
          setIsMaterialFinallySubmitted(response.isFinal);
        } catch (error) {
          console.error("Failed to check final submission:", error);
          // Handle error (e.g., show a message to the user)
        }
      }
    };
 

    checkFinalSubmission();
  }, [selectedMaterial]);
 

  const handleProjectClick = (projectId: string) => {
    navigate(`/dashboard/student/project/${projectId}`);
  };
 

  const handleBack = () => {
    navigate(`/dashboard/student`);
  };
 

  const handleLogout = () => {
    navigate("/");
  };
  const handleProfile = () => {
    navigate("/profile");
  };
 

  const handleAnswerChange = (questionId: string, answer: string) => {
    setQuestions(prevQuestions =>
      prevQuestions.map(q =>
        q.id === questionId ? { ...q, studentAnswer: answer } : q
      )
    );
  };
 

  const handleSubmitAnswer = async (questionId: string) => {
    const question = questions.find(q => q.id === questionId);
    if (!question || !question.studentAnswer.trim()) {
      setSubmissionErrors(prevErrors => ({
        ...prevErrors,
        [questionId]: "Please provide an answer.",
      }));
      return;
    }
 

    setIsSubmitting(true);
    setResponses(prevResponses => ({
      [questionId]: question.studentAnswer,
    }));
    setSubmissionStatus(prevStatus => ({
      ...prevStatus,
      [questionId]: 'submitting',
    }));
    setSubmissionErrors(prevErrors => ({
      ...prevErrors,
      [questionId]: '',
    }));
    try {
      const responseData = await api.saveResponse({
        questionId: question.id,
        response: question.studentAnswer,
      });
      console.log("Response data:", responseData);
      setSubmissionConfirmation(prevConfirmation => ({
        ...prevConfirmation,
        [questionId]: true,
      }));
      setEditMode(prevEditMode => ({
        ...prevEditMode,
        [questionId]: false
      }));
      setSubmissionStatus(prevStatus => ({
        ...prevStatus,
        [questionId]: 'success',
      }));
    } catch (error: any) {
      console.error("Failed to submit answer:", error);
      setSubmissionStatus(prevStatus => ({
        ...prevStatus,
        [questionId]: 'error',
      }));
      setSubmissionErrors(prevErrors => ({
        ...prevErrors,
        [questionId]: error.message || "Failed to submit answer.",
      }));
    } finally {
      setIsSubmitting(false);
      setTimeout(() => {
        setSubmissionStatus(prevStatus => ({
          ...prevStatus,
          [questionId]: 'idle',
        }));
        setSubmissionConfirmation(prevConfirmation => ({
          ...prevConfirmation,
          [questionId]: false,
        }));
      }, 3000);
    }
  };
 

  const toggleEditMode = (questionId: string) => {
    setEditMode(prevEditMode => ({
      ...prevEditMode,
      [questionId]: !prevEditMode[questionId]
    }));
  };
 

  const handleFinalSubmit = async () => {
    if (!selectedMaterial) {
      setError("No material selected for final submission.");
      return;
    }
    if (window.confirm("Are you sure you want to finalize your submission? You will not be able to edit your answers after this.")) {
      setIsSubmitting(true);
      try {
        await api.finalSubmit(selectedMaterial.id); // Call the new API endpoint
        setAllSubmitted(true);
        setIsMaterialFinallySubmitted(true); // Update the local state
        alert("All answers submitted. No more edits allowed."); // Replace with better UI feedback
      } catch (error) {
        console.error("Failed to finalize submission:", error);
        setError("Failed to finalize submission. Please try again.");
      } finally {
        setIsSubmitting(false);
      }
    }
  };
 

  const confirmFinalSubmit = () => {
    // Implement logic to finalize all responses
    // For example, you might want to disable further edits,
    // trigger a final submission API call, etc.
    setAllSubmitted(true);
    alert("All answers submitted. No more edits allowed.");
    setShowFinalSubmitConfirmation(false);
  };
 

  const cancelFinalSubmit = () => {
    setShowFinalSubmitConfirmation(false);
  };
 

  if (loading) {
    return (
      <div className="container text-center mt-5">
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
        <p className="mt-2">Loading project...</p>
      </div>
    );
  }
 

  if (error) {
    return (
      <div className="container mt-5">
        <div className="alert alert-danger">{error}</div>
        <button className="btn btn-secondary" onClick={handleBack}>
          Back to Dashboard
        </button>
      </div>
    );
  }
 

  if (!project) {
    return (
      <div className="container mt-5">
        <div className="alert alert-warning">Project not found.</div>
        <button className="btn btn-secondary" onClick={handleBack}>
          Back to Dashboard
        </button>
      </div>
    );
  }
 

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
              {materials.length > 0 && (
                <div className="mb-4">
                  <h4>Materials</h4>
                  <div className="list-group">
                    {materials.map(material => (
                      <button
                        key={material.id}
                        className="list-group-item list-group-item-action"
                        onClick={() => setSelectedMaterial(material)}
                      >
                        {material.title}
                      </button>
                    ))}
                  </div>
                </div>
              )}
 

              {/* Moved tabs here, below the material list */}
              {selectedMaterial && (
                <ul className="nav nav-tabs mb-4" style={{ marginTop: '2rem' }}>
                  <li className="nav-item">
                    <button
                      className={`nav-link ${activeTab === 'content' ? 'active' : ''}`}
                      onClick={() => setActiveTab('content')}
                    >
                      Content
                    </button>
                  </li>
                  <li className="nav-item">
                    <button
                      className={`nav-link ${activeTab === 'questions' ? 'active' : ''}`}
                      onClick={() => setActiveTab('questions')}
                    >
                      Questions
                    </button>
                  </li>
                </ul>
              )}
 

              {activeTab === 'content' && selectedMaterial && (
                <div>
                  
                  <p>{selectedMaterial.content}</p>
                </div>
              )}
 

              {activeTab === 'questions' && selectedMaterial && (
                <div>
                  {questions.length > 0 ? (
                    <div>
                      <h6>Questions:</h6>
                      {questions.map(question => {
                        const previousResponse = responses[question.id];
                        const isEditing = editMode[question.id];
                        return (
                          <div key={question.id} className="card mt-3">
                            <div className="card-body">
                              <p>{question.question}</p>
                              {/* Display existing response in the textarea */}
                              <div className="mb-3">
                                <label htmlFor={`answer-${question.id}`} className="form-label">Your Answer:</label>
                                <textarea
                                  className="form-control"
                                  id={`answer-${question.id}`}
                                  rows={4}
                                  value={question.studentAnswer}
                                  onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                                  placeholder="Type your answer here..."
                                  disabled={isSubmitting || isMaterialFinallySubmitted} // Disable based on backend status
                                />
                                {submissionErrors[question.id] && (
                                  <div className="text-danger">{submissionErrors[question.id]}</div>
                                )}
                              </div>
                              <div className="d-flex justify-content-end">
                                <button
                                  type="button"
                                  className="btn btn-success me-2"
                                  onClick={() => handleSubmitAnswer(question.id)}
                                  disabled={isSubmitting || isMaterialFinallySubmitted} // Disable based on backend status
                                >
                                  {isSubmitting ? (
                                    <>
                                      <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                      Saving...
                                    </>
                                  ) : (
                                    "Save Answer"
                                  )}
                                </button>
                                {/* Remove edit mode toggle */}
                              </div>
                              {submissionConfirmation[question.id] && (
                                <div className="alert alert-success mt-3">
                                  Answer saved successfully!
                                </div>
                              )}
 

                              {/* Placeholder for feedback and score */}
                              <div className="mt-3">
                                <p>Score: [Score will appear here]</p>
                                <p>Feedback: [Feedback will appear here]</p>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="alert alert-info">No questions available for this material.</div>
                  )}
                  {/* Final Submit Button */}
                  {questions.length > 0 && !isMaterialFinallySubmitted && !allSubmitted && (
                    <div className="mt-4 text-center">
                      <button
                        type="button"
                        className="btn btn-danger btn-lg"
                        onClick={handleFinalSubmit}
                        disabled={isSubmitting}
                      >
                        Final Submit All Answers
                      </button>
                    </div>
                  )}
                  {/* Confirmation Modal */}
                  {showFinalSubmitConfirmation && (
                    <div className="modal show d-block" tabIndex={-1} role="dialog" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                      <div className="modal-dialog modal-dialog-centered" role="document">
                        <div className="modal-content">
                          <div className="modal-header">
                            <h5 className="modal-title">Confirm Final Submission</h5>
                            <button type="button" className="btn-close" onClick={cancelFinalSubmit} aria-label="Close"></button>
                          </div>
                          <div className="modal-body">
                            <p>Are you sure you want to submit all answers? You will not be able to edit them after this.</p>
                          </div>
                          <div className="modal-footer">
                            <button type="button" className="btn btn-secondary" onClick={cancelFinalSubmit}>Cancel</button>
                            <button
                              type="button"
                              className="btn btn-danger"
                              onClick={confirmFinalSubmit}
                              disabled={isSubmitting || isMaterialFinallySubmitted} // Disable final submit during individual submission
                            >
                              Yes, Submit
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
 };
 

 export default StudentModulePage;