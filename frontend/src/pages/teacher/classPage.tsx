import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../../services/api";
import { SimplifiedMaterialUploader } from '../../components/teacher/SimplifiedMaterialUploader';
import ClassProjectManager from "../../pages/teacher/classModuleManager"; // Import ProjectPanel

const TeacherClassPage = () => {
  const { id } = useParams<{ id: string | undefined }>();
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

  const refreshMaterials = () => {
    api.getClassById(id!).then(setClassData);
  };

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
     

        <hr className="my-4" />
     

        <div className="row">
          <div className="col-md-12">
        <h5>Module</h5>
        {id && <ClassProjectManager classroomId={id} />}
          </div>
        </div>
      </div>
    </>
  );
 };
 

 export default TeacherClassPage;