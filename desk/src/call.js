'use strict';
// "Call Glim": hands-free speech to speech. A Call owns one `deskhelper call` child process (Mac): it hears you (speech to text runs on this Mac,
// src/stt.js), we run the text through ask() (the normal agent), cut the streamed answer into sentences and send each
// one to the helper to speak, so speech starts after the first sentence. Talking over Glim stops it (barge-in).
// Pure Node, no Electron: spawn/ask/onEvent are injected so the tests can drive it with a fake helper.
const MIN_SENTENCE = 20, MAX_SENTENCE = 220;
const FILLER = new Set(['uh', 'um', 'uhm', 'umm', 'hmm', 'hm', 'mm', 'mmm', 'mhm', 'er', 'erm', 'ah', 'eh', 'oh', 'huh', 'uh huh']);
const words = (t) => String(t || '').trim().split(/\s+/).filter(Boolean);
// empty, one character, or only "uh / um": not a real utterance
function isFiller(t) {
  const s = String(t || '').toLowerCase().replace(/[^a-z\s]/g, ' ').replace(/\s+/g, ' ').trim();
  return s.length < 2 || FILLER.has(s) || words(s).every((w) => FILLER.has(w));
}

// enough to be a real interruption: 2+ words, or one content word of 3+ letters
const WEAK = new Set(['the', 'and', 'but', 'for', 'you', 'are', 'was', 'not', 'its', 'let', 'now', 'yes']);
function isBargeable(t) {
  const w = words(t);
  return w.length >= 2 || (w.length === 1 && /^[a-z]{3,}$/i.test(w[0].replace(/[^a-z]/gi, '')) && !WEAK.has(w[0].toLowerCase().replace(/[^a-z]/g, '')));
}

// Markdown, emoji, links and code are not read out loud.
function cleanForSpeech(s) {
  return String(s || '')
    .replace(/```[\s\S]*?(```|$)/g, ' ')
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\bhttps?:\/\/[^\s)\]]*[^\s)\].,;:!?]|\bwww\.[^\s)\]]*[^\s)\].,;:!?]/gi, 'a link')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/^\s{0,3}#{1,6}\s+/gm, '').replace(/^\s*>\s?/gm, '').replace(/^\s*([-*+•]|\d+[.)])\s+/gm, '')
    .replace(/\*+/g, '').replace(/(^|\s)_+|_+(?=\s|$|[.,!?])/g, '$1').replace(/\|/g, ' ').replace(/[~#]/g, '')
    .replace(/[\p{Extended_Pictographic}\p{Emoji_Presentation}️‍⃣]/gu, '')
    .replace(/\s+/g, ' ').trim()
    .replace(/^[^\p{L}\p{N}]+$/u, '');
}

// Streaming tokens in, spoken sentences out. A sentence ends at . ! ? followed by a space, or at a newline, once at least
// MIN_SENTENCE characters are buffered ("3.5" and "e.g." do not split). Code fences are held back and dropped.
class Chunker {
  constructor() { this.buf = ''; }
  push(d) {
    this.buf += String(d || '');
    this.buf = this.buf.replace(/```[\s\S]*?```/g, ' ');
    const f = this.buf.indexOf('```');
    let n = f < 0 ? this.buf.length : f; // only text before an open code fence (and not a half-typed fence) can be spoken
    if (f < 0) n -= (this.buf.match(/`{1,2}$/) || [''])[0].length;
    const out = [];
    for (;;) {
      const cut = this._cut(this.buf.slice(0, n));
      if (cut < 0) break;
      out.push(this.buf.slice(0, cut)); this.buf = this.buf.slice(cut); n -= cut;
    }
    return out.map(cleanForSpeech).filter(Boolean);
  }
  _cut(s) {
    for (let i = 0; i < s.length; i++) {
      const c = s[i];
      if (c === '\n' && s.slice(0, i).trim().length >= MIN_SENTENCE) return i + 1;
      if ((c === '.' || c === '!' || c === '?') && i + 1 < s.length && /\s/.test(s[i + 1]) && s.slice(0, i + 1).trim().length >= MIN_SENTENCE) return i + 1;
    }
    if (s.length > MAX_SENTENCE) { const k = Math.max(s.lastIndexOf(', ', MAX_SENTENCE), s.lastIndexOf(' ', MAX_SENTENCE)); return k > 0 ? k + 1 : MAX_SENTENCE; }
    return -1;
  }
  flush() {
    const f = this.buf.indexOf('```');
    const rest = f < 0 ? this.buf : this.buf.slice(0, f);
    this.buf = '';
    const c = cleanForSpeech(rest);
    return c ? [c] : [];
  }
}

const MESSAGES = {
  'mic-denied': 'Glim needs the Microphone. Open System Settings > Privacy & Security > Microphone and switch Premonition on, then call again.'
};

class Call {
  // o.spawn(cmd, args) -> child (stdin, stdout, stderr, on('exit'|'error'), kill)   o.helper: path to deskhelper
  // o.ask(text, {onDelta, signal}) -> Promise (resolves when the whole answer has been streamed)   o.onEvent(ev)
  constructor(o) {
    this.o = o;
    this.state = 'idle';
    this.muted = false;
    this.speaking = false;      // the helper is talking
    this.asking = false;        // an ask() is still streaming
    this.ac = null;             // abort controller of the current ask
    this.last = '';             // newest partial text
    this.said = 0; this.acked = false;
    this.startedAt = 0;
    this.child = null; this.buf = ''; this.err = '';
    this.readied = false;
  }
  emit(ev) { try { this.o.onEvent && this.o.onEvent(ev); } catch (e) { /* the UI must not break the call */ } }
  setState(s) { if (this.state === s || this.state === 'ended') return; this.state = s; this.emit({ type: 'state', state: s, muted: this.muted }); }
  send(obj) { try { if (this.child && this.child.stdin && !this.child.stdin.destroyed) this.child.stdin.write(JSON.stringify(obj) + '\n'); } catch (e) { /* helper gone: the exit handler reports it */ } }

  start() {
    if (this.state !== 'idle') return;
    this.startedAt = Date.now();
    this.setState('connecting');
    let c;
    try { c = this.o.spawn(this.o.helper, ['call']); } catch (e) { return this.fail('Glim could not start the call helper.'); }
    this.child = c;
    c.stdout.on('data', (d) => this._data(String(d)));
    if (c.stderr) c.stderr.on('data', (d) => { this.err = (this.err + String(d)).slice(-400); });
    if (c.stdin && c.stdin.on) c.stdin.on('error', () => { /* helper died; 'exit' says so */ });
    c.on('error', (e) => this.fail(e && e.code === 'ENOENT' ? 'The Glim helper is not installed, so calling is not available.' : 'Glim could not start the call helper.'));
    c.on('exit', (code) => {
      if (this.state === 'ended') return;
      this.fail(this.readied ? 'The call stopped unexpectedly.' : 'The call helper stopped before it was ready.' + (this.err ? ' ' + this.err.trim().split('\n').pop() : ''));
    });
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

  _msg(j) {
    if (this.state === 'ended') return;
    if (j.ready) { this.readied = true; this.setState('listening'); return; }
    if (typeof j.level === 'number') { this.emit({ type: 'level', level: j.level }); return; }
    if (j.note) { this.emit({ type: 'note', note: j.note }); return; }
    if (j.error) return this.fail(MESSAGES[j.error] || ('Calling stopped: ' + j.error), j.error);
    if (typeof j.speaking === 'boolean') {
      this.speaking = j.speaking;
      if (j.speaking) { if (this.asking || this.said) this.setState('speaking'); }
      else if (this.asking) this.setState('thinking'); // between sentences: more is coming
      else this.setState('listening');
      return;
    }
    if (typeof j.partial === 'string') {
      if (this.muted) return;
      this.last = j.partial;
      this.emit({ type: 'partial', text: j.partial });
      if ((this.speaking || this.asking) && !isFiller(j.partial) && words(j.partial).length >= 2) this.bargeIn();
      return;
    }
    if (j.bargein) { if (!isFiller(this.last) && isBargeable(this.last)) this.bargeIn(); return; }
    if (typeof j.final === 'string') {
      this.last = '';
      if (this.muted || isFiller(j.final)) { this.emit({ type: 'partial', text: '' }); return; }
      this.emit({ type: 'final', text: j.final });
      if (this.speaking || this.asking) this.bargeIn();
      this._turn(j.final.trim());
    }
  }

  // Ben talked over Glim: stop talking, drop the answer that is still streaming, go back to listening
  bargeIn() {
    if (!this.speaking && !this.asking) return;
    this.send({ stop: true });
    this._abort();
    this.speaking = false;
    this.setState('listening');
    this.emit({ type: 'bargein' });
  }
  _abort() { if (this.ac) { this.ac.abort(); this.ac = null; } this.asking = false; }

  async _turn(text) {
    this._abort();
    const ac = new AbortController(); this.ac = ac; this.asking = true; this.said = 0; this.acked = false;
    this.setState('thinking');
    const ck = new Chunker();
    const say = (list) => { for (const s of list) { if (ac.signal.aborted) return; this.said++; this.send({ say: s }); this.emit({ type: 'reply', text: s }); } };
    try {
      await this.o.ask(text, { signal: ac.signal, onDelta: (d) => { if (!ac.signal.aborted) say(ck.push(d)); } });
      if (!ac.signal.aborted) say(ck.flush());
    } catch (e) {
      if (!ac.signal.aborted) {
        this.emit({ type: 'error', message: 'Glim could not answer: ' + String((e && e.message) || e).split('\n')[0], fatal: false });
        say(['Sorry, something went wrong.']);
      }
    } finally {
      if (this.ac === ac) {
        this.ac = null; this.asking = false;
        if (!this.speaking) this.setState('listening'); // nothing to say (or already finished)
      }
    }
  }

  // a tool started during a turn: say "One sec." once so the line is not silent
  toolStarted() {
    if (!this.asking || this.acked || !this.ac || this.ac.signal.aborted) return;
    this.acked = true; this.said++; this.send({ say: 'One sec.' });
  }

  setMuted(m) {
    this.muted = !!m; this.send({ mute: this.muted });
    if (this.muted) this.emit({ type: 'partial', text: '' });
    this.emit({ type: 'state', state: this.state, muted: this.muted });
  }

  fail(message, kind) {
    if (this.state === 'ended') return;
    this._abort();
    this.emit({ type: 'error', message, kind: kind || 'call', fatal: true });
    this._end();
  }
  hangup() { if (this.state === 'ended') return; this._abort(); this.send({ quit: true }); this._end(); }
  _end() {
    const c = this.child;
    this.setState('ended');
    if (c) { try { c.stdin && c.stdin.end && c.stdin.end(); } catch (e) { /* closed */ } const t = setTimeout(() => { try { c.kill(); } catch (e) { /* gone */ } }, 1500); if (t.unref) t.unref(); }
  }
  seconds() { return this.startedAt ? Math.floor((Date.now() - this.startedAt) / 1000) : 0; }
}

module.exports = { Call, Chunker, cleanForSpeech, isFiller };
