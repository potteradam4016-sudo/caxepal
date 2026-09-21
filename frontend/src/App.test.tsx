import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { App } from './App'
import { AppProvider } from './context/AppContext'

function renderApp(path = '/recommend') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppProvider><App /></AppProvider>
    </MemoryRouter>,
  )
}

describe('SCNU PICK app', () => {
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
    await user.click(screen.getByRole('button', { name: '저장' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(localStorage.getItem('scnu-pick:v1:profile')).toContain('인공지능공학부')
  })
})
