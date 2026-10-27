'use strict';
// Live cards (browser / screen) are thread items too, so a reopened thread shows them. One card per kind and browser
// per activity group (everything since Ben's last message): later steps update that card instead of adding more.
const { randomBytes } = require('crypto');

function currentCard(thread, t, key) {
  const items = thread.items || [];
  for (let i = items.length - 1; i >= 0; i--) {
    const it = items[i];
    if (it.t === 'user' || it.t === 'notice') return null;
    if (it.t === t && (key === undefined || it.key === key)) return it;
  }
  return null;
}

function ensureCard(thread, t, key, init) {
  thread.items = thread.items || [];
  let c = currentCard(thread, t, key);
  if (!c) {
    c = { t, id: t[0] + 'c_' + randomBytes(4).toString('hex'), key: key || '', ...(init || {}) };
    thread.items.push(c);
  }
  return c;
}

module.exports = { currentCard, ensureCard };
