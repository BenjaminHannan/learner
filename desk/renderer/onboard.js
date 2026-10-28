'use strict';
// First-run setup, a full-pane sheet inside the main window (same family as Settings and Permissions; no extra window).
// Steps: 0 Meet your Glims -> 1 What do you want Glims for? -> 2 Set up recurring Glims -> 3 Permissions (Skip allowed).
// Keys: Enter = next, Esc = skip setup. Picks are saved as settings `uses` / `usesOther`; recurring Glims are created through
// the main process (helpers.add, the same path agent_start uses), so it is instant and needs no model.
window.Onboard = (() => {
  const desk = window.desk;
  const root = document.getElementById('onboard');
  const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x !== undefined) e.textContent = x; return e; };
  const svgIcon = (d) => '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';
  const ICONS = {
    email: svgIcon('<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M3.5 7.5l8.5 6 8.5-6"/>'),
    briefing: svgIcon('<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6"/>'),
    deals: svgIcon('<path d="M3.5 12.2V4.5a1 1 0 011-1h7.7a1 1 0 01.7.3l7.3 7.3a1 1 0 010 1.4l-7.4 7.4a1 1 0 01-1.4 0l-7.2-7.2a1 1 0 01-.7-.7z"/><circle cx="8.3" cy="8.3" r="1.4"/>'),
    school: svgIcon('<path d="M4 5.5A2.5 2.5 0 016.5 3H20v15H6.5A2.5 2.5 0 004 20.5z"/><path d="M4 20.5A2.5 2.5 0 006.5 23H20v-5M8.5 8h7M8.5 12h5"/>'),
    research: svgIcon('<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21M8 10.5h5M10.5 8v5"/>'),
    calendar: svgIcon('<rect x="3.5" y="5" width="17" height="15.5" rx="3"/><path d="M3.5 10h17M8 3v4M16 3v4M8 14h2M14 14h2M8 17h2"/>'),
    files: svgIcon('<path d="M3 7.5A2.5 2.5 0 015.5 5H10l2.2 2.5h6.3A2.5 2.5 0 0121 10v7.5a2.5 2.5 0 01-2.5 2.5h-13A2.5 2.5 0 013 17.5z"/>'),
    news: svgIcon('<path d="M5 20h12.5a2.5 2.5 0 002.5-2.5V4.5H8.5v13A2.5 2.5 0 015.5 20 2.5 2.5 0 013 17.5V9.5h5.5"/><path d="M12 8.5h4.5M12 12h4.5M12 15.5h4.5"/>')
  };
  const CHECK = svgIcon('<path d="M5 12.5l4.5 4.5L19 7.5"/>');
  const STEPS = ['Meet your Glims', 'What for', 'Recurring Glims', 'Permissions'];

  let mode = 'ask';
  let step = 0, picks = new Set(), other = '', info = null, perms = null;
  let wants = new Map();            // use id -> create this Glim (toggle)
  let made = new Map();             // use id -> name of the Glim that exists now (created here, or before)
  let createNote = '';
  let showPermsStep = true;
  let body, nextBtn, backBtn, dots, skipBtn;

  const needsPerms = () => !!(info && Platform.needsPermsStep(info.platform, info.e2e));
  const stepList = () => (showPermsStep ? [0, 1, 4, 2, 3] : [0, 1, 4, 2]); // 4 = how much Glim asks
  const lastStep = () => stepList()[stepList().length - 1];

  function build() {
    root.textContent = '';
    const head = el('div', 'ob-head');
    dots = el('div', 'ob-dots'); dots.setAttribute('role', 'img');
    skipBtn = el('button', 'ghost sm', 'Skip setup'); skipBtn.id = 'obSkip'; skipBtn.title = 'Skip setup (Esc)';
    skipBtn.onclick = () => finish(true);
    head.append(el('span', 'ob-brand', 'Set up Glims'), dots, skipBtn);
    body = el('div', 'ob-body'); body.id = 'obBody';
    const foot = el('div', 'ob-foot');
    backBtn = el('button', 'ghost', 'Back'); backBtn.id = 'obBack'; backBtn.onclick = () => go(-1);
    const hint = el('span', 'ob-hint', 'Enter for next · Esc to skip');
    nextBtn = el('button', 'amber-btn', 'Next'); nextBtn.id = 'obNext'; nextBtn.onclick = () => next();
    foot.append(backBtn, hint, nextBtn);
    root.append(head, body, foot);
  }

  function glimRow(mood, size, label) {
    const d = el('div', 'ob-glim');
    d.append(Mascot.el(mood, size), el('span', null, label));
    return d;
  }

  function paint() {
    const idx = stepList().indexOf(step);
    dots.textContent = ''; dots.setAttribute('aria-label', 'Step ' + (idx + 1) + ' of ' + stepList().length);
    stepList().forEach((s, i) => dots.append(el('i', i < idx ? 'done' : i === idx ? 'on' : '')));
    body.textContent = '';
    body.scrollTop = 0;
    if (perms) perms.hide();
    const page = el('div', 'ob-page'); page.dataset.step = String(step);
    body.append(page);
    backBtn.style.visibility = idx > 0 ? 'visible' : 'hidden';
    nextBtn.textContent = 'Next';
    if (step === 0) paintMeet(page);
    else if (step === 1) paintUses(page);
    else if (step === 2) paintSchedules(page);
    else if (step === 4) paintMode(page);
    else paintPerms(page);
    if (step === lastStep()) nextBtn.textContent = 'Finish';
    if (step === 0) nextBtn.textContent = 'Get started';
    if (step === 3) { skipBtn.textContent = 'Skip setup'; }
    root.dataset.step = String(step);
    setTimeout(() => { const f = step === 1 ? page.querySelector('.ob-tile') : nextBtn; if (f) f.focus({ preventScroll: true }); }, 30);
  }

  function paintMeet(page) {
    page.append(el('h1', null, 'Meet your Glims'));
    const lead = el('p', 'ob-lead');
    lead.textContent = 'Glim is your main assistant: you talk, it gets things done. It can also make more Glims. Each one has a single job, runs on its own on a schedule, and taps you on the shoulder when it finds something.';
    page.append(lead);
    const stage = el('div', 'ob-stage');
    const main = el('div', 'ob-main'); main.append(Mascot.el('idle', 112, { cls: 'follow' }), el('b', null, 'Glim'), el('span', null, 'Your main assistant'));
    const row = el('div', 'ob-kids');
    row.append(glimRow('working', 64, 'Watching your email'), glimRow('done', 64, 'Briefing ready'), glimRow('waiting', 64, 'Needs a quick OK'), glimRow('sleepy', 64, 'Resting until 8:00'));
    stage.append(main, row);
    page.append(stage);
    page.append(el('p', 'ob-fine', 'You stay in charge: Glims only watch and report. They ask before they send, buy or delete anything.'));
  }

  function paintMode(page) {
    page.append(el('h1', null, 'How much should Glim ask first?'));
    page.append(el('p', 'ob-lead', 'You can change this later in Settings only; it is not on the main screen, so it cannot flip by accident.'));
    const grid = el('div', 'ob-grid'); grid.setAttribute('role', 'radiogroup');
    const opts = [['ask', 'Ask first', 'Glim asks before it runs shell commands or clicks and types on your screen. Best to start with.'], ['hands-off', 'Hands-off', 'Glim just does it. Only a short danger list (delete, send, buy) still needs your OK.']];
    const tiles = [];
    for (const [id, title, text] of opts) {
      const b = el('button', 'ob-tile'); b.type = 'button'; b.setAttribute('role', 'radio');
      const txt = el('span', 'ob-txt'); txt.append(el('b', null, title), el('span', null, text));
      b.append(txt);
      tiles.push([id, b]);
      b.onclick = () => { mode = id; sync(); };
      grid.append(b);
    }
    const sync = () => tiles.forEach(([id, b]) => { b.classList.toggle('on', id === mode); b.setAttribute('aria-checked', String(id === mode)); });
    sync(); page.append(grid);
  }

  function paintUses(page) {
    page.append(el('h1', null, 'What do you want Glims for?'));
    page.append(el('p', 'ob-lead', 'Pick as many as you like. This only tunes the suggestions and the Glims we offer next; you can change it any time.'));
    const grid = el('div', 'ob-grid'); grid.setAttribute('role', 'group'); grid.setAttribute('aria-label', 'What you want Glims for');
    for (const u of Uses.USES) {
      const b = el('button', 'ob-tile'); b.type = 'button'; b.dataset.id = u.id; b.setAttribute('role', 'checkbox');
      const ico = el('span', 'ob-ico'); ico.innerHTML = ICONS[u.id] || '';
      const txt = el('span', 'ob-txt'); txt.append(el('b', null, u.title), el('span', null, u.example));
      const chk = el('span', 'ob-chk'); chk.innerHTML = CHECK;
      b.append(ico, txt, chk);
      const sync = () => { const on = picks.has(u.id); b.classList.toggle('on', on); b.setAttribute('aria-checked', String(on)); };
      const flip = () => { if (picks.has(u.id)) picks.delete(u.id); else picks.add(u.id); sync(); };
      b.onclick = flip;
      b.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); next(); } });
      sync(); grid.append(b);
    }
    page.append(grid);
    const f = el('label', 'ob-other');
    f.append(el('span', null, 'Something else…'));
    const inp = el('input'); inp.type = 'text'; inp.id = 'obOther'; inp.maxLength = 200; inp.spellcheck = true; inp.placeholder = 'e.g. keep track of my game releases';
    inp.value = other; inp.oninput = () => { other = inp.value; };
    f.append(inp); page.append(f);
  }

  const withTpl = () => Uses.IDS.filter((id) => picks.has(id) && Uses.templateFor(id));

  function paintSchedules(page) {
    const ids = withTpl();
    page.append(el('h1', null, ids.length ? 'Set up recurring Glims' : 'Nothing to schedule yet'));
    if (!ids.length) {
      page.append(el('p', 'ob-lead', picks.size ? 'Your picks are one-off jobs, so there is nothing to put on a timer. Just ask Glim in the chat any time.' : 'You did not pick anything, and that is fine. Ask Glim for something in the chat, and say "every morning" when you want it to repeat.'));
      const e = el('div', 'ob-empty'); e.append(Mascot.el('idle', 88)); page.append(e);
      return;
    }
    page.append(el('p', 'ob-lead', 'These can run on their own. Switch on the ones you want and Glim creates them right now, no waiting.'));
    const list = el('div', 'ob-list');
    for (const id of ids) {
      const t = Uses.templateFor(id);
      const have = made.get(id);
      const row = el('div', 'ob-row' + (have ? ' made' : '')); row.dataset.id = id;
      row.append(Mascot.el(have ? 'done' : 'idle', 40, { still: true }));
      const lab = el('div', 'ob-rl'); lab.append(el('b', null, t.name), el('span', null, t.what + ' · ' + t.label));
      row.append(lab);
      if (have) row.append(el('span', 'ob-made', 'Created'));
      else {
        const tg = el('button', 'toggle'); tg.type = 'button'; tg.setAttribute('role', 'switch'); tg.setAttribute('aria-label', 'Create the ' + t.name + ' Glim now');
        const sync = () => tg.setAttribute('aria-checked', String(wants.get(id) !== false));
        tg.onclick = () => { wants.set(id, wants.get(id) === false); sync(); updateNext(); };
        tg.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); next(); } });
        sync(); row.append(tg);
      }
      list.append(row);
    }
    page.append(list);
    const safe = el('p', 'ob-fine'); safe.textContent = 'Each Glim only watches and reports. It never sends, replies, buys or deletes without asking you first.';
    page.append(safe);
    if (createNote) page.append(el('p', 'ob-fine bad', createNote));
    if (picks.size > ids.length) page.append(el('p', 'ob-fine', 'Your other picks are one-off jobs: just ask Glim in the chat.'));
    updateNext();
  }
  function updateNext() {
    if (step !== 2) return;
    const n = withTpl().filter((id) => !made.has(id) && wants.get(id) !== false).length;
    nextBtn.textContent = n ? (n === 1 ? 'Create 1 Glim' : 'Create ' + n + ' Glims') : 'Continue';
  }

  function paintPerms(page) {
    page.append(el('h1', null, 'Let Glim use your Mac'));
    page.append(el('p', 'ob-lead', 'Only needed if you want Glim to click, type or look at your screen. Open the pane, drag the app tile into the list and switch it on. You can skip this and do it later in Settings.'));
    const host = el('div', 'ob-perms'); host.id = 'obPerms';
    page.append(host);
    if (!perms || perms.host !== host) { perms = window.createPerms(host, { embedded: true }); perms.host = host; }
    perms.show();
    desk.settings.set({ permsSeen: true });
  }

  async function createGlims() {
    const ids = withTpl().filter((id) => !made.has(id) && wants.get(id) !== false);
    createNote = '';
    if (!ids.length) return;
    const res = await desk.onboard.create(ids);
    const bad = [];
    for (const r of res || []) {
      if (r.ok) made.set(r.use, r.name);
      else if (/already exists/.test(r.error || '')) made.set(r.use, r.name);
      else bad.push(r.name + ': ' + r.error);
    }
    if (bad.length) createNote = 'Could not create ' + bad.join('; ');
    return bad.length === 0;
  }

  async function next() {
    if (!isOpen()) return;
    if (step === 1) await desk.settings.set({ uses: [...picks], usesOther: other });
    if (step === 4) await desk.settings.set({ mode });
    if (step === 2) { const ok = await createGlims(); if (ok === false) { paint(); return; } }
    if (step === lastStep()) return finish(false);
    go(1);
  }
  function go(d) {
    const l = stepList(); const i = Math.max(0, Math.min(l.length - 1, l.indexOf(step) + d));
    step = l[i]; paint();
  }

  async function finish(skipped) {
    if (!isOpen()) return;
    if (perms) perms.hide();
    root.hidden = true;
    const patch = { onboarded: true, uses: [...picks], usesOther: other };
    if (step === 3) patch.permsSeen = true;
    await desk.settings.set(patch);
    window.dispatchEvent(new CustomEvent('onboard-done', { detail: { skipped: !!skipped, created: [...made.values()] } }));
  }

  async function show() {
    info = await desk.info();
    const s = await desk.settings.get();
    picks = new Set(Uses.cleanUses(s.uses)); other = s.usesOther || '';
    wants = new Map(); made = new Map(); createNote = '';
    showPermsStep = needsPerms();
    // Glims that already exist (a re-run of setup): do not offer them twice
    try {
      const have = new Set((await desk.helpers.list()).filter((h) => h.status !== 'stopped').map((h) => h.name.toLowerCase()));
      for (const u of Uses.USES) if (u.tpl && have.has(u.tpl.name.toLowerCase())) made.set(u.id, u.tpl.name);
    } catch (e) { /* ignore */ }
    if (!root.firstChild) build();
    step = 0; mode = 'ask'; root.hidden = false; paint();
  }
  const isOpen = () => !root.hidden;

  document.addEventListener('keydown', (e) => {
    if (!isOpen()) return;
    if (e.key === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); finish(true); return; }
    if (e.key === 'Enter' && !e.isComposing && !e.shiftKey) {
      const t = e.target;
      // buttons keep their own Enter (Back, Skip, Open Settings...); tiles, switches and the text field go to the next step
      if (t && t.tagName === 'BUTTON' && !t.classList.contains('ob-tile') && t.getAttribute('role') !== 'switch') return;
      if (t && t.closest && t.closest('.p-tile')) return;
      e.preventDefault(); e.stopImmediatePropagation(); next();
    }
  }, true);

  return { show, isOpen, hide: () => { root.hidden = true; if (perms) perms.hide(); }, _state: () => ({ step, picks: [...picks], other, made: [...made.entries()] }) };
})();
