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

class ApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(`<span class="math-inline">\{API\_BASE\}</span>{endpoint}`, {
      method: options.method || 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
      ...options,
      credentials: 'include' //  Crucial line for cookies!
    });
    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.error || 'API request failed');
    }

    return response.json();
  }

  // Signup and authentication endpoints - connected to backend index.ts
  async signup(data: SignupData) {
    return this.request<{ token: string }>('/signup', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Signin and authentication endpoints - connected to backend index.ts
  async signin(data: SigninData) {
    return this.request<{ token: string }>('/signin', {
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
  
  // Project endpoints
  async getProjects() {
    return this.request<Project[]>('/projects');
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
    const response = await fetch(`${API_BASE}/materials/upload`, {
      method: 'POST',
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

  async reprocessMaterial(id: string, formData: FormData) {
    const response = await fetch(`${API_BASE}/materials/${id}/reprocess`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.error || 'API request failed');
    }

    return response.json();
  }
}

export const api = new ApiClient(); 