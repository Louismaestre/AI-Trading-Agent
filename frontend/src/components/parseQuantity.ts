export function parseQuantity(value: string): number | null {
  const quantity = Number(value)
  if (!Number.isInteger(quantity) || quantity < 1) {
    return null
  }
  return quantity
}
