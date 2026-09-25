import rawPrograms from './support_programs.json';

const clean = (value = '') => String(value).replace(/\[web:\d+\]/g, '').replace(/\s+/g, ' ').trim();

const titles = {
  4: 'Грант для молодых предпринимателей',
  7: 'Льготный кредит для IT-компаний',
  8: 'Субсидия на цифровизацию бизнеса',
};

const highlights = {
  0: 'от 500 000 ₽',
  2: 'до 350 000 ₽',
  3: 'гранты на развитие',
  4: 'до 500 000 ₽',
  7: 'от 2,5% годовых',
  8: 'до 50% затрат',
  14: 'до 5 000 000 ₽',
  18: '307 008 ₽',
};

export const programs = rawPrograms.map((item, index) => ({
  id: index,
  title: titles[index] || clean(item.название),
  fullTitle: clean(item.название),
  description: clean(item.краткое_описание),
  region: clean(item.регион),
  industries: (item.подходящие_сферы || []).map(clean),
  eligibleStatus: clean(item.допустимый_статус_пользователя),
  type: clean(item.вид_поддержки),
  amount: clean(item.сумма),
  highlight: highlights[index] || clean(item.сумма).split(/[;.]/)[0].slice(0, 56),
  conditions: clean(item.основные_условия),
  deadline: clean(item.дедлайн),
  documents: (item.чек_лист_документов || []).map(clean),
  sourceUrl: item.ссылка_на_официальный_источник,
  checkedAt: item.дата_проверки_информации,
  isMock: true,
}));

export const initialProfile = {
  name: 'Анна Ковалёва',
  status: 'Самозанятый',
  region: 'Москва',
  industry: 'IT',
  priority: 'Развитие',
};

export const options = {
  status: ['Самозанятый', 'Регистрирую ИП', 'ИП'],
  region: ['Москва', 'Московская область', 'Краснодарский край', 'Санкт-Петербург', 'Другой регион'],
  industry: ['IT', 'Услуги', 'Торговля', 'Производство', 'Туризм', 'Сельское хозяйство', 'Креативные индустрии'],
  priority: ['Развитие', 'Деньги на старт', 'Льготный займ', 'Обучение', 'Налоговые льготы'],
};

export function programKind(program) {
  const type = program.type.toLowerCase();
  if (type.includes('кредит') || type.includes('займ')) return 'Кредит';
  if (type.includes('грант')) return 'Грант';
  if (type.includes('субсид') || type.includes('компенсац')) return 'Субсидия';
  if (type.includes('льгота') || type.includes('взнос')) return 'Льгота';
  return 'Поддержка';
}

export function deadlineLabel(program) {
  const deadline = program.deadline.toLowerCase();
  if (deadline.includes('постоянн')) return 'Постоянно';
  if (deadline.includes('ежегодно') || deadline.includes('волнами') || deadline.includes('конкурс')) return 'По конкурсу';
  if (deadline.includes('2026')) return 'В 2026 году';
  return 'Уточните срок';
}

export function matchesRegion(program, region) {
  const text = program.region.toLowerCase();
  if (text.includes('росси') || text.includes('все регионы')) return true;
  return text.includes(region.toLowerCase());
}

function industryMatch(program, industry) {
  const corpus = [program.fullTitle, program.description, ...program.industries].join(' ').toLowerCase();
  const terms = {
    IT: ['it', 'цифров', 'разработк', 'онлайн', 'интернет', 'программного обеспечения'],
    Услуги: ['услуг', 'сервис', 'социальн'],
    Торговля: ['торгов', 'рознич'],
    Производство: ['производ', 'промышлен', 'обрабатыва'],
    Туризм: ['туризм', 'отел', 'гостиниц'],
    'Сельское хозяйство': ['сельск', 'агро', 'фермер'],
    'Креативные индустрии': ['креатив', 'творчес'],
  }[industry] || [];
  return terms.some(term => corpus.includes(term));
}

export function matchReasons(program, profile) {
  const reasons = [];
  if (matchesRegion(program, profile.region)) reasons.push('доступна в вашем регионе');
  if (industryMatch(program, profile.industry)) reasons.push('подходит по сфере');
  const kind = programKind(program);
  if (
    (profile.priority === 'Льготный займ' && kind === 'Кредит') ||
    (profile.priority === 'Налоговые льготы' && kind === 'Льгота') ||
    (profile.priority === 'Деньги на старт' && ['Грант', 'Субсидия', 'Поддержка'].includes(kind)) ||
    (profile.priority === 'Развитие' && ['Грант', 'Кредит', 'Субсидия'].includes(kind))
  ) reasons.push('соответствует вашему приоритету');
  return reasons;
}

export function rankPrograms(profile) {
  return programs
    .filter(program => matchesRegion(program, profile.region))
    .map(program => ({ program, reasons: matchReasons(program, profile) }))
    .filter(item => item.reasons.length >= 2)
    .sort((a, b) => {
      const score = item => item.reasons.length * 10 + ([4, 7, 8].includes(item.program.id) ? 1 : 0);
      return score(b) - score(a);
    });
}

export function sourceIsHttp(url) {
  try { return new URL(url).protocol === 'https:'; } catch { return false; }
}
