import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

type Class = {
  id: string;
  name: string;
};

type LearningMaterial = {
  id: string;
  title: string;
};

const ClassPage: React.FC = () => {
  const { classId } = useParams<{ classId: string }>();
  const navigate = useNavigate();

  const [classData, setClassData] = useState<Class | null>(null);
  const [materials, setMaterials] = useState<LearningMaterial[]>([]);
  const [studentName, setStudentName] = useState("Student");

  useEffect(() => {
    const fetchClassData = async () => {
      try {
        const token = localStorage.getItem("token");
        const response = await fetch(
          `http://localhost:3001/api/classrooms/${classId}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) throw new Error("Class fetch failed");

        const data = await response.json();
        setClassData({
          id: data.id,
          name: data.name,
        });
      } catch (err) {
        console.error("Failed to fetch class data:", err);
      }
    };

    const fetchMaterials = async () => {
      try {
        const placeholderMaterials: LearningMaterial[] = [
          { id: "1", title: "Week 1 material" },
          { id: "2", title: "Week 2 material" },
          { id: "3", title: "Week 3" },
        ];
        setMaterials(placeholderMaterials);
      } catch (err) {
        console.error("Failed to fetch learning materials:", err);
      }
    };

    const fetchStudentProfile = async () => {
      try {
        const token = localStorage.getItem("token");
        const response = await fetch("http://localhost:3001/api/users/me", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (!response.ok) throw new Error("Failed to fetch profile");
        const data = await response.json();
        setStudentName(`${data.firstname} ${data.lastname}`);
      } catch (err) {
        console.error("Failed to fetch student profile:", err);
      }
    };

    fetchStudentProfile();
    fetchClassData();
    fetchMaterials();
  }, [classId]);

  const handleMaterialClick = (materialId: string) => {
    navigate(`/dashboard/student/material/${materialId}`);
  };

  const handleBack = () => {
    navigate("/dashboard/student");
  };

  const handleLogout = () => {
    navigate("/");
  };

  const handleProfile = () => {
    navigate("/profile");
  };

  if (!classData) return <div>Loading class data...</div>;

  return (
    <div className="container-fluid">
      <header className="bg-primary text-white p-3 mb-4">
        <div className="d-flex justify-content-between align-items-center">
          <h1 className="h4 mb-0">
            <i className="bi bi-braces"></i> EdgePrompt
          </h1>
          <nav className="ms-auto d-flex align-items-center gap-3">
            <button className="btn btn-light btn-sm" onClick={handleBack}>
              Dashboard
            </button>
            <button className="btn btn-light btn-sm" onClick={handleProfile}>
              Profile
            </button>
            <button
              className="btn btn-outline-light btn-sm"
              onClick={handleLogout}
            >
              <i className="bi bi-box-arrow-right me-1"></i> Logout
            </button>
          </nav>
        </div>
      </header>

      <div className="d-flex justify-content-between align-items-center mb-3">
          <h2 className="mb-0">{classData.name}</h2>
        <button className="btn btn-secondary btn-sm" onClick={handleBack}>
          <i className="bi bi-arrow-left me-1"></i> Back</button>
      </div>


      <h4 className="mb-3">Learning Materials</h4>
      <div className="row g-3">
        {materials.map((mat) => (
          <div className="col-sm-6 col-md-4" key={mat.id}>
            <div className="card shadow-sm h-100">
              <div className="card-body text-center">
                <h6 className="card-title">{mat.title}</h6>
                <button
                  className="btn btn-outline-primary btn-sm mt-2"
                  onClick={() => handleMaterialClick(mat.id)}
                >
                  View Material
                </button>
              </div>
            </div>
          </div>
        ))}

        {materials.length === 0 && (
          <p className="text-muted">No learning materials available.</p>
        )}
      </div>
    </div>
  );
};

export default ClassPage;
