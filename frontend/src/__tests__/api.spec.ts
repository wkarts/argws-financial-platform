import { describe, expect, it } from 'vitest'
import { sessionStorageKey } from '../api/client'

describe('API client', () => {
  it('isolates browser sessions by hostname', () => {
    expect(sessionStorageKey()).toBe(`argws-financial-session:${window.location.hostname}`)
  })
})
