'use strict';
// LaunchServices gives the separate test process Premonition's app identity.
// For tasks, run this launcher inside realmodel-lock.sh HANDS-ACT.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execFile } = require('node:child_process');
const { promisify } = require('node:util');
const run = promisify(execFile);
async function main() {
  const mode = process.argv[2], names = { preflight:'preflight.js', tasks:'task-trials.js', takeover:'takeover.js' };
  if (!names[mode]) throw Error('Choose preflight, tasks, or takeover');
  const app = '/Applications/Premonition.app', entry = mode === 'preflight' ? path.join(__dirname, names[mode]) : path.join(app,'Contents/Resources/app/src/computer-control',names[mode]);
  if (!fs.existsSync(entry)) throw Error('The installed app does not contain the test');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(),'hands-launch-')); fs.chmodSync(dir,0o700);
  const status = path.join(dir,'status.json'), stdout = path.join(dir,'stdout'), stderr = path.join(dir,'stderr');
  fs.writeFileSync(stdout,'',{mode:0o600}); fs.writeFileSync(stderr,'',{mode:0o600});
  let watcher, timer;
  const completed = new Promise((resolve,reject) => {
    const check = () => { try { const value=JSON.parse(fs.readFileSync(status,'utf8')); watcher.close(); clearTimeout(timer); resolve(value); } catch (_) {} };
    watcher = fs.watch(dir,check); timer = setTimeout(() => { watcher.close(); reject(Error('test did not report a result')); }, mode === 'tasks' ? 7200000 : 120000); check();
  });
  try {
    await run('/usr/bin/open',['-n','-j','-g','-a',app,'--env','ELECTRON_RUN_AS_NODE=1','--env','GLIM_HANDS_TEST=1','--env','GLIM_HANDS_STATUS='+status,'--stdout',stdout,'--stderr',stderr,'--args',entry,...(mode === 'preflight' ? [] : ['--run'])],{ timeout:15000 });
    const result = await completed; console.log(JSON.stringify({ mode, outputDirectory:dir, ...result }));
    if (result.status !== 'pass' && !(mode === 'preflight' && result.status === 'complete')) process.exitCode = 1;
  } catch (error) { if (watcher) watcher.close(); if (timer) clearTimeout(timer); throw error; }
}
main().catch(error => { console.error(error.message); process.exitCode=1; });
