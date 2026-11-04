'use strict';
// Always-on v2 gap fix (Nov 4): the Learn-mode study Motes (the Learn button, "go learn X" in chat, bored-mode Learn) no longer save
// their findings straight to memory. Each memory_save from a study Mote:
//   1. passes the drift guard (src/quiz.js onTopic: "is this still about my topic?"), else it is refused and counted;
//   2. becomes a `maybe` note in src/truthnotes.js (NOT memory, so sleep never sees it) with the page it was read on;
//   3. reaches memory only when 2 independent sites confirm it (or as a correction when 2 contradict it).
// Every web_search step of a study Mote passes the same drift guard. Pure Node: truth / vocab / onDrift are injected.
const Quiz = require('./quiz');

// the topic of a Learn Mote: its stored learnTopic, else the task text LEARN_MOTE wrote ("Go learn: <topic>[, focusing on ...]. Each run")
function topicOf(h) {
  if (h && typeof h.learnTopic === 'string' && h.learnTopic.trim()) return h.learnTopic.trim();
  const m = /^Go learn: (.+?)(?:, focusing on [^.]*)?\. Each run/.exec(String((h && h.task) || ''));
  return m ? m[1].trim() : '';
}
// "Black hole => emits => Hawking radiation" -> "Black hole emits Hawking radiation" (what the web check searches for)
const plain = (fact) => String(fact || '').replace(/\s*=>\s*/g, ' ').replace(/\s+/g, ' ').trim();

// study steps: a search (or a save) is on topic when Quiz.onTopic says so for the topic, the angle words and what is confirmed
function stepOnTopic(text, topic, vocab) { return !topic || Quiz.onTopic(plain(text), topic, vocab || []); }

// The memory object a study Mote's agent gets. Reads (list/forget/...) pass through to the real memory; save() is routed.
// o: { memory, truth (TruthNotes), topic, vocab() -> [text], onDrift(kind, text), from }
function studyMemory(o) {
  const real = o.memory, topic = o.topic;
  const routed = {
    save(fact, saveTopic, options) {
      const text = String(fact || '').replace(/\s+/g, ' ').trim();
      if (!text) return { ok: false, error: 'Empty fact.' };
      const vocab = (o.vocab && o.vocab()) || [];
      if (!stepOnTopic(text, topic, vocab)) {
        try { o.onDrift && o.onDrift('save', text); } catch (e) { /* counting only */ }
        return { ok: false, error: 'Not saved: this is not about ' + topic + '. Stay on the study topic.', drift: true };
      }
      const research = options && options.research ? JSON.parse(JSON.stringify(options.research)) : null;
      const n = o.truth.add(plain(text), { topic, from: o.from || 'learn', saveText: text, saveTopic: saveTopic || '', research });
      if (!n) return { ok: false, error: 'Not saved: already noted (it is waiting for its web check) or it looks private.' };
      return { ok: true, truth: 'maybe', fact: { id: n.id, text }, kept: true };
    }
  };
  return new Proxy(real || {}, { get: (t, k) => (k === 'save' ? routed.save : typeof t[k] === 'function' ? t[k].bind(t) : t[k]) });
}

// wrap a web_search tool so an off-topic search is refused (and counted) instead of run
function guardSearch(run, o) {
  return async (x, ctx) => {
    const q = String((x && x.query) || '');
    if (!stepOnTopic(q, o.topic, (o.vocab && o.vocab()) || [])) {
      try { o.onDrift && o.onDrift('search', q); } catch (e) { /* counting only */ }
      return { text: 'Error: that search drifted off the study topic (' + o.topic + '). Search for something about ' + o.topic + '.', error: true, summary: 'Skipped an off-topic search' };
    }
    return run(x, ctx);
  };
}

module.exports = { topicOf, plain, stepOnTopic, studyMemory, guardSearch };
