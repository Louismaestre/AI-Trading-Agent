import { expect, test } from 'vitest'

import { remainingLabel } from './countdown'

const from = new Date('2026-09-29T10:00:00+02:00')

test('remainingLabel formats hours and minutes', () => {
  expect(remainingLabel(from, new Date('2026-09-29T12:14:00+02:00'))).toBe('2h 14m')
})

test('remainingLabel formats minutes and seconds', () => {
  expect(remainingLabel(from, new Date('2026-09-29T10:08:05+02:00'))).toBe('8m 5s')
})

test('remainingLabel is now when the target is past', () => {
  expect(remainingLabel(from, new Date('2026-09-29T09:59:00+02:00'))).toBe('now')
})
