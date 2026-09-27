export function currentSeoulMonth() {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit' }).formatToParts(new Date())
  return `${parts.find((part) => part.type === 'year')!.value}-${parts.find((part) => part.type === 'month')!.value}`
}
export function shiftMonth(month: string, delta: number) {
  const [year, number] = month.split('-').map(Number)
  return new Date(Date.UTC(year, number - 1 + delta, 1)).toISOString().slice(0, 7)
}
export function calendarDays(month: string): Array<string | null> {
  const [year, number] = month.split('-').map(Number)
  const start = new Date(Date.UTC(year, number - 1, 1)).getUTCDay()
  const count = new Date(Date.UTC(year, number, 0)).getUTCDate()
  return [...Array<null>(start).fill(null), ...Array.from({ length: count }, (_, day) => `${month}-${String(day + 1).padStart(2, '0')}`)]
}
