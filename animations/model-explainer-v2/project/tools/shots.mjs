// One-frame review sheets for a chapter. Usage (from the project folder):
//   node tools/shots.mjs ch03            4 frames per scene, contact sheets in snapshots/ch03/
//   node tools/shots.mjs ch03 s05        only scene s05
//   node tools/shots.mjs ch03 --per 6    6 frames per scene
//   node tools/shots.mjs --demo          the kit demo chapter
// It runs merge + mkindex --only <chapter> first, so you always look at your latest files.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { spawnSync } from 'node:child_process';
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const args = process.argv.slice(2);
const demo = args.includes('--demo');
const perIdx = args.indexOf('--per');
const per = perIdx >= 0 ? Number(args[perIdx + 1]) : 4;
const pos = args.filter((a, i) => !a.startsWith('--') && !(perIdx >= 0 && i === perIdx + 1));
const cid = demo ? 'ch99' : pos[0];
const only = demo ? null : pos[1];
if (!cid) { console.error('usage: node tools/shots.mjs chNN [sceneId] [--per N]'); process.exit(1); }
const run = (cmd, a) => { const r = spawnSync(cmd, a, { cwd: root, stdio: 'inherit' }); if (r.status !== 0) { console.error('failed:', cmd, a.join(' ')); process.exit(1); } };
if (demo) { run('node', ['tools/merge.mjs', '--example']); run('node', ['tools/mkindex.mjs', '--demo', '--only', 'ch99']); }
else { run('node', ['tools/merge.mjs']); run('node', ['tools/mkindex.mjs', '--only', cid]); }
const win = {};
vm.runInNewContext(fs.readFileSync(path.join(root, 'content.js'), 'utf8'), { window: win });
const ch = win.CONTENT.chapters[cid];
if (!ch) { console.error('no content for', cid); process.exit(1); }
let t = ch.card === false ? 0 : (win.CONTENT.global.cardSeconds || 5);
const times = [], labels = [];
for (const s of ch.scenes) {
  if (!only || only === s.id) {
    const fr = per === 1 ? [0.9] : Array.from({ length: per }, (_, i) => 0.18 + (0.8 - 0.18) * (i / (per - 1)));
    fr.forEach((f) => { const tt = Math.min(t + s.duration - 0.6, t + Math.max(1.2, s.duration * f)); times.push(+tt.toFixed(2)); labels.push(`${s.id} @${tt.toFixed(1)}s`); });
  }
  t += s.duration;
}
const out = path.join(root, 'snapshots', cid);
fs.rmSync(out, { recursive: true, force: true }); fs.mkdirSync(out, { recursive: true });
run('npx', ['--yes', 'hyperframes@0.8.143', 'snapshot', '--no-end', '--at', times.join(','), '-o', out, '.']);
const pngs = fs.readdirSync(out).filter((f) => f.endsWith('.png')).sort();
const perSheet = 6;
for (let i = 0; i < pngs.length; i += perSheet) {
  const chunk = pngs.slice(i, i + perSheet).map((f) => path.join(out, f));
  const lab = labels.slice(i, i + perSheet);
  const sheet = path.join(out, `sheet-${String(i / perSheet + 1).padStart(2, '0')}.jpg`);
  const m = ['-background', '#222', '-fill', 'white', '-pointsize', '28'];
  const items = chunk.flatMap((f, k) => ['-label', lab[k] || '', f]);
  const r = spawnSync('montage', [...m, ...items, '-tile', '2x3', '-geometry', '960x540+8+8', sheet], { cwd: root });
  if (r.status !== 0) console.error('montage failed', String(r.stderr));
  else console.log('sheet:', sheet);
}
console.log(`${pngs.length} frames; single frames are in ${out}`);
