import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError, api } from '../api.js';

function mockResponse({ status = 200, body = {} } = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

describe('api client', () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockResolvedValue(mockResponse({ body: [] }));
    delete window.WebApp;
    localStorage.clear();
  });

  afterEach(() => { vi.restoreAllMocks(); });

  it('sends the signed initData string when running inside MAX', async () => {
    window.WebApp = { initData: 'user=%7B%22id%22%3A42%7D&hash=abc' };
    await api.getPrograms();
    const [, init] = global.fetch.mock.calls[0];
    expect(init.headers.Authorization).toBe('tma user=%7B%22id%22%3A42%7D&hash=abc');
    expect(init.headers['X-Max-User-Id']).toBeUndefined();
  });

  it('never sends initDataUnsafe as the identity', async () => {
    window.WebApp = { initData: 'signed', initDataUnsafe: { user: { id: 999 } } };
    await api.getPrograms();
    const [, init] = global.fetch.mock.calls[0];
    expect(init.headers.Authorization).toBe('tma signed');
    expect(JSON.stringify(init.headers)).not.toContain('999');
  });

  it('falls back to a stable per-browser id outside MAX', async () => {
    await api.getPrograms();
    const first = global.fetch.mock.calls[0][1].headers['X-Max-User-Id'];
    await api.getPrograms();
    const second = global.fetch.mock.calls[1][1].headers['X-Max-User-Id'];
    expect(first).toBeTruthy();
    expect(second).toBe(first);
  });

  it('surfaces the backend error detail', async () => {
    global.fetch.mockResolvedValue(mockResponse({ status: 401, body: { detail: 'initData has expired' } }));
    await expect(api.getProfile()).rejects.toThrow('initData has expired');
    await expect(api.getProfile()).rejects.toBeInstanceOf(ApiError);
  });

  it('reports an unreachable backend instead of throwing a raw TypeError', async () => {
    global.fetch.mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(api.getPrograms()).rejects.toThrow(/Сервис недоступен/);
  });

  it('handles the 204 returned when un-saving a program', async () => {
    global.fetch.mockResolvedValue({ ok: true, status: 204, json: async () => { throw new Error('no body'); } });
    await expect(api.deleteApplication(3)).resolves.toBeNull();
  });

  it('asks for the full ranked list for the catalog', async () => {
    await api.getMatches();
    expect(global.fetch.mock.calls[0][0]).toContain('/programs/match/me?limit=50');
  });

  it('sends a JSON body only when there is one', async () => {
    await api.saveApplication(5);
    const [, init] = global.fetch.mock.calls[0];
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({ program_id: 5 });
    expect(init.headers['Content-Type']).toBe('application/json');
  });
});
