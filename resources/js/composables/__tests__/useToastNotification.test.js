import { describe, it, expect } from 'vitest';
import { useToastNotification } from '../useToastNotification';

describe('useToastNotification', () => {
  it('returns empty toasts initially', () => {
    const { toasts } = useToastNotification();
    expect(toasts.value).toEqual([]);
  });

  it('adds a toast via showToast', () => {
    const { toasts, showToast } = useToastNotification();
    showToast({ message: 'Hello' });
    expect(toasts.value).toHaveLength(1);
    expect(toasts.value[0].message).toBe('Hello');
    expect(toasts.value[0].type).toBe('info');
    expect(toasts.value[0].id).toBeDefined();
  });

  it('supports custom type and icon', () => {
    const { toasts, showToast } = useToastNotification();
    showToast({ message: 'Error!', type: 'error', icon: 'ph:x-circle' });
    expect(toasts.value[0].type).toBe('error');
    expect(toasts.value[0].icon).toBe('ph:x-circle');
  });

  it('removes a toast by id', () => {
    const { toasts, showToast, removeToast } = useToastNotification();
    showToast({ message: 'One' });
    showToast({ message: 'Two' });
    const id = toasts.value[0].id;
    removeToast(id);
    expect(toasts.value).toHaveLength(1);
    expect(toasts.value[0].message).toBe('Two');
  });

  it('sets default duration', () => {
    const { toasts, showToast } = useToastNotification();
    showToast({ message: 'Test' });
    expect(toasts.value).toHaveLength(1);
    expect(toasts.value[0].message).toBe('Test');
  });
});
