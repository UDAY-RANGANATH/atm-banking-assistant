import { describe, it, expect, vi } from 'vitest'

/**
 * Phase 5 frontend unit test: API-layer contract helpers.
 * The API module must be importable without DOM APIs (fetch is used lazily
 * at call time), so the form endpoint URLs are well-formed and the
 * application methods exist with the required signatures.
 */
import { api } from '../services/api'

describe('api form methods exist (Phase 5 contract)', () => {
  it('exposes all seven+ form endpoints', () => {
    for (const m of [
      'initApplication',
      'getApplicationForm',
      'autofillApplication',
      'getFieldMappings',
      'patchApplicationField',
      'confirmApplicationFields',
      'saveApplication',
      'getCompletionStatus',
    ] as const) {
      expect(typeof (api as Record<string, unknown>)[m], m).toBe('function')
    }
  })

  it('scanImageUrl builds the masked preview URL used by Review Source Document', async () => {
    const url = await api.scanImageUrl('scan_test123', 'processed')
    expect(url).toBe('/api/scanner/image/scan_test123?variant=processed')
  })
})

// ---- Phase 7: Multilingual AI Assistant ----

/**
 * Network-free contract checks: global.fetch is stubbed so the real client
 * code runs and the captured request (URL / method / headers / body) is
 * asserted. No paid API calls are involved anywhere in the pipeline.
 */
const capturedHref = (): string[] => {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
      calls.push(String(input))
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as unknown as typeof fetch,
  )
  return calls
}

describe('api AI assistant methods (Phase 7 contract)', () => {
  it('exposes the four AI endpoints', () => {
    for (const m of ['aiChat', 'aiHealth', 'aiSuggestions', 'clearConversation'] as const) {
      expect(typeof (api as Record<string, unknown>)[m], m).toBe('function')
    }
  })

  it('aiChat posts to /api/ai/chat with session + message (+language)', async () => {
    const calls = capturedHref()
    await api.aiChat('sid-chat', 'open a savings account', 'te')
    const init = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1] as RequestInit
    expect(calls[0]).toBe('/api/ai/chat')
    expect(init.method).toBe('POST')
    expect(JSON.parse(String(init.body))).toEqual({
      session_id: 'sid-chat',
      message: 'open a savings account',
      language: 'te',
    })
  })

  it('aiHealth GETs /api/ai/health', async () => {
    capturedHref()
    await api.aiHealth()
    const calls = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls
    expect(calls[0][0]).toBe('/api/ai/health')
    expect((calls[0][1] as RequestInit | undefined)?.method ?? 'GET').toBe('GET')
  })

  it('aiSuggestions forwards session and language filters', async () => {
    capturedHref()
    await api.aiSuggestions('sid-sug')
    expect((fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0]).toBe(
      '/api/ai/suggestions?session_id=sid-sug',
    )
    await api.aiSuggestions(undefined, 'hi')
    expect((fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[1][0]).toBe(
      '/api/ai/suggestions?language=hi',
    )
  })

  it('clearConversation sends DELETE with the ownership header X-Session-Id', async () => {
    capturedHref()
    await api.clearConversation('sid-del')
    const [href, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(href).toBe('/api/ai/conversation/sid-del')
    expect((init as RequestInit).method).toBe('DELETE')
    const headers = new Headers((init as RequestInit).headers)
    expect(headers.get('X-Session-Id')).toBe('sid-del')
  })

  it('aiChat surfaces HTTP errors (bad status throws)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('boom', { status: 404 })) as unknown as typeof fetch,
    )
    await expect(api.aiChat('sid', 'hello')).rejects.toThrow(/404/)
  })
})
