'use strict';
// Always-on v2 phase 7: the diary only when asked, consent remembered by default, and the sleep handoff.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const D = require('../src/diary-ao');
const { TruthNotes } = require('../src/truthnotes');
const main = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');

test('"Glim, what did you do?" and close variants are diary asks; ordinary messages are not', () => {
  for (const t of ['Glim, what did you do?', 'what did you do today', 'What have you been up to?', 'hey glim what have you been doing', 'what did you learn while I was away?', 'show me your diary', 'what happened while I was gone', 'so what were you up to']) assert.ok(D.isDiaryAsk(t), t);
  for (const t of ['what did you do to my file?! it is broken and I need it fixed before class tomorrow morning please', 'what is a black hole', 'can you learn about enzymes', 'do the dishes reminder', 'I did my homework']) assert.ok(!D.isDiaryAsk(t), t);
});

test('the recap: time per topic, quiz changes, notes confirmed / wrong, surprises', () => {
  const now = 1e12, t = now - 3600000;
  const activity = [
    { t, kind: 'mote', topic: 'black holes', ok: true, minutes: 3 }, { t, kind: 'mote', topic: 'black holes', ok: true, minutes: 2 }, { t, kind: 'mote', topic: 'npm error', ok: true, minutes: 1 },
    { t, kind: 'quiz', topic: 'black holes', level: 1, pct: 40, was: null, official: false }, { t: t + 1, kind: 'quiz', topic: 'black holes', level: 1, pct: 65, was: 40, official: true },
    { t, kind: 'note', status: 'confirmed', text: 'a' }, { t, kind: 'note', status: 'wrong', text: 'I thought the Sun is a red dwarf; actually it is a G-type star' },
    { t, kind: 'surprise', what: 'Ben switched to Minecraft' }, { t, kind: 'said', text: 'x' },
    { t: now - 3 * 86400000, kind: 'surprise', what: 'too old to show' }
  ];
  const r = D.recap({ activity, truth: { maybe: 2, confirmed: 1, wrong: 1 }, since: now - 86400000, now });
  assert.match(r, /Thought about: black holes \(5 min\), npm error \(1 min\)\./);
  assert.match(r, /Quiz: black holes Lv1 40% → 65%\./);
  assert.match(r, /1 confirmed, 1 wrong \(e\.g\. "I thought the Sun is a red dwarf/);
  assert.match(r, /Surprised 1 time, e\.g\. "Ben switched to Minecraft"/);
  assert.doesNotMatch(r, /too old/);
  assert.match(D.recap({ activity: [], now }), /^Nothing yet/);
});

test('diary text appears only when asked: main builds it only behind isDiaryAsk, and never sends it unprompted', () => {
  const send = main.slice(main.indexOf("h('agent:send'"), main.indexOf("return { started: true, title: t.title };", main.indexOf("h('agent:send'")));
  assert.match(send, /const diary = !goals && !learn && aoState && DiaryAO\.isDiaryAsk\(text\) \? aoDiaryNote\(\) : '';/);
  assert.match(send, /diary \? diary \+ text : text, goals \|\| learn \|\| diary \? \{ display: text \}/, 'a hidden note: the scroll shows only Ben\'s words');
  assert.strictEqual((main.match(/(?<!function )aoDiaryNote\(\)/g) || []).length, 1, 'aoDiaryNote is called in exactly one place');
  assert.strictEqual((main.match(/DiaryAO\.recap\(/g) || []).length, 1, 'the recap is built only inside aoDiaryNote');
  const say = main.slice(main.indexOf('function aoSay('), main.indexOf('\n', main.indexOf('function aoSay(')));
  assert.doesNotMatch(say, /recap|Diary/);
});

test('sleep handoff: confirmed notes, corrections and surprises, never a maybe', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ho-'));
  const tn = new TruthNotes({ dir, search: async () => [{ title: 'a', url: 'https://a.org/1', snippet: '' }, { title: 'b', url: 'https://b.org/1', snippet: '' }], judge: async (c) => ({ verdict: /Sun/.test(c) ? 'contradicts' : 'supports', correction: 'it is a G-type star' }), save: () => ({ ok: true }) });
  const ok = tn.add('Water boils at 100 C at sea level.'); await tn.check(ok);
  const bad = tn.add('The Sun is a red dwarf.'); await tn.check(bad);
  tn.add('A maybe that nobody checked yet.');
  const h = D.sleepHandoff({ truth: tn, surprises: [{ t: 1, stream: 'app', what: 'Ben opened Minecraft at 3 am', kl: 2.1 }] });
  assert.deepStrictEqual(h.confirmed.map((c) => c.text), ['Water boils at 100 C at sea level.']);
  assert.deepStrictEqual(h.corrections.map((c) => c.text), ['I thought The Sun is a red dwarf; actually it is a G-type star']);
  assert.strictEqual(h.surprises[0].text, 'Ben opened Minecraft at 3 am');
  assert.ok(!JSON.stringify(h).includes('nobody checked'), 'no maybe in the handoff');
  const f = D.writeHandoff(dir, h); assert.deepStrictEqual(JSON.parse(fs.readFileSync(f, 'utf8')), h);
  assert.match(main, /try \{ aoNightly\(\); aoSleepHandoff\(\); \}/);
});

test('consent: "Remember my choice" is ticked by default on the first card; Settings > Senses still changes it', () => {
  const r = fs.readFileSync(path.join(__dirname, '..', 'renderer', 'senses.js'), 'utf8');
  assert.match(r, /cb\.checked = v\.consent\.decidedAt \? !!v\.consent\.remember : true;/);
  assert.match(r, /function settingsUi\(\)/);
});
