import { afterEach, describe, expect, it, vi } from 'vitest';

import { BOT_URL, haptic, shareProgram, shareText } from '../bridge.js';

const PROGRAM = {
  title: 'Грант для IT',
  highlight: 'до 500 000 ₽',
  deadline: 'конкурс весной',
  sourceUrl: 'https://example.gov.ru/1',
};

afterEach(() => {
  delete window.WebApp;
  vi.unstubAllGlobals();
});

describe('shareProgram', () => {
  it('opens the MAX share screen with the program and a link to the bot', async () => {
    const shareMaxContent = vi.fn().mockResolvedValue(undefined);
    window.WebApp = { shareMaxContent };
    expect(await shareProgram(PROGRAM)).toBe('shared');
    expect(shareMaxContent).toHaveBeenCalledWith({ text: shareText(PROGRAM), link: BOT_URL });
  });

  it('falls back to the native share sheet on clients without shareMaxContent', async () => {
    const shareContent = vi.fn().mockResolvedValue(undefined);
    window.WebApp = { shareContent };
    expect(await shareProgram(PROGRAM)).toBe('shared');
    expect(shareContent).toHaveBeenCalledOnce();
  });

  it('copies the text in a browser without any share API', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('navigator', { clipboard: { writeText } });
    expect(await shareProgram(PROGRAM)).toBe('copied');
    expect(writeText.mock.calls[0][0]).toContain(BOT_URL);
  });

  it('includes the official source only when it is a web link', () => {
    expect(shareText(PROGRAM)).toContain('Источник: https://example.gov.ru/1');
    expect(shareText({ ...PROGRAM, sourceUrl: 'Корпорация МСП' })).not.toContain('Источник');
  });
});

describe('haptic', () => {
  it('maps outcomes onto MAX haptic feedback', () => {
    const feedback = { notificationOccurred: vi.fn(), selectionChanged: vi.fn() };
    window.WebApp = { HapticFeedback: feedback };
    haptic('success');
    haptic('selection');
    expect(feedback.notificationOccurred).toHaveBeenCalledWith('success');
    expect(feedback.selectionChanged).toHaveBeenCalledOnce();
  });

  it('is a no-op outside MAX', () => {
    expect(() => haptic('error')).not.toThrow();
  });
});
