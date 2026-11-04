const A = globalThis.__ao, log = globalThis.__log, adv = globalThis.__adv, idle = globalThis.__idle;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ears = [];
const ear = (label) => { const e = A.aoEar(); const s = e ? (e.icon || e.face || '') + ' ' + (e.label || e.text || e.hover || '') : 'null'; const short = JSON.stringify(e).slice(0, 160); if (!ears.length || ears[ears.length - 1].icon !== (e && e.icon)) ears.push({ label, icon: e && e.icon }); log('EAR [' + label + '] ' + short); return e; };
let cur = { windows: '', screen: '' };
const win = (front, title, others) => 'Front app: ' + front + '. Open: ' + [front + ' — ' + title].concat(others || []).join('; ') + '.';
(async () => {
  try {
    const r = await A.setSenses({ senses: { windows: true, screen: true }, remember: true, on: true });
    log('senses on:', JSON.stringify(r && r.consent && r.consent.senses));
    // fake senses: the real Senses.sample() reads these instead of the deskhelper
    A.aoSenses.o.samplers = { windows: async () => cur.windows, screen: async () => cur.screen };
    // watch the loop's wake() (the guesser's surprise calls it) without changing it
    const say0 = A.aoLoop.o.deliver.say; A.aoLoop.o.deliver.say = (text, d) => { log('SAY GATE FIRED p=' + (d && d.p != null ? d.p.toFixed(2) : '?') + ' stuckError=' + !!(d && d.features && d.features.stuck_error) + ': ' + text); return say0(text, d); };
    const g0 = A.getGuesser(), ob0 = g0.o.onBig; g0.o.onBig = (s) => { log('GUESSER SURPRISE stream=' + s.stream + ' cat=' + s.cat + ' KL=' + s.kl.toFixed(2) + ' nats'); return ob0(s); };
    const w0 = A.aoLoop.wake.bind(A.aoLoop); A.aoLoop.wake = () => { const ok = w0(); log('LOOP WAKE (early tick) ok=' + ok + ' running=' + A.aoLoop.running + ' inTick=' + A.aoLoop.inTick); return ok; };
    log('loop running=' + A.aoLoop.running + ' gate=' + A.aoLoop.gate() + ' night=' + A.aoNight() + ' moteGate=' + JSON.stringify(A.aoMoteGate()));
    ear('start');
    // ---- phase 1: random browsing (Ben active, not typing): app changes, the model proposes a say, the meter should hold it
    log('=== PHASE 1: browsing ===');
    const pages = [['Safari', 'BBC News - Home'], ['Safari', 'YouTube - lofi beats'], ['Music', 'Library'], ['Safari', 'Wikipedia - Octopus'], ['Messages', 'Messages'], ['Safari', 'Reddit - r/space']];
    idle(10);
    for (const [app, title] of pages) {
      cur = { windows: win(app, title, ['Finder — Downloads']), screen: title + ' — some article text about the day.' };
      adv(25000); await sleep(1200);   // real 1 s clock observes the front app for the guesser
      const t = await A.aoLoop.tick(); log('tick ->', JSON.stringify({ reason: t.reason, said: t.said, meterHeld: t.meterHeld }));
    }
    log('loop stats after browsing:', JSON.stringify(A.aoLoop.stats));
    ear('after browsing');
    // ---- phase 2: the same error 3 times (stuck)
    log('=== PHASE 2: stuck on an error ===');
    for (let i = 1; i <= 3; i++) {
      cur = { windows: win('Terminal', 'npm run build', ['Safari — Stack Overflow']), screen: '$ npm run build (try ' + i + ' at 14:0' + i + ')\nError: Cannot find module \'left-pad\'\n    at Module._resolveFilename (node:internal/modules/cjs/loader:' + (1000 + i) + ':15)' };
      adv(40000); await sleep(1200);
      await A.aoSenses.sample();   // the senses' own 20 s clock
      log('stuck error now:', JSON.stringify(A.aoStuck.error()));
    }
    const t2 = await A.aoLoop.tick(); log('tick ->', JSON.stringify({ reason: t2.reason, said: t2.said, meterHeld: t2.meterHeld, p: t2.decision && t2.decision.p }));
    await sleep(5000);   // the voice waits for a 4 s pause in input before it delivers
    log('voice:', JSON.stringify(A.aoVoice.stats), 'sent:', JSON.stringify((A.aoVoice.sent || []).map((m) => m.text.slice(0, 60))));
    ear('after stuck');
    // ---- phase 3: long idle stretch (bored) -> Motes
    log('=== PHASE 3: idle (bored) ===');
    idle(1500);
    cur = { windows: win('Terminal', 'npm run build', ['Safari — Stack Overflow']), screen: cur.screen };
    for (let m = 0; m < 24; m++) { adv(90000); A.aoUrgeTick(); if (A.aoPool.count()) { log('bored urge started Motes after ' + ((m + 1) * 1.5) + ' idle min: count=' + A.aoPool.count() + ' thinking=' + A.aoPool.thinking()); break; } }
    log('urges:', JSON.stringify(A.aoUrges.view()), 'pool:', JSON.stringify(A.aoPool.stats));
    await sleep(300); ear('Motes thinking');
    await sleep(2500); ear('after first Mote');
    // ---- phase 4: a surprise (a steady Terminal habit, then an app never seen at this hour)
    log('=== PHASE 4: surprise ===');
    await sleep(4000);   // the 1 s clock keeps observing Terminal
    while (A.aoPool.count()) await sleep(500);
    log('ear before surprise'); ear('before surprise');
    cur = { windows: win('Steam', 'Counter-Strike 2', ['Terminal — npm run build']), screen: 'Steam store page' };
    await A.aoSenses.sample(); adv(25000); await A.aoSenses.sample();
    await sleep(2500);
    log('surprises:', JSON.stringify(A.aoState.surprises.slice(-3)));
    ear('after surprise');
    log('EAR SEQUENCE: ' + ears.map((e) => e.icon + ' (' + e.label + ')').join(' -> '));
    const c = globalThis.__calls; log('model calls: ' + c.length + ' ' + JSON.stringify(c.reduce((o, x) => ((o[x.kind] = (o[x.kind] || 0) + 1), o), {})) + ' model calls test-marked=' + c.filter((x) => x.kind !== 'other').every((x) => x.test) + ' (other = GET / health probe)');
    log('activity kinds:', JSON.stringify(A.aoState.activity.map((a) => a.kind)));
  } catch (e) { log('DRIVE FAIL', e && e.stack); process.exitCode = 1; }
  setTimeout(() => process.exit(process.exitCode || 0), 500);
})();
