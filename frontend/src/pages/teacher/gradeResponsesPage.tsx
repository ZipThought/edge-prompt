import React, { useState, useEffect, useCallback } from 'react';
 import { useParams, useNavigate, useLocation } from 'react-router-dom';
 import { api } from '../../services/api';
 import { Material } from '../../types';

 interface GradeSummary {
  totalSubmissions: number;
  gradedSubmissions: number;
 }

 interface Student {
  id: string;
  name: string;
 }

 interface Question {
  id: string;
  responseId: string;
  question: string;
  response: string;
  rubric: any;
  grade: number | null;
  feedback: string | null;
 }

 const GradeResponsesPage: React.FC = () => {
  const { classId, projectId, materialId } = useParams();
  const navigate = useNavigate();

  const [students, setStudents] = useState<Student[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [material, setMaterial] = useState<Material | null>(null);
  const [gradeSummary, setGradeSummary] = useState<GradeSummary>({
    totalSubmissions: 0,
    gradedSubmissions: 0,
  });
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState<{ [questionId: string]: boolean }>({});
  const [saveSuccess, setSaveSuccess] = useState<{ [questionId: string]: boolean }>({});

  // Fetch data from the server
  const fetchPageData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch students
      if (!classId) {
        throw new Error("classId is undefined");
      }
      const studentData = await api.getClassStudents(classId);
      setStudents(studentData);

      // Fetch material details
      const materialData = await api.getMaterial(materialId!);
      setMaterial(materialData);

      // Fetch questions and student responses for the material, filtered by student
      if (selectedStudentId) {
        const responsesData = await api.getStudentResponsesForMaterial(
          materialId!,
          selectedStudentId
        );

        // Organize questions and initial grades/feedback
        const initialQuestions: Question[] = [];
        const initialSavingStates: { [questionId: string]: boolean } = {};
        const initialSuccessStates: { [questionId: string]: boolean } = {};

        if (responsesData && Array.isArray(responsesData)) {
          responsesData.forEach((item: any) => {
            const rubric = item.rubric;
            const parsedRubric =
              typeof rubric === 'string' ? JSON.parse(rubric) : rubric;

            const question: Question = {
              id: item.question_id,
              responseId: item.responseId,
              question: item.question,
              response: item.response,
              rubric: parsedRubric,
              grade: item.grade,
              feedback: item.feedback,
            };
            initialQuestions.push(question);
            initialSavingStates[item.questionId] = false; // Initialize saving state for each question
            initialSuccessStates[item.questionId] = false; // Initialize success state for each question
          });
        }
        setQuestions(initialQuestions);
        setIsSaving(initialSavingStates);
        setSaveSuccess(initialSuccessStates);
      } else {
        setQuestions([]);
        setIsSaving({});
        setSaveSuccess({});
      }

      // Fetch grade summary
      const summary = await api.getGradeSummary(materialId!);
      setGradeSummary(summary);
      setError(null);
    } catch (error) {
      console.error('Error fetching data:', error);
      setError('Failed to load grading data.');
    } finally {
      setLoading(false);
    }
  }, [classId, materialId, selectedStudentId]);

  useEffect(() => {
    fetchPageData();
  }, [fetchPageData]);

  const handleGradeChange = (questionId: string, grade: number | null) => {
    setQuestions((prevQuestions) =>
      prevQuestions.map((q) =>
        q.id === questionId ? { ...q, grade: grade } : q
      )
    );
  };

  const handleFeedbackChange = (questionId: string, feedback: string | null) => {
    setQuestions((prevQuestions) =>
      prevQuestions.map((q) =>
        q.id === questionId ? { ...q, feedback: feedback } : q
      )
    );
  };

  const handleSaveGrade = async (questionId: string) => {
    try {
      setIsSaving((prev) => ({ ...prev, [questionId]: true }));
      setError(null);
      setSaveSuccess((prev) => ({ ...prev, [questionId]: false }));
      
      const questionToUpdate = questions.find((q) => q.id === questionId);
      if (!questionToUpdate) {
        setError(`Question with id ${questionId} not found.`);
        return;
      }

      if (questionToUpdate.grade === null) {
        setError(`Grade for question ${questionId} cannot be null.`);
        return;
      }
      if (questionToUpdate.feedback === null) {
        setError(`Feedback for question ${questionId} cannot be null.`);
        return;
      }

      // API call to update the grade and feedback for a specific response
      await api.updateResponseGradeAndFeedback(
        questionToUpdate.responseId,
        questionToUpdate.grade,
        questionToUpdate.feedback
      );

      // After saving, refresh the grade summary and data
      await fetchPageData();
      setError(null);
      setSaveSuccess((prev) => ({ ...prev, [questionId]: true }));
    } catch (error: any) {
      console.error('Error saving grade for question:', error);
      setError(`Failed to save grade for question ${questionId}.`);
    } finally {
      setIsSaving((prev) => ({ ...prev, [questionId]: false }));
      setTimeout(() => {
        setSaveSuccess((prev) => ({ ...prev, [questionId]: false }));
      }, 3000);
    }
  };

  const goBack = () => {
    navigate(`/dashboard/teacher/project/${projectId}`);
  };

  const getMaxScore = (rubric: any): number => {
    //  Implement logic to extract the max score from your rubric data
    //  This will depend on the structure of your rubric
    if (!rubric) return 0;
    //  Or a default max score

    if (rubric.maxScore !== undefined) {
      return rubric.maxScore;
    } else if (rubric.criteriaWeights) {
      //  If maxScore isn't directly available, calculate it from criteria weights (if applicable)
      return Object.keys(rubric.criteriaWeights).length;
      //  Assuming each criterion is worth 1 point
    } else if (rubric.levels) {
      //  If using levels, the max score might be the highest level key
      const levels = Object.keys(rubric.levels);
      if (levels.length > 0) {
        return Math.max(...levels.map(Number));
      }
    }

    return 100;
    //  Default max score if not found
  };

  return (
    <div className="container mt-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>Grade Responses - Module: {material?.title}</h2>
        <button className="btn btn-secondary btn-sm" onClick={goBack}>
          Back to Module
        </button>
      </div>

      {loading && <div>Loading...</div>}
      {error && <div className="alert alert-danger">{error}</div>}
      {/*saveSuccess && <div className="alert alert-success">Grades saved successfully!</div>*/}

      <div className="mb-3">
        Graded: {gradeSummary.gradedSubmissions} / {gradeSummary.totalSubmissions}{' '}
        Submissions
      </div>

      <div className="card mb-4">
        <div className="card-header bg-light">
          <h4>Select Student</h4>
        </div>
        <div className="card-body">
          <ul className="list-group">
            {students.map((student) => (
              <li
                key={student.id}
                className={`list-group-item list-group-item-action ${
                  selectedStudentId === student.id ? 'active' : ''
                }`}
                onClick={() => setSelectedStudentId(student.id)}
                style={{ cursor: 'pointer' }}
              >
                {student.name}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {selectedStudentId && (
        <div className="card">
          <div className="card-header bg-light">
            <h4>Student Submissions</h4>
          </div>
          <div className="card-body">
            {questions.map((question) => (
              <div key={question.id} className="mb-4 p-3 border rounded">
                <h5>{question.question}</h5>
                <div className="alert alert-info">
                  Student's Answer: {question.response}
                </div>

                {/* Display Rubric Criteria Weights */}
                {question.rubric && question.rubric.criteriaWeights && (
                  <div className="card mt-3">
                    <div className="card-header bg-light">
                      Rubric Criteria Weights
                    </div>
                    <div className="card-body">
                      <ul>
                        {Object.entries(question.rubric.criteriaWeights).map(
                          ([criteria, weight]) => (
                            <li key={criteria}>
                              {criteria}: {String(weight)}
                            </li>
                          )
                        )}
                      </ul>
                    </div>
                  </div>
                )}

                <div className="mb-3">
                  <label htmlFor={`grade-input-${question.id}`} className="form-label">
                    Grade
                  </label>
                  <input
                    type="number"
                    className="form-control"
                    id={`grade-input-${question.id}`}
                    value={question.grade?.toString() ?? ''} // Use question.grade
                    onChange={(e) =>
                      handleGradeChange(
                        question.id,
                        e.target.value ? Number(e.target.value) : null
                      )
                    }
                    placeholder={`Enter grade (out of ${getMaxScore(
                      question.rubric
                    )})`}
                  />
                </div>

                <div className="mb-3">
                  <label htmlFor={`feedback-textarea-${question.id}`} className="form-label">
                    Feedback
                  </label>
                  <textarea
                    className="form-control"
                    id={`feedback-textarea-${question.id}`}
                    value={question.feedback || ''}
                    onChange={(e) =>
                      handleFeedbackChange(question.id, e.target.value)
                    }
                    placeholder="Enter feedback"
                    rows={4}
                  />
                </div>
                <div className="text-end">
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => handleSaveGrade(question?.id)}
                    disabled={isSaving[question.id]}
                  >
                    {isSaving[question.id] ? (
                      <span className="spinner-border spinner-border-sm"></span>
                    ) : (
                      'Save'
                    )}
                  </button>
                  {saveSuccess[question.id] && (
                    <span className="text-success ms-2">Saved!</span>
                  )}
                </div>
              </div>
            ))}
            {/*<button className="btn btn-primary" onClick={handleSaveGrades} disabled={isSaving}>
              {isSaving ? <span className="spinner-border spinner-border-sm"></span> : "Save All Grades"}
            </button>*/}
          </div>
        </div>
      )}
    </div>
  );
};

export default GradeResponsesPage;