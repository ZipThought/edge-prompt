import { Project, PromptTemplate, Material } from '../types';
import { MaterialSource, ContentTemplate, ValidationResult } from '../../../backend/src/types';
import { data } from 'react-router-dom';

const API_BASE = 'http://localhost:3001/api';

export interface ApiError {
  error: string;
  details?: any;
}

export interface SignupData {
  firstname: string;
  lastname: string;
  email: string;
  password: string;
  dob: string;
  roleName: string;
}

export interface SigninData {
  email: string;
  password: string;
}

export interface UpdateProfileData {
  firstname: string;
  lastname: string;
  email: string;
  dob: string;
}

export interface Class {
  id?: string;
  name: string;
  description: string;
  students: string[];
  teacherId?: string;
}

class ApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = localStorage.getItem('token'); //  Get the token from local storage

    const requestOptions: RequestInit = {
      method: options.method || 'GET',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}), // Add Authorization if token exists
      },
    };

    const response = await fetch(`${API_BASE}${endpoint}`, requestOptions);

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.error || 'API request failed');
    }

    return response.json();
  }

  // Signup and authentication endpoints - connected to backend index.ts
  async signup(data: SignupData) {
    return this.request<{ message: String }>('/signup', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Signin and authentication endpoints - connected to backend index.ts
  async signin(data: SigninData) {
    return this.request<{ message: String, token: string, role: string, userId: string }>('/signin', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Profile credentials retrieval endpoints - connected to backend index.ts
  async getProfile() {
    return this.request<{
      firstname: string;
      lastname: string;
      email: string;
      dob: string;
    }>('/profile', {
      method: 'GET',
    });
  }

  // Profile credentials update endpoints - connected to backend index.ts
  async updateProfile(data: UpdateProfileData) {
    return this.request<{ message: string }>('/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // Profile password update endpoints - connected to backend index.ts
  async updatePassword(currentPassword: string, newPassword: string) {
    return this.request<{ message: string }>('/profile/password', {
      method: 'PUT',
      body: JSON.stringify({ currentPassword, newPassword }),
    });
  }

  // Validate a stored token (useful for app initialization)
  async validateToken() {
    return this.request<{ valid: boolean, user?: { userId: string, email: string, role: string } }>('/validate-token', {
      method: 'GET',
    });
  }

  // Helper method to attach auth headers to requests
  getAuthHeaders() {
    const token = localStorage.getItem('token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // Profile logout endpoints - connected to backend index.ts
  async signout() {
    return this.request<{ message: string }>('/signout', {
      method: 'POST',
    });
  }
  // Profile delete account endpoints - connected to backend index.ts
  async deleteAccount() {
    return this.request<{ message: string }>('/delete-account', {
      method: 'DELETE',
    });
  }
  
  // Class endpoints
  // Get all classes for a teacher
  async getClasses() {
    return this.request<Class[]>('/classes');
  }

  // Get a specific class by ID
  async getClass(id: string) {
    return this.request<Class>(`/classes/${id}`);
  }

  // Update class details
  async updateClass(id: string, classData: Partial<Class>) {
    return this.request<Class>(`/classes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(classData),
    });
  }

  // Delete a class
  async deleteClass(classId: string) {
    return this.request<{ message: string }>(`/classrooms/${classId}`, {
      method: 'DELETE',
    });
  }

  // Get classes by ID
  async getClassById(classId: string) {
    return this.request<{
      classId: string;
      className: string;
      subjectName?: string;
      learningMaterials: { id: string; title: string }[];
    }>(`/class/${classId}`);
  }

  // Add these methods to the ApiClient class in api.ts
  async getClassDetails(classId: string) {
    return this.request<Class>(`/classrooms/${classId}`);
  }
  
  async updateClassDetails(classId: string, data: Partial<Class>) {
    return this.request<{ message: string }>(`/classrooms/${classId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }
  
  async getEnrolledStudents(classId: string) {
    return this.request<{ id: string; name: string; email: string }[]>(
      `/classrooms/${classId}/students`
    );
  }
  
  async getAvailableStudents(classId: string) {
    return this.request<{ id: string; name: string; email: string }[]>(
      `/classrooms/${classId}/students/available`
    );
  }

  // Student Management Endpoints for Class
  // Add a student to a class
  async addStudentToClass(classId: string, studentId: string) {
    return this.request<{ message: string }>(
      `/classrooms/${classId}/students/${studentId}`,
      { method: 'POST' }
    );
  }

  // Remove a student from a class
  async removeStudentFromClass(classId: string, studentId: string) {
    return this.request<{ message: string }>(
      `/classrooms/${classId}/students/${studentId}`,
      { method: 'DELETE' }
    );
  }

  // Get all students (for selecting students to add to class)
  async getStudents() {
    return this.request<{ id: string; name: string; email: string }[]>('/users/students');
  }

  // Get a specific student by ID (for managing a student's details within a class)
  async getStudentById(studentId: string) {
    return this.request<{ id: string; name: string; email: string }>(`/users/students/${studentId}`);
  }

  // Get students enrolled in a specific class
  async getClassStudents(classId: string) {
    return this.request<{ id: string; name: string; email: string }[]>(`/classes/${classId}/students`);
  }

  // Get available students for class assignment
  async getAvailableStudentsForClass(classId: string) {
    return this.request<{ id: string; name: string; email: string }[]>(
      `/classes/${classId}/students/available`
    );
  }
  
  // Project endpoints
  async getProject(id: string): Promise<Project> {  // Corrected: Added getProject method
    return this.request<Project>(`/projects/${id}`);
  }
 
  async getProjects() {
    return this.request<Project[]>('/projects');
  }

  async getProjectsForClass(classroomId: string) {
    return this.request<Project[]>(`/classes/${classroomId}/projects`);
  }

  async createProject(project: Omit<Project, 'id' | 'createdAt'>) {
    return this.request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(project),
    });
  }

  async updateProject(id: string, project: Omit<Project, 'id' | 'createdAt'>) {
    return this.request<Project>(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(project),
    });
  }

  async deleteProject(id: string) {
    return this.request(`/projects/${id}`, {
      method: 'DELETE',
    });
  }

  // Prompt template endpoints
  async getPromptTemplates() {
    return this.request<PromptTemplate[]>('/prompt-templates');
  }

  async createPromptTemplate(template: Omit<PromptTemplate, 'id' | 'createdAt'>) {
    return this.request<PromptTemplate>('/prompt-templates', {
      method: 'POST',
      body: JSON.stringify(template),
    });
  }

  async updatePromptTemplate(id: string, template: Omit<PromptTemplate, 'id' | 'createdAt'>) {
    return this.request<PromptTemplate>(`/prompt-templates/${id}`, {
      method: 'PUT',
      body: JSON.stringify(template),
    });
  }

  async deletePromptTemplate(id: string) {
    return this.request(`/prompt-templates/${id}`, {
      method: 'DELETE',
    });
  }

  // Material endpoints
  async getMaterials(projectId: string) {
    return this.request<Material[]>(`/materials?projectId=${projectId}`);
  }

  async getMaterial(id: string) {
    return this.request<Material>(`/materials/${id}`);
  }

  async uploadMaterial(formData: FormData) {
    const token = localStorage.getItem('token');

    const response = await fetch(`${API_BASE}/materials/upload`, {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    });


    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.error || 'API request failed');
    }

    return response.json();
  }

  async deleteMaterial(id: string) {
    return this.request(`/materials/${id}`, {
      method: 'DELETE',
    });
  }

  // Question endpoints
  async generateQuestion(materialId: string, promptTemplateId: string, templateIndex: number, options: { useSourceLanguage?: boolean } = {}) {
    return this.request<any>('/generate', {
      method: 'POST',
      body: JSON.stringify({
        materialId,
        promptTemplateId,
        templateIndex,
        useSourceLanguage: options.useSourceLanguage || false
      }),
    });
  }

  async getQuestions(materialId: string) {
    return this.request<any[]>(`/questions?materialId=${materialId}`);
  }

  async saveQuestion(question: {
    materialId: string;
    promptTemplateId: string;
    question: string;
    questionId?: string;
    metadata?: any;
  }) {
    return this.request<any>('/questions', {
      method: 'POST',
      body: JSON.stringify(question),
    });
  }

  // Response validation endpoints
  async validateResponse(questionId: string, answer: string) {
    return this.request<ValidationResult>('/validate', {
      method: 'POST',
      body: JSON.stringify({
        questionId,
        answer
      }),
    });
  }

  async getResponses(questionId: string) {
    return this.request<any[]>(`/responses?questionId=${questionId}`);
  }

  async saveResponse(response: any) {
    return this.request<any>('/responses', {
      method: 'POST',
      body: JSON.stringify(response),
    });
  }

  async updateResponse(questionId: string, response: string) {  // Add this function
    return this.request<any>(`/responses/${questionId}`, {
      method: 'PUT',
      body: JSON.stringify({ response }),
    });
  }

  async finalSubmit(materialId: string): Promise<{ message: string }> {
    return this.request(`/responses/final-submit`, {
      method: 'POST',
      body: JSON.stringify({ materialId }),
    });
  }

  async isMaterialFinallySubmitted(materialId: string): Promise<{ isFinal: boolean }> {
    console.log('Checking final submission status for material:', materialId);
    return this.request(`/materials/${materialId}/final-submission`, {
        method: 'GET',
    });
  }

  // Content processing
  async processMaterial(material: MaterialSource, projectId: string) {
    return this.request<any>('/materials/process', {
      method: 'POST',
      body: JSON.stringify({ material, projectId }),
    });
  }

  async updateMaterialContent(id: string, content: string) {
    return this.request<Material>(`/materials/${id}/content`, {
      method: 'PATCH',
      body: JSON.stringify({ content }),
    });
  }

  async updateMaterialTitle(id: string, title: string) {
    return this.request<Material>(`/materials/${id}/title`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    });
  }

  async updateMaterial(id: string, data: { title?: string; content?: string; focusArea?: string }) {
    return this.request<Material>(`/materials/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }  
  async reprocessMaterial(id: string, formData: FormData) {
    const token = localStorage.getItem('token');

    const response = await fetch(`${API_BASE}/materials/${id}/reprocess`, {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    });


    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.error || 'API request failed');
    }

    return response.json();
  }

  // Delete a question
async deleteQuestion(questionId: string) {
  return this.request<{ message: string }>(`/questions/${questionId}`, {
    method: 'DELETE',
  });
}

// Update a question
async updateQuestion(questionId: string, updatedText: string) {
  return this.request<{ message: string }>(`/questions/${questionId}`, {
    method: 'PUT',
    body: JSON.stringify({ question: updatedText }),
  });
}

}

export const api = new ApiClient(); 