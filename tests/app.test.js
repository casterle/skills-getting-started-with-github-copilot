import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock DOM for testing
global.document = {
  createElement: vi.fn(() => ({
    setAttribute: vi.fn(),
    classList: { add: vi.fn(), remove: vi.fn() },
    appendChild: vi.fn(),
    innerHTML: '',
    textContent: '',
  })),
  getElementById: vi.fn(() => ({
    textContent: '',
    className: '',
    setAttribute: vi.fn(),
    classList: { add: vi.fn(), remove: vi.fn() },
    innerHTML: '',
    appendChild: vi.fn(),
  })),
  querySelectorAll: vi.fn(() => []),
};
global.navigator = { onLine: true };

describe('sanitize', () => {
  it('escapes HTML', () => {
    const sanitize = (text) => {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    };
    expect(sanitize('<script>')).toBe('&lt;script&gt;');
    expect(sanitize('hello')).toBe('hello');
  });
});

describe('showMessage', () => {
  it('sets message text and class', () => {
    const messageDiv = { textContent: '', className: '', setAttribute: vi.fn(), classList: { remove: vi.fn(), add: vi.fn() } };
    const showMessage = (text, type = 'info') => {
      messageDiv.textContent = text;
      messageDiv.className = type;
      messageDiv.setAttribute('role', 'alert');
      messageDiv.setAttribute('aria-live', 'assertive');
      messageDiv.classList.remove('hidden');
      setTimeout(() => {
        messageDiv.classList.add('hidden');
      }, 5000);
    };
    showMessage('Test', 'success');
    expect(messageDiv.textContent).toBe('Test');
    expect(messageDiv.className).toBe('success');
  });
});
