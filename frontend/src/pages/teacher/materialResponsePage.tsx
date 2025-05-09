import React, { useEffect, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { api } from "../../services/api";
import { GeneratedQuestion } from "../../types/edgeprompt";

interface Response {
  studentName: string;
  response: string;
}

const MaterialResponsePage: React.FC = () => {
  const { materialId } = useParams<{ materialId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const classId = location.state?.classId;

  const [questions, setQuestions] = useState<GeneratedQuestion[]>([]);
  const [responses, setResponses] = useState<Record<string, Response[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchQuestionsAndResponses = async () => {
      if (!materialId) return;
      setLoading(true);
      try {
        const questionData = await api.getQuestions(materialId);
        setQuestions(questionData);

        const allResponses: Record<string, Response[]> = {};

        for (let i = 0; i < questionData.length; i++) {
          const q = questionData[i];
          const questionId = (q as any).questionId || (q as any).id;

          if (!questionId) {
            console.warn(`Question ${i} is missing an ID, skipping response fetch.`);
            continue;
          }

          const resp = await api.getResponses(questionId);
          allResponses[questionId] = resp || [];
        }

        setResponses(allResponses);
      } catch (err) {
        setError("Failed to load questions or responses.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchQuestionsAndResponses();
  }, [materialId]);

  const handleBack = () => {
    if (classId) {
      navigate(`/dashboard/teacher/class/${classId}`);
    } else {
      navigate("/dashboard/teacher");
    }
  };

  if (loading) return <div className="text-center mt-5">Loading student responses...</div>;
  if (error) return <div className="alert alert-danger mt-5">{error}</div>;

  return (
    <div className="container-fluid">
      <header className="bg-primary text-white p-3 mb-4">
        <div className="d-flex justify-content-between align-items-center">
          <h1 className="h4 mb-0">
            <i className="bi bi-list-check me-2"></i> Student Responses
          </h1>
          <button className="btn btn-light btn-sm" onClick={handleBack}>
            <i className="bi bi-arrow-left me-1"></i> Back to Class
          </button>
        </div>
      </header>

      {questions.length === 0 ? (
        <div className="alert alert-info">No responses yet for this material.</div>
      ) : (
        questions.map((question, index) => {
          const questionId = (question as any).questionId || (question as any).id;
          const responseList = responses[questionId] || [];

          let validationChecks: string[] = [];

          try {
            const rules = question.metadata?.rules;
            const parsedRules = typeof rules === 'string' ? JSON.parse(rules) : rules;
            if (Array.isArray(parsedRules?.validationChecks)) {
              validationChecks = parsedRules.validationChecks;
            }
          } catch (e) {
            console.warn(`Failed to parse validationChecks for question ${questionId}`, e);
          }

          return (
            <div className="card shadow-sm mb-4" key={questionId}>
              <div className="card-header bg-light">
                <strong>Question {index + 1}</strong>: {question.question}
              </div>
              <div className="card-body">
                {responseList.length === 0 ? (
                  <div className="text-muted">No student responses yet.</div>
                ) : (
                  <>
                    <table className="table table-bordered table-hover">
                      <thead className="table-light">
                        <tr>
                          <th>Student Name</th>
                          <th>Response</th>
                        </tr>
                      </thead>
                      <tbody>
                        {responseList.map((resp, i) => (
                          <tr key={i}>
                            <td>{resp.studentName}</td>
                            <td>{resp.response}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>

                    {validationChecks.length > 0 && (
                      <div className="mt-4 border-top pt-3">
                        <h6 className="text-secondary">Validation Criteria</h6>
                        <ul className="mb-0 ps-3">
                          {validationChecks.map((check, idx) => (
                            <li key={idx}>{check}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
};

export default MaterialResponsePage;
