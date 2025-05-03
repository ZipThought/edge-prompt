import React, { useState, useEffect } from 'react';
import { Material } from '../../types';
import { api } from '../../services/api';
import { useProject } from '../../contexts/ProjectContext';
import { SimplifiedMaterialUploader } from './SimplifiedMaterialUploader';
import { MaterialDetailView } from './MaterialDetailView';

export const MaterialsManager: React.FC = () => {
  const { activeProject } = useProject();
  const [materials, setMaterials] = useState<Material[]>([]);
  const [selectedMaterialId, setSelectedMaterialId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadMaterials = async () => {
    if (!activeProject) return;
    
    setIsLoading(true);
    setError(null);
    try {
      const projectMaterials = await api.getMaterials(activeProject.id);
      setMaterials(projectMaterials);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load materials');
      console.error('Error loading materials:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMaterials();
  }, [activeProject]);

  if (!activeProject) {
    return (
      <div className="alert alert-warning">
        <i className="bi bi-exclamation-triangle-fill me-2"></i>
        Please select a project to manage materials
      </div>
    );
  }

  return (
    <div className="row">
      {/* Left Sidebar */}
      <div className="col-md-3">
        <SimplifiedMaterialUploader onMaterialUploaded={loadMaterials} />
        
        <div className="card">
          <div className="card-header bg-light">
            <h5 className="mb-0">
              <i className="bi bi-journal-text me-2"></i>
              Materials
            </h5>
          </div>
          <div className="card-body p-0">
            {isLoading ? (
              <div className="text-center py-3">
                <div className="spinner-border spinner-border-sm text-primary" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
                <p className="mt-2 small">Loading materials...</p>
              </div>
            ) : materials.length === 0 ? (
              <div className="text-center py-3">
                <p className="text-muted mb-0 small">No materials found</p>
              </div>
            ) : (
              <div className="list-group list-group-flush">
                {materials.map(material => (
                  <button
                    key={material.id}
                    className={`list-group-item list-group-item-action ${selectedMaterialId === material.id ? 'active' : ''}`}
                    onClick={() => setSelectedMaterialId(material.id)}
                  >
                    <div className="d-flex justify-content-between align-items-start">
                      <div>
                        <div className="fw-semibold text-truncate" style={{ maxWidth: '160px' }}>
                          {material.title || 'Untitled Material'}
                        </div>
                        <div className="small text-truncate" style={{ maxWidth: '160px' }}>
                          {material.focusArea}
                        </div>
                      </div>
                      <span className={`badge bg-${getBadgeColor(material.status)}`}>
                        {material.status}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="col-md-9">
        {selectedMaterialId ? (
          <MaterialDetailView
            project={activeProject}
            materialId={selectedMaterialId}
            onBack={() => setSelectedMaterialId(null)}
            onRefresh={loadMaterials}
          />
        ) : (
          <div className="text-center p-5 bg-light rounded border">
            <i className="bi bi-file-earmark-text display-1 text-muted"></i>
            <h4 className="mt-3">Select a Material</h4>
            <p className="text-muted">
              Click on a material from the list on the left,<br />
              or upload a new material to begin.
            </p>
          </div>
        )}
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