#!/usr/bin/env node
'use strict';
// Stand-in for `python -m sleepmode start|wake|status|summary` (tests and e2e use it as sleepPython).
// It keeps the same files as the real app in SLEEPMODE_HOME: SLEEPING, WAKE, status.json, events.jsonl, inbox.md, summary.md.
// Everything it writes is labelled as a demo run (fake: true); there are no real numbers here.
const fs = require('fs');
const path = require('path');
const home = process.env.SLEEPMODE_HOME;
const P = (n) => path.join(home, n);
const argv = process.argv.slice(2);
const cmd = argv[argv.indexOf('sleepmode') + 1];
const now = () => new Date().toISOString();
const ev = (o) => fs.appendFileSync(P('events.jsonl'), JSON.stringify({ ts: now(), ...o }) + '\n');
const alive = (pid) => { try { process.kill(pid, 0); return true; } catch (e) { return false; } };
const sleeping = () => { try { const pid = parseInt(fs.readFileSync(P('SLEEPING'), 'utf8'), 10); return alive(pid) ? pid : 0; } catch (e) { return 0; } };
fs.mkdirSync(home, { recursive: true });

if (cmd === 'start') {
  if (sleeping()) { console.log('Already sleeping.'); process.exit(1); }
  const since = now(); const t0 = Date.now();
  const hours0 = Number(process.env.FAKE_SLEEP_HOURS || 0);
  const quiz = process.env.FAKE_SLEEP_QUIZ ? Number(process.env.FAKE_SLEEP_QUIZ) : null;
  try { fs.unlinkSync(P('WAKE')); } catch (e) { /* none */ }
  fs.writeFileSync(P('SLEEPING'), process.pid + '\n');
  const status = (extra) => fs.writeFileSync(P('status.json'), JSON.stringify({ state: 'sleeping', mode: 'sleep', pid: process.pid, since, hours_slept: hours0 + (Date.now() - t0) / 3600000, last_quiz: quiz, last_checkin: null, fake: true, updated: now(), ...extra }));
  status(); ev({ kind: 'start', pid: process.pid });
  let sent = false;
  const loop = setInterval(() => {
    if (fs.existsSync(P('WAKE'))) {
      clearInterval(loop);
      fs.writeFileSync(P('summary.md'), '# While you slept\n\nThis was a **demo run**: no real training happened.\n\n- Slept about ' + (Math.round((hours0 + (Date.now() - t0) / 3600000) * 10) / 10) + ' hours\n- 1 check-in: nothing urgent in Mail or Calendar\n- Your Glims\' scheduled runs were held and will catch up now\n');
      ev({ kind: 'wake', reason: 'wake requested' });
      status({ state: 'awake', mode: 'awake' });
      try { fs.unlinkSync(P('SLEEPING')); } catch (e) { /* ignore */ }
      process.exit(0);
    }
    status({ last_checkin: sent ? now() : null });
    if (process.env.FAKE_SLEEP_CHECKIN && !sent && Date.now() - t0 > 600) {
      sent = true;
      fs.writeFileSync(P('inbox.md'), '- Mail: "Quiz moved to today" from Mr. Phipps needs you\n' + (fs.existsSync(P('inbox.md')) ? fs.readFileSync(P('inbox.md'), 'utf8') : ''));
      ev({ kind: 'checkin', counts: { mail: 1 }, errors: {}, notified: 1 });
      if (process.env.FAKE_SLEEP_PERMISSION) ev({ kind: 'checkin_needs_permission', scanner: 'calendar', error: 'not authorized' });
    }
  }, 100);
} else if (cmd === 'wake') {
  if (!sleeping()) { console.log('Not sleeping.'); process.exit(0); }
  fs.writeFileSync(P('WAKE'), now());
  const end = Date.now() + 10000;
  const w = setInterval(() => { if (!sleeping() || Date.now() > end) { clearInterval(w); process.exit(sleeping() ? 1 : 0); } }, 100);
} else if (cmd === 'summary') {
  try { process.stdout.write(fs.readFileSync(P('summary.md'), 'utf8')); } catch (e) { console.log('No summary yet.'); process.exit(1); }
} else { console.log(JSON.stringify(fs.existsSync(P('status.json')) ? JSON.parse(fs.readFileSync(P('status.json'), 'utf8')) : {})); }
