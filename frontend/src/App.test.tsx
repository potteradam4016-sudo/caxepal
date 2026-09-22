import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { App } from './App'
import { AppProviders } from './context/AppProviders'
import { authStorageKeys } from './services/mockAuthService'

function renderApp(path = '/recommend') {
  sessionStorage.setItem(authStorageKeys.session, 'demo')
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppProviders><App /></AppProviders>
    </MemoryRouter>,
  )
}

function renderLoggedOut(path = '/login') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppProviders><App /></AppProviders>
    </MemoryRouter>,
  )
}

describe('SCNU PICK app', () => {
  it('redirects a signed-out user from a protected route to login', async () => {
    renderLoggedOut('/calendar')
    expect(await screen.findByRole('heading', { name: '로그인' })).toBeInTheDocument()
  })

  it('validates signup password confirmation', async () => {
    const user = userEvent.setup()
    renderLoggedOut('/signup')
    await user.type(screen.getByLabelText('아이디'), 'newuser')
    await user.type(screen.getByLabelText('비밀번호', { exact: true }), 'password1')
    await user.type(screen.getByLabelText('비밀번호 확인'), 'password2')
    await user.click(screen.getByRole('button', { name: '가입하고 시작하기' }))
    expect(await screen.findByText('비밀번호가 일치하지 않습니다.')).toBeInTheDocument()
  })

  it('normalizes the username and starts onboarding immediately after signup', async () => {
    const user = userEvent.setup()
    renderLoggedOut('/signup')
    await user.type(screen.getByLabelText('아이디'), 'NewUser')
    expect(screen.getByLabelText('아이디')).toHaveValue('newuser')
    await user.type(screen.getByLabelText('비밀번호', { exact: true }), 'password1')
    await user.type(screen.getByLabelText('비밀번호 확인'), 'password1')
    await user.click(screen.getByRole('button', { name: '가입하고 시작하기' }))
    expect(await screen.findByRole('heading', { name: '학적 정보를 알려주세요' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '다음' }))
    expect(await screen.findByText('학과를 1~60자로 입력해 주세요.')).toBeInTheDocument()
    await user.type(screen.getByLabelText(/^학과/), '인공지능공학부')
    await user.selectOptions(screen.getByLabelText(/^학년/), '3학년')
    await user.selectOptions(screen.getByLabelText(/^학적 상태/), '재학')
    await user.click(screen.getByRole('button', { name: '다음' }))

    expect(await screen.findByRole('heading', { name: '관심 분야를 선택해 주세요' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '선택 완료' }))
    expect(await screen.findByText('관심 분야를 1개 이상 선택해 주세요.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'AI선택' }))
    await user.click(screen.getByRole('button', { name: '프로젝트선택' }))
    await user.click(screen.getByRole('button', { name: '선택 완료' }))

    expect(await screen.findByRole('heading', { name: '맞춤 설정을 완료했어요' })).toBeInTheDocument()
    expect(screen.getByText('인공지능공학부 · 3학년 · 재학')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '추천 공지 보러 가기' }))
    expect(await screen.findByRole('heading', { name: '추천 공지' })).toBeInTheDocument()
  })

  it('rejects invalid and duplicate usernames', async () => {
    const user = userEvent.setup()
    renderLoggedOut('/signup')
    await user.click(screen.getByRole('button', { name: '가입하고 시작하기' }))
    expect(await screen.findByText('아이디는 영문 소문자와 숫자 4~20자로 입력해 주세요.', { selector: '.field-error' })).toBeInTheDocument()
    await user.type(screen.getByLabelText(/^아이디/), 'bad_id')
    await user.type(screen.getByLabelText('비밀번호', { exact: true }), 'password1')
    await user.type(screen.getByLabelText('비밀번호 확인'), 'password1')
    await user.click(screen.getByRole('button', { name: '가입하고 시작하기' }))
    expect(await screen.findByText('아이디는 영문 소문자와 숫자 4~20자로 입력해 주세요.', { selector: '.field-error' })).toBeInTheDocument()
    await user.clear(screen.getByLabelText(/^아이디/))
    await user.type(screen.getByLabelText(/^아이디/), 'demo')
    await user.click(screen.getByRole('button', { name: '가입하고 시작하기' }))
    expect(await screen.findByText('이미 사용 중인 아이디입니다.')).toBeInTheDocument()
  })

  it('logs an existing completed user directly into recommendations', async () => {
    const user = userEvent.setup()
    renderLoggedOut('/login')
    await user.type(screen.getByLabelText('아이디'), 'DEMO')
    expect(screen.getByLabelText('아이디')).toHaveValue('demo')
    await user.type(screen.getByLabelText('비밀번호'), 'password1')
    await user.click(screen.getByRole('button', { name: '로그인' }))
    expect(await screen.findByRole('heading', { name: '추천 공지' })).toBeInTheDocument()
  })

  it('rejects an unknown username and sends removed account routes to login', async () => {
    const user = userEvent.setup()
    const view = renderLoggedOut('/login')
    await user.type(screen.getByLabelText('아이디'), 'unknown')
    await user.type(screen.getByLabelText('비밀번호'), 'password1')
    await user.click(screen.getByRole('button', { name: '로그인' }))
    expect(await screen.findByText('아이디 또는 비밀번호를 확인해 주세요.')).toBeInTheDocument()
    expect(screen.queryByText('비밀번호를 잊으셨나요?')).not.toBeInTheDocument()
    view.unmount()
    renderLoggedOut('/forgot')
    expect(await screen.findByRole('heading', { name: '로그인' })).toBeInTheDocument()
  })

  it('searches recommendations and resets an empty result', async () => {
    const user = userEvent.setup()
    renderApp()

    expect(await screen.findByText('AI 실무 프로젝트 참가자 모집')).toBeInTheDocument()
    await user.type(screen.getByRole('textbox', { name: '추천 공지 검색' }), '존재하지 않는 공지')
    expect(await screen.findByText('조건에 맞는 공지가 없습니다')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '필터 초기화' }))
    expect(await screen.findByText('SW 비교과 특강: 오픈소스 협업')).toBeInTheDocument()
  })

  it('does not open detail when toggling a card favorite', async () => {
    const user = userEvent.setup()
    renderApp()
    const card = (await screen.findByText('AI 실무 프로젝트 참가자 모집')).closest('article')!

    await user.click(within(card).getByRole('button', { name: /AI 실무 프로젝트 참가자 모집 찜 해제/ }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(await screen.findByText('찜을 해제했어요.')).toBeInTheDocument()
  })

  it('opens detail from a card and closes it with Escape', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.click(await screen.findByRole('button', { name: 'AI 실무 프로젝트 참가자 모집 상세 보기' }))

    expect(await screen.findByRole('dialog', { name: 'AI 실무 프로젝트 참가자 모집' })).toBeInTheDocument()
    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('shows favorite application and activity events in the calendar', async () => {
    renderApp('/calendar')
    expect(await screen.findByRole('button', { name: /신청 마감.*AI 실무 프로젝트 참가자 모집/ })).toBeInTheDocument()
    expect(screen.getByText('일정 구분')).toBeInTheDocument()
  })

  it('saves profile changes and closes the modal', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.click(screen.getByRole('button', { name: '내 정보 수정' }))
    await screen.findByRole('dialog', { name: '학적·관심사 수정' })
    const department = await screen.findByLabelText('학과')
    await user.clear(department)
    await user.type(department, '인공지능공학부')
    await user.click(screen.getByRole('button', { name: 'AI' }))
    await user.click(screen.getByRole('button', { name: '개발' }))
    await user.click(screen.getByRole('button', { name: '장학' }))
    await user.click(screen.getByRole('button', { name: '저장' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(localStorage.getItem('scnu-pick:v3:profile:demo')).toContain('인공지능공학부')
    expect(await screen.findByText(/관심 분야 장학 조건이 일치해 추천했어요/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'AI 실무 프로젝트 참가자 모집 찜 해제' })).toHaveAttribute('aria-pressed', 'true')
  })
})
