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
  const [editMode, setEditMode] = useState<{ [questionId: string]: boolean }>({}); // Track edit mode


  // Function to fetch response for a single question
  const fetchResponse = useCallback(async (questionId: string) => {
    try {
      const response = await api.getResponses(questionId);
      return response ? response[0] : null; // Assuming getResponses returns an array
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
            studentAnswer: initialResponses[q.id]?.response || '', // Initialize with existing response
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
        setResponses({});
        setEditMode({});
      }
    };


    fetchQuestionsAndResponses();
  }, [selectedMaterial, fetchResponse]);


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
      const existingResponse = await api.getResponses(questionId);
      let updatedResponse: any;
      console.log("existingResponse", existingResponse);
      if (Array.isArray(existingResponse) && existingResponse.length > 0 && existingResponse[0].response !== "") {
        // Update the existing response
        console.log("existingResponse", questionId);
        updatedResponse = await api.updateResponse(questionId, question.studentAnswer);
      } else {
        // Create a new response
        console.log("newResponse", questionId);
        updatedResponse = await api.saveResponse({
          questionId: question.id,
          response: question.studentAnswer,
        });
      }
      console.log("responses", responses);
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
      setTimeout(() => {
        setSubmissionStatus(prevStatus => ({
          ...prevStatus,
          [questionId]: 'idle',
        }));
        setSubmissionConfirmation(prevConfirmation => ({
          ...prevConfirmation,
          [questionId]: false, // Reset confirmation after the delay
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
          <h1 className="h4 mb-0">
            <i className="bi bi-braces"></i> EdgePrompt | Project: {project.name}
          </h1>
          <nav className="ms-auto d-flex align-items-center gap-3">
            <button className="btn btn-light btn-sm" onClick={handleBack}>
              <i className="bi bi-arrow-left me-1"></i> Back to Class
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
        {/* Sidebar with Module List (as in the screenshot) */}
        <div className="col-md-4 col-lg-3">
          <div className="card shadow-sm mb-4">
            <div className="card-header bg-light">
              <h5 className="mb-0">
                Modules
              </h5>
            </div>
            <div className="card-body">
              {projects.length === 0 ? (
                <div className="alert alert-info">No projects available for this class.</div>
              ) : (
                <div className="list-group list-group-flush">
                  {projects.map(p => (
                    <button
                      key={p.id}
                      className={`list-group-item list-group-item-action ${p.id === projectId ? 'active' : ''}`}
                      onClick={() => handleProjectClick(p.id)}
                      style={{ cursor: 'pointer' }}
                    >
                      {p.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
 

        {/* Main Content Area */}
        <div className="col-md-8 col-lg-9">
          <div className="card shadow-sm">
            <div className="card-body">
              <h2 className="card-title">{project.name}</h2>
              {project.description && <p className="card-text">{project.description}</p>}
 

              <h4>Materials</h4>
              {materials.length === 0 ? (
                <div className="alert alert-info">No materials available for this project.</div>
              ) : (
                <div className="list-group">
                  {materials.map(material => (
                    <button
                      key={material.id}
                      className={`list-group-item list-group-item-action ${selectedMaterial?.id === material.id ? 'active' : ''}`}
                      onClick={() => setSelectedMaterial(material)}
                    >
                      {material.title}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
 

          {selectedMaterial && (
            <div className="card shadow-sm mt-4">
              <div className="card-body">
                <h5>{selectedMaterial.title}</h5>
                <p>{selectedMaterial.content}</p>
 

                {/* Display questions and answer inputs */}
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
                                disabled={submissionStatus[question.id] === 'submitting'}
                              >
                                {submissionStatus[question.id] === 'submitting' ? (
                                  <>
                                    <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                    Submitting...
                                  </>
                                ) : (
                                  "Submit"
                                )}
                              </button>
                              {/* Remove edit mode toggle */}
                            </div>
                            {submissionConfirmation[question.id] && (
                              <div className="alert alert-success mt-3">
                                Answer submitted successfully!
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="alert alert-info">No questions available for this material.</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StudentModulePage;