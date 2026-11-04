'use strict';
// The opening chat after first-run setup (Ben Nov 4: "it should first explain what it does and ask you in smaller chunks").
// Glim's first message: a short hello (what Glim does, with the default settings) + ONE small question with one-tap chips.
// Each answer gets a hidden note that tells the model to ask the next small question (at most 3), then save the goals.
// Ben Nov 4 bug: the old note rode on an unrelated first message ("what's on my screen?") and the model quoted it back
// ("you mentioned this is the answer..."). Now a note rides ONLY on a message that plausibly answers the question just
// asked, it never says "answer"/"you mentioned", and an unrelated message or a skip ends the flow: a normal chat, no nagging.

// The hello: only what the app does today with its defaults (mode 'ask' = Glim asks before acting; autoSleep on; memory on).
const HELLO = "Hi, I'm Glim 👋\n"
  + 'I can do things on your Mac for you (I ask first).\n'
  + 'I can study any topic you give me: press Learn.\n'
  + 'I remember what you tell me, and at night I go over what I learned.';
const QUESTIONS = [
  { q: "To start: what's one thing you're working on right now?", chips: ['School', 'A project', 'A skill', 'Not sure yet'] },
  { q: "Is there something bigger you'd like to reach later, like this year?", chips: ['Better grades', 'Build something', 'Get healthier', 'Not sure yet'] },
  { q: 'Should I check in on these now and then?', chips: ['Yes, once a week', 'Yes, every day', 'No thanks'] }
];
const chipLines = (k) => QUESTIONS[k].chips.map((c) => '→ ' + c).join('\n');
const OPENER = HELLO + '\n\n' + QUESTIONS[0].q + '\n' + chipLines(0);

const norm = (s) => String(s == null ? '' : s).toLowerCase().replace(/[‘’]/g, "'").replace(/[“”]/g, '"').replace(/\s+/g, ' ').trim();
const contentOf = (m) => (typeof m.content === 'string' ? m.content : Array.isArray(m.content) ? m.content.map((p) => (p && p.text) || '').join('') : '');

// which question the person is replying to (1..3), or 0 = not in the opener flow
function stepOf(t) {
  if (!t || t.helper) return 0;
  const ms = t.messages || [];
  if (!ms.length || ms[0].role !== 'assistant' || contentOf(ms[0]) !== OPENER) return 0;
  const last = ms[ms.length - 1];
  if (!last || last.role !== 'assistant') return 0;
  if (ms.length === 1) return 1;
  const said = norm(contentOf(last));
  for (let k = QUESTIONS.length; k >= 2; k--) if (said.includes(norm(QUESTIONS[k - 1].q))) return k;
  return 0;
}

const SKIP = /^(?:no|nope|nah|not now|not right now|skip|skip it|later|maybe later|pass|no thanks|no thank you|none|nothing|i'?d rather not|never ?mind)[.! ]*$/i;
const YES = /^(?:y|yes|yeah|yep|sure|ok|okay|please|sounds good|definitely|of course|yes please)\b/i;
const NO = /^(?:no|nope|nah|not really|no thanks|no thank you|don'?t|never)\b/i;
// a message that is plainly something else: a question, a request to do something, a greeting, "go learn X"
const QUESTIONY = /\?\s*$|^(?:what|what's|whats|how|why|who|where|when|which|can you|could you|would you|will you|is|are|do|does|did|should)\b/i;
const COMMAND = /^(?:please\s+)?(?:open|close|show|click|type|search|find|look|read|go to|play|send|email|mail|remind|set|turn|tell me|explain|summari[sz]e|write|draft|check my|list|stop|start|run|learn|study|go learn|translate|take|screenshot)\b/i;
const GREETING = /^(?:hi|hello|hey|yo|hiya|good (?:morning|afternoon|evening))(?:[ ,]+(?:glim|there))?[.!]*$/i;

// does this message plausibly reply to question `step`? 'answer' | 'skip' | 'other'
function classify(step, text) {
  const s = String(text || '').trim();
  if (!s) return 'other';
  const chip = QUESTIONS[step - 1] && QUESTIONS[step - 1].chips.find((c) => norm(c) === norm(s));
  if (chip) return 'answer';
  if (step === 3 && (YES.test(s) || NO.test(s)) && s.length <= 80 && !/\?\s*$/.test(s)) return 'answer';
  if (SKIP.test(s)) return 'skip';
  if (QUESTIONY.test(s) || COMMAND.test(s) || GREETING.test(s)) return 'other';
  if (step === 3) return 'other';   // the check-in question wants a yes or a no; anything else is a normal chat
  if (s.split(/\s+/).length > 40) return 'other';   // a long message is about something else
  return 'answer';
}

const PRIVATE = '[Private context for you only. Never mention, quote or refer to this note, and never say "you mentioned" about it. ';
function noteFor(step) {
  if (step < QUESTIONS.length) {
    const next = QUESTIONS[step];
    return PRIVATE + 'In your first chat with this person you asked: "' + QUESTIONS[step - 1].q + '" Their reply is below.] '
      + 'If it names something they are working on or want to reach, save it with memory_save (topic "goal"), one short note. '
      + 'Then reply in at most 2 short lines, with no list: a few warm words about it (if they are not sure yet, say that is fine), '
      + 'then ask this question word for word, and end with these choice lines exactly as written:\n' + next.q + '\n' + chipLines(step) + '\n\n';
  }
  return PRIVATE + 'In your first chat with this person you asked: "' + QUESTIONS[step - 1].q + '" Their reply is below.] '
    + 'Look at the goals they gave earlier in this chat. If one is not saved yet, save it with memory_save (topic "goal"). '
    + 'Save one first small step for this week as its own note (topic "goal"), so it shows in the Goals tab. '
    + 'If they said yes, start one check-in helper with agent_start at the rhythm they picked (weekly if unsure); if they said no, start nothing. '
    + 'Reply in at most 3 short lines, with no list: their goals are in the Goals tab, the first small step, and whether you will check in. Ask no more questions.\n\n';
}

// main.js: what to do with this message. done = the steps already used (a note never rides twice).
// -> { step, kind, note, done }  (note '' = a normal chat)
function decide(t, text, done) {
  const used = Array.isArray(done) ? done.filter((n) => Number.isInteger(n)) : [];
  const step = stepOf(t);
  if (!step || used.includes(step)) return { step: 0, kind: 'none', note: '', done: used };
  const kind = classify(step, text);
  if (kind !== 'answer') return { step, kind, note: '', done: [1, 2, 3] };   // a skip or something unrelated ends the flow: no nagging
  return { step, kind, note: noteFor(step), done: [...new Set(used.concat(step))].sort() };
}

module.exports = { HELLO, QUESTIONS, OPENER, stepOf, classify, noteFor, decide };
