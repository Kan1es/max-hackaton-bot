/**
 * MAX Bridge helpers (https://dev.max.ru/docs/webapps/bridge).
 *
 * Every call degrades silently: in a plain browser there is no
 * `window.WebApp`, and older MAX clients may lack a method, so nothing here
 * may throw or block the action it decorates.
 */

// Deep link to the bot: MAX opens the mini-app from its chat with a signed
// initData, which is what unlocks the profile and saved programs. It is also
// what a shared program points at, so the recipient lands in the same flow.
export const BOT_URL = 'https://max.ru/t814_hakaton_max_bot';

const bridge = () => (typeof window === 'undefined' ? undefined : window.WebApp);

/** Tactile confirmation: 'success' | 'error' | 'warning', or 'selection'. */
export function haptic(kind) {
  try {
    const feedback = bridge()?.HapticFeedback;
    if (!feedback) return;
    if (kind === 'selection') feedback.selectionChanged?.();
    else feedback.notificationOccurred?.(kind);
  } catch { /* cosmetic only */ }
}

export function shareText(program) {
  const lines = [`${program.title} — ${program.highlight}`];
  if (program.deadline) lines.push(`Срок: ${program.deadline}`);
  if (/^https?:\/\//.test(program.sourceUrl || '')) lines.push(`Источник: ${program.sourceUrl}`);
  lines.push('', 'Нашёл в «Навигаторе мер поддержки» в MAX — подберите программы под свой бизнес:');
  return lines.join('\n');
}

/**
 * Send a program to a MAX chat — to an accountant, a partner, a colleague.
 * Inside MAX this opens the in-app share screen (shareMaxContent), with the
 * native OS sheet as a fallback; in a browser, the Web Share API or the
 * clipboard. Resolves to 'shared', 'cancelled', 'copied' or 'unavailable'.
 */
export async function shareProgram(program) {
  const payload = { text: shareText(program), link: BOT_URL };
  const webApp = bridge();
  for (const method of ['shareMaxContent', 'shareContent']) {
    if (typeof webApp?.[method] !== 'function') continue;
    try {
      await webApp[method](payload);
      return 'shared';
    } catch { /* try the next channel */ }
  }
  try {
    if (navigator.share) {
      await navigator.share({ text: payload.text, url: payload.link });
      return 'shared';
    }
  } catch (error) {
    // The user closed the share sheet: not a failure, nothing to fall back to.
    if (error?.name === 'AbortError') return 'cancelled';
  }
  try {
    await navigator.clipboard.writeText(`${payload.text}\n${payload.link}`);
    return 'copied';
  } catch {
    return 'unavailable';
  }
}
