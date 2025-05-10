import { expect } from 'chai'
import { AIFeedbackService, AIFeedbackRecord } from './AIFeedbackService.js'
import { LMStudioService } from './LMStudioService.js'

describe('AIFeedbackService', () => {
  it('throws if the response is not found', async () => {
    // fake dbFn: any .first() yields undefined
    const fakeDbFn = (_table: string) => ({
      select: (_col?: string) => ({
        where: (_col: string, _val: any) => ({
          first: () => Promise.resolve(undefined),
        }),
      }),
    })

    const svc = new AIFeedbackService(
      fakeDbFn as any,
      new LMStudioService(),
      () => 'unused'
    )

    let didThrow = false
    try {
      await svc.generate('nope')
    } catch (err: any) {
      didThrow = true
      expect(err.message).to.equal('Response not found')
    }
    if (!didThrow) {
      throw new Error('Expected generate() to throw')
    }
  })

  it('inserts and returns AI feedback when response exists', async () => {
    const responseId    = 'resp-123'
    const studentAnswer = 'Student wrote this.'
    const feedbackText  = 'Great job!'
    const fakeTime      = '2025-05-01T12:00:00Z'
    const inserts: any[] = []

    function fakeDbFn(table: string) {
      if (table === 'responses') {
        return {
          select: (_col?: string) => ({
            where: (_col: string, _val: any) => ({
              first: () => Promise.resolve({ response: studentAnswer }),
            }),
          }),
        }
      }
      if (table === 'ai_feedback') {
        return {
          insert: (row: any) => {
            inserts.push(row)
            return Promise.resolve()
          },
          select: (_col?: string) => ({
            where: (_col: string, _val: any) =>
              Promise.resolve([
                {
                  id:            'uuid-xyz',
                  response_id:   responseId,
                  feedback_text: feedbackText,
                  created_at:    fakeTime,
                },
              ]),
          }),
        }
      }
      throw new Error(`Unexpected table: ${table}`)
    }

    // fake LLMService
    const fakeLm = new LMStudioService()
    ;(fakeLm as any).complete = (_: string) => Promise.resolve(feedbackText)

    const svc = new AIFeedbackService(
      fakeDbFn as any,
      fakeLm as any,
      () => 'uuid-xyz'
    )

    const out = await svc.generate(responseId)

    // verify we inserted exactly the right row
    expect(inserts).to.deep.equal([
      {
        id:            'uuid-xyz',
        response_id:   responseId,
        feedback_text: feedbackText,
      },
    ])

    // verify return value matches what the fake "where" gave us
    expect(out).to.deep.equal({
      id:            'uuid-xyz',
      response_id:   responseId,
      feedback_text: feedbackText,
      created_at:    fakeTime,
    } as AIFeedbackRecord)
  })
})