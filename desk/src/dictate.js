'use strict';
// Dictation: speech to text for the chat box (Mac). A Dictation owns one `deskhelper dictate` child process (plain mic input, local
// speech to text, no speaking, no barge-in) and forwards its partial / final text. It also ends itself after SILENCE_MS without
// speech or MAX_MS in total. Pure Node, no Electron: spawn/onEvent are injected so the tests can drive it with a fake helper.
const SILENCE_MS = 8000, MAX_MS = 120000, VOICE_LEVEL = 0.12;

const MESSAGES = {
  'mic-denied': 'Dictation needs the Microphone. Open System Settings > Privacy & Security > Microphone and switch Premonition on, then try again.'
};

class Dictation {
  // o.spawn(cmd, args) -> child (stdin, stdout, stderr, on('close'|'error'), kill)   o.helper: path to deskhelper   o.onEvent(ev)
  // o.silenceMs / o.maxMs override the auto-stop times (tests).
  constructor(o) {
    this.o = o;
    this.state = 'idle'; // idle -> connecting -> listening -> (stopping) -> ended
    this.child = null; this.buf = ''; this.err = '';
    this.readied = false; this.stopping = false; this.reason = 'stopped';
    this.silenceT = null; this.maxT = null; this.killT = null;
  }
  emit(ev) { try { this.o.onEvent && this.o.onEvent(ev); } catch (e) { /* the UI must not break dictation */ } }
  setState(s) { if (this.state === s || this.state === 'ended') return; this.state = s; this.emit({ type: 'state', state: s, reason: s === 'ended' ? this.reason : undefined }); }
  send(obj) { try { if (this.child && this.child.stdin && !this.child.stdin.destroyed) this.child.stdin.write(JSON.stringify(obj) + '\n'); } catch (e) { /* helper gone: the close handler reports it */ } }
  timer(fn, ms) { const t = setTimeout(fn, ms); if (t.unref) t.unref(); return t; }

  start() {
    if (this.state !== 'idle') return;
    this.setState('connecting');
    let c;
    try { c = this.o.spawn(this.o.helper, ['dictate']); } catch (e) { return this.fail('Glim could not start the dictation helper.'); }
    this.child = c;
    c.stdout.on('data', (d) => this._data(String(d)));
    if (c.stderr) c.stderr.on('data', (d) => { this.err = (this.err + String(d)).slice(-400); });
    if (c.stdin && c.stdin.on) c.stdin.on('error', () => { /* helper died; 'close' says so */ });
    c.on('error', (e) => this.fail(e && e.code === 'ENOENT' ? 'The Glim helper is not installed, so dictation is not available.' : 'Glim could not start the dictation helper.'));
    c.on('close', () => {
      if (this.state === 'ended') return;
      if (this.stopping) return this._end();
      this.fail(this.readied ? 'Dictation stopped unexpectedly.' : 'The dictation helper stopped before it was ready.' + (this.err ? ' ' + this.err.trim().split('\n').pop() : ''));
    });
    this.maxT = this.timer(() => this.stop('limit'), this.o.maxMs || MAX_MS);
  }

  _data(s) {
    this.buf += s;
    let i;
    while ((i = this.buf.indexOf('\n')) >= 0) {
      const line = this.buf.slice(0, i).trim(); this.buf = this.buf.slice(i + 1);
      if (!line) continue;
      let j; try { j = JSON.parse(line); } catch (e) { continue; }
      this._msg(j);
    }
  }
  _heard() {
    if (this.stopping || this.state === 'ended') return;
    clearTimeout(this.silenceT);
    this.silenceT = this.timer(() => this.stop('silence'), this.o.silenceMs || SILENCE_MS);
  }

  _msg(j) {
    if (this.state === 'ended') return;
    if (j.ready) { this.readied = true; if (!this.stopping) { this.setState('listening'); this._heard(); } return; }
    if (typeof j.level === 'number') { if (j.level >= VOICE_LEVEL) this._heard(); this.emit({ type: 'level', level: j.level }); return; }
    if (j.note) { this.emit({ type: 'note', note: j.note }); return; }
    if (j.error) return this.fail(MESSAGES[j.error] || ('Dictation stopped: ' + j.error), j.error);
    if (typeof j.partial === 'string') { this._heard(); this.emit({ type: 'partial', text: j.partial }); return; }
    if (typeof j.final === 'string') { this._heard(); if (j.final.trim()) this.emit({ type: 'final', text: j.final.trim() }); }
  }

  // Ask the helper to flush what it heard and exit; the 'ended' state follows when it has. reason: 'stopped' | 'silence' | 'limit'
  stop(reason) {
    if (this.state === 'ended' || this.stopping) return;
    this.stopping = true; this.reason = reason || 'stopped';
    clearTimeout(this.silenceT); clearTimeout(this.maxT);
    if (!this.child) return this._end();
    this.send({ stop: true });
    this.killT = this.timer(() => this._end(), 20000); // the helper did not exit by itself (its last words go through the speech model first)
  }
  fail(message, kind) {
    if (this.state === 'ended') return;
    this.emit({ type: 'error', message, kind: kind || 'dictate', fatal: true });
    this.reason = 'error';
    this._end();
  }
  _end() {
    if (this.state === 'ended') return;
    clearTimeout(this.silenceT); clearTimeout(this.maxT); clearTimeout(this.killT);
    const c = this.child;
    this.setState('ended');
    if (c) {
      try { c.stdin && c.stdin.end && c.stdin.end(); } catch (e) { /* closed */ }
      const t = setTimeout(() => { try { c.kill(); } catch (e) { /* gone */ } }, 1500); if (t.unref) t.unref();
    }
  }
  // quit / window closed: no flush, just go
  close() { if (this.state === 'ended') return; this.stopping = true; this.send({ quit: true }); this._end(); }
}

module.exports = { Dictation, MESSAGES, SILENCE_MS, MAX_MS, VOICE_LEVEL };
