/**
 * Backend client.
 *
 * Auth: inside MAX we send the raw `WebApp.initData` string, which the server
 * verifies with an HMAC signature. `initDataUnsafe` is never used for
 * identity — only for cosmetic things like a display name. Outside MAX (a
 * plain browser during development) we fall back to a per-browser id header,
 * which the backend accepts only when REQUIRE_SIGNED_INIT_DATA=False.
 *
 * Base URL: empty by default, meaning "same origin" — in Docker nginx proxies
 * /api to the FastAPI service, so there is no CORS to configure.
 */
const BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const API = `${BASE}/api/v1`;
const DEV_USER_KEY = 'max-support-navigator-dev-user-id';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function devUserId() {
  try {
    let id = localStorage.getItem(DEV_USER_KEY);
    if (!id) {
      id = String(Math.floor(Math.random() * 1e9) + 1);
      localStorage.setItem(DEV_USER_KEY, id);
    }
    return id;
  } catch {
    return '1';
  }
}

function authHeaders() {
  const initData = window.WebApp?.initData;
  if (initData) return { Authorization: `tma ${initData}` };
  // Development only: unsigned, and rejected by a production backend.
  return { 'X-Max-User-Id': String(window.WebApp?.initDataUnsafe?.user?.id || devUserId()) };
}

async function request(path, { method = 'GET', body } = {}) {
  let response;
  try {
    response = await fetch(`${API}${path}`, {
      method,
      headers: {
        Accept: 'application/json',
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...authHeaders(),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (cause) {
    throw new ApiError('Сервис недоступен. Проверьте соединение.', 0);
  }

  if (response.status === 204) return null;

  if (!response.ok) {
    let detail = `Ошибка ${response.status}`;
    try {
      const payload = await response.json();
      if (typeof payload.detail === 'string') detail = payload.detail;
    } catch { /* keep the generic message */ }
    throw new ApiError(detail, response.status);
  }

  return response.json();
}

export const api = {
  getOptions: () => request('/options/'),
  getPrograms: () => request('/programs/'),
  getProfile: () => request('/profile/me'),
  saveProfile: patch => request('/profile/', { method: 'POST', body: patch }),
  getMatches: (limit = 50) => request(`/programs/match/me?limit=${limit}`),
  getApplications: () => request('/applications/'),
  saveApplication: programId => request('/applications/', { method: 'POST', body: { program_id: programId } }),
  updateApplication: (id, patch) => request(`/applications/${id}`, { method: 'PATCH', body: patch }),
  deleteApplication: programId => request(`/applications/by-program/${programId}`, { method: 'DELETE' }),
};
