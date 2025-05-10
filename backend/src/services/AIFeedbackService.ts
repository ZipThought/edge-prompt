import { LMStudioService } from './LMStudioService.js'
import { v4 as uuidv4 } from 'uuid'

export interface AIFeedbackRecord {
  id: string
  response_id: string
  feedback_text: string
  created_at: string
}

/**
 * dbFn is a function you pass in that behaves like
 *   dbFn(tableName).select(...).where(...).first()  → Promise<{ response }>
 *   dbFn('ai_feedback').insert(row)               → Promise<void>
 *   dbFn('ai_feedback').select(...).where(...)    → Promise<[record]>
 *
 * You can inject your real knex/db there in production.
 */
export class AIFeedbackService {
  constructor(
    private dbFn: (table: string) => any,
    private llm: { complete(prompt: string): Promise<string> },
    private uuidFn: () => string = uuidv4
  ) {}

  async generate(responseId: string): Promise<AIFeedbackRecord> {
    // 1) fetch student’s raw response
    const respRow = await this.dbFn('responses')
      .select('response')
      .where('id', responseId)
      .first()
    if (!respRow) {
      throw new Error('Response not found')
    }

    // 2) get feedback from LLM
    const feedbackText = await this.llm.complete(respRow.response)

    // 3) insert into ai_feedback
    const id = this.uuidFn()
    await this.dbFn('ai_feedback').insert({
      id,
      response_id: responseId,
      feedback_text: feedbackText,
    })

    // 4) read it back
    const [record] = await this.dbFn('ai_feedback')
      .select('*')
      .where('id', id)

    return record as AIFeedbackRecord
  }
}
