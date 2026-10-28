'use strict';
// Like / dislike on Glim's answers (Ben Oct 28). The mark is kept on the answer item in the thread (fb: 1 | -1) and appended to
// <userData>/feedback.jsonl, which sleep reads (sleepmlx lessons.read_feedback): a liked answer becomes a card Glim practises,
// a disliked one a lesson (what went wrong, what to do next time), like a correction. Clearing a mark appends fb 0 (newest wins).
const fs = require('fs');
const path = require('path');

const norm = (s) => String(s || '').replace(/\s+/g, ' ').trim();

// thread, the answer text as shown, 1 / -1 / 0 -> { user, answer } of the marked turn (and the item updated), or null
function rate(thread, answer, fb) {
  if (!thread || ![1, -1, 0].includes(fb)) return null;
  const items = thread.items || [], want = norm(answer);
  if (!want) return null;
  for (let i = items.length - 1; i >= 0; i--) {
    const it = items[i];
    if (it.t !== 'assistant' || norm(it.text) !== want) continue;
    if (fb) it.fb = fb; else delete it.fb;
    let user = '';
    for (let j = i - 1; j >= 0; j--) if (items[j].t === 'user') { user = items[j].text || ''; break; }
    return { user, answer: it.text };
  }
  return null;
}

function record(dir, entry) {
  fs.mkdirSync(dir, { recursive: true });
  fs.appendFileSync(path.join(dir, 'feedback.jsonl'), JSON.stringify(entry) + '\n');
}

module.exports = { rate, record };
