import React, { useState, useEffect, useCallback } from 'react';
import { Project, Material } from '../../types';
import { api } from '../../services/api';
import { ProjectEditForm } from './ProjectEditForm';
import { useProject } from '../../contexts/ProjectContext';
import { MaterialDetailView } from '../teacher/MaterialDetailView';

interface Props {
  project: Project;
  onUpdate: () => void;
}

export const ProjectView: React.FC<Props> = ({ project, onUpdate }) => {
  const { promptTemplates } = useProject();
  const [isEditing, setIsEditing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedMaterialId, setSelectedMaterialId] = useState<string | null>(null);

  // Extract loadMaterials as a separate function outside useEffect
  const loadMaterials = useCallback(async () => {
    if (!project.id) return;
    
    setIsLoading(true);
    try {
      const projectMaterials = await api.getMaterials(project.id);
      setMaterials(projectMaterials);
    } catch (error) {
      console.error('Error loading materials:', error);
    } finally {
      setIsLoading(false);
    }
  }, [project.id]);

  // Load materials when the component mounts or project changes
  useEffect(() => {
    loadMaterials();
  }, [loadMaterials]);

  // Get the current template
  const currentTemplate = project.promptTemplateId ? 
    promptTemplates.find(t => t.id === project.promptTemplateId) : 
    null;

  const configuration = typeof project.configuration === 'string' 
    ? JSON.parse(project.configuration) 
    : project.configuration;

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this project?')) {
      return;
    }

    setIsDeleting(true);
    try {
      await api.deleteProject(project.id);
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete project');
    } finally {
      setIsDeleting(false);
    }
  };

  // If a material is selected, show its detail view
  if (selectedMaterialId) {
    return (
      <MaterialDetailView 
        project={project}
        materialId={selectedMaterialId} 
        onBack={() => setSelectedMaterialId(null)} 
        onRefresh={() => loadMaterials()}
      />
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <div className="d-flex justify-content-between align-items-center">
          <div>
            <h5 className="mb-0">{project.name}</h5>
            <small className="text-muted">{project.description}</small>
          </div>
          <div>
            <button 
              className="btn btn-sm btn-outline-primary me-2"
              onClick={() => setIsEditing(true)}
            >
              <i className="bi bi-pencil me-1"></i>
            </button>
            <button 
              className="btn btn-sm btn-outline-danger"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              <i className="bi bi-trash"></i>
            </button>
          </div>
        </div>
      </div>

      <div className="list-group list-group-flush">
        <div className="list-group-item">
          <div className="row">
            <div className="col-xxl-4 mb-3">
              <small className="text-muted d-block">Model</small>
              <strong>{project.modelName}</strong>
            </div>
            <div className="col-xxl-4 mb-3">
              <small className="text-muted d-block">Language</small>
              <strong>{configuration.language}</strong>
            </div>
            <div className="col-xxl-4 mb-3">
              <small className="text-muted d-block">Subject</small>
              <strong>{configuration.subject}</strong>
            </div>
          </div>
        </div>

        <div className="list-group-item">
          <div className="row">
            <div className="col-xxl-6 mb-3">
              <small className="text-muted d-block">Grade Level</small>
              <strong>{configuration.gradeLevel}</strong>
            </div>
            <div className="col-xxl-6 mb-3">
              <small className="text-muted d-block">Prompt Template</small>
              {currentTemplate ? (
                <div>
                  <strong>{currentTemplate.name}</strong>
                  <small className="text-muted ms-2">v{currentTemplate.version}</small>
                </div>
              ) : (
                <div className="text-danger">
                  <i className="bi bi-exclamation-triangle me-1"></i>
                  Template not found
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="card-footer">
          <div className="alert alert-danger mb-0">
            <i className="bi bi-exclamation-triangle me-2"></i>
            {error}
          </div>
        </div>
      )}

      {isEditing && (
        <ProjectEditForm
          project={project}
          onClose={() => setIsEditing(false)}
          onSuccess={() => {
            setIsEditing(false);
            onUpdate();
          }}
        />
      )}

      <div className="card mt-4">
        <div className="card-header">
          <h5 className="mb-0">Materials</h5>
        </div>
        <div className="card-body">
          {isLoading ? (
            <div className="text-center py-3">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
              <p className="mt-2">Loading materials...</p>
            </div>
          ) : materials.length === 0 ? (
            <div className="text-center py-3">
              <p className="text-muted">No materials found for this project.</p>
              <button 
                className="btn btn-outline-primary"
                onClick={() => window.location.hash = '#content-generator'}
              >
                <i className="bi bi-plus-circle me-2"></i>
                Add Material
              </button>
            </div>
          ) : (
            <div className="list-group">
              {materials.map(material => (
                <div 
                  key={material.id} 
                  className="list-group-item list-group-item-action"
                  onClick={() => setSelectedMaterialId(material.id)}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="d-flex w-100 justify-content-between">
                    <h5 className="mb-1">{material.title}</h5>
                    <small>
                      <span className={`badge bg-${getBadgeColor(material.status)}`}>
                        {material.status}
                      </span>
                    </small>
                  </div>
                  <p className="mb-1 text-truncate">{material.focusArea}</p>
                  <small className="text-muted">
                    Word count: {material.metadata?.wordCount || 'N/A'} • 
                    Learning objectives: {material.metadata?.learningObjectives?.length || 0}
                  </small>
                </div>
              ))}
            </div>
          )}
        </div>
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