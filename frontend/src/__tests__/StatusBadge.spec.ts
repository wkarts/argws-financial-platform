import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import StatusBadge from '../components/StatusBadge.vue'

describe('StatusBadge', () => {
  it('renders successful status with semantic class', () => {
    const wrapper = mount(StatusBadge, { props: { status: 'PAID' } })
    expect(wrapper.text()).toBe('PAID')
    expect(wrapper.classes()).toContain('bg-emerald-100')
  })

  it('renders failure status with semantic class', () => {
    const wrapper = mount(StatusBadge, { props: { status: 'FAILED' } })
    expect(wrapper.classes()).toContain('bg-rose-100')
  })
})
