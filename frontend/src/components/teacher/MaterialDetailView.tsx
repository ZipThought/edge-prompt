import React, { useState, useEffect, useRef } from 'react';
import { Material } from '../../types';
import { api } from '../../services/api';
import { Project, PromptTemplate } from '../../types';
import { QuestionGenerator } from './QuestionGenerator';

interface Props {
  project: Project | null;
  materialId: string;
  onBack: () => void;
  onRefresh: () => void;
}

export const MaterialDetailView: React.FC<Props> = ({ project, materialId, onBack, onRefresh }) => {
  const [material, setMaterial] = useState<Material | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'content' | 'objectives' | 'templates' | 'questions'>('content');
  
  // State for content editing
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  
  // State for title editing
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editedTitle, setEditedTitle] = useState('');
  const [isSavingTitle, setIsSavingTitle] = useState(false);
  
  // State for file re-upload
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const loadMaterial = async () => {
      setLoading(true);
      try {
        const materialData = await api.getMaterial(materialId);
        setMaterial(materialData);
        setEditedContent(materialData.content);
        setEditedTitle(materialData.title || 'Untitled Material');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load material');
      } finally {
        setLoading(false);
      }
    };

    loadMaterial();
  }, [materialId]);

  const handleSaveContent = async () => {
    if (!material) return;
    
    setIsSaving(true);
    try {
      await api.updateMaterialContent(material.id, editedContent);
      
      // Update the local state
      setMaterial({
        ...material,
        content: editedContent
      });
      
      setIsEditing(false);
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save content');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveTitle = async () => {
    if (!material) return;
    
    setIsSavingTitle(true);
    try {
      await api.updateMaterialTitle(material.id, editedTitle);
      
      // Update the local state
      setMaterial({
        ...material,
        title: editedTitle
      });
      
      setIsEditingTitle(false);
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save title');
    } finally {
      setIsSavingTitle(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleReprocess = async () => {
    if (!material || !selectedFile) return;
    
    setIsReprocessing(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      
      const result = await api.reprocessMaterial(material.id, formData);
      
      // Update the local state with reprocessed content
      setMaterial({
        ...material,
        content: result.content,
        metadata: {
          ...material.metadata,
          learningObjectives: result.objectives,
          templates: result.templates,
          wordCount: result.wordCount,
          processedAt: new Date().toISOString()
        }
      });
      
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reprocess material');
    } finally {
      setIsReprocessing(false);
    }
  };

  const handleDelete = async () => {
    if (!material || !window.confirm('Are you sure you want to delete this material?')) {
      return;
    }
    
    try {
      await api.deleteMaterial(material.id);
      onBack();
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete material');
    }
  };

  const handleGenerateQuestions = () => {
    setActiveTab('questions');
  };

  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
        <p className="mt-3">Loading material...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-danger">
        <h4 className="alert-heading">Error</h4>
        <p>{error}</p>
        <button className="btn btn-outline-danger" onClick={onBack}>
          <i className="bi bi-arrow-left me-2"></i>Back
        </button>
      </div>
    );
  }

  if (!material) {
    return (
      <div className="alert alert-warning">
        <h4 className="alert-heading">Material Not Found</h4>
        <p>The material you're looking for could not be found.</p>
        <button className="btn btn-outline-warning" onClick={onBack}>
          <i className="bi bi-arrow-left me-2"></i>Back
        </button>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header bg-light">
        <div className="d-flex justify-content-between align-items-center">
          <div className="d-flex align-items-center">
            <button className="btn btn-sm btn-outline-secondary me-2" onClick={onBack}>
              <i className="bi bi-arrow-left"></i>
            </button>
            
            {isEditingTitle ? (
              <div className="input-group" style={{ maxWidth: '400px' }}>
                <input
                  type="text"
                  className="form-control form-control-sm"
                  value={editedTitle}
                  onChange={(e) => setEditedTitle(e.target.value)}
                  autoFocus
                />
                <button 
                  className="btn btn-sm btn-success" 
                  onClick={handleSaveTitle}
                  disabled={isSavingTitle || !editedTitle.trim()}
                >
                  {isSavingTitle ? (
                    <span className="spinner-border spinner-border-sm" role="status"></span>
                  ) : (
                    <i className="bi bi-check"></i>
                  )}
                </button>
                <button 
                  className="btn btn-sm btn-outline-secondary" 
                  onClick={() => {
                    setIsEditingTitle(false);
                    setEditedTitle(material.title || 'Untitled Material');
                  }}
                  disabled={isSavingTitle}
                >
                  <i className="bi bi-x"></i>
                </button>
              </div>
            ) : (
              <div className="d-flex align-items-center">
                <span className="h5 mb-0">{material.title || 'Untitled Material'}</span>
                <button 
                  className="btn btn-sm btn-link text-muted" 
                  onClick={() => setIsEditingTitle(true)}
                  title="Edit title"
                >
                  <i className="bi bi-pencil-fill"></i>
                </button>
                <span className={`badge bg-${getBadgeColor(material.status)} ms-2`}>
                  {material.status}
                </span>
              </div>
            )}
          </div>
          
          <div>
            {activeTab !== 'questions' && (
              <button
                className="btn btn-primary"
                onClick={handleGenerateQuestions}
              >
                <i className="bi bi-lightning-charge me-1"></i>
                Generate Questions
              </button>
            )}
          </div>
        </div>
      </div>

      <ul className="nav nav-tabs mb-3">
        <li className="nav-item">
          <button 
            className={`nav-link ${activeTab === 'content' ? 'active' : ''}`}
            onClick={() => setActiveTab('content')}
          >
            <i className="bi bi-file-text me-1"></i> Content
          </button>
        </li>
        <li className="nav-item">
          <button 
            className={`nav-link ${activeTab === 'objectives' ? 'active' : ''}`}
            onClick={() => setActiveTab('objectives')}
          >
            <i className="bi bi-bullseye me-1"></i> Learning Objectives 
            {(material.metadata?.learningObjectives?.length ?? 0) > 0 && (
              <span className="ms-1">({material.metadata?.learningObjectives?.length})</span>
            )}
          </button>
        </li>
        <li className="nav-item">
          <button 
            className={`nav-link ${activeTab === 'templates' ? 'active' : ''}`}
            onClick={() => setActiveTab('templates')}
          >
            <i className="bi bi-grid me-1"></i> Templates 
            {(material.metadata?.templates?.length ?? 0) > 0 && (
              <span className="ms-1">({material.metadata?.templates?.length})</span>
            )}
          </button>
        </li>
        <li className="nav-item">
          <button 
            className={`nav-link ${activeTab === 'questions' ? 'active' : ''}`}
            onClick={() => setActiveTab('questions')}
          >
            <i className="bi bi-question-circle me-1"></i> Questions
          </button>
        </li>
      </ul>

      <div className="card-body">
        {activeTab === 'content' && (
          <div>
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h5 className="mb-0">Material Content</h5>
              <div>
                {isEditing ? (
                  <>
                    <button 
                      className="btn btn-sm btn-success me-2" 
                      onClick={handleSaveContent}
                      disabled={isSaving}
                    >
                      {isSaving ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-1"></span>
                          Saving...
                        </>
                      ) : (
                        <>
                          <i className="bi bi-check-lg me-1"></i>
                          Save
                        </>
                      )}
                    </button>
                    <button 
                      className="btn btn-sm btn-outline-secondary" 
                      onClick={() => {
                        setIsEditing(false);
                        setEditedContent(material.content);
                      }}
                      disabled={isSaving}
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <button 
                    className="btn btn-sm btn-outline-primary"
                    onClick={() => setIsEditing(true)}
                  >
                    <i className="bi bi-pencil me-1"></i>
                    Edit
                  </button>
                )}
              </div>
            </div>
            
            {/* File re-upload section */}
            <div className="mb-3 border p-3 rounded bg-light">
              <div className="d-flex align-items-center">
                <div className="flex-grow-1">
                  <label className="form-label mb-0">Update material file</label>
                  <div className="input-group">
                    <input 
                      ref={fileInputRef}
                      type="file" 
                      className="form-control form-control-sm" 
                      onChange={handleFileChange}
                      accept=".pdf,.docx,.doc,.md,.txt"
                    />
                    <button 
                      className="btn btn-primary btn-sm" 
                      onClick={handleReprocess}
                      disabled={!selectedFile || isReprocessing}
                    >
                      {isReprocessing ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-1"></span>
                          Processing...
                        </>
                      ) : (
                        <>
                          <i className="bi bi-arrow-repeat me-1"></i>
                          Reprocess
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
              <small className="text-muted">Upload a new file to replace and reprocess the content</small>
            </div>
            
            {isEditing ? (
              <textarea
                className="form-control font-monospace"
                style={{ 
                  height: '500px', 
                  fontSize: '0.9rem',
                  whiteSpace: 'pre-wrap'
                }}
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
              />
            ) : (
              <div 
                className="p-3 bg-light rounded border" 
                style={{ 
                  maxHeight: '500px', 
                  overflow: 'auto'
                }}
              >
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.9em' }}>
                  {material.content}
                </pre>
              </div>
            )}
            
            <div className="mt-3">
              <div className="row">
                <div className="col-md-3">
                  <div className="mb-3">
                    <span className="text-muted">Focus Area:</span>
                    <div className="fw-bold">{material.focusArea}</div>
                  </div>
                </div>
                <div className="col-md-3">
                  <div className="mb-3">
                    <span className="text-muted">Word Count:</span>
                    <div className="fw-bold">{material.metadata?.wordCount || 'N/A'}</div>
                  </div>
                </div>
                <div className="col-md-3">
                  <div className="mb-3">
                    <span className="text-muted">Subject:</span>
                    <div className="fw-bold">{material.metadata?.subject || 'N/A'}</div>
                  </div>
                </div>
                <div className="col-md-3">
                  <div className="mb-3">
                    <span className="text-muted">Grade Level:</span>
                    <div className="fw-bold">{material.metadata?.grade || 'N/A'}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'objectives' && (
          <div>
            <h5 className="mb-3">Learning Objectives</h5>
            <div className="list-group">
              {material.metadata?.learningObjectives?.length ? (
                material.metadata.learningObjectives.map((objective, index) => (
                  <div key={index} className="list-group-item">
                    {objective}
                  </div>
                ))
              ) : (
                <div className="alert alert-info">No learning objectives found.</div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'templates' && (
          <div>
            <h5 className="mb-3">Question Templates</h5>
            <div className="list-group">
              {material.metadata?.templates?.length ? (
                material.metadata.templates.map((template, index) => (
                  <div key={index} className="list-group-item">
                    <div className="mb-1 fw-bold">{template.pattern}</div>
                    <div className="mb-2">
                      <span className="badge bg-primary me-1">{template.targetGrade}</span>
                      <span className="badge bg-secondary">{template.subject}</span>
                    </div>
                    <div className="small text-muted mb-2">Constraints:</div>
                    <ul className="mb-0 ps-3">
                      {template.constraints.map((constraint, cIdx) => (
                        <li key={cIdx}><small>{constraint}</small></li>
                      ))}
                    </ul>
                  </div>
                ))
              ) : (
                <div className="alert alert-info">No templates found.</div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'questions' && project && (
          <QuestionGenerator 
          project={project}
          material={material} />
        )}
      </div>

      <div className="card-footer bg-light d-flex justify-content-between">
        <button className="btn btn-sm btn-outline-danger" onClick={handleDelete}>
          <i className="bi bi-trash me-1"></i> Delete Material
        </button>
        <small className="text-muted align-self-center">
          Created: {new Date(material.createdAt).toLocaleString()}
        </small>
      </div>
    </div>
  );
};

function getBadgeColor(status: string): string {
  switch (status) {
    case 'completed': return 'success';
    case 'pending': return 'warning';
    case 'processing': return 'primary';
    case 'error': return 'danger';
    default: return 'secondary';
  }
} 