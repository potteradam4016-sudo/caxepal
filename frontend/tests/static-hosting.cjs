const assert = require('node:assert/strict')
const fs = require('node:fs/promises')
const http = require('node:http')
const path = require('node:path')
const { chromium } = require('playwright')

const root = path.resolve(__dirname, '../dist')
const mimeTypes = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png' }

const server = http.createServer(async (request, response) => {
  const pathname = new URL(request.url, 'http://localhost').pathname
  const file = path.resolve(root, pathname === '/' ? 'index.html' : pathname.slice(1))
  if (!file.startsWith(root + path.sep)) {
    response.writeHead(403).end()
    return
  }
  try {
    response.setHeader('Content-Type', mimeTypes[path.extname(file)] || 'application/octet-stream')
    response.end(await fs.readFile(file))
  } catch {
    response.writeHead(404).end()
  }
})

async function main() {
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
  let browser
  try {
    browser = await chromium.launch({ headless: true })
    const page = await browser.newPage()
    const base = `http://127.0.0.1:${server.address().port}`
    await page.goto(`${base}/#/login`)
    await page.locator('input[autocomplete="username"]').waitFor()
    await page.reload()
    await page.locator('input[autocomplete="username"]').waitFor()
    await page.goto(`${base}/#/recommend`)
    await page.waitForURL('**/#/login')
    assert.equal(await page.locator('input[autocomplete="username"]').count(), 1)
    console.log('Static hosting hash routes: direct visit, reload, and access guard passed')
  } finally {
    if (browser) await browser.close()
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()))
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1 })
