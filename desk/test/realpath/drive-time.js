// Task B real-path check (feeling time + patterns): run with  RP_DRIVE=drive-time.js node test/realpath/harness.js
// Real main.js, fake senses over three fake afternoons, one loop tick (fake model), then the nightly jobs that sleep start runs.
const A = globalThis.__ao, log = globalThis.__log, adv = globalThis.__adv, idle = globalThis.__idle;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let cur = { windows: '', screen: '' };
const win = (front, title) => 'Front app: ' + front + '. Open: ' + front + ' — ' + title + '.';
(async () => {
  try {
    await A.setSenses({ senses: { windows: true, screen: true }, remember: true, on: true });
    A.aoSenses.o.samplers = { windows: async () => cur.windows, screen: async () => cur.screen };
    const ask0 = A.aoLoop.o.ask; let lastPrompt = null;
    A.aoLoop.o.ask = (m, s) => { lastPrompt = m[1].content; return ask0(m, s); };
    idle(10);
    const people = [['Maya', 'Kiro Park'], ['Jonah', 'Vale Field'], ['Priya', 'Lune Hall']];
    const filler = [['Safari', 'BBC News - Home'], ['Music', 'Library'], ['Safari', 'Wikipedia - Octopus'], ['Notes', 'chem lab']];
    for (let day = 0; day < 3; day++) {
      const [P, L] = people[day];
      const steps = [
        [win('Safari', filler[day % 4][1]), filler[day % 4][1] + ' — some article text about the day.'],
        [win('Messages', P), P + ' texted: practice at ' + L + ' moved to 6pm'],
        [win('Calendar', 'Week'), 'Calendar: practice moved to 6pm at ' + L],
        [win(filler[(day + 1) % 4][0], filler[(day + 1) % 4][1]), filler[(day + 1) % 4][1] + ' — reading.']
      ];
      for (const [w, sc] of steps) { cur = { windows: w, screen: sc }; await A.aoSenses.sample(); adv(12 * 60000); }
      if (day < 2) adv(24 * 3600000 - 4 * 12 * 60000);
    }
    const tl = A.getTimeline();
    log('TIMELINE rows=' + tl.items.length + ' with time=' + tl.items.filter((x) => Number.isFinite(x.t)).length);
    for (const x of tl.items.slice(-4)) log('  ROW t=' + new Date(x.t).toString().slice(0, 24) + ' | ' + x.text.slice(0, 70) + ' | shape: ' + x.m.slice(0, 70));
    // one loop tick with something new on screen (a fresh name, same shape)
    cur = { windows: win('Messages', 'Zed'), screen: 'Zed texted: practice at Ombra Center moved to 7pm' };
    adv(25000); await A.aoSenses.sample();
    const t = await A.aoLoop.tick(); log('tick ->', JSON.stringify({ reason: t.reason }));
    log('PROMPT (loop, as sent):\n' + String(lastPrompt || '(none)').split('\n').map((l) => '    | ' + l.slice(0, 160)).join('\n'));
    // fake sleep: the jobs sleep start runs (speak-o-meter refit, guesser decay, handoff, patterns)
    const before = globalThis.__calls.length;
    A.aoNightly(true);
    log('MODEL CALLS during the nightly jobs (patterns made): ' + (globalThis.__calls.length - before));
    log('PATTERNS: ' + tl.patterns.length + ' -> ' + tl.patterns.map((p) => require('../../src/patterns').patternLine(p)).join(' || '));
    log('LAST SLEEP: ' + JSON.stringify(tl.lastSleep));
    // a second tick: the earlier rows are no longer new, so recall (plain + shape) and patterns can show in the prompt
    cur = { windows: win('Messages', 'Ari'), screen: 'Ari texted: practice at Doma Plaza moved to 5pm' };
    adv(25000); await A.aoSenses.sample();
    const t2 = await A.aoLoop.tick(); log('tick 2 ->', JSON.stringify({ reason: t2.reason }));
    log('PROMPT 2 (loop, as sent):\n' + String(lastPrompt || '(none)').split('\n').map((l) => '    | ' + l.slice(0, 200)).join('\n'));
    const ctx = A.aoLoopContext([{ t: Date.now(), sense: 'screen', text: 'Ari texted: practice at Doma Plaza moved to 5pm' }]);
    log('CONTEXT after sleep: ' + JSON.stringify(ctx).slice(0, 600));
    log('TIME NOTE: ' + A.aoTimeNote('What happened right before the calendar said practice moved?').replace(/\n/g, ' | ').slice(0, 400));
    log('TIME NOTE 2: ' + A.aoTimeNote('how long ago did Maya text?').replace(/\n/g, ' | ').slice(0, 300));
    log('PATTERN NOTE: ' + A.aoTimeNote('what usually happens after someone texts that practice moved').replace(/\n/g, ' | ').slice(0, 400));
    const h = A.aoSleepHandoff(); log('HANDOFF file keys: ' + Object.keys(JSON.parse(require('fs').readFileSync(h, 'utf8'))).join(','));
    const c = globalThis.__calls; log('model calls total: ' + c.length + ' ' + JSON.stringify(c.reduce((o, x) => ((o[x.kind] = (o[x.kind] || 0) + 1), o), {})) + ' all test-marked=' + c.filter((x) => x.kind !== 'other').every((x) => x.test));
  } catch (e) { log('DRIVE FAIL', e && e.stack); process.exitCode = 1; }
  setTimeout(() => process.exit(process.exitCode || 0), 500);
})();
