// Pull finished chapters from the authors' delivery folder into this project, then merge + index + audit.
//   node tools/assemble.mjs                       all chapters found in chapters-out
//   node tools/assemble.mjs ch01 ch03             only these
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const out = '/mnt/project-files/animations/model-explainer-build/chapters-out';
const want = process.argv.slice(2);
const ids = fs.readdirSync(out).filter((d) => /^ch\d+$/.test(d) && (!want.length || want.includes(d))).sort();
fs.mkdirSync(path.join(root, 'content'), { recursive: true }); fs.mkdirSync(path.join(root, 'chapters'), { recursive: true });
let n = 0;
for (const id of ids) {
  const j = path.join(out, id, id + '.json'), s = path.join(out, id, id + '.js');
  if (!fs.existsSync(j) || !fs.existsSync(s)) { console.log('skip (not delivered):', id); continue; }
  fs.copyFileSync(j, path.join(root, 'content', id + '.json'));
  fs.copyFileSync(s, path.join(root, 'chapters', id + '.js'));
  n++;
}
console.log('copied', n, 'chapters');
for (const [c, a] of [['node', ['tools/merge.mjs']], ['node', ['tools/mkindex.mjs']], ['node', ['tools/audit.mjs']]]) spawnSync(c, a, { cwd: root, stdio: 'inherit' });
