// Generates index.html (and only.js) from content.js + the chapter files.
//   node tools/mkindex.mjs                 full video: every chapters/chNN*.js
//   node tools/mkindex.mjs --only ch03     one chapter (for your own working copy)
//   node tools/mkindex.mjs --demo          the kit demo chapter
// The root data-duration is computed here from content.js, so re-run it after changing any scene length.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const argv = process.argv.slice(2);
const demo = argv.includes('--demo');
const onlyIdx = argv.indexOf('--only');
const only = onlyIdx >= 0 ? argv.slice(onlyIdx + 1).filter((a) => !a.startsWith('--')) : [];

const win = {};
vm.runInNewContext(fs.readFileSync(path.join(root, 'content.js'), 'utf8'), { window: win });
const CT = win.CONTENT;
const G = CT.global || {};
const order = only.length ? only : CT.order;
let total = 0;
for (const cid of order) {
  const ch = CT.chapters[cid];
  if (!ch) { console.error('missing content for', cid); process.exit(1); }
  if (ch.card !== false) total += G.cardSeconds || 5;
  for (const s of ch.scenes || []) total += s.duration;
}
if (!only.length && G.endCard) total += G.endCard.duration || 8;

let files;
if (demo) files = ['examples/ch99-demo.js'];
else if (only.length) files = only.map((c) => fs.readdirSync(path.join(root, 'chapters')).filter((f) => f.startsWith(c + '.') || f.startsWith(c + '-') || f.startsWith(c + '_')).map((f) => 'chapters/' + f)).flat();
else files = fs.readdirSync(path.join(root, 'chapters')).filter((f) => /^ch\d+.*\.js$/.test(f)).sort().map((f) => 'chapters/' + f);

fs.writeFileSync(path.join(root, 'only.js'), `window.ONLY = ${JSON.stringify(only)};\n`);
const html = `<!doctype html>
<html lang="en" data-resolution="landscape">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <link rel="stylesheet" href="style.css" />
    <script src="vendor/gsap.min.js"></script>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="${total.toFixed(2)}" data-width="1920" data-height="1080"></div>
    <script src="content.js"></script>
    <script src="kit.js"></script>
${files.map((f) => `    <script src="${f}"></script>`).join('\n')}
    <script src="only.js"></script>
    <script src="main.js"></script>
    <script>
      window.__timelines = window.__timelines || {};
      window.__timelines["main"] = window.__buildMain();
      window.__timelines["main"].seek(0);
    </script>
  </body>
</html>
`;
fs.writeFileSync(path.join(root, 'index.html'), html);
console.log(`index.html written: ${files.length} chapter file(s), ${total.toFixed(1)} s`);
