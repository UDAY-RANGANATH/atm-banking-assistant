import { test, expect } from '@playwright/test'

/**
 * Phase 7 E2E: multilingual AI assistant chat on the kiosk Home page.
 *
 * Prerequisites:
 *   backend  - uvicorn on 127.0.0.1:8000 (deterministic engine, no external AI)
 *   frontend - vite dev server on 127.0.0.1:5173 (proxies /api)
 *
 * All conversations use the deterministic catalogue-grounded engine, so the
 * flow is fully reproducible without any paid AI call.
 */

async function seedSession(baseURL: string): Promise<string> {
  const res = await fetch(`${baseURL}/api/session?language=en`, { method: 'POST' })
  const body = (await res.json()) as { session_id: string }
  return body.session_id
}

async function gotoHomeWithSession(page: import('@playwright/test').Page, sessionId: string) {
  await page.addInitScript(
    ([sid]) => {
      localStorage.setItem(
        'atm_session',
        JSON.stringify({ sessionId: sid, language: 'en', currentStep: 'language_selection' }),
      )
    },
    [sessionId],
  )
  await page.goto('/home')
}

test('suggestion chip click produces a catalogue-grounded assistant reply', async ({ page, baseURL }) => {
  const sessionId = await seedSession(baseURL!)
  await gotoHomeWithSession(page, sessionId)

  const chat = page.locator('text=AI Assistant').first()
  await expect(chat).toBeVisible()
  await expect(page.locator('text=Suggested questions')).toBeVisible({ timeout: 30_000 })

  // Suggested questions are served by GET /api/ai/suggestions (language en).
  await page.getByRole('button', { name: 'What is KYC?' }).click()
  await expect(
    page.getByText(/Know Your Customer/i).last(),
  ).toBeVisible({ timeout: 30_000 })
})

test('service question returns a navigation action that opens the checklist', async ({ page, baseURL }) => {
  const sessionId = await seedSession(baseURL!)
  await gotoHomeWithSession(page, sessionId)

  await expect(page.getByText('Suggested questions')).toBeVisible({ timeout: 30_000 })

  const input = page.getByPlaceholder('Type your message...')
  await input.fill('I want to open a savings account.')
  await page.getByRole('button', { name: 'Send' }).click()

  // The reply names the real service from the catalogue.
  await expect(
    page.getByText(/Savings Account Opening \(prototype form ACC-001\)/i).first(),
  ).toBeVisible({ timeout: 30_000 })

  // The assistant only OFFERS navigation; tapping it starts the application.
  await page.getByRole('button', { name: 'Savings Account Opening' }).click()
  await expect(page).toHaveURL(/\/documents\/acc-001$/)
})

test('clear chat empties the conversation and confirms the reset', async ({ page, baseURL }) => {
  const sessionId = await seedSession(baseURL!)
  await gotoHomeWithSession(page, sessionId)

  await expect(page.getByText('Suggested questions')).toBeVisible({ timeout: 30_000 })
  await page.getByRole('button', { name: 'What is KYC?' }).click()
  await expect(page.getByText(/Know Your Customer/i).last()).toBeVisible({ timeout: 30_000 })

  await page.getByRole('button', { name: 'Clear chat' }).click()
  await expect(page.getByText(/Chat history cleared/i)).toBeVisible({ timeout: 30_000 })
  // The assistant's earlier KYC answer is gone from the visible thread.
  await expect(page.getByText(/Know Your Customer/i)).toHaveCount(0)
})
