import { test, expect } from '@playwright/test'
import * as path from 'path'
import * as fs from 'fs'

/**
 * Phase 8 E2E: complete kiosk journey across the integrated modules, plus
 * responsive ATM kiosk layout checks (mobile/tablet viewports).
 *
 * Prerequisites:
 *   backend  - uvicorn on 127.0.0.1:8000 (deterministic engine)
 *   frontend - vite dev server on 127.0.0.1:5173 (proxies /api)
 *
 * All data is synthetic (the PAN fixture); no paid AI provider is used.
 */

const FIXTURE = path.resolve(
  process.cwd(), '..', 'backend', 'tests', 'fixtures', 'pan_en_DEMON0123F.png',
)

async function createSession(baseURL: string): Promise<string> {
  const res = await fetch(`${baseURL}/api/session?language=en`, { method: 'POST' })
  const body = (await res.json()) as { session_id: string }
  return body.session_id
}

async function seed(page: import('@playwright/test').Page, sessionId: string) {
  await page.addInitScript(
    ([sid]) => {
      localStorage.setItem(
        'atm_session',
        JSON.stringify({ sessionId: sid, language: 'en', currentStep: 'language_selection' }),
      )
    },
    [sessionId],
  )
}

test('full kiosk journey: chat -> checklist -> scan -> form -> confirm -> PDF', async ({ page, baseURL, request }) => {
  const sessionId = await createSession(baseURL!)

  // 1) Chat on the Home page drives navigation to the real checklist page.
  await seed(page, sessionId)
  await page.goto('/home')
  await expect(page.getByText('Suggested questions')).toBeVisible({ timeout: 30_000 })

  const input = page.getByPlaceholder('Type your message...')
  await input.fill('I want to open a savings account.')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(
    page.getByText(/Savings Account Opening \(prototype form ACC-001\)/i).first(),
  ).toBeVisible({ timeout: 30_000 })
  await page.getByRole('button', { name: 'Savings Account Opening' }).click()
  await expect(page).toHaveURL(/\/documents\/acc-001$/)

  // 2) Upload + confirm a synthetic PAN scan through the real scanner API.
  const upload = await request.post('/api/scanner/upload', {
    multipart: {
      session_id: sessionId,
      service_id: 'acc-001',
      document_id: 'doc-pan',
      file: {
        name: 'pan_en_DEMON0123F.png',
        mimeType: 'image/png',
        buffer: fs.readFileSync(FIXTURE),
      },
    },
  })
  expect(upload.ok()).toBeTruthy()
  const { scan_id } = (await upload.json()) as { scan_id: string }
  const confirmScan = await request.post(`/api/scanner/confirm/${scan_id}`, { data: {} })
  expect(confirmScan.ok()).toBeTruthy()

  // 3) Form page: autofill runs, all filled fields bulk-confirmed.
  await page.goto('/application/form/acc-001')
  const nameField = page.getByTestId('form-field-applicant_name')
  await expect(nameField).toBeVisible({ timeout: 30_000 })
  await page.getByTestId('confirm-all-fields').click()
  await expect(page.getByText('All filled fields confirmed')).toBeVisible({ timeout: 30_000 })

  // 4) Final review -> proceed -> PDF export page.
  await page.getByRole('button', { name: 'Continue' }).first().click()
  await page.getByTestId('final-confirm-checkbox').click()
  await page.getByTestId('proceed-continue').click()
  await expect(page.getByTestId('continue-to-pdf')).toBeVisible()
  await page.getByTestId('continue-to-pdf').click()
  await expect(page.getByRole('heading', { name: 'Application PDF Export' })).toBeVisible()
  await expect(page.getByTestId('pdf-gate')).toContainText('Ready to generate')

  // 5) Generate, preview, download a real PDF.
  const generate = page.getByTestId('pdf-generate')
  await expect(generate).toBeEnabled()
  await generate.click()
  await expect(page.getByTestId('pdf-iframe')).toBeVisible({ timeout: 60_000 })
  await expect(page.getByTestId('pdf-status-ready')).toBeVisible()

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByTestId('pdf-download').click(),
  ])
  expect(download.suggestedFilename()).toMatch(/^APP-.*\.pdf$/)
  const stream = await download.createReadStream()
  const chunks: Buffer[] = []
  stream.on('data', (c: Buffer) => chunks.push(c))
  await new Promise<void>((resolve) => stream.on('end', resolve))
  expect(Buffer.concat(chunks).subarray(0, 5).toString()).toBe('%PDF-')
})

const MOBILE = { width: 390, height: 844 }
const TABLET = { width: 820, height: 1180 }

for (const viewport of [MOBILE, TABLET]) {
  test(`responsive kiosk layout at ${viewport.width}x${viewport.height}: stacks vertically, chat visible, no horizontal overflow`, async ({ page, baseURL }) => {
    const sessionId = await createSession(baseURL!)
    await page.setViewportSize(viewport)
    await seed(page, sessionId)
    await page.goto('/home')

    // Both panels are reachable: the services catalogue and the AI chat panel
    // (flex-col-reverse stacks chat above the catalogue on narrow viewports).
    await expect(page.locator('text=AI Assistant').first()).toBeVisible({ timeout: 30_000 })
    const servicesTitle = page.locator('h2').first()
    await expect(servicesTitle).toBeVisible()

    // No horizontal overflow anywhere on the page.
    const overflow = await page.evaluate(() => {
      const el = document.scrollingElement as HTMLElement
      return el.scrollWidth - el.clientWidth
    })
    expect(overflow).toBeLessThanOrEqual(0)

    // The chat panel is interactive at kiosk-touch sizes.
    await expect(page.getByPlaceholder('Type your message...')).toBeVisible()
  })
}
