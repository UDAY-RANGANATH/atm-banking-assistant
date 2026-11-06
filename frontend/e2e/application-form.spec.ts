import { test, expect } from '@playwright/test'
import * as path from 'path'
import * as fs from 'fs'

const FIXTURE = path.resolve(
  process.cwd(), '..', 'backend', 'tests', 'fixtures', 'pan_en_DEMON0123F.png',
)

async function createSession(baseURL: string): Promise<string> {
  const res = await fetch(`${baseURL}/api/session?language=en`, { method: 'POST' })
  const body = (await res.json()) as { session_id: string }
  return body.session_id
}

test('form page renders multilingual UI and allows manual field completion', async ({ page, baseURL }) => {
  test.skip(!fs.existsSync(`${FIXTURE}`), 'fixture missing')
  const sessionId = await createSession(baseURL!)

  // Seed the kiosk session (same mechanism the app uses)
  await page.addInitScript(
    ([sid]) => {
      localStorage.setItem(
        'atm_session',
        JSON.stringify({ sessionId: sid, language: 'en', currentStep: 'language_selection' }),
      )
    },
    [sessionId],
  )

  await page.goto('/application/form/acc-001')
  await expect(page.getByRole('heading', { name: 'Application Form' })).toBeVisible()
  await expect(page.getByText(/Educational prototype/)).toBeVisible()
  await expect(page.getByText('Form No.')).toBeVisible()
  await expect(page.getByText('ACC-001')).toBeVisible()

  // All fields start as MISSING with manual-entry affordances
  await expect(page.getByTestId('form-field-mobile_number')).toBeVisible()
  const mobile = page.locator('#in-mobile_number')
  await mobile.fill('9876543210')
  await mobile.blur()
  await expect(
    page.locator('[data-testid="form-field-mobile_number"] [data-testid="field-status-CUSTOMER_EDITED"]'),
  ).toBeVisible()

  // Save progress (never submits)
  await page.getByRole('button', { name: 'Save Progress' }).first().click()
  await expect(page.getByText('Progress saved. Nothing has been submitted.')).toBeVisible()
})

test('OCR autofill populates customer-confirmed scan values with status badges', async ({ page, baseURL, request }) => {
  const sessionId = await createSession(baseURL!)

  // Upload + confirm a synthetic PAN scan through the real Phase 4 pipeline
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
  const uploadBody = (await upload.json()) as { scan_id: string }
  const confirm = await request.post(`/api/scanner/confirm/${uploadBody.scan_id}`, {
    data: {},
  })
  expect(confirm.ok()).toBeTruthy()

  await page.addInitScript(
    ([sid]) => {
      localStorage.setItem(
        'atm_session',
        JSON.stringify({ sessionId: sid, language: 'en', currentStep: 'language_selection' }),
      )
    },
    [sessionId],
  )

  await page.goto('/application/form/acc-001')
  // The page auto-runs autofill after init; the PAN value must appear.
  const nameField = page.getByTestId('form-field-applicant_name')
  await expect(nameField).toBeVisible({ timeout: 30_000 })
  await expect(
    nameField.locator('[data-testid="field-status-AUTO_FILLED"], [data-testid="field-status-LOW_CONFIDENCE"]'),
  ).toBeVisible()
  const committed = await nameField.locator('input').first().inputValue()
  expect(committed.trim().length).toBeGreaterThan(2)

  // Accept the auto-filled value -> CUSTOMER_CONFIRMED badge
  await nameField.getByTestId('accept-value').click()
  await expect(
    nameField.locator('[data-testid="field-status-CUSTOMER_CONFIRMED"]'),
  ).toBeVisible()
})
