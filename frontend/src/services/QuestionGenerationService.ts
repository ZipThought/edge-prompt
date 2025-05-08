import { api } from './api';

export class QuestionGenerationService {
  /**
   * Generates a question using backend processing
   */
  static async generateQuestion(
    materialId: string,
    promptTemplateId: string,
    templateIndex: number,
    useSourceLanguage: boolean = false
  ): Promise<any> {
    try {
      return await api.generateQuestion(
        materialId,
        promptTemplateId,
        templateIndex,
        { useSourceLanguage }
      );
    } catch (error) {
      console.error("Error in question generation:", error);
      throw new Error("Failed to generate question. Please try again later.");
    }
  }
  
  /**
   * Saves a generated question to the database
   */
  static async saveGeneratedQuestion(question: any): Promise<any> {
    try {
      return await api.saveQuestion({
        materialId: question.materialId,
        promptTemplateId: question.promptTemplateId,
        question: question.question,
        metadata: question.metadata
      });
    } catch (error) {
      console.error("Error saving question:", error);
      throw new Error("Failed to save generated question.");
    }
  }
  
  /**
   * Deletes all questions for a specific material
   */
  static async deleteAllMaterialQuestions(materialId: string): Promise<void> {
    try {
      const questions = await api.getQuestions(materialId);
      if (questions.length > 0) {
        await api.deleteQuestions(questions.map(q => q.id));
      }
    } catch (error) {
      console.error("Error deleting questions:", error);
      throw new Error("Failed to delete existing questions.");
    }
  }
}