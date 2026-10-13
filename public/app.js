const $ = s => document.querySelector(s);
const el = (tag, props = {}, ...kids) => {
  const { list, aria, data, ...rest } = props;
  const e = Object.assign(document.createElement(tag), rest);
  if (list) e.setAttribute('list', list);
  for (const [k, v] of Object.entries(aria || {})) e.setAttribute('aria-' + k, v);
  for (const [k, v] of Object.entries(data || {})) e.dataset[k] = v;
  e.append(...kids.filter(k => k != null && k !== false));
  return e;
};
const getJSON = url => fetch(url).then(r => { if (!r.ok) throw new Error('Could not load ' + url); return r.json(); });
const api = (p, body) => fetch('/api/' + p, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {})
  .then(async r => { const j = await r.json(); if (!r.ok) throw new Error(j.error || 'Something went wrong'); return j; });
const toast = msg => { const t = $('#toast'); t.textContent = msg; t.classList.add('on'); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('on'), 2600); };
const fmt = x => x == null ? '—' : x.toFixed(1);
// Bayesian average: pulls courses with few ratings toward 3.0 so one 5-star can't top the table
const PRIOR_N = 3, PRIOR = 3;
const score = m => m.n ? (m.avg * m.n + PRIOR * PRIOR_N) / (m.n + PRIOR_N) : -1;
const tier = a => 'r' + Math.min(5, Math.max(1, Math.round(a)));
const PLACEHOLDER = /anerkennung|recognition|platzhalter|placeholder/i;

let LINKS = {};
getJSON('/data/links.json').then(d => { LINKS = d; }).catch(() => {});
const state = { spo: null, degrees: [], mods: [], areas: [], area: null, sort: 'rating', diff: 'any', limit: 60, open: null };
// difficulty bands on the 1-5 average
const DIFF = { any: () => true, easy: d => d != null && d < 2.5, medium: d => d != null && d >= 2.5 && d < 3.5, hard: d => d != null && d >= 3.5 };
const diffWord = d => d == null ? '' : d < 2.5 ? 'Easy' : d < 3.5 ? 'Medium' : 'Hard';

function prettyDegree(t) {
  const m = t.match(/^\d+ \d+ (.+?) \((\d{4})\d, (\w+?)studium, (\w+)\)/);
  if (!m) return t;
  const level = m[3] === 'Master' ? 'M.Sc.' : m[3] === 'Bachelor' ? 'B.Sc.' : m[3];
  return `${m[1]} ${level} · ${m[2]}${m[4] === 'auslaufend' ? ' · phasing out' : ''}`;
}

// ---------- model ----------
function build(tree, stats, extra) {
  const mods = [], areas = new Map();
  const byId = new Map();
  (function index(n) { n.children ||= []; byId.set(n.id, n); n.key = n.code; n.children.forEach(index); })(tree);
  for (const x of extra) byId.get(x.parent)?.children.push({ id: x.key, key: x.key, name: x.name, user: 1, children: [] });
  (function attach(n) { const s = stats[n.key]; if (s) Object.assign(n, { avg: s[0], n: s[1], pavg: s[2], dist: s.slice(3, 8), diff: s[8] ?? null, diffN: s[9] || 0 }); n.children.forEach(attach); })(tree);
  const hasCode = n => n.children.some(c => c.code || hasCode(c));
  (function walk(n, anc) {
    const leafish = (n.code && !hasCode(n)) || (n.user && !n.children.length);
    if (leafish && anc.length) {
      if (PLACEHOLDER.test(n.name) || /^IN99/.test(n.code || '')) return;
      const group = anc[0], area = anc[1] || anc[0];
      let a = areas.get(area.id);
      if (!a) areas.set(area.id, a = { id: area.id, name: area.name, group: group.name, mods: [], keys: new Set() });
      if (a.keys.has(n.key)) return;
      a.keys.add(n.key);
      const m = { key: n.key, code: n.code, name: n.name, ects: n.ects, avg: n.avg ?? null, n: n.n || 0, dist: n.dist, pavg: n.pavg, diff: n.diff ?? null, area: a, user: n.user };
      a.mods.push(m); mods.push(m);
      return;
    }
    for (const c of n.children) walk(c, n.id.startsWith('root') ? anc : [...anc, n]);
  })(tree, []);
  // a course can sit in several areas: keep one record per key for the global table
  const seen = new Map();
  for (const m of mods) if (!seen.has(m.key)) seen.set(m.key, m);
  for (const a of areas.values()) {
    const rated = a.mods.filter(m => m.avg != null);
    const w = rated.reduce((s, m) => s + m.n, 0);
    a.avg = w ? rated.reduce((s, m) => s + m.avg * m.n, 0) / w : null;
    a.rated = rated.length;
  }
  state.mods = [...seen.values()];
  // order: elective catalogues first, then single-module essentials, then non-CS catalogues
  const all = [...areas.values()].filter(a => a.mods.length);
  const perGroup = {}; for (const a of all) perGroup[a.group] = (perGroup[a.group] || 0) + 1;
  for (const a of all) if (a.group === a.name || perGroup[a.group] < 3) a.group = 'Program essentials';
  const rank = a => /überfachlich|sprach|linde|soft skill|general education/i.test(a.group + ' ' + a.name) ? 2 : a.group === 'Program essentials' ? 1 : 0;
  all.forEach(a => a.rank = rank(a));
  state.areas = all.map((a, i) => [a, i]).sort((x, y) => rank(x[0]) - rank(y[0]) || x[1] - y[1]).map(x => x[0]);
}

async function loadDegree(spo, keepArea) {
  state.spo = +spo;
  const [tree, stats, extra] = await Promise.all([getJSON(`/data/trees/${spo}.json`), api('stats'), api('extra?spo=' + spo).catch(() => [])]);
  build(tree, stats, extra);
  if (!keepArea) { state.area = null; state.limit = 60; }
  else state.area = state.areas.find(a => a.id === state.area?.id) || null;
  const u = new URL(location); u.searchParams.set('d', spo);
  state.area ? u.searchParams.set('a', state.area.id) : u.searchParams.delete('a');
  history.replaceState(null, '', u);
  render();
}

// ---------- render ----------
function render() {
  const d = state.degrees.find(x => x.spo === state.spo);
  const ratings = state.mods.reduce((s, m) => s + m.n, 0);
  $('#summary').replaceChildren(
    el('b', { textContent: state.mods.length }), ' courses in ', el('b', { textContent: state.areas.length }), ' areas of ',
    prettyDegree(d?.title || ''), ' · ', el('b', { textContent: ratings }), ratings === 1 ? ' rating so far.' : ' ratings so far.');
  renderAreas(); renderTable();
}

function bars(mods) {
  const sorted = [...mods].sort((a, b) => score(b) - score(a));
  return el('span', { className: 'bars', aria: { hidden: 'true' } }, ...sorted.slice(0, 140).map(m =>
    el('i', m.avg != null ? { className: tier(m.avg), style: `height:${20 + m.avg * 16}%` } : { className: 'u' })));
}

function renderAreas() {
  const box = $('#areas'); box.replaceChildren();
  let group = null;
  for (const a of state.areas) {
    if (a.group !== group) box.append(el('div', { className: 'group', textContent: a.group }));
    group = a.group;
    box.append(el('button', {
      className: 'area', aria: { pressed: String(state.area === a) },
      onclick: () => { state.area = state.area === a ? null : a; state.limit = 60; syncUrl(); renderAreas(); renderTable(); toListTop(); },
    },
      el('span', { className: 'nm', title: a.name }, el('span', { className: 't', textContent: a.name }), el('small', { textContent: `${a.mods.length} course${a.mods.length === 1 ? '' : 's'} · ${a.rated} rated` })),
      bars(a.mods),
      el('span', { className: 'avg' + (a.avg == null ? ' none' : ''), textContent: fmt(a.avg) })));
  }
}
// show the first row of the list: side-by-side layout only scrolls up if we're past the list start; stacked layout jumps to the list
function toListTop() {
  const mast = $('.mast').offsetHeight;
  const y = $('.table').getBoundingClientRect().top + scrollY - mast;
  const sideBySide = matchMedia('(min-width: 1300px)').matches;
  if (!sideBySide || scrollY > y) scrollTo({ top: Math.max(0, y), behavior: 'instant' });
}
const syncUrl = () => { const u = new URL(location); state.area ? u.searchParams.set('a', state.area.id) : u.searchParams.delete('a'); history.replaceState(null, '', u); };

function sorted(list) {
  const by = {
    rating: (a, b) => score(b) - score(a) || b.n - a.n || a.area.rank - b.area.rank || a.name.localeCompare(b.name),
    count: (a, b) => b.n - a.n || score(b) - score(a) || a.area.rank - b.area.rank || a.name.localeCompare(b.name),
    name: (a, b) => a.name.localeCompare(b.name),
  }[state.sort];
  return [...list].sort(by);
}

function meter(avg) {
  return el('span', { className: 'meter', aria: { hidden: 'true' } }, ...[1, 2, 3, 4, 5].map(i =>
    el('i', {}, el('b', { style: `width:${avg == null ? 0 : Math.max(0, Math.min(1, avg - i + 1)) * 100}%` }))));
}

function renderTable() {
  const list = sorted((state.area ? state.area.mods : state.mods).filter(m => DIFF[state.diff](m.diff)));
  $('#table-h').textContent = state.area ? state.area.name : 'All courses';
  const rows = $('#rows'); rows.replaceChildren();
  let rank = 0;
  for (const m of list.slice(0, state.limit)) {
    const r = m.avg != null && state.sort !== 'name' ? ++rank : null;
    rows.append(el('li', {
      className: 'row' + (r && r <= 3 ? ' top' : '') + (state.open === m.key ? ' on' : ''), tabIndex: 0, data: { key: m.key },
      onclick: () => openCourse(m), onkeydown: e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openCourse(m); } },
    },
      el('span', { className: 'rk', textContent: r ?? '' }),
      el('span', { className: 'cd', textContent: m.code || 'added' }),
      el('span', { className: 'nm' }, el('b', { textContent: m.name, title: m.name }), el('small', { textContent: m.area.name })),
      el('span', { className: 'ec', textContent: m.ects ? `${m.ects} ECTS` : '' }),
      el('span', { className: 'df' + (m.diff == null ? ' none' : ''), title: m.diff == null ? 'No difficulty votes yet' : `Difficulty ${fmt(m.diff)} of 5` }, m.diff == null ? '—' : diffWord(m.diff), m.diff == null ? null : el('small', { textContent: fmt(m.diff) })),
      meter(m.avg),
      el('span', { className: 'sc' + (m.avg == null ? ' none' : '') }, fmt(m.avg), m.n ? el('small', { textContent: `${m.n} rating${m.n > 1 ? 's' : ''}` }) : null)));
  }
  if (!list.length) rows.append(el('li', { className: 'empty', textContent: state.diff === 'any' ? 'No courses here yet.' : 'No course here has enough difficulty votes for this filter yet.' }));
  if (list.length > state.limit) rows.append(el('li', {}, el('button', { className: 'btn more', textContent: `Show all ${list.length}`, onclick: () => { state.limit = Infinity; renderTable(); } })));
  renderSuggest();
}

function renderSuggest() {
  const box = $('#suggest'); box.replaceChildren();
  if (!state.area) return;
  const name = el('input', { className: 'field', maxLength: 80, placeholder: 'Course name', required: true, aria: { label: 'Course name' } });
  const hp = el('input', { className: 'hp', tabIndex: -1, autocomplete: 'off', aria: { hidden: 'true' } });
  const btn = el('button', { className: 'btn', textContent: 'Suggest course' });
  const f = el('form', {}, name, hp, btn);
  f.onsubmit = async e => {
    e.preventDefault(); btn.dataset.state = 'loading'; btn.disabled = true;
    try {
      const r = await api('suggest', { kind: 'course', spo: state.spo, parent: state.area.id, name: name.value, website: hp.value });
      toast(r.message || 'Thanks!'); name.value = '';
    } catch (x) { name.setAttribute('aria-invalid', 'true'); toast(x.message); }
    finally { btn.dataset.state = ''; btn.disabled = false; }
  };
  box.append(`Missing a course in ${state.area.name}? Suggest it, a moderator checks it before it shows up.`, f);
}

// ---------- drawer ----------
let lastFocus = null;
function closeDrawer() {
  const d = $('#drawer'); d.classList.remove('on'); d.setAttribute('aria-hidden', 'true');
  $('#scrim').classList.remove('on'); setTimeout(() => { $('#scrim').hidden = true; }, 280);
  state.open = null; document.querySelectorAll('.row.on').forEach(r => r.classList.remove('on'));
  lastFocus?.focus?.();
}
$('#scrim').onclick = closeDrawer;
addEventListener('keydown', e => { if (e.key === 'Escape' && state.open) closeDrawer(); });

const canHover = matchMedia('(hover: hover)').matches;
function diffPicker(value, onChange) {
  let v = value || 0;
  const wrap = el('span', { className: 'diffpick', role: 'radiogroup', aria: { label: 'Difficulty, 1 easy to 5 very hard' } });
  const words = ['Very easy', 'Easy', 'Medium', 'Hard', 'Very hard'];
  const paint = () => [...wrap.children].forEach((b, i) => { b.classList.toggle('on', i + 1 <= v); b.setAttribute('aria-checked', String(i + 1 === v)); });
  for (let i = 1; i <= 5; i++) wrap.append(el('button', { type: 'button', textContent: i, role: 'radio', title: words[i - 1], aria: { label: `${i}, ${words[i - 1]}` },
    onclick: () => { v = v === i ? 0 : i; paint(); onChange(v); } }));
  paint(); return wrap;
}
function starPicker(label, value, onChange) {
  let v = value || 0;
  const wrap = el('span', { className: 'stars', role: 'radiogroup', aria: { label } });
  const paint = x => [...wrap.children].forEach((b, i) => { b.classList.toggle('on', i < x); b.setAttribute('aria-checked', String(i + 1 === v)); });
  for (let i = 1; i <= 5; i++) wrap.append(el('button', {
    type: 'button', textContent: '★', role: 'radio', aria: { label: `${i} of 5` },
    onclick: () => { v = v === i ? 0 : i; paint(v); onChange(v); },
    onmouseenter: () => canHover && paint(i), onmouseleave: () => paint(v),
  }));
  paint(v); return wrap;
}

async function openCourse(m) {
  lastFocus = document.activeElement;
  state.open = m.key;
  document.querySelectorAll('.row').forEach(r => r.classList.toggle('on', r.dataset.key === m.key));
  const d = $('#drawer');
  d.replaceChildren(el('p', { className: 'where', textContent: 'Loading…' }));
  $('#scrim').hidden = false; requestAnimationFrame(() => $('#scrim').classList.add('on'));
  d.classList.add('on'); d.setAttribute('aria-hidden', 'false'); d.focus();
  let info;
  try {
    const [live, meta] = await Promise.all([api('module/' + encodeURIComponent(m.key)), m.code ? getJSON(`/data/m/${encodeURIComponent(m.code)}.json`).catch(() => ({})) : {}]);
    info = { name: meta.name || m.name, description: meta.description || '', prerequisites: meta.prerequisites || '', professors: meta.professors || [], ...live };
  }
  catch (x) { d.replaceChildren(el('p', { textContent: x.message })); return; }
  if (state.open !== m.key) return;

  const dist = [0, 0, 0, 0, 0]; info.ratings.forEach(r => dist[r.course - 1]++);
  const max = Math.max(1, ...dist);
  const desc = info.description || '';
  const about = el('p', { className: 'prose', textContent: desc.length > 520 ? desc.slice(0, 520).trimEnd() + '…' : desc });
  const more = desc.length > 520 ? el('button', { className: 'link', textContent: 'Read the full description', onclick: e => { about.textContent = desc; e.target.remove(); } }) : null;

  d.replaceChildren(...[
    el('button', { className: 'x', aria: { label: 'Close' }, textContent: '×', onclick: closeDrawer }),
    el('div', { className: 'code', textContent: [m.code || 'Added by students', m.ects ? `${m.ects} ECTS` : null].filter(Boolean).join(' · ') }),
    el('h2', { textContent: info.name }),
    el('div', { className: 'where', textContent: m.area.name }),
    el('div', { className: 'score' },
      el('div', { className: 'big' }, fmt(info.avg), el('small', { textContent: info.n ? `${info.n} rating${info.n > 1 ? 's' : ''}` : 'not rated yet' }),
        el('span', { className: 'dif', textContent: info.difficulty != null ? `${diffWord(info.difficulty)} · ${fmt(info.difficulty)}/5 difficulty` : 'No difficulty votes' })),
      el('div', { className: 'hist', aria: { label: 'Rating distribution' } }, ...[5, 4, 3, 2, 1].map(s =>
        el('div', {}, String(s), el('span', {}, el('b', { style: `width:${dist[s - 1] / max * 100}%` })), String(dist[s - 1]))))),
    info.prof_avgs.length ? el('h3', { textContent: 'Teaching' }) : null,
    ...info.prof_avgs.map(p => el('div', { className: 'prof' }, el('span', { textContent: `${p.name} (${p.n})` }), el('b', { textContent: fmt(p.avg) }))),
    rateForm(m, info),
    desc ? el('h3', { textContent: 'About the course' }) : null, desc ? about : null, more,
    info.prerequisites ? el('h3', { textContent: 'Before you take it' }) : null,
    info.prerequisites ? el('p', { className: 'prose', textContent: info.prerequisites }) : null,
    el('h3', { textContent: `What students say (${info.ratings.filter(r => r.comment).length})` }),
    ...comments(info), ...elsewhere(m)].filter(Boolean));
}

// Discussions on other sites. We deep-link only: their text stays on their site.
function elsewhere(m) {
  const ls = LINKS[m.code] || [];
  if (!ls.length) return [];
  return [el('h3', { textContent: 'Discussed elsewhere' }),
    el('p', { className: 'where', textContent: 'Found on other sites. Opinions there are not part of the ratings above.' }),
    ...ls.map(l => el('a', { className: 'out', href: l.url, target: '_blank', rel: 'noopener nofollow ugc' },
      el('span', { textContent: l.title }), el('small', { textContent: [l.src, l.date].filter(Boolean).join(' · ') })))];
}
function comments(info) {
  const list = info.ratings.filter(r => r.comment);
  if (!list.length) return [el('p', { className: 'where', textContent: 'No comments yet. Be the first.' })];
  return list.map(r => el('div', { className: 'cm' },
    el('div', { className: 'who' }, el('span', {}, el('b', { textContent: `${r.course}/5` }), r.difficulty ? ` · difficulty ${r.difficulty}/5` : '', r.prof ? ` · ${r.prof} ${r.prof_stars}/5` : ''),
      el('button', { textContent: 'Report', onclick: async e => { try { await api('report', { kind: 'rating', id: r.id }); e.target.replaceWith('Reported'); } catch (x) { toast(x.message); } } })),
    el('div', { textContent: r.comment })));
}

function rateForm(m, info) {
  const mine = info.mine || {};
  const st = { cs: mine.course_stars || 0, ps: mine.prof_stars || 0, df: mine.difficulty || 0 };
  const prof = el('input', { className: 'field', maxLength: 60, placeholder: 'Professor’s full name', value: mine.prof_name || '', list: 'profs', aria: { label: 'Professor name' } });
  const dl = el('datalist', { id: 'profs' }, ...info.professors.map(p => el('option', { value: p })));
  const com = el('textarea', { className: 'field', maxLength: 200, rows: 3, placeholder: 'One honest sentence helps the next student. Text only.', value: mine.comment || '', aria: { label: 'Comment' } });
  const cnt = el('span', { textContent: `${com.value.length} / 200` });
  com.oninput = () => { cnt.textContent = `${com.value.length} / 200`; com.removeAttribute('aria-invalid'); };
  const hp = el('input', { className: 'hp', tabIndex: -1, autocomplete: 'off', aria: { hidden: 'true' } });
  const err = el('p', { className: 'err', role: 'alert', textContent: mine.comment_status === 'pending' ? 'Your comment is waiting for a moderator.' : '' });
  const btn = el('button', { className: 'btn primary', textContent: info.mine ? 'Update rating' : 'Post rating' });
  const f = el('form', { className: 'rate' },
    el('h3', { textContent: info.mine ? 'Your rating' : 'Rate it' }),
    el('div', { className: 'line' }, el('label', { textContent: 'Course' }), starPicker('Course rating', st.cs, v => st.cs = v)),
    el('div', { className: 'line' }, el('label', { textContent: 'Professor' }), starPicker('Professor rating', st.ps, v => st.ps = v)),
    el('div', { className: 'line' }, el('label', { textContent: 'Difficulty' }), diffPicker(st.df, v => st.df = v)),
    prof, dl, com, hp, el('div', { className: 'meta' }, cnt, btn), err);
  f.onsubmit = async e => {
    e.preventDefault(); err.textContent = '';
    if (!st.cs) { err.textContent = 'Pick 1 to 5 stars for the course.'; return; }
    if (st.ps && !prof.value.trim()) { err.textContent = 'Add the professor’s name, or clear their stars.'; prof.setAttribute('aria-invalid', 'true'); return; }
    btn.dataset.state = 'loading'; btn.disabled = true; btn.textContent = 'Posting…';
    try {
      const res = await api('rate', { key: m.key, course_stars: st.cs, prof_stars: st.ps || null, prof_name: st.ps ? prof.value : '', difficulty: st.df || null, comment: com.value, website: hp.value });
      await loadDegree(state.spo, true);
      const fresh = state.mods.find(x => x.key === m.key) || m;
      openCourse(fresh); toast(res.message || 'Rating saved');
    } catch (x) {
      err.textContent = x.message; com.setAttribute('aria-invalid', 'true');
      btn.dataset.state = ''; btn.disabled = false; btn.textContent = info.mine ? 'Update rating' : 'Post rating';
    }
  };
  return f;
}

// ---------- search ----------
const q = $('#q'), hits = $('#hits');
let hitList = [], hitIdx = 0;
q.oninput = () => {
  const t = q.value.trim().toLowerCase(); hitIdx = 0;
  if (!t) { hitList = []; hits.replaceChildren(); return; }
  const words = t.split(/\s+/);
  hitList = state.mods.filter(m => { const h = `${m.code || ''} ${m.name} ${m.area.name}`.toLowerCase(); return words.every(w => h.includes(w)); })
    .sort((a, b) => ((b.code || '').toLowerCase() === t) - ((a.code || '').toLowerCase() === t) || (b.avg ?? -1) - (a.avg ?? -1)).slice(0, 10);
  paintHits();
};
function paintHits() {
  hits.replaceChildren(...(hitList.length ? hitList.map((m, i) => el('li', {
    role: 'option', aria: { selected: String(i === hitIdx) }, onmousedown: e => { e.preventDefault(); pick(m); },
  }, el('span', { className: 'c', textContent: m.code || 'added' }), el('span', { className: 'n', textContent: m.name }),
    el('small', { textContent: `${m.area.name}${m.avg != null ? ` · ${fmt(m.avg)}` : ''}` })))
    : [el('li', { className: 'where' }, el('span', { className: 'c', textContent: '' }), el('span', { className: 'n', textContent: 'No course matches.' }))]));
}
function pick(m) { hits.replaceChildren(); q.blur(); openCourse(m); }
q.onkeydown = e => {
  if (!hitList.length) { if (e.key === 'Escape') { q.value = ''; q.blur(); } return; }
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); hitIdx = (hitIdx + (e.key === 'ArrowDown' ? 1 : hitList.length - 1)) % hitList.length; paintHits(); }
  else if (e.key === 'Enter') { e.preventDefault(); pick(hitList[hitIdx]); }
  else if (e.key === 'Escape') { q.value = ''; hitList = []; hits.replaceChildren(); q.blur(); }
};
q.onblur = () => setTimeout(() => hits.replaceChildren(), 120);
q.onfocus = () => q.value && q.oninput();
addEventListener('keydown', e => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'f') { e.preventDefault(); q.focus(); q.select(); } });
if (!/Mac|iPhone|iPad/.test(navigator.platform)) $('.find kbd').textContent = 'Ctrl F';

// ---------- sort tabs / degree / import ----------
document.querySelectorAll('.sort button').forEach(b => b.onclick = () => {
  state.sort = b.dataset.sort;
  document.querySelectorAll('.sort button').forEach(x => x.setAttribute('aria-selected', String(x === b)));
  renderTable();
});
const fitSelect = () => { const s = $('#degree'); const probe = el('span', { textContent: s.selectedOptions[0]?.textContent || '', style: 'position:absolute;visibility:hidden;white-space:nowrap;font:600 var(--text-lg)/1.1 var(--font-display);text-transform:uppercase' }); document.body.append(probe); s.style.width = `calc(${probe.offsetWidth}px + var(--space-xl))`; probe.remove(); };
document.querySelectorAll('.diff button').forEach(b => b.onclick = () => {
  state.diff = b.dataset.diff; state.limit = 60;
  document.querySelectorAll('.diff button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
  renderTable(); toListTop();
});
$('#degree').onchange = e => { fitSelect(); loadDegree(e.target.value); };
$('#adddeg').onclick = () => {
  const foot = $('.foot'); if ($('#impf')) return $('#impf input').focus();
  const inp = el('input', { className: 'field', inputMode: 'numeric', pattern: '[0-9]{1,5}', placeholder: 'SPO number, e.g. 4731', aria: { label: 'TUMonline curriculum number' } });
  const btn = el('button', { className: 'btn', textContent: 'Import' });
  const f = el('form', { id: 'impf', style: 'display:flex;gap:var(--space-2xs);flex-wrap:wrap' }, inp, btn);
  f.onsubmit = async e => { e.preventDefault(); btn.disabled = true; try { const r = await api('suggest', { kind: 'degree', spo: parseInt(inp.value, 10) }); toast(r.message); f.remove(); } catch (x) { toast(x.message); btn.disabled = false; } };
  foot.append(f); inp.focus();
};

(async () => {
  state.degrees = await getJSON('/data/degrees.json');
  const sel = $('#degree');
  sel.replaceChildren(...state.degrees.map(d => el('option', { value: d.spo, textContent: prettyDegree(d.title) })));
  const p = new URLSearchParams(location.search);
  const want = +p.get('d') || (state.degrees.find(d => /Informatik \(\d+, Master.*, laufend\)$/.test(d.title)) || state.degrees.find(d => /, laufend\)$/.test(d.title)) || state.degrees[0]).spo;
  sel.value = want; document.fonts.ready.then(fitSelect);
  await loadDegree(want);
  const a = p.get('a'); if (a) { state.area = state.areas.find(x => x.id === a) || null; renderAreas(); renderTable(); }
})();
