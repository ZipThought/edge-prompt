import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../../services/api";

const TeacherClassPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [classData, setClassData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchClassData = async () => {
      try {
        const data = await api.getClassById(id!);
        setClassData(data);
      } catch (error) {
        console.error("Failed to fetch class data", error);
      } finally {
        setLoading(false);
      }
    };
    fetchClassData();
  }, [id]);

  if (loading) return <div className="text-center mt-5">Loading class...</div>;
  if (!classData) return <div className="text-center mt-5 text-danger">Class not found</div>;

  return (
    <>
      <div className="container-fluid">
        <header className="bg-primary text-white p-3 mb-0">
          <div className="d-flex justify-content-between align-items-center">
            <h1 className="h4 mb-0">
              <i className="bi bi-braces"></i> EdgePrompt <span className="text-white">| Class Page</span>
            </h1>
            <nav className="ms-auto d-flex align-items-center gap-3">
              <button className="btn btn-light btn-sm" onClick={() => navigate("/dashboard/teacher")}>
                Dashboard
              </button>
              <button className="btn btn-light btn-sm" onClick={() => navigate("/profile")}>
                Profile
              </button>
              <button className="btn btn-outline-light btn-sm" onClick={() => navigate("/")}>
                <i className="bi bi-box-arrow-right me-1"></i> Logout
              </button>
            </nav>
          </div>
        </header>
      </div>
  
  
      <div className="container-fluid px-4 mt-4">
        <div className="d-flex justify-content-between align-items-center mb-4">
          <div>
            <h2 className="fw-bold mb-0">{classData.className}</h2>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate("/dashboard/teacher")}>
            <i className="bi bi-arrow-left me-1"></i> Back
          </button>
        </div>

        <div className="d-flex justify-content-between align-items-center mb-3">
          <h5 className="mb-0">Learning Materials</h5>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => navigate(`/dashboard/teacher/class/${id}/add-material`)}
          >
            <i className="bi bi-plus-lg me-1"></i> Add Material
          </button>
        </div>

  
        <div className="row">
          <div className="col-md-9">
  
            {classData.learningMaterials.length === 0 ? (
              <div className="text-muted">No learning materials added yet.</div>
            ) : (
              <div className="row g-3">
                {classData.learningMaterials.map((material: any) => (
                  <div className="col-md-6 col-lg-4" key={material.id}>
                    <div
                      className="card shadow-sm h-100"
                      style={{ cursor: "pointer" }}
                      onClick={() => navigate(`/material/${material.id}`)}
                    >
                      <div className="card-body text-center">
                        <h5 className="card-title">{material.title}</h5>
                        <p className="text-muted small mb-0">Click to view or manage</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
  
          <div className="col-md-3">
            <div className="card shadow-sm h-100">
              <div className="card-header bg-light">
                <h5 className="mb-0">
                  <i className="bi bi-tools me-1"></i> Class Tools
                </h5>
              </div>
              <div className="card-body">
                <p className="text-muted">
                  This space can be used for future tools like analytics,
                  announcements, or class-level actions.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );  
};

export default TeacherClassPage;