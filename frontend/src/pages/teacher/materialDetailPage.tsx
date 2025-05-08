import React, { useEffect, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { api } from "../../services/api";

const MaterialDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const classId = location.state?.classId;

  const [material, setMaterial] = useState<any>(null);
  const [questions, setQuestions] = useState<any[]>([]);
  const [promptTemplates, setPromptTemplates] = useState<any[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editedQuestion, setEditedQuestion] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    const fetchMaterial = async () => {
      try {
        const data = await api.getMaterial(id!);
        setMaterial(data);
        const fetchedQuestions = await api.getQuestions(id!);
        setQuestions(fetchedQuestions);
        const fetchedPromptTemplates = await api.getPromptTemplates();
        setPromptTemplates(fetchedPromptTemplates);
      } catch (error) {
        console.error("Failed to fetch material", error);
      }
    };
    fetchMaterial();
  }, [id]);

  const handleLogout = () => navigate("/");

  const getPromptTemplateName = (id: string) => {
    const template = promptTemplates.find(t => t.id === id);
    return template?.name || template?.title || "Unknown Template";
  };

  const handleGenerateQuestions = async () => {
    if (!material?.metadata?.templates?.length) {
      alert("No templates found for this material.");
      return;
    }

    setIsGenerating(true);
    try {
      const templates = material.metadata.templates;
      const promptTemplates = await api.getPromptTemplates();
      const defaultPromptTemplateId = promptTemplates[0]?.id;

      if (!defaultPromptTemplateId) {
        throw new Error("No prompt template found in the system.");
      }

      await Promise.all(
        templates.map((template: any, index: number) => {
          const payload = {
            materialId: id!,
            promptTemplateId: template.promptTemplateId || defaultPromptTemplateId,
            templateIndex: index,
            useSourceLanguage: material.metadata?.useSourceLanguage || false,
          };

          return api.generateQuestion(
            payload.materialId,
            payload.promptTemplateId,
            payload.templateIndex,
            { useSourceLanguage: payload.useSourceLanguage }
          );
        })
      );

      const updatedQuestions = await api.getQuestions(id!);
      setQuestions(updatedQuestions);
      setSuccessMessage("Questions generated successfully.");
    } catch (error) {
      console.error("Failed to generate questions", error);
      alert("Failed to generate questions");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSaveEdit = async () => {
    if (!editingId || !editedQuestion) return;
    try {
      await api.updateQuestion(editingId, editedQuestion);
      setQuestions(prev =>
        prev.map(q => (q.id === editingId ? { ...q, question: editedQuestion } : q))
      );
      setEditingId(null);
      setEditedQuestion("");
    } catch {
      alert("Failed to update question");
    }
  };

  if (!material) return <div className="text-center mt-5">Loading...</div>;

  return (
    <div className="container-fluid">
      <header className="bg-primary text-white p-3 mb-4">
        <div className="d-flex justify-content-between align-items-center">
          <h1 className="h4 mb-0">
            <i className="bi bi-braces"></i> EdgePrompt <span className="text-white">| Material Detail</span>
          </h1>
          <nav className="ms-auto d-flex align-items-center gap-3">
            <button className="btn btn-light btn-sm" onClick={() => navigate(`/dashboard/teacher/class/${classId}`)}>
              Back
            </button>
            <button className="btn btn-light btn-sm" onClick={() => navigate("/profile")}>Profile</button>
            <button className="btn btn-outline-light btn-sm" onClick={handleLogout}>
              <i className="bi bi-box-arrow-right me-1"></i> Logout
            </button>
          </nav>
        </div>
      </header>

      <div className="row">
        <div className="col-lg-9">
          <div className="card shadow-sm mb-4">
            <div className="card-body">
              <h2 className="mb-1">{material.title || "Untitled Material"}</h2>
              <p className="text-muted">{material.focusArea}</p>
              <hr />

              <div className="d-flex justify-content-between align-items-center mb-3">
                <h5 className="mb-0">Learning Objectives</h5>
                <button
                  className="btn btn-sm btn-primary"
                  onClick={handleGenerateQuestions}
                  disabled={isGenerating}
                >
                  {isGenerating ? "Generating..." : "Generate Questions"}
                </button>
              </div>

              <ul className="mb-4">
                {(material.metadata?.learningObjectives || []).map((obj: string, i: number) => (
                  <li key={i}>{obj}</li>
                ))}
              </ul>

              {successMessage && (
                <div className="alert alert-success alert-dismissible fade show" role="alert">
                  {successMessage}
                  <button type="button" className="btn-close" onClick={() => setSuccessMessage("")}></button>
                </div>
              )}

              <hr />
              <h5 className="mb-3">Generated Questions</h5>

              {questions.length === 0 ? (
                <p className="text-muted">No questions generated yet.</p>
              ) : (
                <div className="accordion" id="questionsAccordion">
                  {questions.map((q, i) => (
                    <div className="accordion-item" key={q.id}>
                      <h2 className="accordion-header" id={`heading-${q.id}`}>
                        <button
                          className="accordion-button collapsed"
                          type="button"
                          data-bs-toggle="collapse"
                          data-bs-target={`#collapse-${q.id}`}
                          aria-expanded="false"
                          aria-controls={`collapse-${q.id}`}
                        >
                          Question {i + 1}
                        </button>
                      </h2>
                      <div
                        id={`collapse-${q.id}`}
                        className="accordion-collapse collapse"
                        aria-labelledby={`heading-${q.id}`}
                        data-bs-parent="#questionsAccordion"
                      >
                        <div className="accordion-body">
                          <p className="text-muted mb-2">
                            <strong>Prompt Template:</strong> {getPromptTemplateName(q.promptTemplateId)}
                          </p>
                          {editingId === q.id ? (
                            <>
                              <textarea
                                className="form-control mb-2"
                                value={editedQuestion}
                                onChange={(e) => setEditedQuestion(e.target.value)}
                              />
                              <div className="d-flex gap-2">
                                <button className="btn btn-success btn-sm" onClick={handleSaveEdit}>
                                  Save
                                </button>
                                <button
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => setEditingId(null)}
                                >
                                  Cancel
                                </button>
                              </div>
                            </>
                          ) : (
                            <>
                              <p>{q.question}</p>
                              <div className="d-flex gap-2">
                                <button
                                  className="btn btn-outline-primary btn-sm"
                                  onClick={() => {
                                    setEditingId(q.id);
                                    setEditedQuestion(q.question);
                                  }}
                                >
                                  Edit
                                </button>
                              </div>
                            </>
                          )}

                          {q.rubric?.validationChecks && (
                            <>
                              <hr />
                              <h6 className="mt-3">Marking Criteria</h6>
                              <ul className="ms-3">
                                {Object.entries(q.rubric.validationChecks).map(([_, v], i) => (
                                  <li key={i}>
                                    <span className="badge bg-secondary me-2">✓</span> {String(v)}
                                  </li>
                                ))}
                              </ul>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-3">
          <div className="card shadow-sm">
            <div className="card-header bg-light">
              <h5 className="mb-0">
                <i className="bi bi-info-circle me-2"></i> Material Info
              </h5>
            </div>
            <div className="card-body text-muted">
              <p><strong>File Name:</strong> {
                material.filePath ? material.filePath.split('/').pop()?.replace(/^\d+-/, '') : "N/A"
              }</p>
              <p><strong>Type:</strong> {material.fileType || material.type || "N/A"}</p>
              <p><strong>Chapter:</strong> {material.metadata?.chapter || "N/A"}</p>
              <p><strong>Language:</strong> {material.metadata?.language || "N/A"}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MaterialDetailPage;
