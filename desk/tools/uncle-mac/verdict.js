'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
async function main() {
const marks = fs.readFileSync(path.join(__dirname, 'marks.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
const required = ['download', 'resume', 'ready', 'bundled-engine', 'name', 'arithmetic', 'restart', 'restart-name', 'remembered-fact', 'measure-Q4_K_M', 'measure-IQ3_M'];
const app = path.resolve(__dirname, '../test-home/Applications/Premonition.app/Contents/Resources/app');
if (fs.existsSync(path.join(app, 'src/recorder-setup.js'))) required.push('recorder-default-off', 'recorder-no', 'recorder-restart-off');
for (const mark of required) if (!marks.some(row => row.mark === mark && row.pass === true)) throw Error('Missing pass: ' + mark);
const dmg = path.resolve(__dirname, '../Glim-2.0.0-mac.dmg');
const hash = crypto.createHash('sha256');
for await (const chunk of fs.createReadStream(dmg)) hash.update(chunk);
const sha256 = hash.digest('hex');
if (sha256 !== fs.readFileSync(path.join(__dirname, 'dmg-under-test.sha256'), 'utf8').trim()) throw Error('Image changed during the test');
const result = { pass: true, checkedAt: new Date().toISOString(), dmg, bytes: fs.statSync(dmg).size, sha256, required, marks };
fs.writeFileSync(path.join(__dirname, 'results.json'), JSON.stringify(result, null, 2) + '\n');
console.log('PASS: all required e2e and measurement marks');
fs.appendFileSync(path.resolve(__dirname, '../REPORT-S.md'), '\n## Runner finished — ' + result.checkedAt + '\n\nThe first-run checks and both brain checks passed. This does not mean the recorder is ready. Ben must still wait for the lead to check both sharing gates.\n\n- Image SHA-256: `' + sha256 + '`\n- Checked marks: ' + required.join(', ') + '\n- Full result: `test/results.json`\n');
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
