'use strict';
// Always-on hearing (src/hearing.js) driven through the real Dictation class with a fake `deskhelper dictate` child. No mic, no Python.
// Plus pass mark 4: none of the always-on modules can write an image or audio to disk.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { EventEmitter } = require('events');
const { Hearing } = require('../src/hearing');

function fakeChild() {
  const c = new EventEmitter();
  c.stdout = new EventEmitter(); c.stderr = new EventEmitter();
  c.stdin = { lines: [], destroyed: false, write(l) { this.lines.push(l); }, end() { this.destroyed = true; }, on() {} };
  c.kill = () => { c.killed = true; };
  c.say = (o) => c.stdout.emit('data', JSON.stringify(o) + '\n');
  return c;
}
function rig(o) {
  o = o || {};
  const kids = [], texts = [], timers = [], sttCalls = [];
  const h = new Hearing({
    helper: () => (o.noHelper ? null : '/fake/deskhelper'),
    sttUrl: async () => { sttCalls.push(1); return o.stt || { url: 'http://127.0.0.1:5555' }; },
    spawn: (cmd, args, url) => { const c = fakeChild(); c.cmd = cmd; c.args = args; c.url = url; kids.push(c); return c; },
    onText: (t) => texts.push(t),
    setTimer: (fn, ms) => { const t = { fn, ms }; timers.push(t); return t; }, clearTimer: (t) => { const i = timers.indexOf(t); if (i >= 0) timers.splice(i, 1); }
  });
  return { h, kids, texts, timers, sttCalls };
}
const flush = () => new Promise((r) => setImmediate(r));

test('enable pre-warms the speech server, then listens with deskhelper dictate; only finished utterances become text', async () => {
  const r = rig();
  r.h.enable(); await flush();
  assert.strictEqual(r.sttCalls.length, 1);
  assert.strictEqual(r.kids.length, 1);
  assert.deepStrictEqual(r.kids[0].args, ['dictate']);
  assert.strictEqual(r.kids[0].url, 'http://127.0.0.1:5555');
  r.kids[0].say({ ready: true });
  assert.strictEqual(r.h.state, 'listening');
  r.kids[0].say({ partial: 'remind me' });
  r.kids[0].say({ final: 'remind me to email Mr Phipps' });
  assert.deepStrictEqual(r.texts, ['remind me to email Mr Phipps']);
  // no silence auto-stop: it is still listening
  assert.ok(r.h.listening());
});

test('a call or dictation pauses hearing (mic released) and it resumes after', async () => {
  const r = rig();
  r.h.enable(); await flush(); r.kids[0].say({ ready: true });
  r.h.pause('call:1');
  assert.ok(!r.h.listening());
  assert.ok(r.kids[0].stdin.lines.some((l) => /"quit":true/.test(l)), 'the helper was told to quit');
  r.kids[0].say({ final: 'words during the call' });
  assert.deepStrictEqual(r.texts, []);
  r.h.pause('dictate:2'); r.h.resume('call:1'); await flush();
  assert.strictEqual(r.kids.length, 1, 'still paused while dictation owns the mic');
  r.h.resume('dictate:2'); await flush();
  assert.strictEqual(r.kids.length, 2);
});

test('hearing off: no helper, no speech server', async () => {
  const r = rig();
  r.h.disable(); await flush();
  assert.strictEqual(r.kids.length, 0); assert.strictEqual(r.sttCalls.length, 0);
  r.h.enable(); await flush(); r.h.disable();
  assert.ok(!r.h.listening());
});

test('the helper stopping by itself restarts with a back-off; mic denied stops for good', async () => {
  const r = rig();
  r.h.enable(); await flush(); r.kids[0].say({ ready: true });
  r.kids[0].emit('close');
  assert.strictEqual(r.timers.length, 1); assert.strictEqual(r.timers[0].ms, 5000);
  r.timers.shift().fn(); await flush();
  assert.strictEqual(r.kids.length, 2);
  r.kids[1].say({ error: 'mic-denied' });
  assert.strictEqual(r.h.state, 'error'); assert.match(r.h.why, /Microphone/);
  assert.strictEqual(r.timers.length, 0);
});

test('missing speech model: says so and does not retry forever', async () => {
  const r = rig({ stt: { error: 'Voice needs the local speech model', needsVoice: true } });
  r.h.enable(); await flush();
  assert.strictEqual(r.h.state, 'error'); assert.strictEqual(r.kids.length, 0); assert.strictEqual(r.timers.length, 0);
});

// ---- pass mark 4: nothing in the always-on path writes an image or audio file
test('no always-on module writes images or audio to disk', () => {
  const root = path.join(__dirname, '..');
  const files = ['src/senses.js', 'src/alwayson.js', 'src/hearing.js', 'src/learnbutton.js', 'renderer/senses.js', 'renderer/learnbtn.js',
    // always-on v2 (pass mark 4 extended): the new modules
    'src/glimvoice.js', 'src/speakometer.js', 'src/guesser.js', 'src/urges.js', 'src/memgauge.js', 'src/motepool.js', 'src/truthnotes.js'];
  const main = fs.readFileSync(path.join(root, 'main.js'), 'utf8');
  const block = main.slice(main.indexOf('// ---- Always-on Premonition'), main.indexOf('function registerIpc() {'));
  assert.ok(block.length > 1000, 'found the always-on block of main.js');
  const sources = files.map((f) => [f, fs.readFileSync(path.join(root, f), 'utf8')]).concat([['main.js always-on block', block]]);
  for (const [f, src] of sources) {
    assert.ok(!/['"]screenshot['"]/.test(src), f + ' must not call the screenshot helper (it writes a JPEG)');
    assert.ok(!/\.(?:jpe?g|png|gif|heic|tiff?|bmp|webp|wav|mp3|m4a|aiff?|caf|flac|ogg|pcm|raw)\b['"]/i.test(src), f + ' names no image/audio file');
    assert.ok(!/toPNG|toJPEG|capturePage|desktopCapturer|getUserMedia|MediaRecorder|toDataURL/.test(src), f + ' captures no picture or sound itself');
    assert.ok(!/base64/.test(src), f + ' keeps no encoded media');
  }
  // the only file writers are the two JSON files and the learn-button JSON
  for (const [f, src] of sources) {
    const writes = src.match(/fs\.(?:writeFileSync|appendFileSync|createWriteStream|writeFile)\([^)]*\)/g) || [];
    for (const w of writes) assert.ok(/tmp|this\.file|this\.logFile|aoGuessFile\(\)/.test(w), f + ': unexpected write ' + w);
  }
  // the helper's new sense commands: text in memory only
  const swift = fs.readFileSync(path.join(root, 'helper', 'deskhelper.swift'), 'utf8');
  const ocr = swift.slice(swift.indexOf('func cmdOcr('), swift.indexOf('func cmdWindows('));
  assert.ok(ocr.length > 200);
  assert.ok(!/write\(|representation\(|jpeg|png|FileManager/i.test(ocr), 'cmdOcr writes nothing');
  // the dictate path posts PCM to the local server and never saves it
  const call = swift.slice(swift.indexOf('final class CallSession'), swift.indexOf('func runCall('));
  assert.ok(!/AVAudioFile|\.write\(to|FileManager|createFile/.test(call), 'the mic path writes no file');
});
