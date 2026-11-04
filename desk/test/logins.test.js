'use strict';
// Track LOGIN1: Glim signs in with saved logins; the password never passes through the model.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const L = require('../src/logins');
const { SafetyLevels, classify, shellCategory, fromBenText, CATEGORIES } = require('../src/safety-levels');
const { SYSTEM_PROMPT, TOOL_DEFS } = require('../src/prompt');
const { Agent } = require('../src/agent');
const { WORDS } = require('../renderer/toolwords');

const PW = 'Tr0ub4dor&3-zz';

test('origin matching: exact https origin only; look-alikes, subdomains, http and userinfo tricks get nothing', () => {
  assert.strictEqual(L.originOf('https://Dresden.Schoology.com/login?x=1'), 'https://dresden.schoology.com');
  assert.strictEqual(L.originOf('http://dresden.schoology.com/login'), null);
  assert.strictEqual(L.originOf('file:///tmp/login.html'), null);
  assert.strictEqual(L.originOf('https://localhost:8443/a'), 'https://localhost:8443');
  const saved = 'https://dresden.schoology.com';
  assert.ok(L.sameOrigin(saved, 'https://dresden.schoology.com/home'));
  for (const bad of ['https://dresden.schoology.com.evil.io/login', 'https://evil.io/dresden.schoology.com', 'https://dresden-schoology.com/login',
    'https://dresden.schooIogy.com/login', 'https://app.dresden.schoology.com/', 'https://schoology.com/', 'http://dresden.schoology.com/',
    'https://dresden.schoology.com@evil.io/', 'https://dresden.schoology.com:8443/', 'https://xn--dresden-schoology-xyz.com/']) assert.ok(!L.sameOrigin(saved, bad), bad);
  assert.strictEqual(L.originFromInput('dresden.schoology.com'), 'https://dresden.schoology.com');
  assert.strictEqual(L.originFromInput('https://dresden.schoology.com/login'), 'https://dresden.schoology.com');
  assert.strictEqual(L.originFromInput('http://dresden.schoology.com'), null);
});

test('store: saves into the box, fills only the exact origin, the index file never holds the password', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'login1-'));
  const box = new L.MemoryBox();
  const s = new L.LoginStore({ dir, box });
  assert.strictEqual((await s.save('http://x.com', 'ben', PW)).ok, false);
  const r = await s.save('https://dresden.schoology.com/login', 'ben@x.org', PW);
  assert.ok(r.ok); assert.strictEqual(r.host, 'dresden.schoology.com');
  assert.ok(!fs.readFileSync(path.join(dir, 'logins.json'), 'utf8').includes(PW));
  assert.deepStrictEqual(new L.LoginStore({ dir, box }).list().map((x) => [x.host, x.user]), [['dresden.schoology.com', 'ben@x.org']]);
  assert.ok(!JSON.stringify(s.list()).includes(PW));
  assert.strictEqual((await s.forPage('https://dresden.schoology.com/x')).password, PW);
  assert.strictEqual(await s.forPage('https://dresden.schoology.com.evil.io/x'), null);
  assert.strictEqual(await s.forPage('http://dresden.schoology.com/x'), null);
  // a new username for the same site replaces the old item (one per origin)
  await s.save('https://dresden.schoology.com', 'other', 'pw-two-xx');
  assert.strictEqual(s.list().length, 1); assert.strictEqual(await box.get('https://dresden.schoology.com', 'ben@x.org'), null);
  assert.ok((await s.remove('https://dresden.schoology.com')).ok); assert.deepStrictEqual(s.list(), []);
  fs.rmSync(dir, { recursive: true, force: true });
});

test('Mac keychain backend: the password goes on stdin, never in argv; reads and deletes use argv arrays with the Premonition label', async () => {
  const calls = []; const items = new Map();
  const run = async (bin, args, input) => {
    calls.push({ bin, args, input });
    if (args[0] === '-i') { const m = /-a "((?:[^"\\]|\\.)*)" -s "([^"]+)".* -w "(pm1:[A-Za-z0-9+/=]+)"/.exec(input); items.set(m[2] + ' ' + m[1].replace(/\\(.)/g, '$1'), m[3]); return { code: 0, out: '' }; }
    if (args[0] === 'find-internet-password') { const k = args[args.indexOf('-s') + 1] + ' ' + args[args.indexOf('-a') + 1]; return items.has(k) ? { code: 0, out: items.get(k) + '\n' } : { code: 44, out: '' }; }
    return { code: 0, out: '' };
  };
  const kc = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'login1k-')), 'test.keychain-db'); fs.writeFileSync(kc, '');   // a fake file: the fake run never opens it
  assert.strictEqual(await new L.MacKeychain({ run, keychain: kc + '-missing' }).set('https://a.example', 'u', PW), false);   // a missing keychain file never falls back to Ben's
  assert.strictEqual(calls.length, 0);
  const k = new L.MacKeychain({ run, keychain: kc });
  assert.ok(await k.set('https://dresden.schoology.com', 'b"en\\x', PW));
  assert.strictEqual(await k.get('https://dresden.schoology.com', 'b"en\\x'), PW);
  for (const c of calls) { assert.strictEqual(c.bin, '/usr/bin/security'); assert.ok(Array.isArray(c.args)); assert.ok(!c.args.some((a) => a.includes(PW)), 'argv: ' + c.args.join(' ')); }
  assert.ok(!calls[0].input.includes(PW));   // even stdin carries it encoded
  assert.ok(calls[1].args.includes('Premonition') && calls[1].args.includes(kc));
  await k.del('https://dresden.schoology.com', 'b"en\\x');
  assert.strictEqual(calls[calls.length - 1].args[0], 'delete-internet-password');
});

test('redaction: any line holding a saved password is dropped (tool results, logs, the sleep diary record, the day log)', () => {
  L.addSecret(PW);
  assert.strictEqual(L.scrub('a\nyour pw is ' + PW + ' ok\nb'), 'a\n' + L.HIDDEN + '\nb');
  assert.strictEqual(L.scrub('nothing here'), 'nothing here');
  assert.strictEqual(L.scrubRecord(JSON.stringify({ messages: [{ content: 'x ' + PW }] })), null);
  L.addSecret('abc');   // too short to scan for: would hide ordinary words
  assert.strictEqual(L.scrub('abc def'), 'abc def');
  const { AlwaysOnState: State } = require('../src/senses');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'login1s-'));
  const st = new State(dir);
  assert.strictEqual(st.add('chats', 'Ben wrote: my password is ' + PW), null);
  assert.ok(st.add('chats', 'Ben wrote: hello there'));
  fs.rmSync(dir, { recursive: true, force: true });
});

test('the model-visible result never holds the password: browser_sign_in texts + the tool runner scrubs any slip', async () => {
  L.addSecret(PW);
  for (const t of [L.say.signedIn('ben', 'x.com'), L.say.noLogin('x.com'), L.say.code('x.com'), L.say.failed('ben', 'x.com', 'Wrong password'), L.say.notHttps(), L.say.noForm('x.com')]) assert.ok(!t.includes(PW));
  assert.match(L.say.signedIn('ben@x.org', 'dresden.schoology.com'), /^Signed in as ben@x\.org on dresden\.schoology\.com/);
  assert.match(L.say.noLogin('dresden.schoology.com'), /No saved login for dresden\.schoology\.com: ask Ben to sign in once in Glim's browser/);
  const evs = [];
  const a = new Agent({ getSettings: () => ({ mode: 'hands-off' }), tools: { browser_sign_in: async () => ({ text: 'Signed in as ben on x.com.\n[1] input(password) "Password" value="' + PW + '"', summary: 'Signed in on x.com ' + PW }) }, emit: (e) => evs.push(e), approve: async () => 'yes', askUser: async () => '', safety: new SafetyLevels() });
  const th = { id: 't', messages: [], items: [] };
  const r = await a.runTool({ id: '1', name: 'browser_sign_in', arguments: '{}' }, th, new AbortController().signal);
  assert.match(r.text, /^Signed in as ben on x\.com\./);
  assert.ok(!r.text.includes(PW)); assert.ok(!JSON.stringify(evs).includes(PW)); assert.ok(!JSON.stringify(th.items).includes(PW));
});

test('capture: Ben submits a sign-in form -> one Save card; the app\'s own fill, never-listed sites, http and failed sign-ins offer nothing', async () => {
  const offers = []; const s = new L.LoginStore({ box: new L.MemoryBox() });
  const c = new L.LoginCapture({ store: s, offer: (e) => offers.push(e), delayMs: 0 });
  const ok = async () => ({ pw: false, failed: false });
  assert.strictEqual(await c.submitted({ key: 1, url: 'https://a.example/login', user: 'ben', password: 'pw-1234', filling: true, probe: ok }), null);
  assert.strictEqual(await c.submitted({ key: 1, url: 'http://a.example/login', user: 'ben', password: 'pw-1234', probe: ok }), null);
  assert.strictEqual(await c.submitted({ key: 1, url: 'https://a.example/login', user: 'ben', password: 'pw-1234', probe: async () => ({ pw: true }) }), null);   // still on the form
  const ev = await c.submitted({ key: 1, url: 'https://a.example/login', user: 'ben', password: 'pw-1234', probe: ok });
  assert.deepStrictEqual([ev.host, ev.user, ev.update], ['a.example', 'ben', false]); assert.ok(!JSON.stringify(offers).includes('pw-1234'));
  assert.strictEqual(await c.submitted({ key: 1, url: 'https://a.example/login', user: 'ben', password: 'pw-1234', probe: ok }), null);   // offered once
  assert.ok((await c.answer(ev.token, 'save')).ok);
  assert.strictEqual((await s.forPage('https://a.example/home')).password, 'pw-1234');
  // two-step: username page, then password page
  const u = await c.submitted({ key: 2, url: 'https://b.example/id', user: 'ben2', password: '', probe: ok }); assert.strictEqual(u, null);
  const ev2 = await c.submitted({ key: 2, url: 'https://b.example/pw', user: '', password: 'pw-5678', probe: ok });
  assert.strictEqual(ev2.user, 'ben2');
  assert.ok((await c.answer(ev2.token, 'never')).never); assert.ok(s.isNever('https://b.example'));
  assert.strictEqual(await c.submitted({ key: 3, url: 'https://b.example/pw', user: 'ben2', password: 'pw-other', probe: ok }), null);
  assert.strictEqual((await c.answer('nope', 'save')).ok, false);
});

test('safety levels: using a saved login is FREE by default; keychain apps and dumping stay NEVER (fixed); banks keep their level', () => {
  const lv = new SafetyLevels();
  assert.strictEqual(lv.level('passwords'), 'free');
  assert.strictEqual(lv.level('keychain'), 'never');
  assert.ok(CATEGORIES.find((c) => c.id === 'keychain').locked);
  assert.strictEqual(lv.set([{ cat: 'keychain', level: 'free' }], { source: 'settings' }).ok, false);
  assert.strictEqual(lv.level('keychain'), 'never');
  assert.strictEqual(classify('browser_sign_in', {}, { pageUrl: 'https://dresden.schoology.com/' }).cat, 'passwords');
  assert.strictEqual(classify('browser_sign_in', {}, { pageUrl: 'https://www.chase.com/' }).cat, 'banking');
  assert.ok(lv.check('browser_sign_in', {}, { pageUrl: 'https://www.chase.com/' }).refuse);
  assert.ok(!lv.check('browser_sign_in', {}, { pageUrl: 'https://dresden.schoology.com/' }).refuse);
  assert.ok(lv.check('open_app', { name: 'Keychain Access' }).refuse);
  assert.ok(lv.check('open_app', { name: '1Password' }).refuse);
  for (const cmd of ['security dump-keychain', 'security find-internet-password -l Premonition -w', 'security export -k login.keychain', 'cp ~/Library/Keychains/login.keychain-db /tmp']) assert.ok(lv.check('run_shell', { command: cmd }).refuse, cmd);
  assert.strictEqual(shellCategory('security find-generic-password -s x'), 'keychain');
  // still editable by Ben, and Glim can change it when he asks
  assert.deepStrictEqual(fromBenText('ask me before you sign in with my passwords'), [{ cat: 'passwords', level: 'ask' }]);
  assert.ok(lv.set(fromBenText('never let Glim use my saved logins'), { source: 'ben-chat' }).ok); assert.strictEqual(lv.level('passwords'), 'never');
  assert.ok(lv.check('browser_sign_in', {}, { pageUrl: 'https://dresden.schoology.com/' }).refuse);
});

test('prompt: passwords in chat are fine (Ben 2026-11-04), saved logins first, codes ask Ben or he does it', () => {
  assert.match(SYSTEM_PROMPT, /passwords in chat are fine/);
  assert.match(SYSTEM_PROMPT, /If Ben gives you a password, use it: type it into the password field with browser_type/);
  assert.match(SYSTEM_PROMPT, /first try browser_sign_in \(the app fills his saved login\)/);
  assert.match(SYSTEM_PROMPT, /ask him for it in one short line, or he can sign in himself in your browser \(the app offers to save it\)/);
  assert.match(SYSTEM_PROMPT, /For codes, 2-step or passkey pages/);
  assert.ok(!/NEVER ask Ben for a password/.test(SYSTEM_PROMPT));
  assert.ok(TOOL_DEFS.browser_sign_in); assert.match(TOOL_DEFS.browser_sign_in.function.description, /never see the password/);
  assert.strictEqual(WORDS.browser_sign_in, 'signing in');
});

test('"save my Schoology login" opens the masked dialog with the likely site; other sentences do not', () => {
  assert.deepStrictEqual(L.saveLoginAsk('save my Schoology login'), { word: 'schoology' });
  assert.deepStrictEqual(L.saveLoginAsk('Glim, please remember my login'), { word: '' });
  assert.strictEqual(L.saveLoginAsk('what is my login'), null);
  assert.strictEqual(L.saveLoginAsk("don't save my login"), null);
  assert.strictEqual(L.guessOrigin('schoology', 'https://dresden.schoology.com/home', []), 'https://dresden.schoology.com');
  assert.strictEqual(L.guessOrigin('schoology', 'https://www.google.com/', ['accounts.google.com', 'dresden.schoology.com', 'schoology.com']), 'https://schoology.com');
  assert.strictEqual(L.guessOrigin('canvas', 'http://x.com', []), '');
  assert.match(L.DIALOG_NOTE('schoology'), /never in the chat/);
});

test('wiring: the browser view has the capture preload; main fills from the store; the log, the diary and Ben\'s chat text are scrubbed', () => {
  const main = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(main, /preload: path\.join\(__dirname, 'preload-browser\.js'\)/);
  assert.match(main, /browser_sign_in: async \(x, ctx\) => \{/);
  assert.match(main, /b\.signIn\(\(u\) => glimLogins\(\)\.forPage\(u\)\)/);
  assert.match(main, /holdsSecret\(line\)/);
  assert.match(main, /text = Logins\.scrub\(/);
  assert.match(main, /'browser_sign_in'/);
  assert.match(fs.readFileSync(path.join(__dirname, '..', 'src', 'gateway.js'), 'utf8'), /scrubRecord\(JSON\.stringify\(rec\)\)/);
  const pre = fs.readFileSync(path.join(__dirname, '..', 'preload-browser.js'), 'utf8');
  assert.match(pre, /ipcRenderer\.send\('pm-login:submit'/); assert.ok(!/contextBridge|exposeInMainWorld/.test(pre));   // nothing for the page to call
});
