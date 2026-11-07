'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { Desktop, desktopAction, stableScreen } = require('../src/computer-control/desktop');
const { actionPlan, execute } = require('../src/computer-control/actions');
const { SafetyLevels } = require('../src/safety-levels');
const { checkAction } = require('../src/computer-control/safety');
const { Agent } = require('../src/agent');
const { buildTools } = require('../src/prompt');
const { startGateway } = require('./helpers');
const Vision = require('../src/computer-control/vision');
const { appearancePassed } = require('../src/computer-control/task-trials');
const { desktopRequest, actionRequested } = require('../src/computer-control/schema');

test('asking for instructions does not start or authorize desktop control', () => {
  for (const text of ['Explain how to open Notes', 'Can you tell me how to open Notes?', 'Give me steps to open Notes']) {
    assert.equal(desktopRequest(text),false); assert.equal(actionRequested(text),false);
  }
  assert.equal(desktopRequest('Open Notes and write hello'),true);
  assert.equal(actionRequested('Open Notes and write hello'),true);
  assert.equal(actionRequested('Open Notes and write "how to cook"'),true);
});

test('appearance trial requires dark and back, preserving the initial setting', () => {
  assert.equal(appearancePassed(['light','dark','light'],'light'),true);
  assert.equal(appearancePassed(['dark','light','dark','light','dark'],'dark'),true);
  assert.equal(appearancePassed(['dark','light','dark'],'dark'),false);
  assert.equal(appearancePassed(['light','dark','unknown','light'],'light'),false);
});

function fixture() {
  const logRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'desktop-test-'));
  const sent = [], ctrl = new AbortController(); let number = 0;
  const native = { cancelled:false, async command(op, event) { if (this.cancelled) throw Error('cancelled'); sent.push({ op, ...event }); }, async close() { this.closed = true; }, stop() { this.cancelled = true; } };
  const desktop = new Desktop({ request:'Open Notes and write hello', signal:ctrl.signal, logRoot, minIdleSeconds:0, idleSeconds:() => 1000, startNative:async () => native, captureScreen:async () => ({ id:'shot-' + ++number, at:new Date().toISOString(), hash:String(number).repeat(64), image:'data:image/png;base64,AA==', fingerprint:Buffer.alloc(64000).toString('base64'), displayId:'1', bounds:{x:0,y:0,width:100,height:100}, size:{width:100,height:100} }) });
  return { desktop, native, sent, ctrl, logRoot };
}
function action(x=10) { return { type:'click', x, y:20 }; }

test('look, prepare, confirm, send, verify and log the checked step', async () => {
  const f = fixture();
  try {
    await f.desktop.look();
    const result = await f.desktop.prepare({ observationId:'shot-1', intent:'click the note', action:action() });
    assert.match(result.text, /fresh picture/i); assert.equal(f.sent.length, 0);
    await assert.rejects(() => f.desktop.execute({ preparedId:f.desktop.pending.id, confirmed:false }), /confirmed/);
    assert.equal(f.sent.length, 0);
    await f.desktop.execute({ preparedId:f.desktop.pending.id, confirmed:true });
    assert.deepEqual(f.sent.map(e => e.op), ['grant','send','send','send','end']);
    assert.throws(() => f.desktop.finish({ result:'pass', evidence:'looked' }), /Verify/);
    f.desktop.verify({ observationId:'shot-4', result:'pass', evidence:'the note is selected' });
    f.desktop.finish({ result:'pass', evidence:'the note is selected' });
    await f.desktop.close();
    const row = JSON.parse(fs.readFileSync(path.join(f.logRoot, 'attempts.jsonl'), 'utf8'));
    assert.equal(row.schema, 'hands-attempt/v1'); assert.equal(row.steps[0].intent, 'click the note');
    assert.equal(row.steps[0].observation.sha256, '2'.repeat(64)); assert.equal(row.steps[0].after.sha256, '4'.repeat(64));
    assert.equal(row.steps[0].verification.result, 'pass'); assert.equal(row.steps[0].actor, 'glim');
    assert.equal(row.outcome.result, 'unknown'); // a model's visual statement is not independent proof
    assert.equal(row.outcome.evidence.observationId,'shot-4'); assert.equal(row.outcome.evidence.screenshotSha256,'4'.repeat(64));
  } finally { await f.desktop.close(); fs.rmSync(f.logRoot, { recursive:true, force:true }); }
});

test('takeover cancels the session and no queued event is sent afterwards', async () => {
  const f = fixture();
  try {
    await f.desktop.look(); await f.desktop.prepare({ observationId:'shot-1', intent:'click', action:action() });
    f.native.cancelled = true;
    await assert.rejects(() => f.desktop.execute({ preparedId:f.desktop.pending.id, confirmed:true }), /control/i);
    assert.equal(f.sent.length, 0);
    await assert.rejects(() => f.desktop.look(), /control/i);
  } finally { await f.desktop.close(); fs.rmSync(f.logRoot, { recursive:true, force:true }); }
});

test('a changed screen prevents a previously confirmed click', async () => {
  const f = fixture();
  try {
    await f.desktop.look(); await f.desktop.prepare({ observationId:'shot-1', intent:'click', action:action() });
    const original = f.desktop.captureScreen;
    f.desktop.captureScreen = async (...args) => ({ ...await original(...args), fingerprint:Buffer.alloc(64000, 255).toString('base64') });
    await assert.rejects(() => f.desktop.execute({ preparedId:f.desktop.pending.id, confirmed:true }), /screen changed/i);
    assert.equal(f.sent.length, 0);
  } finally { await f.desktop.close(); fs.rmSync(f.logRoot, { recursive:true, force:true }); }
});

test('a small change at the target is caught even when most of the screen is unchanged', () => {
  const base = Buffer.alloc(64000), changed = Buffer.from(base);
  for (let y=48; y<=52; y++) for (let x=78; x<=82; x++) changed[(y*160+x)*4] = 255;
  const before = { bounds:{x:0,y:0,width:100,height:100}, frontApp:'Notes', fingerprint:base.toString('base64') };
  const after = { ...before, fingerprint:changed.toString('base64') };
  assert.equal(stableScreen(before,before,{ type:'click', x:50, y:50 }),true);
  assert.equal(stableScreen(before,after,{ type:'click', x:50, y:50 }),false);
});

test('a checked hands proposal is recorded as hands, not Glim', async () => {
  const f = fixture();
  try {
    f.desktop.predictor = async ({ action }) => ({ action:{ ...action, x:12, y:21 }, note:'test proposal' });
    await f.desktop.look(); await f.desktop.prepare({ observationId:'shot-1', intent:'click', action:action() });
    await f.desktop.execute({ preparedId:f.desktop.pending.id, confirmed:true, actor:'hands' });
    f.desktop.verify({ observationId:'shot-4', result:'pass', evidence:'selected' });
    f.desktop.finish({ result:'pass', evidence:'selected' }); await f.desktop.close();
    const row = JSON.parse(fs.readFileSync(path.join(f.logRoot,'attempts.jsonl'),'utf8'));
    assert.equal(row.steps[0].actor,'hands'); assert.equal(row.steps[0].action.x,12);
  } finally { await f.desktop.close(); fs.rmSync(f.logRoot,{ recursive:true, force:true }); }
});

test('a failed mid-drag sends no more packets and ends the lease', async () => {
  let sends = 0; const ops = [];
  const native = { cancelled:false, async command(op) { ops.push(op); if (op === 'send' && ++sends === 3) throw Error('expired'); } };
  await assert.rejects(() => execute(native, { type:'drag', x:1, y:1, toX:20, toY:20 }, new AbortController().signal), /expired/);
  assert.deepEqual(ops, ['grant','send','send','send','end']);
});

test('action validation rejects malformed input and makes balanced holds', () => {
  assert.throws(() => actionPlan({ type:'click', x:Infinity, y:0 }), /invalid/);
  assert.throws(() => actionPlan({ type:'click', x:1, y:0, count:0 }), /invalid/);
  assert.throws(() => actionPlan({ type:'scroll', dy:0 }), /invalid/);
  assert.throws(() => actionPlan({ type:'type', text:'' }), /invalid/);
  assert.throws(() => actionPlan({ type:'press', combo:'cmd+madeup' }), /unsupported/);
  const p = actionPlan({ type:'press', combo:'cmd+shift+b' });
  assert.deepEqual(p.map(x => x.down), [true,true,true,false,false,false]);
  assert.deepEqual(p.map(x => x.code), [55,56,11,11,56,55]);
});

test('image points map to display coordinates including a negative monitor origin', () => {
  const shot = { bounds:{ x:-1200, y:100, width:1200, height:800 }, size:{ width:600, height:400 } };
  assert.deepEqual(desktopAction({ type:'click', x:300, y:200 }, shot), { type:'click', x:-600, y:500 });
  assert.throws(() => desktopAction({ type:'click', x:600, y:0 }, shot), /outside/);
  assert.deepEqual(desktopAction({ type:'click', coordinateSpace:'desktop', x:-600, y:500 }, shot), { type:'click', x:-600, y:500 });
});

test('an abandoned proposal is logged as a proposal, not an action', async () => {
  const f = fixture();
  try {
    await f.desktop.look(); await f.desktop.prepare({ observationId:'shot-1', intent:'click', action:action() });
    await f.desktop.close();
    const row = JSON.parse(fs.readFileSync(path.join(f.logRoot, 'attempts.jsonl'), 'utf8'));
    assert.equal(f.sent.length, 0); assert.equal(row.steps.length, 0); assert.equal(row.preparations.length, 1); assert.deepEqual(row.corrections, []);
  } finally { await f.desktop.close(); fs.rmSync(f.logRoot, { recursive:true, force:true }); }
});

test('a test attempt writes one final line after its independent check', async () => {
  const f = fixture();
  try {
    f.desktop.deferFinish = true;
    await f.desktop.look(); await f.desktop.prepare({ observationId:'shot-1', intent:'click', action:action() });
    await f.desktop.execute({ preparedId:f.desktop.pending.id, confirmed:true });
    f.desktop.verify({ observationId:'shot-4', result:'pass', evidence:'selected' });
    f.desktop.finish({ result:'pass', evidence:'selected' }); await f.desktop.close();
    assert.equal(fs.existsSync(path.join(f.logRoot,'attempts.jsonl')),false);
    f.desktop.attempt.finish('pass',{ source:'independent-check', result:'pass' });
    const lines = fs.readFileSync(path.join(f.logRoot,'attempts.jsonl'),'utf8').trim().split('\n');
    assert.equal(lines.length,1); assert.equal(JSON.parse(lines[0]).outcome.result,'pass');
  } finally { await f.desktop.close(); fs.rmSync(f.logRoot,{ recursive:true, force:true }); }
});

test('safety denies unrequested sending and respects Never', () => {
  const safety = new SafetyLevels();
  assert.throws(() => checkAction(safety, () => ({}), action(), 'click Send', 'open Notes'), /not explicitly requested/);
  safety.set([{ cat:'hands', level:'never' }], { source:'settings' });
  assert.throws(() => checkAction(safety, () => ({}), action(), 'click', 'click the button'), /Never/);
});

test('chat exposes only the checked desktop path and passes images back to the model', async () => {
  const gw = await startGateway([
    { tool_calls:[{ name:'computer_look', arguments:{} }] },
    { tool_calls:[{ name:'computer_prepare', arguments:{ observationId:'one', intent:'click the note', action:action() } }] },
    { tool_calls:[{ name:'computer_execute', arguments:{ preparedId:'p', confirmed:true, actor:'glim' } }] },
    { tool_calls:[{ name:'computer_verify', arguments:{ observationId:'after', result:'pass', evidence:'note selected' } }] },
    { tool_calls:[{ name:'computer_finish', arguments:{ result:'pass', evidence:'note selected' } }] },
    { content:'Done.' }
  ]);
  try {
    let closed = false, calls = [];
    const desktop = { pending:{ action:action(), intent:'click the note' }, attempt:{ row:{ steps:[] } },
      async look() { calls.push('look'); return { text:'one', image:'data:image/png;base64,AA==' }; },
      async prepare() { calls.push('prepare'); return { text:'p', image:'data:image/png;base64,AA==' }; },
      async execute() { calls.push('execute'); return { text:'after', image:'data:image/png;base64,AA==' }; },
      verify() { calls.push('verify'); return { text:'checked' }; }, finish() { calls.push('finish'); return { text:'finished' }; },
      async close() { closed = true; } };
    const agent = new Agent({ getSettings:() => ({ gatewayUrl:gw.url, model:'m', maxSteps:10, mode:'hands-off', vision:'off', verify:false }),
      toolDefs:buildTools({}), tools:{}, safety:new SafetyLevels(), safetyCtx:() => ({}), desktopFactory:() => desktop, desktopEyes:async () => ({ type:'image_features', image_features:{ f16:'test',shape:[64,768],eye:'test' } }), emit:() => {}, approve:async () => 'deny' });
    await agent.run({ id:'t', title:'x', messages:[], items:[] }, 'Open Notes and select a note');
    assert.deepEqual(calls, ['look','prepare','execute','verify','finish']); assert.equal(closed, true);
    const names = gw.requests[0].tools.map(t => t.function.name);
    assert.ok(names.includes('computer_execute')); assert.ok(!names.includes('screen_click')); assert.ok(!names.includes('run_shell'));
    assert.ok(gw.requests[1].messages.some(m => Array.isArray(m.content) && m.content.some(part => part.type === 'image_features')));
  } finally { gw.close(); }
});

test('Glim feature budgeting restores the actual image payload', () => {
  const features = { type:'image_features', image_features:{ f16:'a'.repeat(131072), shape:[64,768], eye:'test' } };
  const messages = [{ role:'system', content:'system' },{ role:'user', content:'open Notes' },{ role:'user', content:[{type:'text',text:'screen'},features] }];
  assert.ok(Vision.tokens(messages,[]) < 3000);
  const result = Vision.fit(messages,[],5000,1,[]);
  assert.equal(result.messages.at(-1).content[1].image_features.f16,features.image_features.f16);
});

test('if the eyes fail, chat stops before any action', async () => {
  const gw = await startGateway([{ tool_calls:[{ name:'computer_look', arguments:{} }] }]);
  try {
    let sent = false;
    const fake = { async init() {}, async look() { return { text:'screen', image:'data:image/png;base64,AA==' }; }, async execute() { sent = true; return { text:'sent' }; }, async close() {} };
    const agent = new Agent({ getSettings:() => ({ gatewayUrl:gw.url, model:'m', maxSteps:3, mode:'hands-off', vision:'off', verify:false }), toolDefs:buildTools({}), tools:{}, safety:new SafetyLevels(), desktopFactory:() => fake, desktopEyes:async () => { throw Error('eyes unavailable'); }, emit:() => {} });
    const result = await agent.run({ id:'t', title:'x', messages:[], items:[] },'Open Notes');
    assert.match(result.error,/eyes unavailable/); assert.equal(sent,false);
  } finally { gw.close(); }
});

test('chat starts its watcher before asking the model to plan', async () => {
  let started = false;
  const gw = await startGateway([{ content:'I could not finish.' }]);
  try {
    const agent = new Agent({ getSettings:() => ({ gatewayUrl:gw.url, model:'m', maxSteps:2, mode:'hands-off', vision:'off', verify:false }),
      toolDefs:buildTools({}), tools:{}, safety:new SafetyLevels(), desktopFactory:() => ({ async init() { started = true; }, async close() {} }), emit:() => {} });
    const run = agent.requestWithBudget.bind(agent);
    agent.requestWithBudget = (...args) => { assert.equal(started, true); return run(...args); };
    await agent.run({ id:'t', title:'x', messages:[], items:[] }, 'Open Notes');
    assert.equal(started, true);
  } finally { gw.close(); }
});

test('ordinary chat and instruction questions do not start control', async () => {
  const gw = await startGateway([{ content:'Hello!' }, { content:'Open Notes from the Dock.' }]);
  try {
    let started = false;
    const agent = new Agent({ getSettings:() => ({ gatewayUrl:gw.url, model:'m', maxSteps:2, mode:'hands-off', vision:'off', verify:false }),
      toolDefs:buildTools({}), tools:{}, safety:new SafetyLevels(), desktopFactory:() => { started = true; throw Error('unexpected'); }, emit:() => {} });
    await agent.run({ id:'t', title:'x', messages:[], items:[] }, 'Hello!');
    await agent.run({ id:'u', title:'x', messages:[], items:[] }, 'Explain how to open Notes');
    assert.equal(started, false);
  } finally { gw.close(); }
});

test('a look-only request cannot send desktop input', async () => {
  const gw = await startGateway([{ tool_calls:[{ name:'computer_execute', arguments:{ preparedId:'p', confirmed:true, actor:'glim' } }] }, { content:'I could not finish.' }]);
  try {
    let sent = false;
    const fake = { pending:{ intent:'click', action:action() }, async init() {}, async execute() { sent=true; return { text:'sent' }; }, async close() {} };
    const agent = new Agent({ getSettings:() => ({ gatewayUrl:gw.url, model:'m', maxSteps:3, mode:'hands-off', vision:'off', verify:false }),
      toolDefs:buildTools({}), tools:{}, safety:new SafetyLevels(), desktopFactory:() => fake, emit:() => {} });
    await agent.run({ id:'t', title:'x', messages:[], items:[] }, 'What is on my screen?');
    assert.equal(sent, false);
  } finally { gw.close(); }
});
