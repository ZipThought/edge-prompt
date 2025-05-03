import React, { useState, useEffect } from 'react';
import { MaterialUploader } from './MaterialUploader';
import { MaterialSource } from '../../../../backend/src/types';
import { useProject } from '../../contexts/ProjectContext';

interface Props {
  onMaterialLoad?: (material: MaterialSource) => void;
  onMaterialUploaded?: () => void;
  projectId?: string;
  classroomId?: string;
}

export const SimplifiedMaterialUploader: React.FC<Props> = ({ 
  onMaterialLoad, 
  onMaterialUploaded, 
  projectId: propProjectId,
  classroomId 
}) => {
  const { activeProject } = useProject();
  const [showModal, setShowModal] = useState(false);
  
  // Use projectId from props if available, otherwise from context
  const projectId = propProjectId || (activeProject?.id);
  
  const handleMaterialUploaded = (material: MaterialSource) => {
    if (onMaterialLoad) {
      onMaterialLoad(material);
    }
    if (onMaterialUploaded) {
      onMaterialUploaded();
    }
    setShowModal(false);
  };
  
  const handleUploadClick = () => {
    if (!projectId) {
      // Show a toast or alert if no project is selected
      alert('Please select a project from the dropdown in the navigation bar before uploading materials.');
      return;
    }
    
    setShowModal(true);
  };
  
  return (
    <>
      <div className="mb-3">
        <button 
          className="btn btn-sm btn-primary"
          onClick={handleUploadClick}
        >
          <i className="bi bi-plus-lg me-1"></i> Add Material
        </button>
      </div>
      
      {/* Only show modal if we have a project ID */}
      {showModal && projectId && (
        <>
          <div 
            className="modal-backdrop" 
            style={{ 
              opacity: 0.5, 
              position: 'fixed', 
              top: 0, 
              left: 0, 
              right: 0, 
              bottom: 0, 
              zIndex: 1040 
            }}
            onClick={() => setShowModal(false)}
          ></div>
          
          <div 
            className="modal" 
            tabIndex={-1} 
            role="dialog"
            style={{ 
              display: 'block', 
              position: 'fixed', 
              top: 0, 
              left: 0, 
              right: 0, 
              bottom: 0, 
              zIndex: 1050,
              overflow: 'auto'
            }}
          >
            <div 
              className="modal-dialog modal-lg" 
              role="document"
              style={{ 
                margin: '1.75rem auto',
                transform: 'none'
              }}
            >
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title">
                    <i className="bi bi-cloud-upload me-2"></i>
                    Upload Learning Material
                  </h5>
                  <button 
                    type="button" 
                    className="btn-close" 
                    onClick={() => setShowModal(false)}
                    aria-label="Close"
                  ></button>
                </div>
                <div className="modal-body">
                  {/* Always pass the projectId to MaterialUploader */}
                  <MaterialUploader 
                    onMaterialLoad={handleMaterialUploaded} 
                    projectId={projectId}
                    classroomId = {classroomId}
                    showTitle={false}
                  />
                </div>
                <div className="modal-footer">
                  <button 
                    type="button" 
                    className="btn btn-secondary" 
                    onClick={() => setShowModal(false)}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}; 