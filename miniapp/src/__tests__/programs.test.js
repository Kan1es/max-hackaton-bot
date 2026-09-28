import { describe, expect, it } from 'vitest';

import {
  deadlineLabel, formatCheckedAt, normalizeProgram, programKind, regionLabel, sourceIsHttp,
} from '../data/programs.js';

const apiProgram = {
  id: 7,
  name: 'Льготный кредит для малых технологических компаний',
  short_title: 'Льготный кредит для IT-компаний',
  description: 'Кредиты по сниженной ставке',
  region: 'Россия',
  industries: ['IT'],
  eligible_status: 'ИП и организации из реестра МСП',
  conditions: 'Аккредитация Минцифры',
  type: 'льготный кредит',
  amount: 'до 500 000 000 руб.',
  highlight: 'от 2,5% годовых',
  deadline: 'действует на постоянной основе',
  doc_checklist: ['заявка', 'паспорт'],
  source_url: 'https://example.gov.ru/program',
  checked_at: '2026-09-22',
  is_mock: true,
};

describe('normalizeProgram', () => {
  it('maps the API shape onto what the components render', () => {
    const program = normalizeProgram(apiProgram);
    expect(program.title).toBe('Льготный кредит для IT-компаний');
    expect(program.fullTitle).toBe(apiProgram.name);
    expect(program.documents).toEqual(['заявка', 'паспорт']);
    expect(program.sourceUrl).toBe(apiProgram.source_url);
    expect(program.checkedAt).toBe('2026-09-22');
  });

  it('falls back to the official name when there is no short title', () => {
    expect(normalizeProgram({ ...apiProgram, short_title: null }).title).toBe(apiProgram.name);
  });

  it('derives a highlight from the amount when none is stored', () => {
    const program = normalizeProgram({ ...apiProgram, highlight: null });
    expect(program.highlight).toBe('до 500 000 000 руб');
  });

  it('never leaves list fields undefined', () => {
    const program = normalizeProgram({ id: 1, name: 'x', is_mock: false });
    expect(program.documents).toEqual([]);
    expect(program.industries).toEqual([]);
    expect(program.reasons).toEqual([]);
  });
});

describe('display helpers', () => {
  it('buckets support types', () => {
    expect(programKind({ type: 'льготный микрозайм' })).toBe('Кредит');
    expect(programKind({ type: 'грант' })).toBe('Грант');
    expect(programKind({ type: 'нефинансовая' })).toBe('Поддержка');
    expect(programKind({})).toBe('Поддержка');
  });

  it('labels deadlines', () => {
    expect(deadlineLabel({ deadline: 'действует на постоянной основе' })).toBe('Постоянно');
    expect(deadlineLabel({ deadline: 'конкурс в марте' })).toBe('По конкурсу');
    expect(deadlineLabel({})).toBe('Уточните срок');
  });

  it('shows the real region instead of guessing "Краснодар or Russia"', () => {
    expect(regionLabel({ region: 'Россия' })).toBe('Вся Россия');
    expect(regionLabel({ region: 'Санкт-Петербург' })).toBe('Санкт-Петербург');
    expect(regionLabel({})).toBe('Регион не указан');
  });

  it('only opens https sources', () => {
    expect(sourceIsHttp('https://example.gov.ru')).toBe(true);
    expect(sourceIsHttp('javascript:alert(1)')).toBe(false);
    expect(sourceIsHttp('')).toBe(false);
  });

  it('formats or drops the verification date', () => {
    expect(formatCheckedAt('2026-09-22')).toBe('22.09.2026');
    expect(formatCheckedAt('')).toBeNull();
    expect(formatCheckedAt('не дата')).toBeNull();
  });
});
