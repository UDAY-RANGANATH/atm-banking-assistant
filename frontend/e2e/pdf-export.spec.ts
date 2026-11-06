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

function seedSession(sessionId: string) {
  return (page: import('@playwright/test').Page) => {
    page.addInitScript(([sid]) => {
      localStorage.setItem(
        'atm_session',
        JSON.stringify({ sessionId: sid, language: 'en', currentStep: 'language_selection' }),
      )
    }, [sessionId])
  }
}

test('PDF export page blocks generation until fields are customer-confirmed', async ({ page, baseURL }) => {
  const sessionId = await createSession(baseURL!)

  await page.addInitScript(
    ([sid]) => {
      localStorage.setItem(
        'atm_session',
        JSON.stringify({ sessionId: sid, language: 'en', currentStep: 'language_selection' }),
      )
    },
    [sessionId],
  )

  await page.goto('/application/pdf/acc-001')
  await expect(page.getByRole('heading', { name: 'Application PDF Export' })).toBeVisible()
  await expect(page.getByText('EDUCATIONAL PROTOTYPE — NOT AN OFFICIAL BANK DOCUMENT').first()).toBeVisible()

  // No fields confirmed in this session -> generation blocked
  await expect(page.getByTestId('pdf-status-blocked')).toBeVisible()
  const generate = page.getByTestId('pdf-generate')
  await expect(generate).toBeDisabled()
  await expect(page.getByTestId('pdf-gate')).toContainText('PDF generation is blocked')
  await expect(page.getByTestId('pdf-gate')).toContainText(/customer-confirmed field is required/i)
})

test('full flow: confirm fields in form, then generate, preview and download the PDF', async ({ page, baseURL, request }) => {
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
  const confirm = await request.post(`/api/scanner/confirm/${uploadBody.scan_id}`, { data: {} })
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

  // 1) Form page: autofill runs, then bulk-confirm all filled fields
  await page.goto('/application/form/acc-001')
  const nameField = page.getByTestId('form-field-applicant_name')
  await expect(nameField).toBeVisible({ timeout: 30_000 })
  await expect(page.getByTestId('confirm-all-fields')).toBeVisible()
  await page.getByTestId('confirm-all-fields').click()
  await expect(page.getByText('All filled fields confirmed')).toBeVisible({ timeout: 30_000 })

  // 2) Continue -> final review -> proceed records confirmations, done modal
  await page.getByRole('button', { name: 'Continue' }).first().click()
  await page.getByTestId('final-confirm-checkbox').click()
  await page.getByTestId('proceed-continue').click()
  await expect(page.getByTestId('continue-to-pdf')).toBeVisible()

  // 3) Continue to the PDF export page
  await page.getByTestId('continue-to-pdf').click()
  await expect(page.getByRole('heading', { name: 'Application PDF Export' })).toBeVisible()
  await expect(page.getByTestId('pdf-status-empty')).toBeVisible()
  await expect(page.getByTestId('pdf-gate')).toContainText('Ready to generate')
  const generate = page.getByTestId('pdf-generate')
  await expect(generate).toBeEnabled()

  // 4) Generate -> status flips to Ready and the PDF preview renders
  await generate.click()
  await expect(page.getByTestId('pdf-iframe')).toBeVisible({ timeout: 60_000 })
  await expect(page.getByTestId('pdf-status-ready')).toBeVisible()

  // 5) Download produces a real PDF file
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByTestId('pdf-download').click(),
  ])
  expect(download.suggestedFilename()).toMatch(/^APP-.*\.pdf$/)
  const stream = await download.createReadStream()
  const chunks: Buffer[] = []
  stream.on('data', (c: Buffer) => chunks.push(c))
  await new Promise<void>((resolve) => stream.on('end', resolve))
  const head = Buffer.concat(chunks).subarray(0, 5).toString()
  expect(head).toBe('%PDF-')
})
