import { render, screen } from '@testing-library/react'
import { fireEvent } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import type { Instrument } from '../api/types'
import { OrderForm } from './OrderForm'
import { parseQuantity } from './parseQuantity'

const instruments: Instrument[] = [
  {
    ticker: 'MC.PA',
    name: 'LVMH',
    isin: null,
    sector: 'Luxury',
    currency: 'EUR',
    is_active: true,
  },
]

test('parseQuantity rejects zero, decimals and empty values', () => {
  expect(parseQuantity('')).toBeNull()
  expect(parseQuantity('0')).toBeNull()
  expect(parseQuantity('1.5')).toBeNull()
  expect(parseQuantity('10')).toBe(10)
})

test('the form does not submit an invalid quantity', () => {
  const onSubmit = vi.fn()
  render(<OrderForm instruments={instruments} isPending={false} error={null} onSubmit={onSubmit} />)

  fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '0' } })
  fireEvent.click(screen.getByRole('button', { name: 'Place order' }))

  expect(onSubmit).not.toHaveBeenCalled()
  expect(screen.getByRole('button', { name: 'Place order' })).toBeDisabled()
})

test('the form submits a valid buy order', () => {
  const onSubmit = vi.fn()
  render(<OrderForm instruments={instruments} isPending={false} error={null} onSubmit={onSubmit} />)

  fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '10' } })
  fireEvent.click(screen.getByRole('button', { name: 'Place order' }))

  expect(onSubmit).toHaveBeenCalledWith({ ticker: 'MC.PA', side: 'BUY', quantity: 10 })
})
