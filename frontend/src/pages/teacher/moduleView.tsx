import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { api } from '../../services/api';
import { MaterialDetailView } from '../../components/teacher/MaterialDetailView';
import { SimplifiedMaterialUploader } from '../../components/teacher/SimplifiedMaterialUploader';
import { Material, Project } from '../../types';


const ProjectDetailPage: React.FC = () => { // Receive classId as a prop
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const location = useLocation();
    const classId = location.state?.id; // Get classId from the state
    console.log("moduleView.tsx - classId:", classId);

    const [project, setProject] = useState<Project | null>(null);
    const [materials, setMaterials] = useState<Material[]>([]);
    const [projects, setProjects] = useState<Project[]>([]);
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
                const allProjects = await api.getProjects();
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
        api.getMaterials(id!).then(setMaterials);
    };

    const handleGradeResponses = (materialId: string) => {
        console.log("moduleView.tsx - Navigating to grade-responses with:");
        console.log("  projectId:", id);
        console.log("  materialId:", materialId);
        console.log("  classId:", classId);
        const navigationPath = `/dashboard/teacher/project/${id}/grade-responses`;
        const navigationState = { state: { classId, materialId } };
        navigate(navigationPath, navigationState);
    };

    const handleProjectClick = (projectId: string) => {
        navigate(`/dashboard/teacher/project/${projectId}`, { state: { classId } });
    };

    const handleBack = () => {
        navigate("/dashboard/teacher");
    };

    const handleLogout = () => {
        navigate("/");
    };

    return (
        <div className="container-fluid">
            <header className="bg-primary text-white p-3 mb-4">
                <div className="d-flex justify-content-between align-items-center">
                    <h1 className="h4 mb-0">
                        <i className="bi bi-braces"></i> EdgePrompt | Module: {project?.name ?? ''}
                    </h1>
                    <button className="btn btn-light btn-sm" onClick={handleBack}>
                        <i className="bi bi-arrow-left me-1"></i> Back to Class
                    </button>
                </div>
            </header>

            <div className="row">
                <div className="col-md-3">
                    <div className="card shadow-sm mb-4">
                        <div className="card-header bg-light">
                            <h5 className="mb-0">Switch Module</h5>
                        </div>
                        <div className="card-body">
                            <ul className="list-group list-group-flush">
                                {projects.map(p => (
                                    <button
                                        key={p.id}
                                        className={`list-group-item list-group-item-action ${project && p.id === project.id ? 'active' : ''}`}
                                        onClick={() => handleProjectClick(p.id)}
                                    >
                                        {p.name}
                                    </button>
                                ))}
                            </ul>
                        </div>
                    </div>

                    <div className="card shadow-sm">
                        <div className="card-header bg-light">
                            <h5 className="mb-0">Add Material</h5>
                        </div>
                        <div className="card-body">
                            <SimplifiedMaterialUploader
                                projectId={project?.id}
                                onMaterialUploaded={handleMaterialUploaded}
                            />
                        </div>
                    </div>
                </div>

                <div className="col-md-9">
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
                                        <div key={material.id} className="list-group-item">
                                            <div className="d-flex justify-content-between align-items-center">
                                                <span onClick={() => setSelectedMaterialId(material.id)} style={{ cursor: 'pointer' }}>
                                                    {material.title}
                                                </span>
                                                <button
                                                    className="btn btn-outline-secondary btn-sm"
                                                    onClick={() => handleGradeResponses(material.id)}
                                                >
                                                    Grade Responses
                                                </button>
                                            </div>
                                        </div>
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