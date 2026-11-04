'use strict';
// Preload for Glim's own browser views (track LOGIN1). It runs in an isolated world: page scripts cannot see or call it.
// Its only job: when Ben submits a sign-in form here, hand the username + password to the app (main process), which offers a
// "Save this login?" card. The model never sees these values. A username-only step (two-step pages) sends just the username.
const { ipcRenderer } = require('electron');

const vis = (el) => { try { const r = el.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return false; const cs = getComputedStyle(el); return cs.visibility !== 'hidden' && cs.display !== 'none'; } catch (e) { return false; } };
const typ = (i) => String(i.getAttribute('type') || 'text').toLowerCase();
const words = (i) => ((i.name || '') + ' ' + (i.id || '') + ' ' + (i.placeholder || '') + ' ' + (i.getAttribute('aria-label') || '') + ' ' + (i.getAttribute('autocomplete') || '')).toLowerCase();
const isCode = (i) => /one-time-code|\b(otp|totp|2fa|mfa|verification|passcode|code|pin)\b/.test(words(i).replace(/[_-]/g, ' '));
const userLike = (i) => /^(text|email|tel)$/.test(typ(i)) && !isCode(i) && (typ(i) === 'email' || /username|email|user|e-?mail|login|account|identifier|mail/.test(words(i)));
let last = '';

function grab(from) {
  try {
    const root = (from && from.closest && from.closest('form')) || document;
    const inputs = Array.from(root.querySelectorAll('input')).filter(vis);
    const pw = inputs.find((i) => typ(i) === 'password' && i.value && !/new-password/.test(String(i.getAttribute('autocomplete') || '')) && !isCode(i));
    let user = '';
    if (pw) {
      const c = inputs.filter((i) => userLike(i) && i.value && (i.compareDocumentPosition(pw) & Node.DOCUMENT_POSITION_FOLLOWING));
      user = c.length ? c[c.length - 1].value : '';
    } else {
      const u = inputs.find((i) => userLike(i) && i.value);
      if (!u || inputs.some((i) => typ(i) === 'password')) return;
      user = u.value;
    }
    const sig = user + '\n' + (pw ? pw.value : '');
    if (sig === last) return;
    last = sig;
    setTimeout(() => { if (last === sig) last = ''; }, 3000);
    ipcRenderer.send('pm-login:submit', { user: String(user).slice(0, 256), password: pw ? String(pw.value).slice(0, 1024) : '' });
  } catch (e) { /* never break the page */ }
}

window.addEventListener('submit', (e) => grab(e.target), true);
window.addEventListener('click', (e) => { const b = e.target && e.target.closest && e.target.closest('button,input[type=submit],input[type=button],[role=button]'); if (b) grab(b); }, true);
window.addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.target && e.target.tagName === 'INPUT') grab(e.target); }, true);
