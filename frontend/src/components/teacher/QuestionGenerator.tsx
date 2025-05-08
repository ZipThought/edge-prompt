import React, { useState, useEffect } from 'react';
import { Material } from '../../types';
import { GeneratedQuestion } from '../../types/edgeprompt';
import { api } from '../../services/api';
import { useProject } from '../../contexts/ProjectContext';
import { Project, PromptTemplate } from '../../types';
import { QuestionGenerationService } from '../../services/QuestionGenerationService';
import { useQuestions } from '../../contexts/QuestionContext';

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
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null);
  const [editedQuestionText, setEditedQuestionText] = useState<string>('');
  const [editingRubric, setEditingRubric] = useState<boolean>(false);
  const [editedRubricItems, setEditedRubricItems] = useState<string[]>([]);
  const [isPosting, setIsPosting] = useState(false);
  const [selectedQuestions, setSelectedQuestions] = useState<Set<string>>(new Set());

  // Uncomment if using context for questions
  // const { 
  //   questions, 
  //   loading, 
  //   error, 
  //   selectedQuestions,
  //   editingQuestionId,
  //   generateQuestion,
  //   saveQuestion,
  //   deleteQuestion,
  //   toggleQuestionSelection,
  //   setEditingQuestion,
  //   postQuestionsToStudents
  // } = useQuestions();
  
  // // Local state for editing
  // const [editedQuestionText, setEditedQuestionText] = useState('');
  // const [editedRubricItems, setEditedRubricItems] = useState<string[]>([]);
  
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

  const handleGenerateQuestion = async (template: any, index: number) => {
    if (!project?.promptTemplateId) {
      setError('Module has no prompt template configured');
      return;
    }
  
    setGeneratingTemplate(`${index}`);
    setError(null);
  
    try {
      // Find existing question for this template index
      const existingQuestion = savedQuestions.find(q => 
        q.metadata?.templateIndex === index
      );
      
      // If we found an existing question, delete it first
      if (existingQuestion && existingQuestion.id) {
        await api.deleteQuestion(existingQuestion.id);
      }
      
      // Generate a new question
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
  
    setGeneratingTemplate('all');
    setError(null);
  
    try {
      // Store generated questions to update UI state at once
      const newGeneratedQuestions: {[templateIndex: string]: GeneratedQuestion} = {};
      
      // Generate questions for each template
      for (let i = 0; i < availableTemplates.length; i++) {
        // Generate a new question for this template
        const generatedQuestion = await QuestionGenerationService.generateQuestion(
          material.id,
          project.promptTemplateId,
          i,
          material.metadata?.useSourceLanguage || false
        );
        
        // Store for UI update
        newGeneratedQuestions[`${i}`] = generatedQuestion;
        
        // Save question to database
        await QuestionGenerationService.saveGeneratedQuestion({
          ...generatedQuestion,
          metadata: {
            ...generatedQuestion.metadata,
            templateIndex: i
          }
        });
      }
      
      // Update UI with all generated questions at once
      setGeneratedQuestions(newGeneratedQuestions);
      
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

  // Add function to handle edit mode toggle
  const handleEditQuestion = (question: GeneratedQuestion) => {
    setEditingQuestionId(question.id);
    setEditedQuestionText(question.question);

    // Initialize rubric editing state
    if (question.rubric && question.rubric.validationChecks) {
      const checks = Array.isArray(question.rubric.validationChecks) 
        ? question.rubric.validationChecks 
        : Object.values(question.rubric.validationChecks);
      setEditedRubricItems(checks.map((check: string | number) => String(check)));
    } else {
      setEditedRubricItems([]);
    }
  };

  // Add function to cancel edit mode
  const handleCancelEdit = () => {
    setEditingQuestionId(null);
    setEditedQuestionText('');
    setEditingRubric(false);
    setEditedRubricItems([]);
  };

  const handleSaveEdit = async (questionId: string) => {
    if (!editedQuestionText.trim()) return;
    
    try {
      // Create the updated rubric structure
      const updatedRubric = {
        ...generatedQuestions[questionId]?.rubric,
        validationChecks: editedRubricItems.filter(item => item.trim())
      };
      
      // Call API to update the question
      await api.updateQuestion(questionId, editedQuestionText, updatedRubric);
      
      // Update local state
      const updatedQuestion = {
        ...generatedQuestions[questionId],
        question: editedQuestionText,
        rubric: updatedRubric
      };
      
      // Update the questions in state
      setGeneratedQuestions(prev => ({
        ...prev,
        [questionId]: updatedQuestion
      }));
      
      // Also update in the saved questions list if it exists there
      const updatedSavedQuestions = savedQuestions.map(q => 
        q.id === questionId ? updatedQuestion : q
      );
      setSavedQuestions(updatedSavedQuestions);
      
      // Exit edit mode
      handleCancelEdit();
      
      // Show success message
      // Here we could add a notification system, but for simplicity:
      alert('Question updated successfully');
      
    } catch (error) {
      console.error('Error updating question:', error);
      setError(error instanceof Error ? error.message : 'Failed to update question');
    }
  };

  // Toggle question selection for posting
  const toggleQuestionSelection = (questionId: string) => {
    setSelectedQuestions(prev => {
      const newSelection = new Set(prev);
      if (newSelection.has(questionId)) {
        newSelection.delete(questionId);
      } else {
        newSelection.add(questionId);
      }
      return newSelection;
    });
  };

  // Handle posting questions to students
  const handlePostToStudents = async () => {
    if (selectedQuestions.size === 0) {
      alert('Please select at least one question to post');
      return;
    }
    
    setIsPosting(true);
    
    try {
      // Call API to post questions to students
      await api.postQuestionsToStudents(Array.from(selectedQuestions));
      
      // Reset selection and show success message
      setSelectedQuestions(new Set());
      alert('Questions have been posted to students successfully');
      
    } catch (error) {
      console.error('Error posting questions:', error);
      setError(error instanceof Error ? error.message : 'Failed to post questions');
    } finally {
      setIsPosting(false);
    }
  };

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="mb-0">Question Generator</h5>
        <button 
          className="btn btn-primary"
          onClick={handleGenerateAllQuestions}
          disabled={generatingTemplate !== null || availableTemplates.length === 0}
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
              
              return (
                <div key={index} className="list-group-item">
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
                      <div className="card">
                        <div className="card-header bg-light d-flex justify-content-between align-items-center">
                          <div className="d-flex align-items-center">
                            <div className="form-check me-2">
                              <input 
                                className="form-check-input" 
                                type="checkbox" 
                                checked={selectedQuestions.has(generatedQuestion.id)}
                                onChange={() => toggleQuestionSelection(generatedQuestion.id)}
                                id={`question-select-${generatedQuestion.id}`}
                              />
                              <label className="form-check-label visually-hidden" htmlFor={`question-select-${generatedQuestion.id}`}>
                                Select question
                              </label>
                            </div>
                            <h6 className="mb-0">Generated Question</h6>
                          </div>
                          <div>
                            {editingQuestionId === generatedQuestion.id ? (
                              <>
                                <button 
                                  className="btn btn-sm btn-success me-2"
                                  onClick={() => handleSaveEdit(generatedQuestion.id)}
                                  disabled={!editedQuestionText.trim()}
                                >
                                  <i className="bi bi-check me-1"></i>
                                  Save
                                </button>
                                <button 
                                  className="btn btn-sm btn-outline-secondary me-2"
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
                                  onClick={() => handleEditQuestion(generatedQuestion)}
                                >
                                  <i className="bi bi-pencil me-1"></i>
                                  Edit
                                </button>
                                <button 
                                  className="btn btn-sm btn-outline-primary me-2"
                                  onClick={() => handleGenerateQuestion(template, index)}
                                  disabled={generatingTemplate !== null}
                                >
                                  <i className="bi bi-arrow-repeat me-1"></i>
                                  Regenerate
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
                            {editingQuestionId === generatedQuestion.id ? (
                              <textarea
                                className="form-control mb-3"
                                value={editedQuestionText}
                                onChange={(e) => setEditedQuestionText(e.target.value)}
                                rows={5}
                              />
                            ) : (
                              <p className="card-text">{generatedQuestion.question}</p>
                            )}
                          </div>
                          
                          {generatedQuestion.rubric && (
                            <div className="mt-3">
                              <div className="d-flex justify-content-between align-items-center mb-2">
                                <h6 className="mb-0">Rubric:</h6>
                                {editingQuestionId === generatedQuestion.id && !editingRubric && (
                                  <button 
                                    className="btn btn-sm btn-outline-primary"
                                    onClick={() => setEditingRubric(true)}
                                  >
                                    <i className="bi bi-pencil me-1"></i>
                                    Edit Rubric
                                  </button>
                                )}
                              </div>
                              {editingQuestionId === generatedQuestion.id && editingRubric ? (
                                <div className="mb-3">
                                  {editedRubricItems.map((item, idx) => (
                                    <div key={idx} className="input-group mb-2">
                                      <input 
                                        type="text" 
                                        className="form-control"
                                        value={item}
                                        onChange={(e) => {
                                          const newItems = [...editedRubricItems];
                                          newItems[idx] = e.target.value;
                                          setEditedRubricItems(newItems);
                                        }}
                                      />
                                      <button 
                                        className="btn btn-outline-danger"
                                        onClick={() => {
                                          const newItems = [...editedRubricItems];
                                          newItems.splice(idx, 1);
                                          setEditedRubricItems(newItems);
                                        }}
                                      >
                                        <i className="bi bi-trash"></i>
                                      </button>
                                    </div>
                                  ))}
                                  <button 
                                    className="btn btn-sm btn-outline-primary"
                                    onClick={() => setEditedRubricItems([...editedRubricItems, ''])}
                                  >
                                    <i className="bi bi-plus-circle me-1"></i>
                                    Add Criteria
                                  </button>
                                </div>
                              ) : (
                                <ul className="list-group list-group-flush">
                                  {generatedQuestion.rubric.validationChecks && 
                                   (Array.isArray(generatedQuestion.rubric.validationChecks) ? 
                                     generatedQuestion.rubric.validationChecks : 
                                     Object.values(generatedQuestion.rubric.validationChecks)
                                   ).map((check: string, idx: number) => (
                                     <li key={idx} className="list-group-item py-1 small">{check}</li>
                                   ))}
                                </ul>
                              )}
                            </div>
                          )}

                          {savedQuestions.length > 0 && (
                            <div className="mt-4 d-flex justify-content-between">
                              <div>
                                <span className="me-2">Selected: {selectedQuestions.size}/{savedQuestions.length}</span>
                                <button 
                                  className="btn btn-sm btn-outline-secondary"
                                  onClick={() => setSelectedQuestions(new Set())}
                                  disabled={selectedQuestions.size === 0}
                                >
                                  Clear Selection
                                </button>
                              </div>
                              <button 
                                className="btn btn-primary"
                                onClick={handlePostToStudents}
                                disabled={isPosting || selectedQuestions.size === 0}
                              >
                                {isPosting ? (
                                  <>
                                    <span className="spinner-border spinner-border-sm me-2"></span>
                                    Posting...
                                  </>
                                ) : (
                                  <>
                                    <i className="bi bi-send-fill me-2"></i>
                                    Post Selected Questions to Students
                                  </>
                                )}
                              </button>
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
                        disabled={generatingTemplate !== null}
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