'use strict';
const fs = require('node:fs'), path = require('node:path'), net = require('node:net');
const { execFileSync } = require('node:child_process');
const base = __dirname, socket = path.join(base, 'premonition-recorder.sock');
const command = process.argv[2] || 'status';
const allowed = ['start', 'stop', 'status', 'preflight', 'permissions', 'canary', 'canary-permissions', 'scratch-benchmark'];
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
function send(request) {
  return new Promise((resolve, reject) => {
    const client = net.createConnection(socket); let data = '';
    client.setTimeout(25000, () => client.destroy(Error('Recorder response timeout')));
    client.once('connect', () => client.write(JSON.stringify(request) + '\n'));
    client.on('data', bytes => { data += bytes; });
    client.once('error', reject);
    client.once('end', () => { try { const r = JSON.parse(data); if (r.error) reject(Error(r.error)); else resolve(r.result); } catch (e) { reject(e); } });
  });
}
async function main() {
  if (!allowed.includes(command)) throw Error('Use: recorderctl preflight | permissions | canary-permissions | canary | start [--fake] | stop | status');
  if (command === 'stop') fs.writeFileSync(path.join(base, 'state.json'), JSON.stringify({ enabled: false }), { mode: 0o600 });
  try { return await send({ command, fake: process.argv.includes('--fake'), benConfirmedAway: process.argv.includes('--ben-confirmed-away') }); }
  catch (error) {
    if (!['ENOENT', 'ECONNREFUSED'].includes(error.code)) throw error;
    if (command === 'stop' || command === 'status') return { enabled: false, stopped: true };
    // Stale socket only. A connected socket or a response error is never replaced.
    if (fs.existsSync(socket)) fs.unlinkSync(socket);
    const env = { ...process.env };
    delete env.ELECTRON_RUN_AS_NODE;
    execFileSync('/usr/bin/open', ['-n', '-g', '/Applications/Premonition.app', '--args', '--glim-recorder-host'], { env });
    for (let n = 0; n < 80; n++) {
      await wait(100);
      try { return await send({ command, fake: process.argv.includes('--fake'), benConfirmedAway: process.argv.includes('--ben-confirmed-away') }); }
      catch (e) { if (!['ENOENT', 'ECONNREFUSED'].includes(e.code)) throw e; }
    }
    throw Error('Premonition recorder role did not start');
  }
}
main().then(result => { console.log(JSON.stringify(result)); }).catch(error => { console.error(error.message); process.exitCode = 1; });
