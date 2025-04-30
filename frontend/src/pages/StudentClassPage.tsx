import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

type Class = {
  id: string;
  name: string;
  subject: string;
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
          subject: data.subject,
        });
      } catch (err) {
        console.error("Failed to fetch class data:", err);
      }
    };

    const fetchMaterials = async () => {
      try {
        const placeholderMaterials: LearningMaterial[] = [
          { id: "1", title: "Material 1" },
          { id: "2", title: "Material 2" },
          { id: "3", title: "Material 3" },
        ];
    
    
        setMaterials(placeholderMaterials);
      } catch (err) {
        console.error("Failed to fetch learning materials:", err);
      }
    };
    

    fetchClassData();
    fetchMaterials();
  }, [classId]);

  const handleMaterialClick = (materialId: string) => {
    console.log("material clicked")
    // navigates to home for now since material page hasnt been built
    navigate(`/dashboard/student/material/${materialId}`);
  };

  const handleBack = () => {
    navigate("/dashboard/student");
  };

  if (!classData) return <div>Loading class data...</div>;

  return (
    <div className="container py-4">
      <button className="btn btn-secondary mb-3" onClick={handleBack}>
        ← Back to Dashboard
      </button>

      <h2 className="mb-2">{classData.name}</h2>
      <p className="text-muted mb-4">Subject: {classData.subject}</p>

      <h4>Learning Materials</h4>
      <div className="row g-3">
      {materials.map((mat) => (
        <div
          className="col-sm-6 col-md-4"
          key={mat.id}
        >
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
