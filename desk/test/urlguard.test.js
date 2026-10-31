'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { UrlGuard, baseDomain, hostsIn, seenHosts, sameSite, normalizeUrl, NET_FAIL } = require('../src/urlguard');
const { webSearch } = require('../src/tools/web');

// Oct 30-31: the Motes reopened a dead site every 3 minutes for 40 minutes and made up school addresses all night
const thread = (...messages) => ({ messages });
const M = { strict: true, thread: { messages: [{ role: 'tool', content: '1. x\n   https://www.summarizeitforme.com/\n2. y\n   https://ok.org/\n3. z\n   https://school.benedictine.edu/' }] } };

test('url guard: a Mote never opens a test domain; Ben\'s own chat is not held to any of this', () => {
  const g = new UrlGuard();
  for (const u of ['https://www.schoolsite.example.com/assignments', 'calendar.example.com', 'http://my.school.test/x', 'https://a.invalid'])
    assert.match(g.check(u, { strict: true, thread: thread() }), /made-up test address/, u);
  assert.match(g.check('https://example.community/x', { strict: true, thread: thread() }), /did not come from/, 'only the reserved names are "made up"');
  assert.strictEqual(g.check('cats near me', { strict: true, thread: thread() }), null, 'plain words are a search');
  assert.strictEqual(g.check('http://myapp.test/', {}), null, 'Ben can open his own test site');
});

test('url guard: a page that failed twice is not opened again for half an hour; a host that does not resolve counts for all its pages', () => {
  let now = 0;
  const g = new UrlGuard({ now: () => now });
  const dead = { text: 'Error: could not open https://www.summarizeitforme.com/ (ERR_CONNECTION_TIMED_OUT (-118) loading ...)', error: true };
  assert.strictEqual(g.check('https://www.summarizeitforme.com/', M), null);
  g.record('https://www.summarizeitforme.com/', dead);
  assert.strictEqual(g.check('https://www.summarizeitforme.com', M), null, 'one more try is fine');
  g.record('https://www.summarizeitforme.com', dead);
  assert.match(g.check('www.summarizeitforme.com/', M), /already failed 2 times[\s\S]*ERR_CONNECTION_TIMED_OUT[\s\S]*Do not try it again/);
  g.record('https://ok.org/', { text: 'URL: https://ok.org/ | Title: OK' });
  assert.strictEqual(g.check('https://ok.org/', M), null, 'a page that opened does not count');
  g.record('https://ok.org/', { text: 'Error: could not open https://ok.org/ (ERR_INTERNET_DISCONNECTED (-106))', error: true });
  g.record('https://ok.org/', { text: 'Error: could not open https://ok.org/ (ERR_NETWORK_CHANGED (-21))', error: true });
  assert.strictEqual(g.check('https://ok.org/', M), null, 'the Mac being offline is not the site\'s fault');
  now += 31 * 60000;
  assert.strictEqual(g.check('https://www.summarizeitforme.com/', M), null, 'after half an hour it may be back');
  const nx = { text: 'Error: could not open https://school.benedictine.edu/a (ERR_NAME_NOT_RESOLVED (-105) loading ...)', error: true };
  g.record('https://school.benedictine.edu/a', nx); g.record('https://school.benedictine.edu/b', nx);
  assert.match(g.check('https://school.benedictine.edu/a', M), /school\.benedictine\.edu already failed 2 times/, 'the host count wins over the page\'s own count');
  assert.match(g.check('https://school.benedictine.edu/calendar', M), /already failed/);
  g.clear();
  assert.strictEqual(g.check('https://school.benedictine.edu/a', M), null, 'cleared when the Mac wakes');
});

test('url guard: a Mote may only open sites that came from somewhere real', () => {
  const g = new UrlGuard();
  const t = thread(
    { role: 'user', content: '[Saved notes] Ben\'s school uses Schoology: https://dresden.schoology.com/home\nTask: find what is due' },
    { role: 'assistant', content: 'I will open schools.benedictine.edu', tool_calls: [{ id: 'a', type: 'function', function: { name: 'browser_go', arguments: '{"url":"https://made-up-site.com"}' } }] },
    { role: 'tool', tool_call_id: 'a', content: 'Error: could not open https://made-up-site.com (ERR_NAME_NOT_RESOLVED)' },
    { role: 'tool', tool_call_id: 'b', content: 'Page 1 of 1 (https://other-guess.org/assignments) (no readable text)' },
    { role: 'tool', tool_call_id: 'c', content: '1. Weather\n   https://wttr.in/Cambridge\n   Forecast' },
    { role: 'tool', tool_call_id: 'd', content: 'URL: https://duckduckgo.com/?q=guessed-school.org+homework | Title: guessed-school.org homework at DuckDuckGo' }
  );
  const strict = { strict: true, thread: t, extraHosts: ['accounts.instructure.com', 'mail.yahoo.com'] };
  assert.strictEqual(g.check('https://dresden.schoology.com/user/123', strict), null, 'from Ben\'s saved notes');
  assert.match(g.check('https://benedictine.schoology.com/', strict), /did not come from/, 'another school\'s Schoology is not his');
  assert.match(g.check('https://guessed-school.org/', strict), /did not come from/, 'a search page echoing the guessed words back does not count');
  assert.strictEqual(g.check('wttr.in/Boston', strict), null, 'from a search result');
  assert.strictEqual(g.check('https://accounts.instructure.com/courses', strict), null, 'a site he is signed in to');
  assert.strictEqual(g.check('https://login.yahoo.com/', strict), null, 'the same site as one he is signed in to');
  assert.strictEqual(g.check('https://mail.google.com/mail/u/0/', strict), null, 'a site everyone has');
  assert.match(g.check('https://schools.benedictine.edu/assignments', strict), /did not come from a search result[\s\S]*Never guess web addresses: use web_search/, 'its own words do not count');
  assert.match(g.check('https://made-up-site.com', strict), /did not come from/, 'an error that repeats the guess does not count');
  assert.match(g.check('https://other-guess.org/x', strict), /did not come from/, 'nor an empty read of an error page');
  assert.strictEqual(g.check('https://schools.benedictine.edu/', { thread: t }), null, 'Ben\'s own chat is not held to this');
  assert.strictEqual(new UrlGuard().check('https://www.wttr.in/x', strict), null, 'www. or not');
});

test('url guard: helpers', () => {
  assert.strictEqual(baseDomain('a.b.dresden.schoology.com'), 'schoology.com');
  assert.strictEqual(baseDomain('www.bbc.co.uk'), 'bbc.co.uk');
  assert.strictEqual(baseDomain('127.0.0.1'), '127.0.0.1');
  assert.deepStrictEqual([...hostsIn('see https://www.x.org/a?b, or y.co.uk/p. Also z.com.')], ['x.org', 'y.co.uk', 'z.com']);
  assert.deepStrictEqual([...hostsIn('see https://www.x.org/a?b, or y.co.uk/p.', true)], ['x.org'], 'tool results: full addresses only');
  assert.ok(seenHosts(thread({ role: 'system', content: 'go to q.net' })).has('q.net'));
  assert.ok(sameSite('news.bbc.co.uk', 'www.bbc.co.uk') && sameSite('x.org', 'a.x.org') && !sameSite('a.k12.tn.us', 'b.k12.tn.us') && !sameSite('evil.github.io', 'ben.github.io'));
  assert.strictEqual(normalizeUrl('dresden.schoology.com/home'), 'https://dresden.schoology.com/home');
  assert.match(normalizeUrl('what is due'), /^https:\/\/duckduckgo\.com\/\?q=/);
  assert.ok(NET_FAIL.test('ERR_NAME_NOT_RESOLVED (-105)') && NET_FAIL.test('ERR_CONNECTION_TIMED_OUT') && !NET_FAIL.test('ERR_ABORTED (-3)'));
});

test('web search gives up after its time limit instead of holding the run', async () => {
  const hang = (u, o) => new Promise((resolve, reject) => o.signal.addEventListener('abort', () => reject(new Error('aborted'))));
  const t0 = Date.now();
  assert.match(await webSearch('x', { fetch: hang, timeoutMs: 50 }), /Search failed: no answer within/);
  assert.ok(Date.now() - t0 < 2000);
  const stop = new AbortController(); setTimeout(() => stop.abort(), 20);
  await assert.rejects(webSearch('x', { fetch: hang, timeoutMs: 5000, signal: stop.signal }), 'stopping the run still stops it');
});

test('url guard: a Mote may open a few unshown pages on a real site, then has to use links or search', () => {
  // Oct 31 live test: after one real result it made up 25 ?year= variants of the same Google Sites page
  const g = new UrlGuard();
  const t = { id: 'tA', messages: [{ role: 'tool', content: '1. BSMS\n   https://sites.google.com/bennps.org/bsms-practice/home\n   school' }] };
  const S = { strict: true, thread: t };
  assert.strictEqual(g.check('https://sites.google.com/bennps.org/bsms-practice/home', S), null, 'the page that was shown');
  for (let i = 1; i <= 5; i++) assert.strictEqual(g.check('https://sites.google.com/bennps.org/bsms-practice/home/agenda?year=2026-0' + i, S), null, 'guess ' + i);
  assert.match(g.check('https://sites.google.com/bennps.org/bsms-practice/home/agenda?year=2026-06', S), /already made up 5 page addresses on sites\.google\.com[\s\S]*browser_click/);
  assert.strictEqual(g.check('https://sites.google.com/bennps.org/bsms-practice/home', S), null, 'shown pages stay open');
  assert.strictEqual(g.check('https://sites.google.com/', S), null, 'and the front page');
  assert.strictEqual(g.check('https://sites.google.com/x/y', { strict: true, thread: { id: 'tB', messages: [] } }), null, 'another task has its own count');
});
