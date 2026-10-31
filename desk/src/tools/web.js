'use strict';
const SEARCH_TIMEOUT_MS = 15000;

function decode(s) {
  return s.replace(/<[^>]+>/g, '')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
    .replace(/&#x27;|&#39;/g, "'").replace(/&nbsp;/g, ' ')
    .replace(/&#(\d+);/g, (m, n) => String.fromCharCode(+n)).replace(/\s+/g, ' ').trim();
}

function realUrl(href) {
  href = href.replace(/&amp;/g, '&');
  if (href.startsWith('//')) href = 'https:' + href;
  try {
    const u = new URL(href, 'https://duckduckgo.com');
    const t = u.searchParams.get('uddg');
    return t ? decodeURIComponent(t) : u.href;
  } catch (e) { return href; }
}

// Parse DuckDuckGo's HTML results page.
function parseDDG(html, max) {
  const out = [];
  const re = /<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>([\s\S]*?)(?=<a[^>]*class="[^"]*result__a|$)/g;
  let m;
  while ((m = re.exec(html)) && out.length < (max || 8)) {
    const sn = /class="[^"]*result__snippet[^"]*"[^>]*>([\s\S]*?)<\/(?:a|td|div)>/.exec(m[3]);
    out.push({ title: decode(m[2]), url: realUrl(m[1]), snippet: sn ? decode(sn[1]) : '' });
  }
  return out;
}

async function webSearch(query, opts) {
  opts = opts || {};
  const base = opts.baseUrl || 'https://html.duckduckgo.com/html/?q=';
  const f = opts.fetch || fetch;
  // a search that hangs must not hold a run: it gives up after SEARCH_TIMEOUT_MS (or when the run is stopped)
  const ctl = new AbortController(), stop = () => ctl.abort();
  const t = setTimeout(stop, opts.timeoutMs || SEARCH_TIMEOUT_MS);
  if (opts.signal) { if (opts.signal.aborted) ctl.abort(); else opts.signal.addEventListener('abort', stop, { once: true }); }
  let html;
  try {
    const res = await f(base + encodeURIComponent(query), {
      headers: { 'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15', accept: 'text/html' },
      signal: ctl.signal
    });
    if (!res.ok) return 'Search failed: HTTP ' + res.status;
    html = await res.text();
  } catch (e) {
    if (opts.signal && opts.signal.aborted) throw e;
    if (ctl.signal.aborted) return 'Search failed: no answer within ' + Math.round((opts.timeoutMs || SEARCH_TIMEOUT_MS) / 1000) + ' s. Try again once, or use another source.';
    throw e;
  } finally { clearTimeout(t); if (opts.signal) opts.signal.removeEventListener('abort', stop); }
  const rs = parseDDG(html, 8);
  if (!rs.length) return 'No results found.';
  return rs.map((r, i) => (i + 1) + '. ' + r.title + '\n   ' + r.url + (r.snippet ? '\n   ' + r.snippet : '')).join('\n');
}

module.exports = { webSearch, parseDDG, SEARCH_TIMEOUT_MS };
