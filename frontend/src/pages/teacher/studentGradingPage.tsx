import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../../services/api";

interface Student {
  id: string;
  name: string;
  email: string;
}

interface Grade {
  score: number;
  feedback: string;
}

const TeacherAssignStudentGradePage: React.FC = () => {
  const { studentId } = useParams<{ studentId: string }>();
  const navigate = useNavigate();

  const [student, setStudent] = useState<Student | null>(null);
  const [grade, setGrade] = useState<Grade>({ score: 0, feedback: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const fetchStudentData = async () => {
      try {
        const studentInfo = await api.getUserById(studentId!);
        //FIX-ME: Im plmenet when ready
        //const studentGrade = await api.getGradeForStudent(studentId!);
        setStudent(studentInfo);
        // if (studentGrade) setGrade(studentGrade);
      } catch (err) {
        console.error(err);
        setError("Failed to load student data.");
      } finally {
        setLoading(false);
      }
    };

    fetchStudentData();
  }, [studentId]);

  const handleBack = () => {
    navigate(-1); 
  };

  const handleSubmit = async () => {
    navigate(-1); 
    //FIXE-ME: Add submission logic here
    // try {
    //   await api.submitGrade(studentId!, grade);
    //   setSuccess("Grade submitted successfully.");
    // } catch (err) {
    //   console.error(err);
    //   setError("Failed to submit grade.");
    // }
  };

  if (loading) {
    return (
      <div className="container text-center mt-5">
        <div className="spinner-border" role="status" />
        <p className="mt-2">Loading student data...</p>
      </div>
    );
  }

  if (!student) {
    return (
      <div className="container mt-5">
        <div className="alert alert-danger">Student not found.</div>
        <button className="btn btn-secondary" onClick={handleBack}>
          Back
        </button>
      </div>
    );
  }

  return (
    
    <>
  <header className="bg-primary text-white p-3 mb-4 w-100">
    <div className="container d-flex justify-content-between align-items-center">
      <h1 className="h4 mb-0">
        <i className="bi bi-braces"></i> EdgePrompt
      </h1>
      <nav className="ms-auto d-flex align-items-center gap-3">
      </nav>
    </div>
  </header>

  <div className="container mt-4">
    <header className="mb-4">
      <h1 className="h4">
        <i className="bi bi-pencil-square me-2"></i> Grade Student: {student.name}
      </h1>
      <button className="btn btn-outline-secondary btn-sm mt-2" onClick={handleBack}>
        <i className="bi bi-arrow-left me-1"></i> Back
      </button>
    </header>

    {error && <div className="alert alert-danger">{error}</div>}
    {success && <div className="alert alert-success">{success}</div>}

    <div className="card shadow-sm">
      <div className="card-body">
        <div className="mb-3">
          <label className="form-label">Score (out of 100)</label>
          <input
            type="number"
            className="form-control"
            value={grade.score}
            onChange={(e) => setGrade({ ...grade, score: parseInt(e.target.value) })}
            min={0}
            max={100}
          />
        </div>

        <div className="mb-3">
          <label className="form-label">Feedback (optional)</label>
          <textarea
            className="form-control"
            rows={4}
            value={grade.feedback}
            onChange={(e) => setGrade({ ...grade, feedback: e.target.value })}
          />
        </div>

        <button className="btn btn-primary" onClick={handleSubmit}>
          <i className="bi bi-check2-circle me-2"></i> Submit Grade
        </button>
      </div>
    </div>
  </div>
</>

  );
};

export default TeacherAssignStudentGradePage;