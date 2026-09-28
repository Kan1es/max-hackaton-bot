/**
 * Presentation helpers for programs coming from the API.
 *
 * This file used to carry its own copy of the catalog, the option lists and
 * the matching rules — a second implementation that had already drifted from
 * the backend's. All of that now lives on the server: the catalog comes from
 * GET /api/v1/programs/, the options from /options/ and the ranking from
 * /programs/match/me. What is left here is purely how things are displayed.
 */

/** Map an API program (snake_case) onto the shape the components render. */
export function normalizeProgram(raw) {
  const documents = raw.doc_checklist || [];
  return {
    id: raw.id,
    title: raw.short_title || raw.name,
    fullTitle: raw.name,
    description: raw.description || '',
    region: raw.region || '',
    industries: raw.industries || [],
    eligibleStatus: raw.eligible_status || '',
    type: raw.type || '',
    amount: raw.amount || '',
    highlight: raw.highlight || (raw.amount || '').split(/[;.]/)[0].slice(0, 56),
    conditions: raw.conditions || '',
    deadline: raw.deadline || '',
    documents,
    sourceUrl: raw.source_url || '',
    checkedAt: raw.checked_at || '',
    isMock: Boolean(raw.is_mock),
    // Present only on /programs/match/me results.
    reasons: raw.reasons || [],
    score: raw.score,
  };
}

/** Coarse bucket used for the colour pill and the catalog filter chips. */
export function programKind(program) {
  const type = (program.type || '').toLowerCase();
  if (type.includes('кредит') || type.includes('займ')) return 'Кредит';
  if (type.includes('грант')) return 'Грант';
  if (type.includes('субсид') || type.includes('компенсац')) return 'Субсидия';
  if (type.includes('льгота') || type.includes('взнос')) return 'Льгота';
  return 'Поддержка';
}

export function deadlineLabel(program) {
  const deadline = (program.deadline || '').toLowerCase();
  if (deadline.includes('постоянн')) return 'Постоянно';
  if (deadline.includes('ежегодно') || deadline.includes('волнами') || deadline.includes('конкурс')) return 'По конкурсу';
  if (deadline.includes('2026')) return 'В 2026 году';
  return 'Уточните срок';
}

/** Short region caption for cards; federal programs read as "Вся Россия". */
export function regionLabel(program) {
  const region = program.region || '';
  if (!region) return 'Регион не указан';
  if (/росси|все регион/i.test(region)) return 'Вся Россия';
  return region;
}

export function sourceIsHttp(url) {
  try { return new URL(url).protocol === 'https:'; } catch { return false; }
}

export function formatCheckedAt(value) {
  if (!value) return null;
  const date = new Date(`${value}T12:00:00`);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleDateString('ru-RU');
}

export const KIND_FILTERS = ['Все', 'Грант', 'Кредит', 'Субсидия', 'Льгота', 'Поддержка'];
