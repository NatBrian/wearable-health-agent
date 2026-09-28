import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api'

function response(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('HTTP API error and absence handling', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  it('does not turn an unexpected resource 404 into an empty success', async () => {
    vi.mocked(fetch).mockResolvedValue(response(404, { detail: 'route not found' }))

    await expect(api.listSubjects()).rejects.toMatchObject({ status: 404 })
  })

  it('treats an absent night detail as optional but still reports a failed request', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(response(404, { detail: 'No such night' }))
    await expect(api.getNightDetail('sim', '2026-09-01')).resolves.toBeNull()

    vi.mocked(fetch).mockResolvedValueOnce(response(503, { detail: 'database unavailable' }))
    await expect(api.getNightDetail('sim', '2026-09-01')).rejects.toMatchObject({ status: 503 })
  })

  it('can scope Today conversation sessions to the active night', async () => {
    vi.mocked(fetch).mockResolvedValue(response(200, []))

    await api.getConversationSessions('sim', 40, '2026-09-04')

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('since_night=2026-09-04'),
      expect.objectContaining({ cache: 'no-store' }),
    )
  })

  it('exposes the existing record, review, settings, profile and diagnostic routes', () => {
    expect(api.listPipelineNights).toBeTypeOf('function')
    expect(api.submitReview).toBeTypeOf('function')
    expect(api.getUrgency).toBeTypeOf('function')
    expect(api.acknowledgeUrgency).toBeTypeOf('function')
    expect(api.getHandover).toBeTypeOf('function')
    expect(api.getAudit).toBeTypeOf('function')
    expect(api.exportAudit).toBeTypeOf('function')
    expect(api.getKnowledgeProvenance).toBeTypeOf('function')
    expect(api.getSubjectProfile).toBeTypeOf('function')
    expect(api.updateSubjectProfile).toBeTypeOf('function')
    expect(api.testComponent).toBeTypeOf('function')
    expect(api.deleteSubject).toBeTypeOf('function')
  })
})
