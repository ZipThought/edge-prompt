import React, { useState, useRef } from 'react';
import { MaterialSource, ContentTemplate } from '../../../../backend/src/types';
import { api } from '../../services/api';
import DOMPurify from 'dompurify';


interface Props {
  onMaterialLoad: (material: MaterialSource) => void;
  projectId?: string;
  classroomId?: string;
  showTitle?: boolean;
}

interface Metadata {
  title: string;
  chapter: string;
  focusArea: string;
  useSourceLanguage: boolean;
  learningObjectives?: string[];
  templates?: ContentTemplate[];
}

export const MaterialUploader: React.FC<Props> = ({ onMaterialLoad, projectId, classroomId, showTitle = false }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const focusAreaRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [metadata, setMetadata] = useState<Metadata>({
    title: '',
    chapter: '',
    focusArea: '',
    useSourceLanguage: false,
  });
  const [isUploading, setIsUploading] = useState(false);

  // Add disabled state based on project presence
  const isDisabled = !projectId;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const resetForm = () => {
    setFile(null);
    setMetadata({
      title: '',
      chapter: '',
      focusArea: '',
      useSourceLanguage: false,
    });
    
    // Reset and focus file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
      fileInputRef.current.focus();
    }

    // Focus the focus area input after a short delay to allow for DOM updates
    setTimeout(() => {
      if (focusAreaRef.current) {
        focusAreaRef.current.focus();
      }
    }, 100);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !metadata.focusArea) {
      alert('Please select a file and specify the focus area');
      return;
    }

    if (!projectId) {
      alert('No project selected. Please select a project first.');
      return;
    }

    setIsUploading(true); // Start loading

    try {
      const formData = new FormData();
      formData.append('file', file);
      
      // Always include projectId in metadata
      const metadataWithProject = { 
        title: DOMPurify.sanitize(metadata.title),
        chapter: DOMPurify.sanitize(metadata.chapter),
        focusArea: DOMPurify.sanitize(metadata.focusArea),
        useSourceLanguage: metadata.useSourceLanguage,
        projectId: projectId,
        classroomId: classroomId
      };
      
      formData.append('metadata', JSON.stringify(metadataWithProject));

      // Use API client instead of direct fetch
      const result = await api.uploadMaterial(formData);
      
      // Create MaterialSource object with the file extension as type
      const fileExt = file.name.split('.').pop()?.toLowerCase() || '';
      onMaterialLoad({
        id: result.id, // Include the returned material ID
        type: fileExt,
        content: result.content || '',
        metadata: {
          ...metadata,
          learningObjectives: result.objectives || [],
          templates: result.templates || []
        }
      });

      // Clear form
      resetForm();
    } catch (error) {
      console.error('Upload error:', error);
      alert('Failed to upload material. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="card mb-4">
      {showTitle && (
        <div className="card-header bg-primary text-white">
          <h5 className="mb-0">
            <i className="bi bi-cloud-upload"></i> Upload Learning Material
          </h5>
        </div>
      )}
      
      <div className="card-body">
        {isDisabled && (
          <div className="alert alert-warning">
            <i className="bi bi-exclamation-triangle-fill me-2"></i>
            Please select a project from the dropdown in the navigation bar before uploading materials.
          </div>
        )}
        
        {!isDisabled && (
          <form onSubmit={handleSubmit}>
            <div className="row">
              <div className="col-md-6">
                <div className="mb-3">
                  <label className="form-label">
                    Material File <span className="text-danger">*</span>
                  </label>
                  <input 
                    ref={fileInputRef}
                    type="file" 
                    className="form-control"
                    accept=".pdf,.docx,.md,.txt"
                    onChange={handleFileChange}
                    required
                  />
                  <small className="text-muted">
                    Supported formats: PDF, Word, Markdown, Text
                  </small>
                </div>
              </div>
              <div className="col-md-6">
                <div className="mb-3">
                  <label className="form-label">
                    Focus Area <span className="text-danger">*</span>
                    <small className="text-muted ms-1">(What should students learn from this material?)</small>
                  </label>
                  <input
                    ref={focusAreaRef}
                    type="text"
                    className="form-control"
                    value={metadata.focusArea}
                    onChange={e => setMetadata({...metadata, focusArea: e.target.value})}
                    placeholder="e.g., Grammar rules, Reading comprehension, etc."
                    required
                  />
                </div>
                <div className="mb-3">
                  <div className="form-check">
                    <input
                      type="checkbox"
                      className="form-check-input"
                      id="useSourceLanguage"
                      checked={metadata.useSourceLanguage}
                      onChange={e => setMetadata({...metadata, useSourceLanguage: e.target.checked})}
                    />
                    <label className="form-check-label" htmlFor="useSourceLanguage">
                      Use source material's language for generated content
                      <small className="text-muted d-block">
                        When checked, questions and feedback will be generated in the same language as the teaching material
                      </small>
                    </label>
                  </div>
                </div>
              </div>
            </div>

            <div className="row">
              <div className="col-md-6">
                <div className="mb-3">
                  <label className="form-label">
                    Title <small className="text-muted">(Optional)</small>
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    value={metadata.title}
                    onChange={e => setMetadata({...metadata, title: e.target.value})}
                    placeholder="Enter material title"
                  />
                </div>
              </div>
              <div className="col-md-6">
                <div className="mb-3">
                  <label className="form-label">
                    Chapter <small className="text-muted">(Optional)</small>
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    value={metadata.chapter}
                    onChange={e => setMetadata({...metadata, chapter: e.target.value})}
                    placeholder="e.g., Chapter 1"
                  />
                </div>
              </div>
            </div>

            <button 
              type="submit" 
              className="btn btn-primary"
              disabled={isUploading}
            >
              {isUploading ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" />
                  Processing...
                </>
              ) : (
                <>
                  <i className="bi bi-cloud-upload"></i> Upload and Process
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}; 