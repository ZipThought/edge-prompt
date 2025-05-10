import React, { useState, useEffect } from 'react';
import { Material } from '../../types';
import { GeneratedQuestion } from '../../types/edgeprompt';
import { api } from '../../services/api';
import { useProject } from '../../contexts/ProjectContext';
import { Project, PromptTemplate } from '../../types';
import { QuestionGenerationService } from '../../services/QuestionGenerationService';

interface Props {
  project: Project;
  material: Material;
}

export const QuestionGenerator: React.FC<Props> = ({ project, material }) => {
  const { activeProject } = useProject();
  const [generatedQuestions, setGeneratedQuestions] = useState<{[templateIndex: string]: GeneratedQuestion}>({});
  const [generatingTemplate, setGeneratingTemplate] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedQuestions, setSavedQuestions] = useState<GeneratedQuestion[]>([]);

  // Use a composite key that uniquely identifies a question
  // This ensures we can differentiate between questions unambiguously
  const [editingQuestionKey, setEditingQuestionKey] = useState<string | null>(null);
  const [editedQuestionText, setEditedQuestionText] = useState('');
  const [editedRubricChecks, setEditedRubricChecks] = useState<string[]>([]);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [showCancelConfirmation, setShowCancelConfirmation] = useState(false);
  
  // Get templates from material metadata
  const availableTemplates = material.metadata?.templates || [];

  // Load previously generated questions
  useEffect(() => {
    const loadQuestions = async () => {
      try {
        const questions = await api.getQuestions(material.id);
        setSavedQuestions(questions);
      } catch (err) {
        console.error('Error loading saved questions:', err);
      }
    };
    
    loadQuestions();
  }, [material.id]);

  // Generate a unique key for each question
  const getQuestionKey = (questionId: string, templateIndex: number) => {
    return `${questionId}-${templateIndex}`;
  };

  // Reset all editing states
  const resetEditingState = () => {
    setEditingQuestionKey(null);
    setEditedQuestionText('');
    setEditedRubricChecks([]);
    setHasUnsavedChanges(false);
    setShowCancelConfirmation(false);
  };

  // Handle saving edited questions
  const handleSaveEditedQuestion = async (questionId: string) => {
    if (!editedQuestionText.trim()) {
      return;
    }

    try {
      // Create a rubric object with the edited validation checks
      const rubric = {
        validationChecks: editedRubricChecks
      };

      // Call the API to update the question
      await api.updateQuestion(questionId, editedQuestionText, rubric);

      // Update the local state to reflect the changes
      const updatedQuestions = savedQuestions.map(q => {
        if (q.questionId === questionId) { // Use question.questionId instead of materialId
          return {
            ...q,
            question: editedQuestionText, 
            rubric: {
              ...q.rubric,
              validationChecks: editedRubricChecks
            }
          };
        }
        return q;
      });

      // Reset the editing state
      setSavedQuestions(updatedQuestions);
      resetEditingState();

      // Show success message
      setError(null);

      // Refresh questions from the server
      const questions = await api.getQuestions(material.id);
      setSavedQuestions(questions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save question');
    }
  };

  // Handle edit cancellation with confirmation if there are unsaved changes
  const handleCancelEdit = () => {
    if (hasUnsavedChanges) {
      setShowCancelConfirmation(true);
    } else {
      resetEditingState();
    }
  };

  // Handle entering edit mode for a question
  const handleEditQuestion = (question: GeneratedQuestion, questionKey: string) => {
    // Don't allow editing if already editing another question
    if (editingQuestionKey !== null && editingQuestionKey !== questionKey) {
      return;
    }
    
    setEditingQuestionKey(questionKey);
    setEditedQuestionText(question.question);
    setEditedRubricChecks(question.rubric?.validationChecks || []);
    setHasUnsavedChanges(false);
  };

  const handleGenerateQuestion = async (template: any, index: number) => {
    if (!project?.promptTemplateId) {
      setError('Module has no prompt template configured');
      return;
    }

    // Don't allow generating if we're currently editing
    if (editingQuestionKey !== null) {
      setError('Please finish editing the current question before generating a new one');
      return;
    }

    setGeneratingTemplate(`${index}`);
    setError(null);

    try {
      // Only pass IDs to the service, not the full template
      const generatedQuestion = await QuestionGenerationService.generateQuestion(
        material.id,
        project.promptTemplateId,
        index,
        material.metadata?.useSourceLanguage || false
      );
      
      // Update the UI with the new question
      setGeneratedQuestions(prev => ({
        ...prev,
        [`${index}`]: generatedQuestion
      }));
      
      // Save question to database
      await QuestionGenerationService.saveGeneratedQuestion({
        ...generatedQuestion,
        metadata: {
          ...generatedQuestion.metadata,
          templateIndex: index
        }
      });
      
      // Refresh the saved questions list
      const questions = await api.getQuestions(material.id);
      setSavedQuestions(questions);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate question');
      console.error('Error generating question:', err);
    } finally {
      setGeneratingTemplate(null);
    }
  };

  const handleGenerateAllQuestions = async () => {
    if (!project?.promptTemplateId) {
      setError('Module has no prompt template configured');
      return;
    }

    if (availableTemplates.length === 0) {
      setError('No templates available for this material');
      return;
    }

    // Don't allow generating all if we're currently editing
    if (editingQuestionKey !== null) {
      setError('Please finish editing the current question before generating new questions');
      return;
    }

    setGeneratingTemplate('all');
    setError(null);

    try {
      // Generate questions for each template
      for (let i = 0; i < availableTemplates.length; i++) {
        const template = availableTemplates[i];
        
        // Simply pass the original template to the backend
        const generatedQuestion = await QuestionGenerationService.generateQuestion(
          material.id,
          project.promptTemplateId,
          i,
          material.metadata?.useSourceLanguage || false
        );
        
        // Update the UI with the new question
        setGeneratedQuestions(prev => ({
          ...prev,
          [`${i}`]: generatedQuestion
        }));
        
        // Save question to database
        await QuestionGenerationService.saveGeneratedQuestion({
          ...generatedQuestion,
          metadata: {
            ...generatedQuestion.metadata,
            templateIndex: i
          }
        });
      }
      
      // Refresh the saved questions list
      const questions = await api.getQuestions(material.id);
      setSavedQuestions(questions);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate questions');
      console.error('Error generating questions:', err);
    } finally {
      setGeneratingTemplate(null);
    }
  };

  // Get a previously generated question for a template
  const getQuestionForTemplate = (index: number): GeneratedQuestion | null => {
    // First check in the current session's generated questions
    if (generatedQuestions[`${index}`]) {
      return generatedQuestions[`${index}`];
    }
    
    // Then check in previously saved questions
    const savedQuestion = savedQuestions.find(q => 
      q.metadata?.templateIndex === index
    );
    
    return savedQuestion || null;
  };

  return (
    <div>
      {/* Confirmation Modal for Canceling Edit */}
      {showCancelConfirmation && (
        <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Discard Changes?</h5>
                <button type="button" className="btn-close" onClick={() => setShowCancelConfirmation(false)}></button>
              </div>
              <div className="modal-body">
                <p>You have unsaved changes. Are you sure you want to discard them?</p>
              </div>
              <div className="modal-footer">
                <button 
                  className="btn btn-secondary" 
                  onClick={() => setShowCancelConfirmation(false)}
                >
                  Continue Editing
                </button>
                <button 
                  className="btn btn-danger" 
                  onClick={() => {
                    resetEditingState();
                  }}
                >
                  Discard Changes
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="mb-0">Question Generator</h5>
        <div>
          {editingQuestionKey && (
            <div className="badge bg-warning text-dark me-3">
              <i className="bi bi-pencil me-1"></i>
              Editing in progress
            </div>
          )}
          <button 
            className="btn btn-primary"
            onClick={handleGenerateAllQuestions}
            disabled={generatingTemplate !== null || availableTemplates.length === 0 || editingQuestionKey !== null}
          >
            {generatingTemplate === 'all' ? (
              <>
                <span className="spinner-border spinner-border-sm me-2"></span>
                Generating All Questions...
              </>
            ) : (
              <>
                <i className="bi bi-lightning-charge-fill me-2"></i>
                Generate All Questions
              </>
            )}
          </button>
        </div>
      </div>
      
      {error && (
        <div className="alert alert-danger">
          <i className="bi bi-exclamation-triangle-fill me-2"></i>
          {error}
        </div>
      )}
      
      <div className="mb-4">
        <h6 className="mb-3">Question Templates</h6>
        {availableTemplates.length === 0 ? (
          <div className="alert alert-info">
            <i className="bi bi-info-circle me-2"></i>
            No templates available for this material. Process the material first to generate templates.
          </div>
        ) : (
          <div className="list-group">
            {availableTemplates.map((template, index) => {
              const generatedQuestion = getQuestionForTemplate(index);
              // Create a unique key for this question
              const questionKey = generatedQuestion 
                ? getQuestionKey(generatedQuestion.materialId, index) 
                : null;
              const isEditing = questionKey && editingQuestionKey === questionKey;
              
              return (
                <div key={index} className={`list-group-item ${isEditing ? 'border-primary' : ''}`}>
                  <div className="d-flex flex-column mb-3">
                    <div className="fw-bold mb-2">{template.pattern}</div>
                    <div className="d-flex align-items-center mb-2">
                      <span className="badge bg-primary me-2">{template.targetGrade}</span>
                      <span className="badge bg-secondary">{template.subject}</span>
                    </div>
                    <div className="small text-muted">
                      <strong>Constraints:</strong> {template.constraints.join(', ')}
                    </div>
                    <div className="small text-muted mt-1">
                      <strong>Learning Objectives:</strong> {template.learningObjectives?.join(', ') || 'None specified'}
                    </div>
                  </div>
                  
                  {generatedQuestion ? (
                    <div className="mb-3">
                      <div className={`card ${isEditing ? 'border-primary' : ''}`}>
                        <div className="card-header bg-light d-flex justify-content-between align-items-center">
                          <h6 className="mb-0">
                            Generated Question
                            {isEditing && (
                              <span className="badge bg-primary ms-2">Editing</span>
                            )}
                          </h6>
                          <div>
                            {isEditing ? (
                              <>
                                <button 
                                  className="btn btn-sm btn-success me-2"
                                  onClick={() => {
                                    if (generatedQuestion.questionId) {
                                      handleSaveEditedQuestion(generatedQuestion.questionId);
                                    } else {
                                      console.error('Question ID is undefined');
                                    }
                                  }}
                                >
                                  <i className="bi bi-check me-1"></i>
                                  Save
                                </button>
                                <button 
                                  className="btn btn-sm btn-outline-secondary"
                                  onClick={handleCancelEdit}
                                >
                                  <i className="bi bi-x me-1"></i>
                                  Cancel
                                </button>
                              </>
                            ) : (
                              <>
                                <button 
                                  className="btn btn-sm btn-outline-primary me-2"
                                  onClick={() => handleGenerateQuestion(template, index)}
                                  disabled={generatingTemplate !== null || editingQuestionKey !== null}
                                >
                                  <i className="bi bi-arrow-repeat me-1"></i>
                                  Regenerate
                                </button>
                                <button 
                                  className="btn btn-sm btn-outline-secondary me-2"
                                  onClick={() => {
                                    if (questionKey && generatedQuestion) {
                                      handleEditQuestion(generatedQuestion, questionKey);
                                    }
                                  }}
                                  disabled={editingQuestionKey !== null && editingQuestionKey !== questionKey}
                                >
                                  <i className="bi bi-pencil me-1"></i>
                                  Edit
                                </button>
                                <button 
                                  className="btn btn-sm btn-outline-success"
                                  onClick={() => {
                                    navigator.clipboard.writeText(generatedQuestion.question);
                                    alert('Question copied to clipboard');
                                  }}
                                >
                                  <i className="bi bi-clipboard me-1"></i>
                                  Copy
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                        <div className="card-body">
                          <div>
                            <h6>Question:</h6>
                            {isEditing ? (
                              <textarea
                                className="form-control mb-3"
                                value={editedQuestionText}
                                onChange={(e) => {
                                  setEditedQuestionText(e.target.value);
                                  setHasUnsavedChanges(true);
                                }}
                                rows={4}
                              />
                            ) : (
                              <p className="card-text">{generatedQuestion.question}</p>
                            )}
                          </div>
                          
                          {(generatedQuestion.rubric?.validationChecks || isEditing) && (
                            <div className="mt-3">
                              <h6>Rubric:</h6>
                              {isEditing ? (
                                <div className="mb-3">
                                  {editedRubricChecks.map((check, idx) => (
                                    <div key={idx} className="input-group mb-2">
                                      <input
                                        type="text"
                                        className="form-control form-control-sm"
                                        value={check}
                                        onChange={(e) => {
                                          const updated = [...editedRubricChecks];
                                          updated[idx] = e.target.value;
                                          setEditedRubricChecks(updated);
                                          setHasUnsavedChanges(true);
                                        }}
                                      />
                                      <button
                                        className="btn btn-sm btn-outline-danger"
                                        onClick={() => {
                                          const updated = editedRubricChecks.filter((_, i) => i !== idx);
                                          setEditedRubricChecks(updated);
                                          setHasUnsavedChanges(true);
                                        }}
                                      >
                                        <i className="bi bi-trash"></i>
                                      </button>
                                    </div>
                                  ))}
                                  <button
                                    className="btn btn-sm btn-outline-primary"
                                    onClick={() => {
                                      setEditedRubricChecks([...editedRubricChecks, '']);
                                      setHasUnsavedChanges(true);
                                    }}
                                  >
                                    <i className="bi bi-plus"></i> Add Criterion
                                  </button>
                                </div>
                              ) : (
                                <ul className="list-group list-group-flush">
                                  {Array.isArray(generatedQuestion.rubric?.validationChecks) ? 
                                    generatedQuestion.rubric.validationChecks.map((check: string, idx: number) => (
                                      <li key={idx} className="list-group-item py-1 small">{check}</li>
                                    )) : 
                                    <li className="list-group-item py-1 small">No validation checks available</li>
                                  }
                                </ul>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="d-grid">
                      <button 
                        className="btn btn-outline-primary"
                        onClick={() => handleGenerateQuestion(template, index)}
                        disabled={generatingTemplate !== null || editingQuestionKey !== null}
                      >
                        {generatingTemplate === `${index}` ? (
                          <>
                            <span className="spinner-border spinner-border-sm me-2"></span>
                            Generating...
                          </>
                        ) : (
                          <>
                            <i className="bi bi-lightning-charge me-2"></i>
                            Generate Question
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};