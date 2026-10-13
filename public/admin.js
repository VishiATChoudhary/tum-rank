const $ = s => document.querySelector(s);
const el = (t, p = {}, ...k) => { const e = Object.assign(document.createElement(t), p); e.append(...k.filter(x => x != null)); return e; };
const toast = m => { const t = $('#toast'); t.textContent = m; t.classList.add('on'); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('on'), 3500); };
let token = sessionStorage.getItem('tr-admin') || '';
const call = (path, body) => fetch('/api/admin/' + path, {
  method: body ? 'POST' : 'GET', headers: { 'X-Admin-Token': token, ...(body ? { 'Content-Type': 'application/json' } : {}) }, body: body && JSON.stringify(body),
}).then(async r => { const j = await r.json(); if (!r.ok) throw new Error(j.error || 'Error'); return j; });

async function load() {
  let q;
  try { q = await call('queue'); } catch (e) { sessionStorage.removeItem('tr-admin'); $('#queue').hidden = true; $('#login').hidden = false; toast(e.message); return; }
  sessionStorage.setItem('tr-admin', token); $('#login').hidden = true; $('#queue').hidden = false;
  const act = (type, id, action) => el('button', { className: 'btn' + (action === 'approve' || action === 'restore' ? ' primary' : ''), textContent: action,
    onclick: async () => { try { const r = await call('act', { type, id, action }); toast(r.message); load(); } catch (e) { toast(e.message); } } });
  $('#sug').replaceChildren(...(q.suggestions.length ? q.suggestions.map(s => el('li', {},
    el('div', { className: 'what' }, el('b', { textContent: s.kind === 'degree' ? `Degree · SPO ${s.spo}` : s.name }),
      el('small', { textContent: s.kind === 'degree' ? `https://campus.tum.de/tumonline/wbstpcs.showSpoTree?pStpStpNr=${s.spo}` : `course in degree ${s.spo}, under node ${s.parent} · ${s.created.slice(0, 16)}` })),
    el('div', { className: 'acts' }, act('suggestion', s.id, 'approve'), act('suggestion', s.id, 'reject'))))
    : [el('li', { className: 'empty', textContent: 'Nothing waiting.' })]));
  $('#flag').replaceChildren(...(q.flagged.length ? q.flagged.map(r => el('li', {},
    el('div', { className: 'what' }, el('b', { textContent: `${r.key} · ${r.course_stars}/5` }), el('div', { textContent: r.comment || '(no comment)' }),
      el('small', { textContent: `${r.reports} reports${r.prof_name ? ` · ${r.prof_name} ${r.prof_stars}/5` : ''}` })),
    el('div', { className: 'acts' }, act('rating', r.id, 'restore'), act('rating', r.id, 'remove'))))
    : [el('li', { className: 'empty', textContent: 'No reported comments.' })]));
}
$('#login').onsubmit = e => { e.preventDefault(); token = $('#tok').value.trim(); load(); };
$('#refresh').onclick = load;
if (token) load();
