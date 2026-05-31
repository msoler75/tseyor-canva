import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import ErrorBoundary from '../ErrorBoundary.vue';

describe('ErrorBoundary.vue', () => {
  it('renders default slot content', () => {
    const wrapper = mount(ErrorBoundary, {
      slots: { default: '<p>Safe content</p>' },
    });
    expect(wrapper.text()).toContain('Safe content');
  });

  it('renders default slot when no error', () => {
    const wrapper = mount(ErrorBoundary, {
      slots: { default: '<p>Main</p>' },
    });
    expect(wrapper.text()).toContain('Main');
  });
});
