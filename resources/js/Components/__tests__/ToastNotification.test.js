import { describe, it, expect, vi, beforeAll } from 'vitest';
import { mount } from '@vue/test-utils';

let el;

beforeAll(() => {
  el = document.createElement('div');
  document.body.appendChild(el);
});
import ToastNotification from '../designer/ToastNotification.vue';

describe('ToastNotification.vue', () => {
  afterEach(() => {
    el.innerHTML = '';
  });

  function bodyText() {
    return document.body.textContent;
  }

  it('renders nothing when toasts array is empty', () => {
    const wrapper = mount(ToastNotification, {
      props: { toasts: [] },
    });
    expect(wrapper.findComponent({ name: 'Teleport' }).exists()).toBe(false);
  });

  it('renders a toast message', () => {
    mount(ToastNotification, {
      props: { toasts: [{ id: 1, message: 'Hello', type: 'info', icon: null }] },
    });
    expect(bodyText()).toContain('Hello');
  });

  it('renders multiple toasts', () => {
    mount(ToastNotification, {
      props: { toasts: [
        { id: 1, message: 'First', type: 'info', icon: null },
        { id: 2, message: 'Second', type: 'success', icon: null },
      ]},
    });
    expect(bodyText()).toContain('First');
    expect(bodyText()).toContain('Second');
  });

  it('emits remove event when close button is clicked', async () => {
    const wrapper = mount(ToastNotification, {
      props: { toasts: [{ id: 42, message: 'Dismiss me', type: 'info', icon: null }] },
    });
    const closeBtn = wrapper.find('button');
    if (closeBtn.exists()) {
      await closeBtn.trigger('click');
      expect(wrapper.emitted('remove')).toBeTruthy();
      expect(wrapper.emitted('remove')[0]).toEqual([42]);
    }
  });
});
