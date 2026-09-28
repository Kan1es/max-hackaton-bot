import { vi } from 'vitest';

// jsdom has no layout, so scrollTo is unimplemented and logs on every render.
window.scrollTo = vi.fn();
