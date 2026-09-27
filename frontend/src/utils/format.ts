export function formatShortDate(value: string | null) {
  if (!value) return '일정 미정'
  const [, month, day] = value.split('-')
  return `${Number(month)}/${Number(day)}`
}

export function formatLongDate(value: string | null) {
  if (!value) return '일정 미정'
  return new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' }).format(
    new Date(`${value}T00:00:00`),
  )
}

export function getScheduleSummary(schedule: {
  applicationEnd: string | null
  eventStart: string | null
  eventEnd: string | null
}) {
  const parts: string[] = []
  if (schedule.applicationEnd) parts.push(`신청 ${formatShortDate(schedule.applicationEnd)} 마감`)
  if (schedule.eventStart) {
    const eventRange =
      schedule.eventEnd && schedule.eventEnd !== schedule.eventStart
        ? `${formatShortDate(schedule.eventStart)}~${formatShortDate(schedule.eventEnd)}`
        : formatShortDate(schedule.eventStart)
    parts.push(`행사 ${eventRange}`)
  }
  return parts.length ? parts.join(' · ') : '세부 일정 원문 확인'
}
