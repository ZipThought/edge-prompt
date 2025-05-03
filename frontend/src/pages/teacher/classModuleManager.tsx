import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../services/api';
import { ProjectForm } from '../../components/project/ProjectForm'; // Assuming you still use ProjectForm
import { useNavigate, useParams } from 'react-router-dom';
import { PromptTemplate, Project } from '../../types'; // Import Project type for consistency


interface Props {
 classroomId: string;
}


const ClassProjectManager: React.FC<Props> = ({ classroomId }) => {
 const { id: classId } = useParams<{ id: string }>(); // Get classId from URL (consider consistency)
 const [projects, setProjects] = useState<Project[]>([]);
 const [isCreating, setIsCreating] = useState(false);
 const [error, setError] = useState<string | null>(null);
 const navigate = useNavigate();


 const fetchProjects = useCallback(async () => {
   try {
     const classProjects = await api.getProjectsForClass(classroomId); // Use classroomId prop
     setProjects(classProjects);
   } catch (error) {
     console.error("Error fetching modules:", error);
     setError("Failed to load modules for this class.");
   }
 }, [classroomId]); // Dependency array is crucial


 useEffect(() => {
   fetchProjects();
 }, [fetchProjects]);


 const handleProjectCreated = useCallback(async () => {
   setIsCreating(false);
   await fetchProjects(); // Refresh the list after creation
 }, [fetchProjects]);


 return (
   <div className="card shadow-sm">
     <div className="card-header bg-light d-flex justify-content-between align-items-center"> {/* Improved header */}
       <h5 className="mb-0">Modules</h5>
       <button className="btn btn-sm btn-primary" onClick={() => setIsCreating(true)} disabled={isCreating}> {/* Disabled during creation */}
         {isCreating ? <span className="spinner-border spinner-border-sm me-1"></span> : <i className="bi bi-plus-circle me-1"></i>}
         Create Module
       </button>
     </div>
     <div className="card-body">
       {error && <div className="alert alert-danger">{error}</div>}
       {isCreating && (
         <div className="mb-3"> {/* Added margin for spacing */}
           <ProjectForm
             onSuccess={handleProjectCreated}
             onClose={() => setIsCreating(false)}
             classroom_id={classId}
           />
         </div>
       )}
       {projects.length > 0 ? (
         <div className="list-group">
           {projects.map(project => (
             <button
               key={project.id}
               className="list-group-item list-group-item-action"
               onClick={() => navigate(`/dashboard/teacher/project/${project.id}`)}
             >
               {project.name}
             </button>
           ))}
         </div>
       ) : (
         <div className="alert alert-info">No modules created for this class yet.</div>
       )}
     </div>
   </div>
 );
};


export default ClassProjectManager;