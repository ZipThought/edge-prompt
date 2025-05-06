import React, { useEffect, useState } from "react";
 import { useNavigate, useParams } from "react-router-dom";
 import { api } from "../../services/api";
 import { Project } from "../../types";


 const TeacherGradeClassPage: React.FC = () => {
  const { classId } = useParams<{ classId: string }>();
  const navigate = useNavigate();
  const [classData, setClassData] = useState<any>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false); 
  const [students, setStudents] = useState<any[]>([]);

  interface Student {
    id: string;
    name: string;
    email: string;
  }

  useEffect(() => {
    const fetchClassData = async () => {
      try {
        const data = await api.getClassById(classId!);
        setClassData(data);
      } catch (error) {
        console.error("Failed to fetch class data", error);
      } finally {
        setLoading(false);
      }
    };

    const fetchProjects = async () => {
      try {
        const classProjects = await api.getProjectsForClass(classId!);
        setProjects(classProjects);
      } catch (error) {
        console.error("Failed to fetch modules:", error);
        setError("Failed to load modules for this class.");
      }
    };
    const fetchStudents = async () => {
        try {
          //const classStudents = await api.getStudentsForClass(classId!);
          const classStudents: any = []
          setStudents(classStudents);
        } catch (error) {
          console.error("Failed to fetch students", error);
        }
      };

   
        
      
        fetchStudents();
    fetchClassData();
    fetchProjects();
  }, [classId]);

  const handleCreateModule = () => {
    setShowCreateForm(true); // Show the form instead of navigating
  };

  const handleProjectCreated = () => {
    setShowCreateForm(false); // Hide the form after creation
    api.getProjectsForClass(classId!).then(setProjects); // Refresh the list after creation
  };

  const handleViewModule = (moduleId: string) => {
    navigate(`/dashboard/teacher/project/${moduleId}`);
  };

  const handleBack = () => {
    navigate("/dashboard/teacher");
  };

  const handleAssignGrade = (studentId: string) => {
    navigate(`/dashboard/teacher/grade/${studentId}`);
  };
  

  

  return (
    <div className="container-fluid">
      <header className="bg-primary text-white p-3 mb-4">
        <div className="d-flex justify-content-between align-items-center">
          <h1 className="h4 mb-0">
            <i className="bi bi-braces"></i> EdgePrompt | Class: {classData.className}
          </h1>
          <nav className="ms-auto d-flex align-items-center gap-3">
            <button className="btn btn-light btn-sm" onClick={() => handleBack()}>
              <i className="bi bi-arrow-left me-1"></i> Back to Dashboard
            </button>
            <button
              className="btn btn-outline-light btn-sm"
              onClick={() => navigate("/")}
            >
              <i className="bi bi-box-arrow-right me-1"></i> Logout
            </button>
          </nav>
        </div>
      </header>

      <div className="row">
      <div className="col-12">
  <div className="d-flex justify-content-between align-items-center mb-4">
    <h2>Students</h2>
    <button className="btn btn-primary" onClick={handleCreateModule}>
      <i className="bi bi-plus-circle me-2"></i> Create Module
    </button>
  </div>

  {students.length === 0 ? (
    <div className="alert alert-info">No students in this class.</div>
  ) : (
    <table className="table table-hover">
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {students.map((student) => (
          <tr key={student.id}>
            <td>
              <button
                className="btn btn-link p-0 text-decoration-none"
                onClick={() => handleAssignGrade(student.id)}
              >
                {student.name}
              </button>
            </td>
            <td>{student.email}</td>
            <td>
              <button
                className="btn btn-outline-secondary btn-sm"
                onClick={() => handleAssignGrade(student.id)}
              >
                Assign Grade
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )}
</div>

        
        </div>
      </div>
  );
 };

 export default TeacherGradeClassPage;