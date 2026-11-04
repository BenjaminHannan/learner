// Ingredients A real-path check: real main.js, fake senses, an idle stretch -> the bored urge -> the Mote pool -> a sandbox experiment.
// Expected in the log: guess -> result -> label -> surprise (sleep candidate), with real sandbox runs. Read-only towards Ben's files.
const fs = require('fs'), path = require('path');
const A = globalThis.__ao, log = globalThis.__log, adv = globalThis.__adv, idle = globalThis.__idle;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const win = (front, title) => 'Front app: ' + front + '. Open: ' + front + ' — ' + title + '.';
(async () => {
  try {
    await A.setSenses({ senses: { windows: true, screen: true }, remember: true, on: true });
    let cur = { windows: win('Terminal', 'zsh'), screen: '$ ls' };
    A.aoSenses.o.samplers = { windows: async () => cur.windows, screen: async () => cur.screen };
    log('gate=' + A.aoLoop.gate() + ' moteGate=' + JSON.stringify(A.aoMoteGate()));
    idle(1500);   // Ben away
    for (let m = 0; m < 30; m++) { adv(90000); A.aoUrgeTick(); if (A.aoPool.count()) { log('bored urge started ' + A.aoPool.count() + ' Motes after ' + ((m + 1) * 1.5) + ' idle min'); break; } }
    const last = A.aoState.activity.filter((a) => a.kind === 'bored').pop(); log('bored batch:', JSON.stringify(last));
    for (let i = 0; i < 240 && A.aoPool.count(); i++) await sleep(250);
    log('pool:', JSON.stringify(A.aoPool.stats));
    const sci = A.aoScientist(), ev = sci.events();
    for (const e of ev) log('SCIENTIST', e.event.toUpperCase(), JSON.stringify(e).slice(0, 230));
    const ids = [...new Set(ev.filter((e) => e.event === 'start').map((e) => e.id))];
    for (const id of ids) {
      const mine = ev.filter((e) => e.id === id), order = mine.map((e) => e.event).join(' -> ');
      const g = mine.filter((e) => e.event === 'guess'), r = mine.find((e) => e.event === 'result');
      log('EXPERIMENT ' + id + ' ' + (mine[0].kind) + ': ' + order + (r ? ' | every guess before result: ' + g.every((x) => x.guessAt < r.resultAt) : ''));
    }
    const lf = path.join(A.aoDir(), 'checker-labels.jsonl');
    const labels = fs.existsSync(lf) ? fs.readFileSync(lf, 'utf8').trim().split('\n').map(JSON.parse) : [];
    log('LABELS ' + labels.length + ' rows in checker-labels.jsonl; right=' + labels.filter((l) => l.correct).length + ' kinds=' + JSON.stringify([...new Set(labels.map((l) => l.kind))]) + ' all source sandbox/truth executor=' + labels.every((l) => l.source === 'sandbox' && l.truth === 'executor'));
    const sur = A.aoState.surprises.filter((s) => s.stream === 'sandbox');
    log('SURPRISES (sleep candidates) from the sandbox: ' + sur.length + (sur[0] ? ' e.g. ' + JSON.stringify(sur[0]).slice(0, 220) : ''));
    const f = A.aoSleepHandoff(); const h = JSON.parse(fs.readFileSync(f, 'utf8'));
    log('SLEEP HANDOFF ' + path.basename(f) + ': surprises ' + h.surprises.length + ', of which sandbox ' + h.surprises.filter((s) => s.stream === 'sandbox').length + '; confirmed ' + h.confirmed.length + '; corrections ' + h.corrections.length + '; any maybe=' + /"maybe"/.test(JSON.stringify(h)));
    const c = globalThis.__calls;
    log('model calls: ' + c.length + ' ' + JSON.stringify(c.reduce((o, x) => ((o[x.kind] = (o[x.kind] || 0) + 1), o), {})) + ' all test-marked=' + c.filter((x) => x.kind !== 'other').every((x) => x.test));
    // Ben comes back and types: everything stops at once
    idle(0); A.aoPool.stopAll('typing'); log('after typing: pool count=' + A.aoPool.count());
    log('diary scientist line: ' + sci.recap(0));
    log('checker: ' + A.aoChecker().reportLine());
  } catch (e) { log('DRIVE FAIL', e && e.stack); process.exitCode = 1; }
  setTimeout(() => process.exit(process.exitCode || 0), 500);
})();
