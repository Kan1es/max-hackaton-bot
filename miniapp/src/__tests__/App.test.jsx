import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import React from 'react';

const api = {
  getOptions: vi.fn(),
  getPrograms: vi.fn(),
  getProfile: vi.fn(),
  getApplications: vi.fn(),
  getMatches: vi.fn(),
  saveProfile: vi.fn(),
  saveApplication: vi.fn(),
  updateApplication: vi.fn(),
  deleteApplication: vi.fn(),
};

vi.mock('../api.js', () => ({
  api,
  ApiError: class ApiError extends Error {},
}));

const { default: App } = await import('../App.jsx');

// main.jsx renders inside StrictMode, which mounts, unmounts and remounts
// every component in development. Rendering the tests the same way is what
// catches effects that don't survive that second mount.
const renderApp = () => render(<React.StrictMode><App /></React.StrictMode>);

const OPTIONS = {
  status: ['Самозанятый', 'ИП'],
  region: ['Москва', 'Другой регион'],
  industry: ['IT', 'Услуги'],
  priority: ['Развитие'],
  application_status: ['saved'],
  other_region_label: 'Другой регион',
  industry_keywords: {},
};

const PROGRAM = {
  id: 1,
  name: 'Грант на развитие цифровых проектов',
  short_title: 'Грант для IT',
  description: 'Поддержка цифровых проектов',
  region: 'Москва',
  industries: ['IT'],
  eligible_status: 'ИП и организации из реестра МСП',
  conditions: 'Защита проекта',
  type: 'грант',
  amount: 'до 500 000 руб.',
  highlight: 'до 500 000 ₽',
  deadline: 'конкурс весной',
  doc_checklist: ['заявка'],
  source_url: 'https://example.gov.ru',
  checked_at: '2026-09-22',
  is_mock: true,
};

const PROFILE = {
  id: 1, user_id: 1, status: 'ИП', region: 'Москва', industry: 'IT',
  priority: 'Развитие', created_at: '2026-09-25T10:00:00Z', updated_at: '2026-09-25T10:00:00Z',
};

function resolveAll() {
  api.getOptions.mockResolvedValue(OPTIONS);
  api.getPrograms.mockResolvedValue([PROGRAM]);
  api.getProfile.mockResolvedValue(PROFILE);
  api.getApplications.mockResolvedValue([]);
  api.getMatches.mockResolvedValue([{ ...PROGRAM, score: 100, reasons: ['доступна в вашем регионе', 'подходит по сфере'] }]);
}

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    resolveAll();
  });

  afterEach(cleanup);

  it('shows a loading state before the backend answers', () => {
    renderApp();
    expect(screen.getByText(/Загружаем меры поддержки/)).toBeTruthy();
  });

  it('renders recommendations coming from the API', async () => {
    renderApp();
    await waitFor(() => expect(screen.getAllByText('Грант для IT').length).toBeGreaterThan(0));
    expect(screen.getByText(/Мы нашли для вас/)).toBeTruthy();
    // The profile shown is the one the bot collected, not a hardcoded demo user.
    expect(screen.getAllByText('Москва').length).toBeGreaterThan(0);
  });

  it('shows a retry screen when the backend is down', async () => {
    api.getOptions.mockRejectedValue(new Error('Сервис недоступен. Проверьте соединение.'));
    renderApp();
    await waitFor(() => expect(screen.getByText(/Не удалось загрузить данные/)).toBeTruthy());
    expect(screen.getByText(/Попробовать снова/)).toBeTruthy();
  });

  it('does not invent saved programs when the user has none', async () => {
    renderApp();
    await waitFor(() => expect(screen.getByText(/Мы нашли для вас/)).toBeTruthy());
    expect(screen.getByText('0 сохранено')).toBeTruthy();
  });

  it('reflects the saved programs returned by the API', async () => {
    api.getApplications.mockResolvedValue([
      { id: 10, profile_id: 1, program_id: 1, status: 'saved', checked_docs: ['заявка'], created_at: '2026-09-25T10:00:00Z' },
    ]);
    renderApp();
    await waitFor(() => expect(screen.getByText('1 сохранено')).toBeTruthy());
  });

  it('falls back to a read-only catalog in a browser outside MAX', async () => {
    const unauthorized = Object.assign(new Error('Authentication required'), { status: 401 });
    api.getProfile.mockRejectedValue(unauthorized);
    api.getApplications.mockRejectedValue(unauthorized);
    renderApp();
    await waitFor(() => expect(screen.getByText(/Вы смотрите каталог в браузере/)).toBeTruthy());
    expect(screen.getAllByText('Грант для IT').length).toBeGreaterThan(0);
    expect(screen.queryByText(/Не удалось загрузить данные/)).toBeNull();
    expect(api.getMatches).not.toHaveBeenCalled();
  });

  it('shares a program to a MAX chat from its card', async () => {
    const shareMaxContent = vi.fn().mockResolvedValue(undefined);
    window.WebApp = { initData: 'signed', shareMaxContent };
    try {
      renderApp();
      await waitFor(() => expect(screen.getAllByText('Грант для IT').length).toBeGreaterThan(0));
      fireEvent.click(screen.getAllByText('Грант для IT')[0]);
      fireEvent.click(await screen.findByLabelText('Поделиться программой в MAX'));
      await waitFor(() => expect(shareMaxContent).toHaveBeenCalledOnce());
      expect(shareMaxContent.mock.calls[0][0].text).toContain('Грант для IT');
    } finally {
      delete window.WebApp;
    }
  });

  it('still reports a 401 as an error inside MAX', async () => {
    window.WebApp = { initData: 'user=%7B%7D&hash=bad' };
    api.getProfile.mockRejectedValue(Object.assign(new Error('Invalid initData'), { status: 401 }));
    try {
      renderApp();
      await waitFor(() => expect(screen.getByText(/Не удалось загрузить данные/)).toBeTruthy());
    } finally {
      delete window.WebApp;
    }
  });
});
