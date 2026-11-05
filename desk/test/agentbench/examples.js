'use strict';
// AGENT1: good/bad step examples from bench runs, for a LATER sleep to train on (nothing trains here; Ben's rule: weights change only in
// sleep). node examples.js OUT.jsonl DIR [DIR ...]
// Each line is one model step: the page the model saw (newest tool result, cut), its action, and a label.
// - good: a step of a task that passed, and not a repeat;
// - bad: a repeat of the previous identical call, a reply that hands back without acting while a usable page was open, or the last step of
//   a task that failed or timed out;
// - other steps of failed tasks are left out (not known to be bad).
// Bench chats are tagged test (never in the nightly diary), so this file is the only way they could reach sleep, and only if the lead adds it.
const fs = require('fs'), path = require('path');
const [out, ...dirs] = process.argv.slice(2);
const lines = [];
for (const d of dirs) for (const f of fs.readdirSync(d).filter((x) => x.endsWith('.json'))) {
  const r = JSON.parse(fs.readFileSync(path.join(d, f), 'utf8'));
  const msgs = r.msgs || [];
  let lastTool = '', prevCall = '';
  const steps = [];
  for (const m of msgs) {
    if (m.role === 'tool') { lastTool = m.content; continue; }
    if (m.role !== 'assistant') continue;
    const call = (m.calls || []).join(' | ');
    steps.push({ seen: String(lastTool).slice(0, 1500), said: String(m.content || '').trim().slice(0, 400), action: call || '(answer)', repeat: !!call && call === prevCall });
    if (call) prevCall = call;
  }
  steps.forEach((s, i) => {
    let label = null;
    if (s.repeat) label = 'bad:repeat';
    else if (r.ok && !r.timedOut) label = 'good';   // a capped task fails (MARKS)
    else if (i === steps.length - 1) label = r.timedOut ? 'bad:timeout' : 'bad:final';
    if (label) lines.push(JSON.stringify({ task: r.task, kind: r.kind, version: r.label, run: r.run, step: i + 1, label, ...s }));
  });
}
fs.writeFileSync(out, lines.join('\n') + (lines.length ? '\n' : ''));
console.log(lines.length + ' examples -> ' + out);
