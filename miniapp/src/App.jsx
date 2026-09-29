import React, { Suspense, lazy, useEffect, useLayoutEffect, useMemo, useState } from 'react';
import {
  ArrowLeft, ArrowRight, Bell, Bookmark, BriefcaseBusiness, Check, CheckCircle2,
  ChevronRight, CircleHelp, ExternalLink, FileText, Filter, Laptop,
  LineChart, Mail, MapPin, RefreshCw, Search, ShieldCheck, SlidersHorizontal, Sparkles,
  UserRound, X, Landmark, ListChecks, Pencil,
} from 'lucide-react';
import {
  KIND_FILTERS, deadlineLabel, formatCheckedAt, programKind, regionLabel, sourceIsHttp,
} from './data/programs.js';
import { documentInfo } from './data/documents.js';
import { useAppData } from './useAppData.js';

// Leaflet and its tiles are ~150 KB and only ever needed on the document
// page, so they load on demand instead of on first paint.
const DocumentLocations = lazy(() => import('./DocumentLocations.jsx'));

const navItems = [
  { id: 'home', label: 'Рекомендации', icon: Sparkles },
  { id: 'catalog', label: 'Программы', icon: Search },
  { id: 'saved', label: 'Мои программы', icon: Bookmark },
  { id: 'profile', label: 'Профиль', icon: UserRound },
];

const NOT_SET = 'Не указано';
const value = raw => raw || NOT_SET;

function IconSquare({ icon: Icon, tone = 'violet' }) {
  return <span className={`icon-square ${tone}`}><Icon size={18} strokeWidth={1.8} /></span>;
}

function Button({ children, variant = 'primary', icon: Icon, onClick, className = '', disabled = false, ...rest }) {
  return <button className={`btn btn-${variant} ${className}`} onClick={onClick} disabled={disabled} {...rest}>
    {Icon && <Icon size={17} strokeWidth={1.9} />}{children}
  </button>;
}

function Card({ children, className = '' }) {
  return <section className={`card ${className}`}>{children}</section>;
}

function PageHeading({ title, subtitle, onBack, trailing }) {
  return <div className="page-heading">
    <div className="heading-main">
      {onBack && <button className="back-button" onClick={onBack} aria-label="Назад"><ArrowLeft size={19} /></button>}
      <div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>
    </div>
    {trailing && <div className="heading-trailing">{trailing}</div>}
  </div>;
}

function FooterNote({ count }) {
  return <p className="data-note">Демо-каталог из {count} программ</p>;
}

function ProgramCard({ program, reasons, onOpen, onSave, saved, compact = false }) {
  const kind = programKind(program);
  return <Card className={`program-card ${compact ? 'compact' : ''}`}>
    <div className="program-card-top">
      <span className={`pill ${kind === 'Кредит' ? 'pill-amber' : kind === 'Грант' ? 'pill-blue' : 'pill-green'}`}>{kind}</span>
      <button className={`icon-button ${saved ? 'active' : ''}`} onClick={() => onSave(program.id)} title={saved ? 'Убрать из моих программ' : 'Сохранить программу'} aria-label={saved ? 'Убрать из моих программ' : 'Сохранить программу'}><Bookmark size={18} fill={saved ? 'currentColor' : 'none'} /></button>
    </div>
    <h3>{program.title}</h3>
    <p className="program-card-description">{program.description}</p>
    <div className="program-card-bottom">
      <strong>{program.highlight}</strong>
      <span><MapPin size={13} />{regionLabel(program)}</span>
    </div>
    {reasons?.length > 0 && <div className="match-line"><span className="match-dot" />{reasons.slice(0, 2).join(' · ')}</div>}
    <div className="program-card-actions">
      <Button onClick={() => onOpen(program.id)} className="flex-1">Подробнее</Button>
    </div>
  </Card>;
}

function HomePage({ profile, savedCount, recommendations, catalogSize, onCatalog, onOpen, onProfile }) {
  const top = recommendations.slice(0, 3);
  return <div className="page page-home">
    <div className="mobile-page-label"><span className="mobile-brand-mark"><img src="/logo.png" alt="" /></span><span>Навигатор поддержки</span></div>
    <div className="home-grid">
      <div className="home-primary">
        <section className="hero">
          <div className="hero-icon"><Sparkles size={23} strokeWidth={1.6} /></div>
          <span className="hero-eyebrow">Подбор для предпринимателя</span>
          <h1>Мы нашли для вас<br />{recommendations.length} программ поддержки</h1>
          <p>Предварительный подбор по вашему региону, сфере и приоритету.</p>
          <Button variant="white" onClick={onCatalog} icon={ArrowRight} className="hero-desktop-cta">Все рекомендации</Button>
          <div className="hero-orb orb-one" /><div className="hero-orb orb-two" />
        </section>
        <div className="section-heading"><h2>Рекомендации</h2><span>Для вас</span></div>
        {top.length ? <div className="recommendation-list">
          {top.map(program => <button key={program.id} className="recommendation" onClick={() => onOpen(program.id)}>
            <div><strong>{program.title}</strong><span>{program.highlight}</span></div>
            <small><span className="match-dot" />{program.reasons.length ? program.reasons[0] : 'Предварительный подбор'}</small>
            <ChevronRight size={18} className="recommendation-chevron" />
          </button>)}
        </div> : <Card className="empty-state">
          <Sparkles size={30} />
          <h3>Пока нечего рекомендовать</h3>
          <p>Заполните профиль — статус, регион, сферу и приоритет, — и подбор заработает.</p>
          <Button onClick={onProfile}>Заполнить профиль</Button>
        </Card>}
        <Button onClick={onCatalog} className="full mobile-catalog-btn">Открыть все рекомендации</Button>
      </div>
      <aside className="home-aside">
        <Card className="profile-preview">
          <div className="aside-card-header"><h3>Ваш профиль</h3><IconSquare icon={UserRound} /></div>
          <p>Рекомендации учитывают ваши данные.</p>
          <div className="preview-row"><span>Статус</span><strong>{value(profile.status)}</strong></div>
          <div className="preview-row"><span>Регион</span><strong>{value(profile.region)}</strong></div>
          <div className="preview-row"><span>Сфера</span><strong>{value(profile.industry)}</strong></div>
          <Button variant="secondary" onClick={onProfile} className="full">Изменить данные</Button>
        </Card>
        <Card className="tip-card"><IconSquare icon={Bookmark} tone="blue" /><h3>Сохраняйте подходящее</h3><p>В «Моих программах» удобно следить за документами и готовностью к подаче.</p><strong>{savedCount} сохранено</strong></Card>
      </aside>
    </div>
    <FooterNote count={catalogSize} />
  </div>;
}

function CatalogPage({ programs, recommendations, reasonsById, savedIds, onOpen, onSave, onBack }) {
  const [query, setQuery] = useState('');
  const [kind, setKind] = useState('Все');
  const [matchedOnly, setMatchedOnly] = useState(true);

  const source = matchedOnly ? recommendations : programs;
  const visible = useMemo(() => {
    const needle = query.toLowerCase().trim();
    return source.filter(program => {
      const isKind = kind === 'Все' || programKind(program) === kind;
      const text = `${program.title} ${program.fullTitle} ${program.description} ${program.type}`.toLowerCase();
      return isKind && text.includes(needle);
    });
  }, [source, kind, query]);

  return <div className="page page-catalog">
    <PageHeading title="Программы поддержки" subtitle="Выберите подходящую меру и изучите условия" onBack={onBack} trailing={<span className="count-badge">{visible.length} программ</span>} />
    <div className="catalog-tools">
      <label className="search-box"><Search size={18} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Поиск по программам" aria-label="Поиск по программам" />{query && <button onClick={() => setQuery('')} aria-label="Очистить поиск"><X size={16} /></button>}</label>
      <button className={`filter-match ${matchedOnly ? 'on' : ''}`} onClick={() => setMatchedOnly(!matchedOnly)}><SlidersHorizontal size={17} /> {matchedOnly ? 'Для моего профиля' : 'Весь каталог'}</button>
    </div>
    <div className="chips" role="group" aria-label="Вид поддержки">{KIND_FILTERS.map(item => <button key={item} onClick={() => setKind(item)} className={`chip ${kind === item ? 'chosen' : ''}`}>{item}</button>)}</div>
    {visible.length ? <div className="catalog-grid">{visible.map(program => <ProgramCard key={program.id} program={program} reasons={reasonsById.get(program.id)} onOpen={onOpen} onSave={onSave} saved={savedIds.includes(program.id)} />)}</div> : <Card className="empty-state"><Filter size={30} /><h3>Ничего не найдено</h3><p>Попробуйте изменить запрос или фильтр.</p><Button variant="secondary" onClick={() => { setQuery(''); setKind('Все'); setMatchedOnly(false); }}>Показать все программы</Button></Card>}
    <FooterNote count={programs.length} />
  </div>;
}

function DetailPage({ program, reasons, saved, onSave, onChecklist, onBack }) {
  const checkedAt = formatCheckedAt(program.checkedAt);
  const openSource = () => {
    if (!sourceIsHttp(program.sourceUrl)) return;
    if (window.WebApp?.openLink) window.WebApp.openLink(program.sourceUrl);
    else window.open(program.sourceUrl, '_blank', 'noopener,noreferrer');
  };
  return <div className="page page-detail">
    <PageHeading title={program.title} subtitle={program.fullTitle !== program.title ? program.fullTitle : programKind(program)} onBack={onBack} trailing={<span className="pill pill-blue">{programKind(program)}</span>} />
    <div className="detail-grid">
      <div className="detail-main">
        <Card className="amount-card"><strong>{program.highlight}</strong><div className="detail-facts"><div><span>Срок</span><b>{deadlineLabel(program)}</b></div><div><span>Регион</span><b>{regionLabel(program)}</b></div><div><span>Категория</span><b>Развитие бизнеса</b></div><div><span>Поддержка</span><b>{programKind(program)}</b></div></div>{reasons.length > 0 && <p className="eligibility-note"><span className="match-dot" /> Предварительно подходит по {reasons.length} параметрам профиля</p>}</Card>
        <Card><h2>Почему подходит вам</h2><p>{reasons.length ? `Программа ${reasons.join(', ')}. ` : 'Эта программа не попала в ваш персональный подбор — проверьте, подходите ли вы по условиям. '}Проверьте полные условия у организатора перед подачей заявки.</p></Card>
        <Card><h2>О программе</h2><p>{program.description}</p></Card>
        <Card><h2>Требования</h2><div className="check-text"><Check size={16} /> <span>{program.eligibleStatus || 'Требования к заявителю уточняйте у организатора.'}</span></div><div className="check-text"><Check size={16} /> <span>{program.conditions}</span></div></Card>
      </div>
      <div className="detail-side">
        <Card><h2>Необходимые документы</h2><p className="document-summary">{program.documents.slice(0, 4).join(' · ')}{program.documents.length > 4 ? ' · …' : ''}</p><Button variant="secondary" onClick={onChecklist} className="full" icon={ListChecks}>Открыть чек-лист</Button></Card>
        <Card><h2>Условия и срок</h2><p>{program.amount}</p><div className="divider" /><p>{program.deadline}</p></Card>
        <Card className="source-card"><h2>Источник данных</h2><p>{checkedAt ? (program.isMock ? `Снимок от ${checkedAt}. ` : `Проверено на официальном портале ${checkedAt}. `) : ''}Сроки и доступность могут измениться.</p>{sourceIsHttp(program.sourceUrl) && <button className="text-link" onClick={openSource}>Открыть источник <ExternalLink size={15} /></button>}</Card>
      </div>
    </div>
    <div className="detail-actions"><Button variant="secondary" onClick={() => onSave(program.id)} className={`flex-1 save-action ${saved ? 'saved' : ''}`} icon={Bookmark} aria-pressed={saved} aria-label={saved ? 'Сохранено. Нажмите, чтобы убрать из моих программ' : 'Сохранить в мои программы'}>{saved ? 'Сохранено' : 'Сохранить'}</Button><Button onClick={onChecklist} className="flex-1">Получить чек-лист</Button></div>
  </div>;
}

function SavedPage({ items, checkedByProgram, catalogSize, onOpen, onChecklist, onCatalog, onBack }) {
  return <div className="page page-saved">
    <PageHeading title="Мои программы" subtitle="Следите за подготовкой документов" onBack={onBack} trailing={<span className="count-badge">{items.length} сохранено</span>} />
    {items.length ? <div className="saved-grid">{items.map(program => {
      const done = (checkedByProgram[program.id] || []).length;
      const total = program.documents.length;
      const progress = total ? Math.round(done / total * 100) : 0;
      return <Card className="saved-card" key={program.id}>
        <span className={`pill ${progress === 100 ? 'pill-green' : progress > 0 ? 'pill-amber' : 'pill-blue'}`}>{progress === 100 ? 'Готово к подаче' : progress > 0 ? 'Собираю документы' : 'Сохранено'}</span>
        <h3>{program.title}</h3><p>Срок: {deadlineLabel(program)}</p>
        <div className="progress-label"><span>Документы</span><strong>{progress}%</strong></div><div className="progress"><i style={{ width: `${progress}%` }} /></div>
        <div className="saved-actions"><Button onClick={() => onOpen(program.id)} className="flex-1">Открыть</Button><Button variant="secondary" onClick={() => onChecklist(program.id)} className="flex-1">Чек-лист</Button></div>
      </Card>;
    })}</div> : <Card className="empty-state"><Bookmark size={32} /><h3>Пока ничего не сохранено</h3><p>Добавьте программы из рекомендаций, чтобы вернуться к ним позже.</p><Button onClick={onCatalog}>Смотреть программы</Button></Card>}
    <FooterNote count={catalogSize} />
  </div>;
}

function ChecklistPage({ program, checkedItems, onToggle, onDocument, onBack }) {
  const total = program.documents.length;
  const done = checkedItems.length;
  const progress = total ? Math.round(done / total * 100) : 0;
  return <div className="page page-checklist">
    <PageHeading title="Чек-лист документов" subtitle={program.title} onBack={onBack} />
    <div className="checklist-layout"><div className="checklist-main">
      <Card className="checklist-progress"><div className="progress-label"><strong>{done} из {total} готово</strong><strong>{progress}%</strong></div><div className="progress"><i style={{ width: `${progress}%` }} /></div></Card>
      <Card className="checklist-card"><div className="checklist-items">{program.documents.map((doc, index) => <div className={`checklist-item ${checkedItems.includes(doc) ? 'complete' : ''}`} key={`${doc}-${index}`}>
        <button className="check-toggle" onClick={() => onToggle(program.id, doc)} aria-label={`${checkedItems.includes(doc) ? 'Отметить как неготовый' : 'Отметить как готовый'}: ${doc}`}><Check size={15} /></button>
        <span>{doc}</span><button className="help-button" onClick={() => onDocument(doc)} aria-label={`Подробнее о документе: ${doc}`}><CircleHelp size={17} /></button>
      </div>)}</div></Card>
    </div><aside className="checklist-aside"><Card><IconSquare icon={ShieldCheck} tone="green" /><h3>Подготовьте документы заранее</h3><p>Отметки сохраняются на сервере, поэтому не теряются при смене устройства. Список составлен на основе описания программы — организатор может запросить дополнительные документы.</p></Card></aside></div>
  </div>;
}

function ProfileField({ field, icon, label, value: current, choices, open, menuLayout, onToggle, onChange }) {
  const optionsId = `profile-options-${field}`;
  return <div className={`profile-field-wrap ${open ? `open ${menuLayout.direction}` : ''}`} style={open ? { '--menu-max-height': `${menuLayout.maxHeight}px` } : undefined}>
    <button id={`profile-field-${field}`} type="button" className="profile-field" onClick={onToggle} aria-expanded={open} aria-controls={open ? optionsId : undefined}>
      <IconSquare icon={icon} /><span className="profile-field-label">{label}</span><strong className="profile-field-value">{current}</strong><ChevronRight size={17} className="profile-field-chevron" />
    </button>
    {open && <div id={optionsId} className="profile-options" role="group" aria-label={`${label}: выберите значение`}>
      {choices.map(choice => <button key={choice} type="button" aria-pressed={choice === current} className={`profile-option ${choice === current ? 'selected' : ''}`} onClick={() => onChange(choice)}><span>{choice}</span>{choice === current && <Check size={17} />}</button>)}
    </div>}
  </div>;
}

function ProfilePage({ profile, options, prefs, onPrefs, onProfile, onBack }) {
  const [editingName, setEditingName] = useState(false);
  const [openField, setOpenField] = useState(null);
  const [customRegion, setCustomRegion] = useState(null);
  const [menuLayout, setMenuLayout] = useState({ direction: 'down', maxHeight: 200 });

  useEffect(() => {
    if (!openField) return;
    const closeOnOutside = event => {
      if (!event.target.closest('.profile-field-wrap')) setOpenField(null);
    };
    const closeOnEscape = event => { if (event.key === 'Escape') setOpenField(null); };
    document.addEventListener('pointerdown', closeOnOutside);
    document.addEventListener('keydown', closeOnEscape);
    return () => { document.removeEventListener('pointerdown', closeOnOutside); document.removeEventListener('keydown', closeOnEscape); };
  }, [openField]);

  const toggleField = (field, anchor) => {
    if (openField === field) { setOpenField(null); return; }
    const rect = anchor.getBoundingClientRect();
    const mobile = window.matchMedia('(max-width: 760px)').matches;
    const below = window.innerHeight - rect.bottom - (mobile ? 78 : 16);
    const above = rect.top - 16;
    const direction = below < 170 && above > below ? 'up' : 'down';
    const available = direction === 'up' ? above : below;
    setMenuLayout({ direction, maxHeight: Math.max(100, Math.min(200, available - 8)) });
    setOpenField(field);
  };

  const selectField = (field, chosen) => {
    // "Другой регион" is a button label, not an answer: the API rejects it, so
    // choosing it opens a text field for the real region name instead.
    if (field === 'region' && chosen === options.other_region_label) {
      setCustomRegion(profile.region || '');
      setOpenField(null);
      return;
    }
    onProfile({ [field]: chosen });
    setOpenField(null);
  };

  const submitCustomRegion = event => {
    event.preventDefault();
    const region = customRegion.trim();
    if (!region) return;
    onProfile({ region });
    setCustomRegion(null);
  };

  const regionChoices = useMemo(() => {
    const list = [...options.region];
    if (profile.region && !list.includes(profile.region)) list.unshift(profile.region);
    return list;
  }, [options.region, profile.region]);

  const initials = prefs.name.split(' ').map(part => part[0]).slice(0, 2).join('');

  return <div className="page page-profile">
    <PageHeading title="Профиль" onBack={onBack} />
    <div className="profile-grid"><div className="profile-main">
      <div className="person"><div className="avatar">{initials}</div><div><strong>{prefs.name}</strong><span>Профиль для персональных рекомендаций</span></div><button className="person-edit" type="button" onClick={() => setEditingName(!editingName)}><Pencil size={15} />{editingName ? 'Готово' : 'Изменить имя'}</button></div>
      {editingName && <label className="name-edit">Имя<input value={prefs.name} onChange={event => onPrefs({ name: event.target.value })} maxLength={60} /></label>}
      <Card><h2>Данные для подбора</h2><p>Эти параметры используются для подбора программ, мер поддержки и персональных рекомендаций. Они те же, что вы указали боту.</p>
        <ProfileField field="status" icon={BriefcaseBusiness} label="Статус" value={value(profile.status)} choices={options.status} open={openField === 'status'} menuLayout={menuLayout} onToggle={event => toggleField('status', event.currentTarget)} onChange={chosen => selectField('status', chosen)} />
        <ProfileField field="region" icon={MapPin} label="Регион" value={value(profile.region)} choices={regionChoices} open={openField === 'region'} menuLayout={menuLayout} onToggle={event => toggleField('region', event.currentTarget)} onChange={chosen => selectField('region', chosen)} />
        {customRegion !== null && <form className="name-edit" onSubmit={submitCustomRegion}>
          Название региона
          <input autoFocus value={customRegion} onChange={event => setCustomRegion(event.target.value)} maxLength={150} placeholder="Например, Тверская область" />
          <div className="saved-actions">
            <Button type="submit" className="flex-1" disabled={!customRegion.trim()}>Сохранить</Button>
            <Button type="button" variant="secondary" className="flex-1" onClick={() => setCustomRegion(null)}>Отмена</Button>
          </div>
        </form>}
        <ProfileField field="industry" icon={Laptop} label="Отрасль" value={value(profile.industry)} choices={options.industry} open={openField === 'industry'} menuLayout={menuLayout} onToggle={event => toggleField('industry', event.currentTarget)} onChange={chosen => selectField('industry', chosen)} />
        <ProfileField field="priority" icon={LineChart} label="Приоритет" value={value(profile.priority)} choices={options.priority} open={openField === 'priority'} menuLayout={menuLayout} onToggle={event => toggleField('priority', event.currentTarget)} onChange={chosen => selectField('priority', chosen)} />
      </Card>
    </div><div className="profile-side">
      <Card><h2>Уведомления</h2><label className="setting-row"><IconSquare icon={Bell} /><span>Новые рекомендации</span><input type="checkbox" checked={prefs.notices} onChange={event => onPrefs({ notices: event.target.checked })} /></label><label className="setting-row"><IconSquare icon={Mail} /><span>Дайджест программ</span><input type="checkbox" checked={prefs.digest} onChange={event => onPrefs({ digest: event.target.checked })} /></label><p className="settings-note">Переключатели и имя сохраняются в этом браузере. Рассылка уведомлений ботом пока не подключена.</p></Card>
      <Card><h2>Источники и данные</h2><div className="info-row"><IconSquare icon={Sparkles} /><span>Как работают рекомендации</span></div><p className="settings-note">Предварительная сортировка по статусу, региону, сфере и приоритету. Подача заявки и проверка права на участие не выполняются.</p><div className="info-row"><IconSquare icon={CircleHelp} /><span>О сервисе</span><small>Демо 1.0</small></div></Card>
    </div></div>
  </div>;
}

function DocumentPage({ name, region, onBack }) {
  const info = documentInfo(name);
  return <div className="page page-document"><PageHeading title="Документ" onBack={onBack} />
    <div className="document-layout"><Card className="document-info"><span className={`pill ${info.office ? 'pill-green' : 'pill-blue'}`}>{info.label}</span><h2>{name}</h2>
      <div className="document-point"><IconSquare icon={FileText} /><div><strong>Что это</strong><p>{info.what}</p></div></div>
      <div className="document-point"><IconSquare icon={ShieldCheck} /><div><strong>Зачем нужен</strong><p>{info.why}</p></div></div>
      <div className="document-point"><IconSquare icon={ListChecks} /><div><strong>Как подготовить</strong><ol className="document-steps">{info.steps.map(step => <li key={step}>{step}</li>)}</ol></div></div>
      <div className="document-point"><IconSquare icon={FileText} /><div><strong>Что понадобится</strong><p>{info.prepare}</p></div></div>
      <div className="document-point"><IconSquare icon={Landmark} /><div><strong>Где получить</strong><p>{info.where}</p>{info.link && <a className="document-source" href={info.link} target="_blank" rel="noreferrer">{info.linkLabel} <ExternalLink size={14} /></a>}</div></div>
      <p className="document-caveat">Точные требования к форме и сроку действия документа проверьте в правилах выбранной программы.</p>
    </Card>{info.office ? <Suspense fallback={<Card className="document-self-note"><span className="boot-spinner" /><p>Загружаем карту пунктов…</p></Card>}><DocumentLocations office={info.office} region={region} /></Suspense> : <Card className="document-self-note"><IconSquare icon={CircleHelp} tone="blue" /><h2>Пункт выдачи не требуется</h2><p>Этот материал обычно готовит сам заявитель или выдаёт указанная в правилах программы организация. Проверьте источник и шаблон в условиях программы.</p></Card>}</div>
  </div>;
}

function LoadingScreen() {
  return <div className="boot-screen" role="status" aria-live="polite">
    <span className="boot-spinner" /><p>Загружаем меры поддержки…</p>
  </div>;
}

// Deep link to the bot: MAX opens the mini-app from its chat with a signed
// initData, which is what unlocks the profile and saved programs.
const BOT_URL = 'https://max.ru/t814_hakaton_max_bot';

function GuestBanner() {
  return <div className="guest-banner" role="note">
    <CircleHelp size={20} />
    <p>Вы смотрите каталог в браузере. Чтобы получить персональный подбор и сохранять программы, откройте приложение в MAX.</p>
    <a href={BOT_URL} target="_blank" rel="noreferrer">Открыть в MAX</a>
  </div>;
}

function ErrorScreen({ message, onRetry }) {
  return <div className="boot-screen">
    <Card className="empty-state">
      <CircleHelp size={30} />
      <h3>Не удалось загрузить данные</h3>
      <p>{message}</p>
      <Button onClick={onRetry} icon={RefreshCw}>Попробовать снова</Button>
    </Card>
  </div>;
}

export default function App() {
  const data = useAppData();
  const [page, setPage] = useState({ type: 'home' });
  const [history, setHistory] = useState([]);

  useLayoutEffect(() => { window.scrollTo(0, 0); }, [page]);

  useEffect(() => {
    if (!data.toast) return;
    const timer = window.setTimeout(() => data.setToast(''), 3200);
    return () => window.clearTimeout(timer);
  }, [data.toast, data.setToast]);

  const go = (type, id) => { setHistory(current => [...current, page]); setPage({ type, id }); window.scrollTo(0, 0); };
  const goTab = type => { setHistory([]); setPage({ type }); window.scrollTo(0, 0); };
  const back = () => { if (history.length) { setPage(history.at(-1)); setHistory(current => current.slice(0, -1)); } else { setPage({ type: 'home' }); } window.scrollTo(0, 0); };

  useEffect(() => {
    const bridge = window.WebApp?.BackButton;
    if (!bridge) return;
    const isDetail = !navItems.some(item => item.id === page.type);
    if (isDetail) { bridge.show?.(); bridge.onClick?.(back); }
    else bridge.hide?.();
    return () => { if (isDetail) bridge.offClick?.(back); };
  }, [page, history]);

  if (data.status === 'loading') return <LoadingScreen />;
  if (data.status === 'error') return <ErrorScreen message={data.error} onRetry={data.reload} />;

  const {
    programs, ranked, profile, options, prefs, savedIds, checkedByProgram,
    programsById, reasonsById, toast,
  } = data;

  const openDetail = id => go('detail', id);
  const openChecklist = id => go('checklist', id);
  const activeTab = navItems.some(item => item.id === page.type) ? page.type : page.type === 'detail' ? 'catalog' : page.type === 'checklist' || page.type === 'document' ? 'saved' : 'home';
  const mobileActiveTab = ['catalog', 'detail'].includes(page.type) ? 'home' : activeTab;
  const selectedProgram = typeof page.id === 'number' ? programsById.get(page.id) : undefined;
  const savedPrograms = savedIds.map(id => programsById.get(id)).filter(Boolean);

  return <div className="app-shell">
    <aside className="sidebar"><div className="brand"><div className="brand-mark"><img src="/logo.png" alt="" /></div><div><strong>Навигатор</strong><span>мер поддержки</span></div></div><nav aria-label="Основная навигация">{navItems.map(({ id, label, icon: Icon }) => <button key={id} className={`side-nav-item ${activeTab === id ? 'active' : ''}`} onClick={() => goTab(id)}><Icon size={20} /><span>{label}</span>{id === 'saved' && <small>{savedIds.length}</small>}</button>)}</nav><div className="sidebar-bottom"><span className="demo-badge">Демо-версия</span></div></aside>
    <div className="app-content"><header className="desktop-header"><div><b>Меры поддержки бизнеса</b></div><button className="header-profile" onClick={() => goTab('profile')}><span className="avatar small">{prefs.name.split(' ').map(part => part[0]).slice(0, 2).join('')}</span><span>{prefs.name}</span><ChevronRight size={16} /></button></header><main>
      {data.guest && <GuestBanner />}
      {page.type === 'home' && <HomePage profile={profile} savedCount={savedIds.length} recommendations={ranked} catalogSize={programs.length} onCatalog={() => goTab('catalog')} onOpen={openDetail} onProfile={() => goTab('profile')} />}
      {page.type === 'catalog' && <CatalogPage programs={programs} recommendations={ranked} reasonsById={reasonsById} savedIds={savedIds} onOpen={openDetail} onSave={data.toggleSaved} onBack={() => goTab('home')} />}
      {page.type === 'detail' && selectedProgram && <DetailPage program={selectedProgram} reasons={reasonsById.get(selectedProgram.id) || []} saved={savedIds.includes(selectedProgram.id)} onSave={data.toggleSaved} onChecklist={() => openChecklist(selectedProgram.id)} onBack={back} />}
      {page.type === 'saved' && <SavedPage items={savedPrograms} checkedByProgram={checkedByProgram} catalogSize={programs.length} onOpen={openDetail} onChecklist={openChecklist} onCatalog={() => goTab('catalog')} />}
      {page.type === 'checklist' && selectedProgram && <ChecklistPage program={selectedProgram} checkedItems={checkedByProgram[selectedProgram.id] || []} onToggle={data.toggleDocument} onDocument={name => go('document', name)} onBack={back} />}
      {page.type === 'profile' && <ProfilePage profile={profile} options={options} prefs={prefs} onPrefs={patch => data.setPrefs(current => ({ ...current, ...patch }))} onProfile={data.updateProfile} />}
      {page.type === 'document' && <DocumentPage name={page.id} region={profile.region} onBack={back} />}
    </main><nav className="bottom-nav" aria-label="Основная навигация">{[navItems[0], navItems[2], navItems[3]].map(({ id, label, icon: Icon }) => <button key={id} className={mobileActiveTab === id ? 'active' : ''} onClick={() => goTab(id)}><Icon size={20} strokeWidth={1.6} /><span>{label}</span></button>)}</nav>{toast && <div className="toast" role="status" aria-live="polite"><CheckCircle2 size={19} />{toast}</div>}</div>
  </div>;
}
