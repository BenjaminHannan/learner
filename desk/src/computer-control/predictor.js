'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { createHash } = require('node:crypto');
const { spawn } = require('node:child_process');

// Toy weights are not promoted by this code. Until an approved, hash-checked
// artifact exists, return no proposal and let Glim choose the coordinates.
async function propose({ shot, intent, action }) {
  const root = path.join(os.homedir(), 'learner-ops', 'hands-policy');
  const manifestPath = path.join(root, 'current.json'), model = path.join(root, 'current.ts');
  let manifest, hash;
  try {
    manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    if (manifest.approved !== true || !/^[0-9a-f]{64}$/.test(manifest.sha256 || '') || fs.statSync(model).size > 100_000_000) return null;
    hash = createHash('sha256').update(fs.readFileSync(model)).digest('hex');
  } catch (_) { return null; }
  if (manifest.sha256 !== hash || !shot.cursor || shot.cursor.some(n => !Number.isFinite(n) || n < 0 || n > 1)) return null;
  const python = path.join(os.homedir(), 'learner-ops', 'nb2-venv', 'bin', 'python');
  return new Promise(resolve => {
    let child; try { child = spawn(python, [path.join(__dirname, 'predictor.py')], { stdio:['pipe','pipe','ignore'], env:{ ...process.env, OMP_NUM_THREADS:'1', CUDA_VISIBLE_DEVICES:'' } }); } catch (_) { return resolve(null); }
    let output = '', settled = false;
    const done = value => { if (settled) return; settled = true; clearTimeout(timer); resolve(value); };
    const timer = setTimeout(() => { child.kill(); done(null); }, 5000);
    child.once('error', () => done(null));
    child.stdout.on('data', data => { output += data; if (output.length > 4096) { child.kill(); done(null); } });
    child.once('close', code => {
      if (code !== 0) return done(null);
      try {
        const v = JSON.parse(output); if (!Number.isFinite(v.dx) || !Number.isFinite(v.dy)) return done(null);
        if (createHash('sha256').update(fs.readFileSync(model)).digest('hex') !== hash) return done(null);
        const x = shot.bounds.x + (shot.cursor[0] + v.dx / 320) * shot.bounds.width;
        const y = shot.bounds.y + (shot.cursor[1] + v.dy / 180) * shot.bounds.height;
        return done({ action:{ ...action, x, y }, modelSha256:hash, note:'Toy policy sees pixels and the action category; it does not understand the target words. Glim must check the proposed point.' });
      } catch (_) { return done(null); }
    });
    child.stdin.on('error', () => done(null));
    child.stdin.end(JSON.stringify({ model, png:shot.image.split(',')[1], cursor:shot.cursor, action:action.type, intent }));
  });
}
module.exports = { propose };
