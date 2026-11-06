'use strict';
// Installed Premonition role; fake source only, no TCC prompts or real input.
const fs = require('node:fs'), path = require('node:path'), os = require('node:os');
const { execFileSync } = require('node:child_process');
const base = path.join(os.homedir(), 'learner-ops/hands-recorder');
const ctl = (...args) => JSON.parse(execFileSync(path.join(base, 'recorderctl'), args, { encoding: 'utf8' }));
async function main() {
  const preflight = ctl('preflight');
  if (preflight.responsibleBundleId !== 'com.electron.premonition-desk') throw Error('Wrong Privacy identity');
  if (ctl('status').enabled) throw Error('Expected OFF');
  let denied = false;
  try { ctl('start'); } catch (e) { denied = true; }
  if (!denied) throw Error('Real start bypassed lead release');
  const active = ctl('start', '--fake');
  await new Promise(resolve => setTimeout(resolve, 2500));
  const stop = ctl('stop');
  let alive = true;
  for (let n = 0; n < 40; n++) {
    try { process.kill(active.hostPid, 0); } catch (e) { if (e.code === 'ESRCH') { alive = false; break; } throw e; }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  const status = ctl('status');
  if (alive || status.enabled || !stop.stopped) throw Error('Stop failed');
  ctl('preflight'); // A fresh host checks permissions but must never resume capture.
  if (ctl('status').enabled) throw Error('Auto-resumed after OFF');
  ctl('stop');
  const result = { at: new Date().toISOString(), stopPassed: true, autoResume: false, realStartDenied: denied,
    privacyName: preflight.responsibleName, privacyBundle: preflight.responsibleBundleId, exactHostPid: active.hostPid };
  fs.writeFileSync(path.join(base, 'STOP-TEST.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
