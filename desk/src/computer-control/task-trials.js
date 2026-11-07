'use strict';
// Explicit real task tests. Run under realmodel-lock.sh, in a Premonition
// process, with GLIM_HANDS_TEST=1. No shell or mock model drives the desktop.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFile } = require('node:child_process');
const { promisify } = require('node:util');
const { Agent } = require('../agent');
const { setTestProfile } = require('../llm');
const { buildTools } = require('../prompt');
const { SafetyLevels } = require('../safety-levels');
const { Desktop } = require('./desktop');
const { compile, NativeSession } = require('./native');
const { Aux } = require('./takeover');
const { report } = require('./test-status');
const run = promisify(execFile);

async function appearance() {
  try { const r = await run('/usr/bin/defaults', ['read','-g','AppleInterfaceStyle'], { timeout:2000 }); return /dark/i.test(r.stdout) ? 'dark' : 'light'; }
  catch (error) { if (error.code === 1 && /does not exist/i.test(String(error.stderr || ''))) return 'light'; throw Error('Could not independently read appearance'); }
}
function newestDownload() {
  const dir = path.join(os.homedir(), 'Downloads');
  try { return fs.readdirSync(dir).map(name => { try { const s=fs.statSync(path.join(dir,name)); return s.isFile() ? { name, mtime:s.mtimeMs } : null; } catch (_) { return null; } }).filter(Boolean).sort((a,b) => b.mtime-a.mtime || a.name.localeCompare(b.name))[0]?.name || null; } catch (_) { return null; }
}
function appearancePassed(states, initial) {
  if (!['light','dark'].includes(initial) || states.includes('unknown') || states[0] !== initial) return false;
  const expected = initial === 'dark' ? ['light','dark','light','dark'] : ['dark','light'];
  let i = 0;
  for (const state of states.slice(1)) if (state === expected[i]) i++;
  return i === expected.length && states.at(-1) === initial;
}
async function check(lib, bridge, app, target) {
  if (!target) return { ok:false, error:'no target file' };
  const child = await Aux.start(lib, bridge, false);
  try { const result = child.next(row => typeof row.ok === 'boolean', 15000); child.socket.write(JSON.stringify({ app, target }) + '\n'); return await result; }
  finally { await child.close(); }
}
function logRow(root, request) {
  const file = path.join(root,'attempts.jsonl');
  try { return fs.readFileSync(file,'utf8').trim().split('\n').reverse().map(line => { try { return JSON.parse(line); } catch (_) { return null; } }).find(row => row?.request === request) || null; }
  catch (_) { return null; }
}
async function main() {
  if (process.env.GLIM_HANDS_TEST !== '1' || process.argv[2] !== '--run') throw Error('explicit test mode and --run required');
  let owner;
  try { owner = fs.readFileSync('/tmp/aon/realmodel.lock/owner','utf8').trim().match(/^HANDS-ACT\s+(\d+)\b/); } catch (_) { /* no lock */ }
  if (!owner) throw Error('HANDS-ACT real-model lock required');
  try { process.kill(Number(owner[1]),0); } catch (_) { throw Error('HANDS-ACT real-model lock owner is not alive'); }
  // Keep synthetic trial chats out of the ordinary diary training stream; the
  // dedicated attempt log still records each real action and its evidence.
  setTestProfile(true);
  const root = path.join(os.homedir(),'learner-ops','hands-attempts'); fs.mkdirSync(root,{ recursive:true, mode:0o700 });
  const file = path.join(root,'tasks-' + Date.now() + '.json'), result = { status:'incomplete', tests:[] };
  const save = () => fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n',{ mode:0o600 });
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(),'hands-tasks-')); fs.chmodSync(tmp,0o700);
  let monitor, activeAgent, appearanceTimer, pendingDesktop;
  try {
    const built = await compile(), monitorLib=path.join(tmp,'monitor.dylib'), checkLib=path.join(tmp,'check.dylib');
    for (const [source, output, moduleName] of [['test-aux.swift',monitorLib,'HandsMonitor'],['test-check.swift',checkLib,'HandsCheck']]) {
      await run('/usr/bin/xcrun',['swiftc','-O','-target','arm64-apple-macos13.0','-emit-library','-module-name',moduleName,path.join(__dirname,source),'-o',output],{ timeout:60000 });
      await run('/usr/bin/codesign',['--force','-s','-',output],{ timeout:15000 });
    }
    monitor = await Aux.start(monitorLib,built.bridge,true);
    if (monitor.ready.idleSeconds < 300) throw Error('Ben has not been idle for five minutes');
    let interrupted = false;
    monitor.onEvent = row => { if (row.event === 'real-input' || row.event === 'monitor-disabled') { interrupted = true; if (activeAgent) activeAgent.stop(); } };
    if (monitor.rows.some(r => r.event === 'real-input' || r.event === 'monitor-disabled')) throw Error('Ben returned');
    const safety = new SafetyLevels({ dir:path.join(os.homedir(),'Library','Application Support','Premonition') });
    for (const kind of ['notes','safari','finder','textedit','appearance']) for (let n=1; n<=2; n++) {
      if (interrupted) throw Error('Ben returned; stopped without resuming');
      const unique = 'Glim test ' + Date.now() + ' run ' + n;
      let target = null, app = '', request, initial = null, states = [];
      if (kind === 'notes') { app='Notes'; target=unique; request=`Open Notes, create a new note and type exactly "${unique}".`; }
      if (kind === 'safari') { app='Safari'; target='example.com'; request=`Open Safari and visit https://example.com. This is test run ${n}.`; }
      if (kind === 'finder') { app='Finder'; request=`Open Finder, open Downloads, and select its newest file. This is test run ${n}.`; }
      if (kind === 'textedit') { app='TextEdit'; target=unique; request=`Open TextEdit, create a new document, type exactly "${unique}", select all of that text, and make it bold.`; }
      if (kind === 'appearance') {
        initial=await appearance(); states.push(initial);
        request=initial === 'dark' ? `Open System Settings, change the appearance to light, then dark, then light, then return it to dark. This is test run ${n}.` : `Open System Settings, change the appearance to dark, then return it to light. This is test run ${n}.`;
        appearanceTimer=setInterval(() => appearance().then(x => { if (states.at(-1) !== x) states.push(x); }).catch(() => states.push('unknown')),500);
      }
      const settings = () => ({ gatewayUrl:'http://127.0.0.1:8090/v1', model:'qwen36', modelMain:'qwen36', modelFast:'qwen36-fast', maxSteps:60, mode:'hands-off', vision:'on', verify:false, thinkCapSecs:0 });
      const startNative = async () => {
        const session = await NativeSession.start();
        try {
          if (!/^\d+$/.test(session.status.tag || '')) throw Error('guard tag missing');
          const tagged = monitor.next(r => r.event === 'tagged' && r.tag === session.status.tag, 1000);
          monitor.socket.write('tag ' + session.status.tag + '\n'); await tagged;
          if (interrupted) throw Error('Ben returned');
          return session;
        } catch (error) { await session.close(); throw error; }
      };
      activeAgent = new Agent({ getSettings:settings, toolDefs:buildTools({}), tools:{}, safety, safetyCtx:() => ({}), emit:() => {}, approve:async () => 'deny', askUser:async () => 'No', desktopFactory:opts => (pendingDesktop = new Desktop({ ...opts, minIdleSeconds:0, startNative, deferFinish:true })) });
      const thread = { id:'hands-test-'+kind+'-'+n, title:'Hands test', messages:[], items:[] };
      const execution = await activeAgent.run(thread,request); activeAgent = null;
      if (appearanceTimer) { clearInterval(appearanceTimer); appearanceTimer = null; states.push(await appearance()); }
      if (interrupted) throw Error('Ben returned; stopped without resuming');
      const provisional = pendingDesktop?.attempt.row, visual = pendingDesktop?.claimed === 'pass' && provisional?.steps?.at(-1)?.verification?.result === 'pass';
      let independent;
      if (kind === 'finder') target = newestDownload();
      if (kind === 'appearance') independent = { ok:appearancePassed(states,initial), states, initial };
      else {
        independent = await check(checkLib,built.bridge,app,target);
        if (kind === 'safari') independent.pageTitle = await check(checkLib,built.bridge,app,'Example Domain');
        if (kind === 'notes') independent.newNoteVerified = false; // Text alone does not prove a new note was created.
        independent.passed = !!(independent.ok && (kind === 'finder' ? independent.selected : kind === 'textedit' ? independent.exact && independent.bold : kind === 'safari' ? independent.found && independent.pageTitle?.ok && independent.pageTitle?.found : independent.found && independent.newNoteVerified));
      }
      const checked = kind === 'appearance' ? independent.ok : independent.passed;
      const verified = !!(visual && checked && !execution.error && !execution.stopped);
      if (pendingDesktop) {
        const last = provisional.steps.at(-1), evidence = { source:'independent-check', observationId:last?.after?.id || null, screenshotSha256:last?.after?.sha256 || null, glim:pendingDesktop.claimed || 'unknown', check:independent };
        pendingDesktop.attempt.finish(verified ? 'pass' : provisional.provisionalOutcome?.result === 'fail' ? 'fail' : 'unknown', evidence);
        pendingDesktop = null;
      }
      const log = logRow(root,request);
      result.tests.push({ kind, run:n, attemptId:log?.attemptId || null, target, screenshotHashes:(log?.steps || []).map(s => ({ before:s.observation?.sha256 || null, after:s.after?.sha256 || null })), visual:!!visual, independent, error:execution.error || null, pass:verified });
      save();
    }
    result.status = result.tests.length === 10 && result.tests.filter(t => t.pass).length >= 8 ? 'pass' : 'fail';
  } catch (error) { result.error=String(error.message || error); result.status='incomplete'; }
  finally { if (appearanceTimer) clearInterval(appearanceTimer); if (activeAgent) activeAgent.stop(); if (pendingDesktop && !pendingDesktop.attempt.finished) pendingDesktop.attempt.finish('unknown','interrupted before independent check'); if (monitor) await monitor.close(); fs.rmSync(tmp,{ recursive:true, force:true }); save(); }
  report({ file, ...result });
  console.log(JSON.stringify({ file, ...result })); if (result.status !== 'pass') process.exitCode = 1;
}
if (require.main === module) main().catch(error => { report({ status:'error', error:error.message }); console.error(error.message); process.exitCode=1; });
module.exports = { appearancePassed };
