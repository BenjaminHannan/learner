'use strict';
const fs = require('node:fs'), path = require('node:path');
function verifyCanary(root, additionalRoots = []) {
  const result = JSON.parse(fs.readFileSync(path.join(root, 'result.json')));
  let count = 0; const hits = [], searchedFiles = [];
  function walk(dir) {
    if (!fs.existsSync(dir)) return;
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, entry.name);
      if (entry.isSymbolicLink()) throw Error('Unexpected canary file symlink');
      if (entry.isDirectory()) walk(p);
      else if (entry.isFile()) {
        count++; searchedFiles.push(p);
        if (fs.readFileSync(p).includes(Buffer.from('HandsFakePass7x93'))) hits.push(p);
      }
    }
  }
  for (const dir of [root, ...additionalRoots]) walk(dir);
  const pass = result.status === 'PASS' && result.normalControl && result.secureCanaryTyped && hits.length === 0;
  const report = { status: pass ? 'PASS' : 'INCOMPLETE/FAIL', native: result, savedFilesSearched: count, searchedRoots: [root, ...additionalRoots], searchedFiles, hits };
  fs.writeFileSync(path.join(root, 'verified.json'), JSON.stringify(report, null, 2), { mode: 0o600 });
  return report;
}
module.exports = { verifyCanary };
if (require.main === module) {
  const report = verifyCanary(process.argv[2]);
  console.log(JSON.stringify(report));
  if (report.status !== 'PASS') process.exitCode = 1;
}
