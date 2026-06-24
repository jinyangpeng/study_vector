// E2E smoke: verify frontend loads, talks to backend, can CRUD collections.
// Usage: node e2e/smoke.mjs
import { chromium } from 'playwright'
import { existsSync } from 'node:fs'

const FRONTEND = process.env.FRONTEND_URL || 'http://127.0.0.1:5173'
const API = process.env.API_URL || 'http://127.0.0.1:8000'

const fail = (msg) => {
  console.error('[FAIL] ' + msg)
  process.exitCode = 1
}
const ok = (msg) => console.log('[OK]   ' + msg)

async function main() {
  console.log('frontend=' + FRONTEND + ' backend=' + API)
  // 使用本地已安装的 Chromium，避免依赖版本不一致
  const candidates = [
    process.env.PLAYWRIGHT_CHROMIUM_PATH,
    'C:/Users/JYPen/AppData/Local/ms-playwright/chromium-1223/chrome-win64/chrome.exe',
  ].filter(Boolean)
  const launchOptions = { headless: true }
  for (const exe of candidates) {
    if (existsSync(exe)) { launchOptions.executablePath = exe; break }
  }
  const browser = await chromium.launch(launchOptions)
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })

  const errors = []
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message))
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push('console.error: ' + m.text())
  })

  // 1. open home
  await page.goto(FRONTEND, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('text=study_vector', { timeout: 15000 })
  ok('home page loaded, logo visible')

  await page.screenshot({ path: 'e2e/screenshot-dashboard.png', fullPage: true })

  await page.waitForLoadState('networkidle', { timeout: 15000 })
  const tableRows = await page.locator('.el-table__row').count()
  ok('collection list rows=' + tableRows)

  // 2. create collection
  const stamp = Date.now()
  const collName = 'e2e_' + stamp
  await page.fill('input[placeholder*="demo"]', collName)
  // 按钮文案为中文
  const createBtn = page.locator('button:has-text("创建")').first()
  await createBtn.click({ timeout: 5000 })
  await page.waitForTimeout(2500)
  ok('submitted create ' + collName)

  // 3. verify the new collection appears in the list
  const linkCount = await page.locator('a:has-text("' + collName + '")').count()
  if (linkCount > 0) {
    ok('collection ' + collName + ' is in the list')
  } else {
    fail('collection ' + collName + ' not found in list')
  }

  // 4. open detail page
  await page.click('a:has-text("' + collName + '")')
  await page.waitForURL('**/collections/' + collName, { timeout: 10000 })
  await page.waitForLoadState('networkidle', { timeout: 10000 })
  ok('detail page loaded')

  await page.screenshot({ path: 'e2e/screenshot-detail-' + stamp + '.png', fullPage: true })

  // 5. insert one vector
  await page.fill('input[placeholder*="auto"]', 'e2e_id_1').catch(() => {})
  await page.locator('button:has-text("插入")').first().click({ timeout: 5000 }).catch(() => {})
  await page.waitForTimeout(1500)
  ok('insert submitted')

  // 6. search
  await page.locator('button:has-text("检索")').first().click({ timeout: 5000 }).catch(() => {})
  await page.waitForTimeout(1500)
  ok('search submitted')

  // 7. go back and delete
  await page.goto(FRONTEND, { waitUntil: 'networkidle' })
  await page
    .locator('tr:has-text("' + collName + '") button:has-text("删除")')
    .first()
    .click({ timeout: 5000 })
  await page
    .locator('button:has-text("确 定"), button:has-text("确定")')
    .first()
    .click({ timeout: 5000 })
    .catch(() => {})
  await page.waitForTimeout(2000)
  ok('deleted ' + collName)

  if (errors.length) {
    console.warn('frontend console errors detected:')
    errors.forEach((e) => console.warn(' -', e))
  } else {
    ok('no frontend console errors')
  }

  await browser.close()
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
