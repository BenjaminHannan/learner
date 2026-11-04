'use strict';
// Always-on Premonition, part 4: hearing. One long-running `deskhelper dictate` (plain mic input, no voice processing, no ducking)
// whose FINISHED utterances become observations. The helper streams 16 kHz PCM to the local speech server over 127.0.0.1 only;
// no audio is ever written to disk, here or in the helper, and only the words come back.
// It steps aside while a call or dictation owns the mic (pause / resume), restarts with a back-off if the helper stops, and stops for
// good on a permanent error (mic denied, speech model missing). Pure Node: Dictation's spawn and the STT lookup are injected.
const { Dictation } = require('./dictate');

const FOREVER_MS = 2 ** 31 - 1;   // no silence / length auto-stop: it keeps listening
const RETRY_MS = 5000, RETRY_MAX_MS = 300000;

class Hearing {
  // o: { helper: () => path | null, spawn(cmd, args, url) -> child, sttUrl: async () => ({url} | {error, needsVoice}),
  //      onText(text), onState(state, why), setTimer, clearTimer, makeDictation(opts) (tests) }
  constructor(o) {
    this.o = o; this.want = false; this.paused = new Set(); this.d = null; this.starting = false;
    this.retryMs = RETRY_MS; this.retryT = null; this.state = 'off'; this.why = ''; this.heard = 0;
    this.setTimer = o.setTimer || ((fn, ms) => { const t = setTimeout(fn, ms); if (t.unref) t.unref(); return t; });
    this.clearTimer = o.clearTimer || clearTimeout;
  }
  set(state, why) { this.state = state; this.why = why || ''; try { this.o.onState && this.o.onState(state, this.why); } catch (e) { /* UI only */ } }
  // Ben switched hearing on: listen whenever nothing else owns the mic
  enable() { this.want = true; this._go(); }
  disable() { this.want = false; this._halt(); this.set('off'); }
  // a call / dictation is taking the mic (by name, so two owners are counted separately)
  pause(owner) { this.paused.add(owner || 'other'); this._halt(); if (this.want) this.set('paused', 'Another voice feature is using the microphone.'); }
  resume(owner) { this.paused.delete(owner || 'other'); this._go(); }
  listening() { return !!(this.d && this.d.state !== 'ended'); }

  _halt() {
    if (this.retryT) { this.clearTimer(this.retryT); this.retryT = null; }
    const d = this.d; this.d = null;
    if (d) { d.stopped = true; try { d.close(); } catch (e) { /* gone */ } }
  }
  async _go() {
    if (!this.want || this.paused.size || this.d || this.starting) return;
    const bin = this.o.helper && this.o.helper();
    if (!bin) { this.set('error', 'Hearing needs the Glim helper, which is not installed in this build.'); return; }
    this.starting = true; this.set('starting', 'Loading the speech model (the first time takes about 2 minutes).');
    let stt;
    try { stt = await this.o.sttUrl(); } catch (e) { stt = { error: String(e && e.message || e) }; }
    this.starting = false;
    if (!this.want || this.paused.size || this.d) return;   // switched off or the mic was taken while the model loaded
    if (!stt || stt.error) { this.set('error', (stt && stt.error) || 'The speech model did not start.'); if (!(stt && stt.needsVoice)) this._retry(); return; }
    const opts = {
      helper: bin, silenceMs: FOREVER_MS, maxMs: FOREVER_MS,
      spawn: (cmd, args) => this.o.spawn(cmd, args, stt.url),
      onEvent: (ev) => this._event(d, ev)
    };
    const d = this.o.makeDictation ? this.o.makeDictation(opts) : new Dictation(opts);
    this.d = d;
    d.start();
  }
  _event(d, ev) {
    if (d !== this.d && !(ev && ev.type === 'state')) return;
    if (ev.type === 'final' && ev.text) { this.heard++; this.retryMs = RETRY_MS; try { this.o.onText(ev.text); } catch (e) { /* the inbox owns it */ } return; }
    if (ev.type === 'state' && ev.state === 'listening' && d === this.d) { this.set('listening'); return; }
    if (ev.type === 'error' && d === this.d) {
      // the mic was refused: no point retrying until Ben changes it
      if (/Microphone/.test(ev.message || '')) { this.want = false; this.d = null; this.set('error', ev.message); return; }
      this.set('error', ev.message);
    }
    if (ev.type === 'state' && ev.state === 'ended') {
      if (d !== this.d || d.stopped) return;   // we stopped it ourselves
      this.d = null; this._retry();
    }
  }
  _retry() {
    if (!this.want || this.paused.size || this.retryT) return;
    const ms = this.retryMs; this.retryMs = Math.min(RETRY_MAX_MS, this.retryMs * 2);
    this.retryT = this.setTimer(() => { this.retryT = null; this._go(); }, ms);
  }
}

module.exports = { Hearing, FOREVER_MS, RETRY_MS, RETRY_MAX_MS };
