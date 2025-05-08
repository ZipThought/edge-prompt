// src/contexts/QuestionContext.tsx
import React, { createContext, useState, useContext, useEffect } from 'react';
import { api } from '../services/api';
import { GeneratedQuestion } from '../types/edgeprompt';

interface QuestionContextType {
  questions: GeneratedQuestion[];
  loading: boolean;
  error: string | null;
  selectedQuestions: Set<string>;
  editingQuestionId: string | null;
  
  generateQuestion: (materialId: string, promptTemplateId: string, templateIndex: number) => Promise<void>;
  saveQuestion: (questionId: string, questionText: string, rubric: any) => Promise<void>;
  deleteQuestion: (questionId: string) => Promise<void>;
  toggleQuestionSelection: (questionId: string) => void;
  setEditingQuestion: (questionId: string | null) => void;
  postQuestionsToStudents: (questionIds: string[]) => Promise<void>;
}

const QuestionContext = createContext<QuestionContextType | undefined>(undefined);

export const QuestionProvider: React.FC<{children: React.ReactNode, materialId: string}> = ({ children, materialId }) => {
  const [questions, setQuestions] = useState<GeneratedQuestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedQuestions, setSelectedQuestions] = useState<Set<string>>(new Set());
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null);
  
  useEffect(() => {
    // Load initial questions
    const loadQuestions = async () => {
      setLoading(true);
      try {
        const fetchedQuestions = await api.getQuestions(materialId);
        setQuestions(fetchedQuestions);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load questions');
      } finally {
        setLoading(false);
      }
    };
    
    loadQuestions();
  }, [materialId]);
  
  const generateQuestion = async (materialId: string, promptTemplateId: string, templateIndex: number) => {
    setLoading(true);
    try {
      const newQuestion = await api.generateQuestion(materialId, promptTemplateId, templateIndex);
      setQuestions(prev => [newQuestion, ...prev.filter(q => q.id !== newQuestion.id)]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate question');
    } finally {
      setLoading(false);
    }
  };
  
  const saveQuestion = async (questionId: string, questionText: string, rubric: any) => {
    setLoading(true);
    try {
      await api.updateQuestion(questionId, questionText, rubric);
      setQuestions(prev => prev.map(q => 
        q.id === questionId 
          ? { ...q, question: questionText, rubric } 
          : q
      ));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save question');
    } finally {
      setLoading(false);
    }
  };
  
  const deleteQuestion = async (questionId: string) => {
    setLoading(true);
    try {
      await api.deleteQuestion(questionId);
      setQuestions(prev => prev.filter(q => q.id !== questionId));
      setSelectedQuestions(prev => {
        const newSelection = new Set(prev);
        newSelection.delete(questionId);
        return newSelection;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete question');
    } finally {
      setLoading(false);
    }
  };
  
  const toggleQuestionSelection = (questionId: string) => {
    setSelectedQuestions(prev => {
      const newSelection = new Set(prev);
      if (newSelection.has(questionId)) {
        newSelection.delete(questionId);
      } else {
        newSelection.add(questionId);
      }
      return newSelection;
    });
  };
  
  const postQuestionsToStudents = async (questionIds: string[]) => {
    setLoading(true);
    try {
      await api.postQuestionsToStudents(questionIds);
      // Update questions to reflect published status
      setQuestions(prev => prev.map(q => 
        questionIds.includes(q.id) 
          ? { ...q, status: 'published', metadata: { ...q.metadata, publishedAt: new Date().toISOString() } }
          : q
      ));
      setSelectedQuestions(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to post questions');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <QuestionContext.Provider 
      value={{ 
        questions, 
        loading, 
        error, 
        selectedQuestions,
        editingQuestionId,
        generateQuestion,
        saveQuestion,
        deleteQuestion,
        toggleQuestionSelection,
        setEditingQuestion: setEditingQuestionId,
        postQuestionsToStudents
      }}
    >
      {children}
    </QuestionContext.Provider>
  );
};

export const useQuestions = () => {
  const context = useContext(QuestionContext);
  if (context === undefined) {
    throw new Error('useQuestions must be used within a QuestionProvider');
  }
  return context;
};