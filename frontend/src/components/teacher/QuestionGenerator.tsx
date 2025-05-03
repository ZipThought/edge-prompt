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
    console.log('Active project:', activeProject);
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
                          <h6 className="mb-0">Generated Question</h6>
                          <div>
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
                          </div>
                        </div>
                        <div className="card-body">
                          <div>
                            <h6>Question:</h6>
                            <p className="card-text">{generatedQuestion.question}</p>
                          </div>
                          
                          {generatedQuestion.rubric && generatedQuestion.rubric.validationChecks && Array.isArray(generatedQuestion.rubric.validationChecks) && (
                            <div className="mt-3">
                              <h6>Rubric:</h6>
                              <ul className="list-group list-group-flush">
                                {generatedQuestion.rubric.validationChecks.map((check: string, idx: number) => (
                                  <li key={idx} className="list-group-item py-1 small">{check}</li>
                                ))}
                              </ul>
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