/**
 * Domain-constrained content template (Tc from the paper)
 */
export interface ContentTemplate {
  pattern: string;           // Question pattern (e.g., "Write a descriptive paragraph about [topic]")
  constraints: string[];     // Domain constraints (e.g., ["Grade-appropriate", "Safe content"])
  subject: string;           // Subject area
  targetGrade: string;       // Target grade level
  source: any;               // Source material reference
  
  // Answer space specification (As from the paper)
  answerSpace: {
    minWords: number;        // Minimum word count
    maxWords: number;        // Maximum word count
    vocabulary: string;      // Vocabulary requirements (e.g., "grade-appropriate")
    structure: string;       // Structure requirements (e.g., "paragraph format")
  };
  
  // Learning objective mapping (O: Tc → L from the paper)
  learningObjectives: string[];  // Mapped learning outcomes
}

/**
 * Validation parameters (vp from the paper)
 */
export interface ValidationParameters {
  threshold: number;         // Confidence threshold
  boundaries: {
    min: number;             // Minimum score
    max: number;             // Maximum score
  };
}

/**
 * Teacher criteria (ct from the paper)
 */
export interface TeacherCriteria {
  relevance: number;         // Weight for relevance to question
  clarity: number;           // Weight for clarity of expression
  accuracy: number;          // Weight for factual accuracy
  creativity: number;        // Weight for creative expression
  grammar: number;           // Weight for grammatical correctness
  vocabulary: number;        // Weight for vocabulary usage
}

/**
 * Formalized rubric (R(ct, vp) from the paper)
 */
export interface FormalizedRubric {
  criteria: TeacherCriteria;
  parameters: ValidationParameters;
  scoringLevels: {
    [level: number]: string;  // Description of each scoring level
  };
}

/**
 * Edge-compatible transformed rubric (R' from the paper)
 */
export interface EdgeRubric {
  criteriaWeights: { [criteria: string]: number };
  validationChecks: string[];
  scoringGuidelines: string[];
  maxScore: number;
}

/**
 * Generated question with validation structure
 */
export interface GeneratedQuestion {
  id: string;
  materialId: string;
  promptTemplateId: string;
  questionId?: string;
  question: string;
  template?: any;
  rubric?: any;
  metadata: {
    generatedAt: string;
    templateIndex?: number;
    validationStages?: string[];
  };
}

/**
 * Validation result from backend
 */
export interface ValidationResult {
  isValid: boolean;
  score: number;
  feedback: string;
  details?: any;
  error?: string;
  id?: string;
} 