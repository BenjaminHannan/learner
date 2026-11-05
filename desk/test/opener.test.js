'use strict';
// The opening chat after setup (Ben Nov 4): short hello + one small question with chips; at most 3 questions, one per message;
// the hidden note rides only on replies that plausibly answer the question just asked, never twice, never on unrelated chats.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const O = require('../src/opener');
const { parseChoices } = require('../renderer/choices');

const opener = () => ({ id: 't1', messages: [{ role: 'assistant', content: O.OPENER }] });
const after = (t, user, reply) => ({ ...t, messages: [...t.messages, { role: 'user', content: user }, { role: 'assistant', content: reply }] });
const replyWith = (k) => 'Nice, school is a big one.\n' + O.QUESTIONS[k].q + '\n' + O.QUESTIONS[k].chips.map((c) => '→ ' + c).join('\n');
// Nov 5: question 1 is the person's name (no chips); the old three questions are now 2..4. `named` = the thread after "Dave".
const named = () => after(opener(), 'Dave', 'Nice to meet you, Dave!\n' + O.QUESTIONS[1].q + '\n' + O.QUESTIONS[1].chips.map((c) => '→ ' + c).join('\n'));

test('the hello is short, says "My name is Glim", only what the defaults do, then asks the person\'s name (no chips)', () => {
  const lines = O.HELLO.split('\n');
  assert.ok(lines.length <= 4, lines.length + ' lines');
  assert.ok((O.HELLO.match(/\p{Extended_Pictographic}/gu) || []).length <= 1);
  assert.match(O.HELLO, /I ask first/, 'the main agent defaults to mode "ask"');
  assert.match(O.HELLO, /My name is Glim/);
  assert.ok(!/at night/.test(O.HELLO), 'sleep is off on the built-in brain: the hello does not promise night learning');
  const pc = parseChoices(O.OPENER);
  assert.deepStrictEqual(pc.choices, []);
  assert.match(pc.text, /What's your name\?$/);
  assert.strictEqual((pc.text.match(/\?/g) || []).length, 1, 'one question');
  assert.strictEqual(O.QUESTIONS.length, 4, 'the name + at most 3 small questions');
  for (const q of O.QUESTIONS.slice(1)) { assert.ok(q.q.length < 80); assert.ok(q.chips.length >= 2 && q.chips.length <= 4); }
  const store = fs.readFileSync(path.join(__dirname, '..', 'src/store.js'), 'utf8');
  assert.match(store, /mode: 'ask',/); assert.match(store, /autoSleep: true,/);
});

test('step 1 (name): a short reply gets the note, which saves the name and asks question 2 with its chips', () => {
  for (const s of ['Dave', "I'm Dave", 'Dave Smith']) {
    const r = O.decide(opener(), s, []);
    assert.strictEqual(r.step, 1, s); assert.deepStrictEqual(r.done, [1]);
    assert.match(r.note, /memory_save \(topic "me"\)/); assert.match(r.note, /greet them by that name/);
    assert.ok(r.note.includes(O.QUESTIONS[1].q)); assert.ok(r.note.includes('→ School'));
  }
});

test('step 2: a chip or a short reply gets the note, which asks question 3 word for word with its chips', () => {
  assert.strictEqual(O.stepOf(named()), 2);
  const r = O.decide(named(), 'School', [1]);
  assert.strictEqual(r.step, 2); assert.deepStrictEqual(r.done, [1, 2]);
  assert.ok(r.note.includes(O.QUESTIONS[2].q)); assert.ok(r.note.includes('→ Better grades'));
  assert.match(r.note, /at most 2 short lines, with no list/);
  assert.ok(O.decide(named(), 'my chemistry lab report', [1]).note);
});

test('Ben Nov 4 bug: an unrelated first message gets NO note, ends the flow, and the chat is normal', () => {
  for (const s of ["what's on my screen?", 'What is on my screen', 'open Safari', 'hi', 'Hey Glim!', 'can you check my email', 'go learn about volcanoes', 'tell me a joke']) {
    const r = O.decide(opener(), s, []);
    assert.strictEqual(r.note, '', s); assert.deepStrictEqual(r.done, [1, 2, 3, 4], s + ' ends the flow');
  }
  // ...and once ended, nothing rides later either (no nagging)
  const t2 = after(opener(), "what's on my screen?", 'You have Safari open.\n' + O.QUESTIONS[1].q);
  assert.strictEqual(O.decide(t2, 'School', [1, 2, 3, 4]).note, '');
});

test('a skip ("not now") ends the flow with no note', () => {
  for (const s of ['not now', 'Skip', 'no thanks', 'later']) assert.deepStrictEqual(O.decide(opener(), s, []), { step: 1, kind: 'skip', note: '', done: [1, 2, 3, 4] }, s);
});

test('the note never refers to itself the way the old one did ("this is the answer", "you mentioned")', () => {
  for (const k of [1, 2, 3, 4]) {
    const n = O.noteFor(k);
    assert.ok(!/this is the answer/i.test(n), k);
    assert.match(n, /Never mention, quote or refer to this note/);
    assert.ok(!/brainstorm/i.test(n), 'no big brainstorm lists');
  }
});

test('steps 3 and 4 ride only after Glim asked that question; the last one saves goals and asks nothing more; nothing fires twice', () => {
  const t1 = after(named(), 'School', replyWith(2));
  assert.strictEqual(O.stepOf(t1), 3);
  const r2 = O.decide(t1, 'Better grades', [1, 2]);
  assert.strictEqual(r2.step, 3); assert.ok(r2.note.includes(O.QUESTIONS[3].q)); assert.deepStrictEqual(r2.done, [1, 2, 3]);
  const t2 = after(t1, 'Better grades', 'Good one.\n' + O.QUESTIONS[3].q + '\n→ Yes, once a week\n→ Yes, every day\n→ No thanks');
  const r3 = O.decide(t2, 'Yes, once a week', [1, 2, 3]);
  assert.strictEqual(r3.step, 4); assert.match(r3.note, /memory_save \(topic "goal"\)/); assert.match(r3.note, /Ask no more questions/); assert.match(r3.note, /agent_start/);
  assert.strictEqual(O.decide(t2, 'No thanks', [1, 2, 3]).kind, 'answer', 'no is a fine answer to the check-in question');
  // fired once: the same step does not fire again, even if the model repeats the question
  assert.strictEqual(O.decide(t2, 'Yes', [1, 2, 3, 4]).note, '');
  // the model did not ask question 2 (it chatted about something else): nothing rides
  assert.strictEqual(O.stepOf(after(opener(), 'Dave', 'Great to meet you!')), 0);
  // an unrelated question at the check-in step is a normal chat
  assert.strictEqual(O.decide(t2, 'what time is it?', [1, 2, 3]).note, '');
});

test('never on other threads: a helper, a normal chat, or one whose first message is not the opener', () => {
  assert.strictEqual(O.stepOf({ helper: true, messages: [{ role: 'assistant', content: O.OPENER }] }), 0);
  assert.strictEqual(O.stepOf({ messages: [] }), 0);
  assert.strictEqual(O.stepOf({ messages: [{ role: 'assistant', content: 'Hello' }] }), 0);
  assert.strictEqual(O.decide({ messages: [{ role: 'user', content: 'School' }, { role: 'assistant', content: replyWith(1) }] }, 'Better grades', []).note, '');
});

test('main.js: the opener is written by onboard:goals; the note comes from Opener.decide and the used steps are stored', () => {
  const m = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(m, /const GOALS_ASK = Opener\.OPENER;/);
  assert.match(m, /const r = Opener\.decide\(t, text, store\.getSettings\(\)\.goalsSteps\);\n  if \(r\.step\) store\.saveSettings\(\{ goalsSteps: r\.done \}\);/);
  assert.match(m, /const goalsNote = goalsNoteFor\(t, text\), goals = !!goalsNote;/);
  assert.match(m, /goals \? goalsNote \+ text :/);
  assert.ok(!/GOALS_NOTE|isGoalsAnswer/.test(m));
  const { Store } = require('../src/store');
  const os = require('os'); const s = new Store(fs.mkdtempSync(path.join(os.tmpdir(), 'op-')));
  assert.deepStrictEqual(s.getSettings().goalsSteps, []);
  s.saveSettings({ goalsSteps: [2, 1, 9, 'x', 2, 4] });
  assert.deepStrictEqual(s.getSettings().goalsSteps, [1, 2, 4]);
});
