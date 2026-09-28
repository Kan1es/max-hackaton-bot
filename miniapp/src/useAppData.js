/**
 * Loads everything the screens need from the backend and keeps it in sync.
 *
 * All shared state — profile, saved programs, checklist progress — lives in
 * Postgres, so the bot and the mini-app show the same thing and a user who
 * switches device doesn't lose their work. localStorage is used only for
 * per-browser cosmetics (display name, notification toggles), which is the
 * one thing it's actually suited for.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { api } from './api.js';
import { normalizeProgram } from './data/programs.js';

const PREFS_KEY = 'max-support-navigator-prefs-v2';
const EMPTY_PROFILE = { status: null, region: null, industry: null, priority: null };
export const GUEST_TOAST = 'Откройте приложение в MAX, чтобы сохранять программы и профиль';

// Opened in a plain browser rather than inside MAX: there is no signed
// initData, so a production backend refuses every personal endpoint.
const insideMax = () => Boolean(window.WebApp?.initData);
const defaultPrefs = { name: '', notices: true, digest: true };

function readPrefs() {
  try {
    const value = JSON.parse(localStorage.getItem(PREFS_KEY));
    return value && typeof value === 'object' ? { ...defaultPrefs, ...value } : defaultPrefs;
  } catch {
    return defaultPrefs;
  }
}

function displayName(prefs) {
  if (prefs.name) return prefs.name;
  const user = window.WebApp?.initDataUnsafe?.user;
  // Display only — the server never trusts initDataUnsafe for identity.
  const fromMax = [user?.first_name, user?.last_name].filter(Boolean).join(' ');
  return fromMax || 'Предприниматель';
}

export function useAppData() {
  const [state, setState] = useState({
    status: 'loading',   // loading | ready | error
    error: null,
    // Read-only catalog mode for a browser outside MAX.
    guest: false,
    options: null,
    programs: [],
    ranked: [],
    profile: null,
    applications: [],
  });
  const [prefs, setPrefs] = useState(readPrefs);
  const [toast, setToast] = useState('');
  const mounted = useRef(true);
  const guest = useRef(false);

  // Set on mount as well as cleared on unmount: React StrictMode mounts,
  // unmounts and remounts in development, and a ref that is only ever
  // cleared would stay false for the rest of the session — every response
  // would then be discarded and the app would sit on its loading screen.
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  useEffect(() => {
    try { localStorage.setItem(PREFS_KEY, JSON.stringify(prefs)); } catch { /* private mode */ }
  }, [prefs]);

  const load = useCallback(async () => {
    setState(current => ({ ...current, status: 'loading', error: null }));
    try {
      const [options, programs] = await Promise.all([api.getOptions(), api.getPrograms()]);
      let profile = EMPTY_PROFILE;
      let applications = [];
      let ranked = programs;
      guest.current = false;
      try {
        [profile, applications] = await Promise.all([api.getProfile(), api.getApplications()]);
        // Matching depends on the profile, so it is requested after it exists.
        ranked = await api.getMatches();
      } catch (error) {
        // Inside MAX a 401 means a real problem (expired or forged initData)
        // and is shown as an error; in a plain browser it is expected, and
        // the public catalog is still worth showing.
        if (error.status !== 401 || insideMax()) throw error;
        guest.current = true;
      }
      if (!mounted.current) return;
      setState({
        status: 'ready',
        error: null,
        guest: guest.current,
        options,
        programs: programs.map(normalizeProgram),
        ranked: ranked.map(normalizeProgram),
        profile,
        applications,
      });
    } catch (error) {
      if (!mounted.current) return;
      setState(current => ({ ...current, status: 'error', error: error.message }));
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const refreshMatches = useCallback(async () => {
    const ranked = await api.getMatches();
    if (mounted.current) setState(current => ({ ...current, ranked: ranked.map(normalizeProgram) }));
  }, []);

  const updateProfile = useCallback(async patch => {
    if (guest.current) { setToast(GUEST_TOAST); return; }
    // Optimistic: the dropdown should not lag behind the tap.
    setState(current => ({ ...current, profile: { ...current.profile, ...patch } }));
    try {
      const profile = await api.saveProfile(patch);
      if (mounted.current) setState(current => ({ ...current, profile }));
      await refreshMatches();
    } catch (error) {
      setToast(`Не удалось сохранить профиль: ${error.message}`);
      await load();
    }
  }, [load, refreshMatches]);

  const toggleSaved = useCallback(async programId => {
    if (guest.current) { setToast(GUEST_TOAST); return; }
    const existing = state.applications.find(item => item.program_id === programId);
    try {
      if (existing) {
        await api.deleteApplication(programId);
        setState(current => ({
          ...current,
          applications: current.applications.filter(item => item.program_id !== programId),
        }));
        setToast('Программа убрана из «Моих программ»');
      } else {
        const created = await api.saveApplication(programId);
        setState(current => ({ ...current, applications: [created, ...current.applications] }));
        setToast('Программа сохранена в «Моих программах»');
      }
    } catch (error) {
      setToast(`Не удалось сохранить: ${error.message}`);
      await load();
    }
  }, [state.applications, load]);

  const toggleDocument = useCallback(async (programId, doc) => {
    if (guest.current) { setToast(GUEST_TOAST); return; }
    let application = state.applications.find(item => item.program_id === programId);
    try {
      // Ticking a document on an unsaved program saves it first — otherwise
      // there is nowhere to store the progress.
      if (!application) {
        application = await api.saveApplication(programId);
        setState(current => ({ ...current, applications: [application, ...current.applications] }));
      }
      const current = application.checked_docs || [];
      const next = current.includes(doc)
        ? current.filter(value => value !== doc)
        : [...current, doc];
      setState(previous => ({
        ...previous,
        applications: previous.applications.map(item =>
          item.id === application.id ? { ...item, checked_docs: next } : item),
      }));
      await api.updateApplication(application.id, { checked_docs: next });
    } catch (error) {
      setToast(`Не удалось отметить документ: ${error.message}`);
      await load();
    }
  }, [state.applications, load]);

  const savedIds = useMemo(
    () => state.applications.map(item => item.program_id),
    [state.applications],
  );

  const checkedByProgram = useMemo(() => {
    const map = {};
    for (const item of state.applications) map[item.program_id] = item.checked_docs || [];
    return map;
  }, [state.applications]);

  const programsById = useMemo(() => {
    const map = new Map();
    for (const program of state.programs) map.set(program.id, program);
    return map;
  }, [state.programs]);

  const reasonsById = useMemo(() => {
    const map = new Map();
    for (const program of state.ranked) map.set(program.id, program.reasons);
    return map;
  }, [state.ranked]);

  return {
    ...state,
    prefs: { ...prefs, name: displayName(prefs) },
    setPrefs,
    savedIds,
    checkedByProgram,
    programsById,
    reasonsById,
    toast,
    setToast,
    reload: load,
    updateProfile,
    toggleSaved,
    toggleDocument,
  };
}
