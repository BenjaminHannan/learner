// Builds content.js from content/global.json + content/chNN.json (one JSON object per chapter).
//   node tools/merge.mjs
// Order comes from content/global.json "order" (only chapters whose json exists are included). --example: only examples/ch99.json (the kit demo).
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const dir = path.join(root, 'content');
const global = JSON.parse(fs.readFileSync(path.join(dir, 'global.json'), 'utf8'));
const chapters = {};
const order = [];
if (process.argv.includes('--example')) global.order = ['ch99'];
for (const cid of global.order) {
  if (cid === 'ch99') { const ef = path.join(root, 'examples', 'ch99.json'); chapters.ch99 = JSON.parse(fs.readFileSync(ef, 'utf8')); order.push('ch99'); continue; }
  const f = path.join(dir, cid + '.json');
  if (fs.existsSync(f)) { chapters[cid] = JSON.parse(fs.readFileSync(f, 'utf8')); order.push(cid); }
}
const { order: _o, ...g } = global;
const out = { global: g, order, chapters };
fs.writeFileSync(path.join(root, 'content.js'), 'window.CONTENT = ' + JSON.stringify(out, null, 2) + ';\n');
console.log('content.js written:', order.join(', '));
