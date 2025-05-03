import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../../services/api';
import { MaterialDetailView } from '../../components/teacher/MaterialDetailView';
import { SimplifiedMaterialUploader } from '../../components/teacher/SimplifiedMaterialUploader';
import { Material, Project } from '../../types'; // Import Project type


const ProjectDetailPage: React.FC = () => {
 const { id } = useParams<{ id: string }>(); // Get projectId from URL
 const navigate = useNavigate();


 const [project, setProject] = useState<Project | null>(null);
 const [materials, setMaterials] = useState<Material[]>([]);
 const [projects, setProjects] = useState<Project[]>([]); // All projects
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState<string | null>(null);
 const [selectedMaterialId, setSelectedMaterialId] = useState<string | null>(null);


 useEffect(() => {
   const fetchProjectData = async () => {
     setLoading(true);
     try {
       const projectData = await api.getProject(id!);
       setProject(projectData);
       const projectMaterials = await api.getMaterials(id!);
       setMaterials(projectMaterials);
       const allProjects = await api.getProjects(); // Fetch all projects
       setProjects(allProjects);
     } catch (err) {
       setError(err instanceof Error ? err.message : 'Failed to load project details');
     } finally {
       setLoading(false);
     }
   };


   fetchProjectData();
 }, [id]);


 const handleMaterialUploaded = () => {
   // Refresh materials list after upload
   api.getMaterials(id!).then(setMaterials);
 };


 if (loading) {
   return <div className="text-center mt-5">Loading module details...</div>;
 }


 if (error) {
   return <div className="alert alert-danger mt-5">{error}</div>;
 }


 if (!project) {
   return <div className="alert alert-warning mt-5">Module not found</div>;
 }


 return (
   <div className="container-fluid">
     <header className="bg-primary text-white p-3 mb-4">
       <div className="d-flex justify-content-between align-items-center">
         <h1 className="h4 mb-0">
           <i className="bi bi-braces"></i> EdgePrompt | Module: {project.name}
         </h1>
         <button className="btn btn-light btn-sm" onClick={() => navigate("/dashboard/teacher")}>
           <i className="bi bi-arrow-left me-1"></i> Back to Class
         </button>
       </div>
     </header>


     <div className="row">
       <div className="col-md-3">
         {/* Project Navigation */}
         <div className="card shadow-sm mb-4">
           <div className="card-header bg-light">
             <h5 className="mb-0">Switch Module</h5>
           </div>
           <div className="card-body">
             <ul className="list-group list-group-flush">
               {projects.map(p => (
                 <button
                   key={p.id}
                   className={`list-group-item list-group-item-action ${p.id === project.id ? 'active' : ''}`}
                   onClick={() => navigate(`/dashboard/teacher/project/${p.id}`)}
                 >
                   {p.name}
                 </button>
               ))}
             </ul>
           </div>
         </div>


         {/* Add Material */}
         <div className="card shadow-sm">
           <div className="card-header bg-light">
             <h5 className="mb-0">Add Material</h5>
           </div>
           <div className="card-body">
             <SimplifiedMaterialUploader
               projectId={project.id}
               onMaterialUploaded={handleMaterialUploaded}
             />
           </div>
         </div>
       </div>


       <div className="col-md-9">
         {/* Material List and Detail */}
         <div className="card shadow-sm mb-4">
           <div className="card-header bg-light">
             <h5 className="mb-0">Materials</h5>
           </div>
           <div className="card-body">
             {materials.length === 0 ? (
               <div className="alert alert-info">No materials found for this project.</div>
             ) : (
               <div className="list-group">
                 {materials.map(material => (
                   <button
                     key={material.id}
                     className="list-group-item list-group-item-action"
                     onClick={() => setSelectedMaterialId(material.id)}
                   >
                     {material.title}
                   </button>
                 ))}
               </div>
             )}
           </div>
         </div>


         {selectedMaterialId && (
           <MaterialDetailView
             project={project}
             materialId={selectedMaterialId}
             onBack={() => setSelectedMaterialId(null)}
             onRefresh={handleMaterialUploaded}
           />
         )}
       </div>
     </div>
   </div>
 );
};


export default ProjectDetailPage;