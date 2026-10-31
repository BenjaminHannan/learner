'use strict';
// Oct 30-31 on Ben's Mac the Motes spent the night on websites that did not work: the Week planner opened a dead summarizer site every
// 3 minutes for 40 minutes, and the Deadline check made up school addresses (schoolsite.example.com, schools.benedictine.edu) instead of
// finding Ben's real one. A Mote's browser_go now goes through this guard (Ben's own chat does not; he is watching it):
//  - a page that failed twice (or a host whose name did not resolve twice) in the last half hour is not opened again, for any Mote:
//    use another source. Failures from the Mac's own network (offline, a changed network) do not count;
//  - an address on a reserved test domain (example.com, .test, .invalid ...) is never a real site;
//  - the site has to come from somewhere real: a search result or a page it opened (written as a full https:// address), Ben's messages
//    or saved notes, a site Ben is signed in to in the built-in browser, or one of a few sites everyone has. Plain search words are
//    always fine (they become a search).

const FAIL_LIMIT = 2;
const FAIL_TTL_MS = 30 * 60000;
const COMMON = ['google.com', 'gmail.com', 'youtube.com', 'wikipedia.org', 'duckduckgo.com', 'bing.com', 'apple.com', 'icloud.com', 'microsoft.com', 'live.com', 'outlook.com', 'office.com', 'github.com'];
// errors that leave Chrome's error page instead of the site
const NET_FAIL = /ERR_(NAME_NOT_RESOLVED|NAME_RESOLUTION_FAILED|CONNECTION_[A-Z_]+|TIMED_OUT|ADDRESS_UNREACHABLE|ADDRESS_INVALID|INTERNET_DISCONNECTED|NETWORK_CHANGED|EMPTY_RESPONSE|TUNNEL_CONNECTION_FAILED|PROXY_CONNECTION_FAILED|CERT_[A-Z_]+|SSL_[A-Z_]+|BAD_SSL_CLIENT_AUTH_CERT|INVALID_URL|UNSAFE_PORT)|load timed out/;
const NO_HOST = /ERR_NAME_NOT_RESOLVED|ERR_NAME_RESOLUTION_FAILED/;
// the Mac's network, not the site
const LOCAL_FAIL = /ERR_(INTERNET_DISCONNECTED|NETWORK_CHANGED|PROXY_CONNECTION_FAILED|TUNNEL_CONNECTION_FAILED|NETWORK_IO_SUSPENDED)/;
// one base domain, many unrelated sites (each school has its own Schoology, each person their own github.io page): only the same host,
// or a host above or below it, counts as the same site
const SHARED_BASE = /(^|\.)(schoology\.com|instructure\.com|google\.com|github\.io|blogspot\.com|vercel\.app|netlify\.app|herokuapp\.com|wordpress\.com|sharepoint\.com|[a-z]{2}\.us)$/;

// the same rules as Browser.normalize: a full URL, a bare host (example.org/path) or plain words (a DuckDuckGo search)
function normalizeUrl(url) {
  url = String(url || '').trim();
  if (!url) return '';
  if (/^(https?|file|about):/i.test(url)) return url;
  if (/^(localhost|127\.|\d+\.\d+\.\d+\.\d+)/.test(url)) return 'http://' + url;
  if (/^[\w-]+(\.[\w-]+)+(\/|$|:)/.test(url) && !/\s/.test(url)) return 'https://' + url;
  return 'https://duckduckgo.com/?q=' + encodeURIComponent(url);
}
function hostOf(url) { try { return new URL(normalizeUrl(url)).hostname.toLowerCase().replace(/\.$/, ''); } catch (e) { return ''; } }
// a.b.example.co.uk -> example.co.uk, www.schoology.com -> schoology.com (subdomains of a site that came up are the same site)
function baseDomain(host) {
  host = String(host || '').toLowerCase().replace(/^\.+|\.+$/g, '');
  if (!host || /^[\d.]+$/.test(host) || host.includes(':')) return host;
  const p = host.split('.');
  if (p.length <= 2) return host;
  const tld = p[p.length - 1], sld = p[p.length - 2];
  return tld.length === 2 && /^(co|com|ac|edu|gov|org|net|ne|or|go|gob|mil|sch|nhs)$/.test(sld) ? p.slice(-3).join('.') : p.slice(-2).join('.');
}
function reserved(host) {
  return /(^|\.)example\.(com|net|org)$/.test(host) || /\.(example|invalid|test|localhost)$/.test(host) || /^(example|invalid|test)$/.test(host);
}
// every host written in a text: full URLs and bare hosts (dresden.schoology.com/home)
// (full: only full http(s):// addresses, for tool results: a search page that echoes the guessed words back must not make them "seen")
function hostsIn(text, full) {
  const out = new Set();
  const re = full ? /https?:\/\/((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,24})(?=[/:?#\s"'`)\]},;>|]|\.(?:\s|$)|$)/gi
    : /(?:https?:\/\/)?((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,24})(?=[/:?#\s"'`)\]},;>|]|\.(?:\s|$)|$)/gi;
  let m;
  while ((m = re.exec(String(text || '')))) out.add(m[1].toLowerCase().replace(/^www\./, ''));
  return out;
}
function textOf(content) {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) return content.map((p) => (p && typeof p.text === 'string' ? p.text : '')).join('\n');
  return '';
}
// a tool result that only echoes an address that did not work (a refused or failed open, Chrome's error page, an empty read of it)
const FAILED_ECHO = /^\s*Error: (could not open|not opened)|DNS_PROBE|This site can.t be reached|chrome-error:|\(no readable text\)/;
// the hosts the thread has actually seen: everything but the model's own words (its text and tool-call arguments could be guesses)
// and the results that only repeat a guess back
function seenHosts(thread) {
  const out = new Set();
  for (const m of (thread && thread.messages) || []) {
    if (!m || m.role === 'assistant') continue;
    const t = textOf(m.content);
    if (m.role === 'tool' && FAILED_ECHO.test(t)) continue;
    for (const h of hostsIn(t, m.role === 'tool')) out.add(h);
  }
  return out;
}
// is `host` the same site as `known`? the same host or one above/below it; or the same base domain, unless that base is shared by
// unrelated sites (SHARED_BASE)
function sameSite(host, known) {
  host = String(host || '').replace(/^www\./, ''); known = String(known || '').replace(/^\.+/, '').replace(/^www\./, '');
  if (!host || !known) return false;
  if (host === known || host.endsWith('.' + known) || known.endsWith('.' + host)) return true;
  const b = baseDomain(host);
  return b === baseDomain(known) && !SHARED_BASE.test(b) && b.includes('.');
}
function urlKey(url) {
  try { const u = new URL(normalizeUrl(url)); return (u.hostname.toLowerCase() + u.pathname.replace(/\/+$/, '') + u.search).toLowerCase(); } catch (e) { return String(url || '').toLowerCase(); }
}

class UrlGuard {
  constructor(o) { this.o = { now: () => Date.now(), ...(o || {}) }; this.fails = new Map(); }
  clear() { this.fails.clear(); }   // the Mac woke up or came back online: what failed before may work now
  _count(key) {
    const f = this.fails.get(key);
    if (!f) return null;
    if (this.o.now() - f.at > FAIL_TTL_MS) { this.fails.delete(key); return null; }
    return f;
  }
  // -> null (go ahead) or the error text the model gets instead of the page. strict: a Mote. extraHosts: sites Ben is signed in to.
  check(url, { strict, thread, extraHosts } = {}) {
    const u = normalizeUrl(url), host = hostOf(url);
    if (!strict || !u || !host || !/^https?:/i.test(u)) return null;
    if (reserved(host)) return 'Error: not opened. ' + host + ' is a made-up test address, not a real site. Never guess web addresses: use web_search to find the real page.';
    for (const f of [this._count('u:' + urlKey(url)), this._count('h:' + host)]) {
      if (f && f.n >= FAIL_LIMIT) return 'Error: not opened. ' + (f.host ? host : u) + ' already failed ' + f.n + ' times in the last half hour (' + f.why + '). Do not try it again: use a different source, or report that it is down.';
    }
    const base = baseDomain(host);
    if (base === 'duckduckgo.com' || COMMON.includes(base)) return null;
    for (const h of seenHosts(thread)) if (sameSite(host, h)) return null;
    for (const h of extraHosts || []) if (sameSite(host, h)) return null;
    return 'Error: not opened. ' + host + ' did not come from a search result, a page you opened, Ben\'s messages or saved notes, or a site he is signed in to. Never guess web addresses: use web_search to find the real site (or browser_go with plain search words). If you cannot find it, say so in your report.';
  }
  // after browser_go: a failed load counts against the page (and against the host when its name did not resolve)
  record(url, result) {
    const text = typeof result === 'string' ? result : (result && result.text) || '';
    if (!(result && result.error) && !/^Error:/.test(text)) return;
    if (LOCAL_FAIL.test(text) || /^Error: not opened/.test(text)) return;
    const why = (NET_FAIL.exec(text) || [String(text).replace(/^Error:\s*/, '').slice(0, 60)])[0];
    const bump = (key, isHost) => { const f = this._count(key) || { n: 0, host: isHost }; f.n++; f.at = this.o.now(); f.why = why; this.fails.set(key, f); };
    bump('u:' + urlKey(url), false);
    if (NO_HOST.test(text)) bump('h:' + hostOf(url), true);
  }
}

module.exports = { UrlGuard, normalizeUrl, hostOf, baseDomain, hostsIn, seenHosts, sameSite, reserved, NET_FAIL, FAIL_LIMIT, COMMON };
