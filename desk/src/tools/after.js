'use strict';
// "After" observations: a compact note appended to the result of every state-changing browser/screen action,
// so the (weak, text-only) model sees what the action changed without another call. Pure functions: no Electron here.

const AFTER_MAX = 600;
const MASK = '••••';

const clean = (s, n) => { s = String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n - 1) + '…' : s; };
const noId = (l) => String(l).replace(/^\[\d+\]\s*/, '');
const hostPath = (u) => { try { const x = new URL(u); return x.host.replace(/^www\./, '') + (x.pathname === '/' ? '' : x.pathname) + (x.search ? '?…' : ''); } catch (e) { return clean(u, 50); } };

// Browser snapshot lines already mask passwords; this also masks the value="..." of any line that looks sensitive.
function maskLine(l) {
  l = String(l);
  if (/input\((password|[^)]*payment)/.test(l)) return l.replace(/value="[^"]*"/, 'value="' + MASK + '"');
  return l;
}

function snapDiff(prev, cur) {
  const d = { urlChanged: false, titleChanged: false, textChanged: false, added: [], removed: [] };
  if (!prev || !cur) return Object.assign(d, { noBaseline: true });
  d.urlChanged = prev.url !== cur.url;
  d.titleChanged = prev.title !== cur.title;
  d.textChanged = (prev.text || '') !== (cur.text || '');
  const a = new Set((prev.lines || []).map(noId)), b = new Set((cur.lines || []).map(noId));
  d.added = [...b].filter((x) => !a.has(x));
  d.removed = [...a].filter((x) => !b.has(x));
  d.changed = d.urlChanged || d.titleChanged || d.textChanged || d.added.length > 0 || d.removed.length > 0;
  return d;
}

const VERB = { click: 'click', type: 'typing', navigate: 'navigation', back: 'going back', key: 'key press', open: 'opening' };
const clampNote = (s) => (s.length > AFTER_MAX ? s.slice(0, AFTER_MAX - 1) + '…' : s);

// prev/cur: {url,title,lines,text,focus?,alerts?[]}. kind: click|type|navigate|back
function browserAfter(prev, cur, kind) {
  const d = snapDiff(prev, cur);
  const parts = [];
  parts.push(d.urlChanged ? 'URL now ' + hostPath(cur.url) : 'URL unchanged');
  if (d.titleChanged || d.urlChanged) parts.push('title "' + clean(cur.title, 50) + '"');
  if (d.noBaseline) parts.push('no earlier snapshot to compare');
  else if (d.changed) {
    const bits = [];
    if (d.added.length || d.removed.length) bits.push('+' + d.added.length + '/-' + d.removed.length + ' elements');
    if (d.textChanged && !d.added.length && !d.removed.length) bits.push('page text changed');
    parts.push('Changed: ' + bits.join(', '));
    if (d.added.length) parts.push('new: ' + d.added.slice(0, 3).map((x) => clean(maskLine(x), 45)).join('; '));
    if (d.removed.length && !d.urlChanged) parts.push('gone: ' + d.removed.slice(0, 2).map((x) => clean(maskLine(x), 35)).join('; '));
  } else if (kind === 'click' || kind === 'type') {
    parts.unshift('Nothing changed on the page after this ' + (kind === 'type' ? 'typing' : 'click') + ' (same URL, elements and text). It had no effect: try a different element or approach, do not repeat it');
  }
  if (cur && cur.focus) parts.push('Focus: ' + clean(maskLine(cur.focus), 80));
  if (cur && cur.alerts && cur.alerts.length) parts.push('Alert on page: ' + cur.alerts.slice(0, 2).map((x) => '"' + clean(x, 80) + '"').join(' | '));
  return clampNote('After ' + (VERB[kind] || kind) + ': ' + parts.join('. ') + '.');
}

// ---- screen (deskhelper look json: {app, windows:[{title}], elements:[{id,role,title,value}]}) ----
const isSecureRole = (r) => /secure/i.test(String(r || ''));
const elKey = (e) => (e.role || '') + '|' + (e.title || '') ;
const elDesc = (e) => (e.role || 'element').replace(/^AX/, '') + (e.title ? ' "' + clean(e.title, 30) + '"' : '') + (e.value !== undefined && e.value !== '' ? ' value="' + (isSecureRole(e.role) ? MASK : clean(e.value, 40)) + '"' : '');

function lookSummary(j) {
  const els = (j && j.elements) || [];
  return { app: j && j.app || '', window: j && j.windows && j.windows[0] ? j.windows[0].title || '' : '', n: els.length, els: els.map((e) => ({ role: e.role || '', title: e.title || '', value: e.value == null ? '' : String(e.value) })) };
}

function screenAfter(prev, curJson, kind, extra) {
  const cur = lookSummary(curJson);
  const parts = [];
  parts.push('front app ' + (cur.app || '?') + (cur.window ? ', window "' + clean(cur.window, 40) + '"' : ''));
  let changed = true;
  if (!prev) parts.push('no earlier look to compare');
  else {
    const pa = new Map(prev.els.map((e) => [elKey(e), e]));
    const ca = new Map(cur.els.map((e) => [elKey(e), e]));
    const added = cur.els.filter((e) => !pa.has(elKey(e)));
    const removed = prev.els.filter((e) => !ca.has(elKey(e)));
    const valued = cur.els.filter((e) => pa.has(elKey(e)) && pa.get(elKey(e)).value !== e.value);
    const appChanged = prev.app !== cur.app, winChanged = prev.window !== cur.window;
    changed = appChanged || winChanged || added.length || removed.length || valued.length;
    if (appChanged) parts.push('app changed from ' + (prev.app || '?'));
    else if (winChanged) parts.push('window title changed');
    if (added.length || removed.length) parts.push('Changed: +' + added.length + '/-' + removed.length + ' elements');
    if (added.length) parts.push('new: ' + added.slice(0, 3).map(elDesc).join('; '));
    if (valued.length) parts.push('values changed: ' + valued.slice(0, 2).map(elDesc).join('; '));
    if (!changed && (kind === 'click' || kind === 'type' || kind === 'key')) parts.unshift('Nothing changed on the screen after this ' + (kind === 'type' ? 'typing' : kind === 'key' ? 'key press' : 'click') + ' (same app, window, elements and values). It had no effect: try a different element or approach, do not repeat it');
  }
  if (extra) parts.push(extra);
  return clampNote('After ' + (VERB[kind] || kind) + ': ' + parts.join('. ') + '.');
}

module.exports = { AFTER_MAX, MASK, snapDiff, browserAfter, screenAfter, lookSummary, maskLine };
