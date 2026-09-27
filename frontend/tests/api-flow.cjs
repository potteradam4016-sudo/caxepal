const assert = require('node:assert/strict')
const { spawn, spawnSync } = require('node:child_process')
const fs = require('node:fs')
const net = require('node:net')
const path = require('node:path')
const { setTimeout: delay } = require('node:timers/promises')
const { chromium } = require('playwright')

const frontend = path.resolve(__dirname, '..')
const backend = path.resolve(frontend, '../backend')
const output = path.join(frontend, 'test-results')
const children = []
async function freePort() {
  const server = net.createServer()
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
  const port = server.address().port
  await new Promise((resolve) => server.close(resolve))
  return port
}
function launch(command, args, options) {
  const child = spawn(command, args, { ...options, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] })
  child.output = ''
  child.stdout.on('data', (chunk) => { child.output += chunk })
  child.stderr.on('data', (chunk) => { child.output += chunk })
  child.on('error', (error) => { child.launchError = error })
  children.push(child)
  return child
}
async function waitReady(url, child) {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (child.launchError) throw child.launchError
    if (child.exitCode !== null) throw new Error(child.output)
    try { if ((await fetch(url)).ok) return } catch {}
    await delay(200)
  }
  throw new Error('Server did not start: ' + child.output)
}
async function stop(child, graceful = false) {
  if (child.exitCode !== null || child.launchError) return
  if (graceful) {
    child.stdin.end('stop\n')
    for (let attempt = 0; attempt < 50 && child.exitCode === null; attempt++) await delay(100)
  }
  if (child.exitCode === null) {
    if (process.platform === 'win32') spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' })
    else child.kill('SIGTERM')
    for (let attempt = 0; attempt < 50 && child.exitCode === null; attempt++) await delay(100)
  }
}
async function main() {
  const apiPort = await freePort()
  const webPort = await freePort()
  const apiUrl = `http://127.0.0.1:${apiPort}`
  const webUrl = `http://127.0.0.1:${webPort}`
  const python = path.join(backend, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
  const apiServer = launch(python, ['-m', 'tests.serve_frontend_fixture', '--port', String(apiPort), '--frontend-port', String(webPort)],
    { cwd: backend, env: { ...process.env, PYTHONUTF8: '1' } })
  let browser
  let page
  const httpErrors = []
  try {
    await waitReady(apiUrl + '/health', apiServer)
    const vite = launch(process.execPath, [path.join(frontend, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', String(webPort), '--strictPort'],
      { cwd: frontend, env: { ...process.env, VITE_API_BASE_URL: apiUrl } })
    await waitReady(webUrl, vite)
    browser = await chromium.launch({ headless: true })
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' })
    page = await context.newPage()
    page.on('response', (response) => {
      if (response.url().startsWith(apiUrl) && response.status() >= 400) httpErrors.push({ path: new URL(response.url()).pathname, status: response.status() })
    })
    page.on('requestfailed', (request) => { httpErrors.push({ path: new URL(request.url()).pathname, failure: request.failure()?.errorText }) })
    const errors = []
    page.on('pageerror', (error) => errors.push(error.message))
    fs.mkdirSync(output, { recursive: true })
    async function screenshot(name) {
      await page.evaluate(() => document.fonts.ready)
      await page.screenshot({ path: path.join(output, name + '.png'), fullPage: false })
    }
    async function fits(name) {
      const metrics = await page.evaluate(() => ({
        width: window.innerWidth, scroll: document.documentElement.scrollWidth,
        bodyScroll: document.body.scrollWidth,
        root: document.querySelector('#root')?.getBoundingClientRect().toJSON(),
        layout: document.querySelector('.auth-layout, .app-shell')?.getBoundingClientRect().toJSON(),
        images: [...document.querySelectorAll('img')].every((img) => img.complete && img.naturalWidth > 0),
      }))
      assert.ok(metrics.scroll <= metrics.width + 1, name + ' horizontal overflow: ' + JSON.stringify(metrics))
      assert.ok(metrics.images, name + ' missing image')
    }
    const click = (name) => page.getByRole('button', { name, exact: true }).click()
    async function setSize(width, height) {
      await page.setViewportSize({ width, height })
      await page.waitForFunction(({ width, height }) => {
        if (window.innerWidth !== width || window.innerHeight !== height) return false
        const expected = 1.1 * (width <= 680 ? 1 : Math.min(width / 2560, height / 1440))
        const layout = document.querySelector('.auth-layout, .app-shell')
        const renderedWidth = width <= 680 ? width : Math.min(width, height * 2560 / 1440)
        return Math.abs(Number(document.querySelector('#root').style.zoom) - expected) < 0.0001 &&
          Math.abs(layout.getBoundingClientRect().width - renderedWidth) < 1
      }, { width, height })
    }
    async function measure(selectors) {
      return page.evaluate((names) => Object.fromEntries(names.map((name) => {
        const rect = document.querySelector(name).getBoundingClientRect()
        return [name, { x: rect.x, y: rect.y, width: rect.width, height: rect.height }]
      })), selectors)
    }
    async function compareComposition(selectors, sizes) {
      await setSize(2560, 1440)
      const reference = await measure(selectors)
      for (const { width, height } of sizes) {
        await setSize(width, height)
        const actual = await measure(selectors)
        const scale = Math.min(width / 2560, height / 1440)
        for (const selector of selectors) {
          for (const property of selector === '.main-content' || selector === '.page' ? ['x', 'y', 'width'] : ['x', 'y', 'width', 'height']) {
            const delta = Math.abs(actual[selector][property] / scale - reference[selector][property])
            assert.ok(delta < 5, `${selector} ${property} changed at ${width}x${height}: ${JSON.stringify({ delta, actual: actual[selector][property], reference: reference[selector][property], scale })}`)
          }
        }
      }
    }
    async function checkAuthSizes(name) {
      for (const width of [390, 320]) {
        await setSize(width, 844)
        await fits(name + ' ' + width)
        await screenshot(name + '-' + width)
      }
      await setSize(1440, 1000)
    }
    await page.goto(webUrl + '/recommend')
    await page.getByRole('heading', { name: '로그인', exact: true }).waitFor()
    await screenshot('01-login')
    await compareComposition(['.auth-layout', '.auth-story', '.auth-panel'], [
      { width: 1920, height: 1080 }, { width: 1280, height: 720 },
    ])
    await setSize(1440, 1000)
    await checkAuthSizes('login')
    await page.getByRole('link', { name: '회원가입' }).click()
    await page.getByRole('heading', { name: '회원가입', exact: true }).waitFor()
    await checkAuthSizes('signup')
    await page.getByLabel('아이디', { exact: true }).fill('integration_user')
    await page.getByLabel('비밀번호', { exact: true }).fill('integration-password-123')
    await page.getByLabel('비밀번호 확인', { exact: true }).fill('integration-password-123')
    await click('가입하고 시작하기')
    await page.waitForURL('**/academic')
    await page.getByLabel('학과', { exact: true }).fill('컴퓨터공학과')
    await page.getByLabel('학년', { exact: true }).selectOption('2')
    await page.getByLabel('학적 상태', { exact: true }).selectOption('enrolled')
    await screenshot('02-academic')
    await checkAuthSizes('academic')
    await click('다음')
    await page.waitForURL('**/preferences')
    await click('AI·SW 선택')
    await click('해커톤 선택')
    await page.reload()
    await page.getByRole('button', { name: 'AI·SW 선택됨', exact: true }).waitFor()
    await screenshot('03-preferences')
    await checkAuthSizes('preferences')
    await click('선택 완료')
    await page.getByRole('heading', { name: '맞춤 설정을 완료했어요' }).waitFor()
    await click('추천 공지 보러 가기')
    await page.getByRole('button', { name: '통합 시험 AI 해커톤 1 상세 보기', exact: true }).waitFor()
    await fits('recommend desktop')
    await screenshot('04-recommend')
    await compareComposition(['.sidebar', '.nav', '.main-content', '.page'], [
      { width: 1920, height: 1080 }, { width: 1280, height: 720 },
    ])
    await setSize(1440, 1000)
    await click('통합 시험 AI 해커톤 1 찜 추가')
    await page.getByRole('button', { name: '통합 시험 AI 해커톤 1 찜 해제', exact: true }).waitFor()
    await click('통합 시험 AI 해커톤 1 상세 보기')
    await page.getByText('시험 행사', { exact: false }).waitFor()
    await screenshot('05-detail')
    await page.keyboard.press('Escape')
    await click('내 정보 수정')
    await page.getByRole('dialog').waitFor()
    await click('문화·예술 선택')
    await screenshot('06-profile')
    await click('저장')
    await page.getByRole('dialog').waitFor({ state: 'hidden' })
    await page.getByRole('button', { name: '통합 시험 AI 해커톤 1 찜 해제', exact: true }).waitFor()
    await page.getByRole('link', { name: '신규 공지', exact: true }).click()
    await page.getByRole('button', { name: '통합 시험 AI 해커톤 23 상세 보기', exact: true }).waitFor()
    await click('교육·특강')
    await click('공모전·대회')
    await click('다음 페이지')
    await page.getByRole('button', { name: '통합 시험 AI 해커톤 1 상세 보기', exact: true }).waitFor()
    await page.getByRole('link', { name: '내 캘린더', exact: true }).click()
    await page.locator('.calendar-event').first().waitFor()
    assert.equal(await page.locator('.calendar-event').count() > 0, true)
    await screenshot('07-calendar')
    await click('다음 달')
    await click('다음 달')
    await page.getByText('이번 달에 표시할 일정이 없습니다.').waitFor()
    assert.ok(await page.getByRole('button', { name: '이전 달', exact: true }).isEnabled())
    for (const size of [{ width: 1280, height: 800 }, { width: 390, height: 844 }, { width: 320, height: 740 }]) {
      await setSize(size.width, size.height)
      for (const route of ['recommend', 'new', 'calendar']) {
        await page.goto(webUrl + '/' + route)
        await page.locator('.page-header h1').waitFor()
        await page.locator('.skeleton-list').waitFor({ state: 'hidden' })
        await fits(route + ' ' + size.width)
        await screenshot(route + '-' + size.width)
      }
      await click('내 정보 수정')
      await page.getByLabel('학과', { exact: true }).waitFor()
      const box = await page.getByRole('dialog').boundingBox()
      assert.ok(box.y >= -1 && box.y + box.height <= size.height + 1, 'modal bounds ' + size.width + ': ' + JSON.stringify(box))
      await fits('profile ' + size.width)
      await screenshot('profile-' + size.width)
      await click('취소')
    }
    await setSize(1440, 1000)
    await click('로그아웃')
    await page.getByRole('heading', { name: '로그인', exact: true }).waitFor()
    assert.equal(await page.evaluate(() => sessionStorage.getItem('scnu-pick:api:v1:session')), null)
    await page.getByLabel('아이디', { exact: true }).fill('integration_user')
    await page.getByLabel('비밀번호', { exact: true }).fill('integration-password-123')
    await click('로그인')
    await page.waitForURL('**/recommend')
    await page.getByRole('button', { name: '통합 시험 AI 해커톤 1 찜 해제', exact: true }).waitFor()
    assert.deepEqual(errors, [])
    console.log(JSON.stringify({ passed: true, realApi: true, temporaryDatabase: true, browserErrors: errors, screenshots: output }))
  } catch (error) {
    if (page && !page.isClosed()) {
      await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true })
      console.error(JSON.stringify({ url: page.url(), text: await page.locator('body').innerText(), httpErrors }))
    }
    throw error
  } finally {
    if (browser) await browser.close()
    for (const child of [...children].reverse()) await stop(child, child === apiServer)
  }
}
main().catch((error) => { console.error(error); process.exitCode = 1 })
