import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';
import { PromptTemplate } from '../../types';
import DOMPurify from 'dompurify';

interface Props {
  onClose: () => void;
  onSuccess: () => void;
  classroom_id?: string;
}

export const ProjectForm: React.FC<Props> = ({ onClose, onSuccess, classroom_id }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [promptTemplates, setPromptTemplates] = useState<PromptTemplate[]>([]);
  
  const [formData, setFormData] = useState({
    name: '',
    classroomId: '',
    description: '',
    modelName: 'Llama 3.2 3B', // Default model
    promptTemplateId: '',
    configuration: {
      language: 'English',
      gradeLevel: '',
      subject: ''
    }
  });

  useEffect(() => {
    // Load prompt templates
    api.getPromptTemplates()
      .then(templates => setPromptTemplates(templates))
      .catch(err => setError('Failed to load prompt templates'));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const projectData = {
        name: DOMPurify.sanitize(formData.name),
        classroomId: classroom_id,
        description: DOMPurify.sanitize(formData.description),
        modelName: formData.modelName,
        promptTemplateId: DOMPurify.sanitize(formData.promptTemplateId),
        configuration:{
          language: formData.configuration.language,
          gradeLevel: DOMPurify.sanitize(formData.configuration.gradeLevel),
          subject: DOMPurify.sanitize(formData.configuration.subject)
        }
      }

      await api.createProject(projectData);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <h5 className="mb-0">Create New Module</h5>
      </div>
      <div className="card-body">
        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="form-label">Module Name</label>
            <input
              type="text"
              className="form-control"
              value={formData.name}
              onChange={e => setFormData({...formData, name: e.target.value})}
              required
            />
          </div>

          <div className="mb-3">
            <label className="form-label">Description</label>
            <textarea
              className="form-control"
              value={formData.description}
              onChange={e => setFormData({...formData, description: e.target.value})}
              rows={2}
            />
          </div>

          <div className="row">
            <div className="col-md-4">
              <div className="mb-3">
                <label className="form-label">Model</label>
                <select 
                  className="form-select"
                  value={formData.modelName}
                  onChange={e => setFormData({...formData, modelName: e.target.value})}
                  required
                >
                  <option value="Llama 3.2 3B">Llama 3.2 3B</option>
                  <option value="Llama 3.2 7B">Llama 3.2 7B</option>
                </select>
              </div>
            </div>
            <div className="col-md-4">
              <div className="mb-3">
                <label className="form-label">Language</label>
                <select
                  className="form-select"
                  value={formData.configuration.language}
                  onChange={e => setFormData({
                    ...formData,
                    configuration: {
                      ...formData.configuration,
                      language: e.target.value
                    }
                  })}
                  required
                >
                  <option value="English">English</option>
                  <option value="Indonesian">Indonesian</option>
                </select>
              </div>
            </div>
            <div className="col-md-4">
              <div className="mb-3">
                <label className="form-label">Subject</label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.configuration.subject}
                  onChange={e => setFormData({
                    ...formData,
                    configuration: {
                      ...formData.configuration,
                      subject: e.target.value
                    }
                  })}
                  placeholder="e.g., English"
                  required
                />
              </div>
            </div>
          </div>

          <div className="mb-3">
            <label className="form-label">Grade Level</label>
            <input
              type="text"
              className="form-control"
              value={formData.configuration.gradeLevel}
              onChange={e => setFormData({
                ...formData,
                configuration: {
                  ...formData.configuration,
                  gradeLevel: e.target.value
                }
              })}
              placeholder="e.g., 5th Grade"
              required
            />
          </div>

          <div className="mb-3">
            <label className="form-label">Prompt Template</label>
            {promptTemplates.length > 0 ? (
              <select 
                className="form-select"
                value={formData.promptTemplateId}
                onChange={e => setFormData({...formData, promptTemplateId: e.target.value})}
                required
              >
                <option value="">Select template...</option>
                {promptTemplates.map(template => (
                  <option key={template.id} value={template.id}>
                    {template.name} (v{template.version})
                  </option>
                ))}
              </select>
            ) : (
              <div className="alert alert-warning">
                <i className="bi bi-exclamation-triangle me-2"></i>
                No prompt templates available. Please create one first.
              </div>
            )}
          </div>

          {error && (
            <div className="alert alert-danger">
              <i className="bi bi-exclamation-triangle me-2"></i>
              {error}
            </div>
          )}

          <div className="d-flex justify-content-end gap-2">
            <button 
              type="button" 
              className="btn btn-light"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" />
                  Creating...
                </>
              ) : (
                <>
                  <i className="bi bi-check-circle me-2"></i>
                  Create Module
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}; 