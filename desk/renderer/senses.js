'use strict';
// Always-on senses: the consent card shown at start (every sense OFF until Ben switches it on) and the Senses section in Settings.
// Main owns the truth (userData/senses.json, src/senses.js); this file only shows it and sends Ben's choices back.
window.SensesUI = (() => {
  const desk = window.desk;
  const $ = (s) => document.querySelector(s);
  const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x !== undefined) e.textContent = x; return e; };
  const PERM_WORDS = { screenRecording: 'Screen Recording', accessibility: 'Accessibility', microphone: 'Microphone' };

  function toggle(label, on, onChange) {
    const b = el('button', 'toggle'); b.type = 'button'; b.setAttribute('role', 'switch'); b.setAttribute('aria-label', label); b.setAttribute('aria-checked', String(!!on));
    b.onclick = () => { const v = b.getAttribute('aria-checked') !== 'true'; b.setAttribute('aria-checked', String(v)); onChange(v); };
    return b;
  }
  // rows of senses with switches; draft = {screen: bool, ...} is changed in place
  function rows(list, draft, onChange) {
    const box = el('div', 'se-rows');
    for (const s of list) {
      const row = el('div', 'p-row se-row'); row.dataset.sense = s.id;
      const lab = el('div', 'p-lab'); lab.append(el('b', null, s.label), el('span', null, s.help));
      row.append(lab, toggle(s.label, draft[s.id], (v) => { draft[s.id] = v; row.classList.toggle('on', v); if (onChange) onChange(); }));
      row.classList.toggle('on', !!draft[s.id]);
      box.append(row);
    }
    return box;
  }
  // "Screen needs Screen Recording" + a button that asks macOS (deskhelper ask-permissions)
  function permLine(missing) {
    const box = el('div', 'se-perm'); box.setAttribute('role', 'alert');
    if (!missing || !missing.length) { box.hidden = true; return box; }
    const words = missing.map((m) => m.label + ' needs ' + (PERM_WORDS[m.perm] || m.perm)).join('. ');
    box.append(el('span', null, words + '. macOS has not allowed it yet, so that sense stays quiet.'));
    const b = el('button', 'amber-btn sm', 'Ask macOS'); b.id = 'sensesAskPerms';
    b.onclick = async () => { b.disabled = true; b.textContent = 'Asking…'; await desk.senses.askPerms(); const v = await desk.senses.get(); box.replaceWith(permLine(v.missing)); };
    box.append(b);
    return box;
  }

  // ---- the start-up card
  async function showCard(force) {
    const v = await desk.senses.get();
    if (!force && !v.needs) return false;
    const root = $('#sensesCard'); root.textContent = '';
    const draft = { ...v.consent.senses };
    const card = el('div', 'p-card se-card');
    const head = el('div', 'p-head'); head.append(el('h2', null, 'What may Glim notice?'));
    card.append(head, el('p', 'p-sub', 'Glim can stay switched on and speak up by itself when it notices something useful. Pick what it may pay attention to. Everything is off until you switch it on, stays on this Mac, and you can change it in Settings > Senses.'));
    card.append(rows(v.senses, draft));
    const rem = el('label', 'sl-check'); const cb = el('input'); cb.type = 'checkbox'; cb.id = 'sensesRemember'; cb.checked = !!v.consent.remember;
    rem.append(cb, el('span', null, 'Remember my choice')); card.append(rem);
    const perm = el('div'); card.append(perm);
    const btns = el('div', 'sl-btns');
    const none = el('button', 'ghost', 'Not now'); none.id = 'sensesNone';
    const ok = el('button', 'amber-btn', 'Save'); ok.id = 'sensesSave';
    btns.append(none, ok); card.append(btns);
    root.append(card); root.hidden = false;
    const finish = async (senses) => {
      const r = await desk.senses.set({ senses, remember: cb.checked, on: v.consent.on });
      if (r.missing && r.missing.length) { perm.replaceWith(permLine(r.missing)); ok.textContent = 'Done'; ok.onclick = () => { root.hidden = true; }; none.hidden = true; return; }
      root.hidden = true;
    };
    ok.onclick = () => finish(draft);
    none.onclick = () => finish(Object.fromEntries(Object.keys(draft).map((k) => [k, false])));
    root.onkeydown = (e) => { if (e.key === 'Escape') none.click(); };
    ok.focus();
    return true;
  }

  // ---- Settings > Senses (a block for one settings row)
  function settingsUi() {
    const box = el('div', 'se-settings'); box.id = 'sensesSettings';
    const paint = async () => {
      const v = await desk.senses.get();
      box.textContent = '';
      const draft = { ...v.consent.senses };
      const top = el('div', 'p-row se-row'); const tl = el('div', 'p-lab');
      tl.append(el('b', null, 'Always-on Glim'), el('span', null, v.status || 'Glim watches the senses below and speaks up by itself when it has something useful. Off = it only answers when you write.'));
      top.append(tl, toggle('Always-on Glim', v.consent.on, async (on) => { await desk.senses.set({ ...v.consent, senses: draft, on }); paint(); }));
      top.id = 'alwaysOnRow'; top.classList.toggle('on', !!v.consent.on);
      box.append(top, rows(v.senses, draft, async () => { const r = await desk.senses.set({ ...v.consent, senses: draft }); const p = box.querySelector('.se-perm'); if (p) p.replaceWith(permLine(r.missing)); }), permLine(v.missing));
      const again = el('button', 'ghost sm', 'Show the start-up card'); again.onclick = () => showCard(true); box.append(again);
    };
    paint();
    return box;
  }

  return { showCard, settingsUi };
})();
