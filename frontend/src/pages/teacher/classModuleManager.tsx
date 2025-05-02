import React, { useState, useEffect } from 'react';
 import { api } from '../../services/api';
 import { ProjectForm } from '../../components/project/ProjectForm'; // Assuming you still use ProjectForm
 import { useNavigate, useParams } from 'react-router-dom';
 

 interface Project {
  id: string;
  name: string;
  // Add other properties as needed
 }
 

 interface Props{
    classroomId: string;
 }

 const ClassProjectManager: React.FC<Props> = ({classroomId}) => {
  const { id: classId } = useParams<{ id: string }>(); // Get classId from URL
  const [projects, setProjects] = useState<Project[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const navigate = useNavigate();
 

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        // Fetch only projects associated with this class
        const classProjects = await api.getProjectsForClass(classroomId); // Assuming you create this API endpoint
        setProjects(classProjects);
      } catch (error) {
        console.error("Error fetching projects for class:", error);
      }
    };
 

    fetchProjects();
  }, [classId]);
 

  const handleProjectCreated = () => {
    setIsCreating(false);
    window.location.reload();
  };
 

  return (
    <div className="card">
      <div className="card-header">
        <h5>Modules for this Class</h5>
        <button className="btn btn-sm btn-primary" onClick={() => setIsCreating(true)}>
          Create Module for Class
        </button>
      </div>
      <div className="card-body">
        {isCreating && (
          <ProjectForm
            onSuccess={handleProjectCreated}
            onClose={() => setIsCreating(false)}
            classroom_id={classId} // Pass classId to ProjectForm
          />
        )}
        {projects.length > 0 ? (
          <ul>
            {projects.map(project => (
              <li key={project.id}>
                <button
                  key={project.id}
                  className="list-group-item list-group-item-action"
                  onClick={() => navigate(`/dashboard/teacher/project/${project.id}`)} // Adjust navigation as needed
                >
                  {project.name}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p>No modules created for this class yet.</p>
        )}
      </div>
    </div>
  );
 };
 

 export default ClassProjectManager;