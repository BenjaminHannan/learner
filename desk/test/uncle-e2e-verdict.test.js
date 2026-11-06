'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { compareApps } = require('../tools/uncle-mac/compare-apps');
const required = ['download', 'resume', 'ready', 'bundled-engine', 'name', 'arithmetic', 'restart', 'restart-name', 'remembered-fact', 'measure-Q4_K_M', 'measure-IQ3_M'];

function fixture(context) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'uncle-verdict-'));
  context.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const directory = path.join(root, 'test');
  fs.mkdirSync(directory);
  fs.copyFileSync(path.join(__dirname, '../tools/uncle-mac/verdict.js'), path.join(directory, 'verdict.js'));
  const bytes = Buffer.from('synthetic disk image, not a real package');
  fs.writeFileSync(path.join(root, 'Glim-2.0.0-mac.dmg'), bytes);
  fs.writeFileSync(path.join(directory, 'dmg-under-test.sha256'), crypto.createHash('sha256').update(bytes).digest('hex'));
  const marks = names => fs.writeFileSync(path.join(directory, 'marks.jsonl'), names.map(mark => JSON.stringify({ mark, pass: true })).join('\n'));
  marks(required);
  return { root, directory, marks, run: () => spawnSync(process.execPath, [path.join(directory, 'verdict.js')], { encoding: 'utf8' }) };
}

test('complete synthetic marks produce a checked verdict', context => {
  const { directory, run } = fixture(context);
  assert.equal(run().status, 0);
  assert.equal(JSON.parse(fs.readFileSync(path.join(directory, 'results.json'))).pass, true);
});

test('a missing pass or changed image cannot become a pass', context => {
  const { directory, marks, run } = fixture(context);
  marks(required.filter(mark => mark !== 'remembered-fact'));
  assert.notEqual(run().status, 0);
  assert.equal(fs.existsSync(path.join(directory, 'results.json')), false);
  marks(required);
  fs.writeFileSync(path.join(directory, 'dmg-under-test.sha256'), 'wrong hash');
  assert.notEqual(run().status, 0);
  assert.equal(fs.existsSync(path.join(directory, 'results.json')), false);
});

test('a recorder package also requires the off, No and restart checks', context => {
  const { root, marks, run } = fixture(context);
  const source = path.join(root, 'test-home/Applications/Premonition.app/Contents/Resources/app/src');
  fs.mkdirSync(source, { recursive: true });
  fs.writeFileSync(path.join(source, 'recorder-setup.js'), 'synthetic setup');
  assert.notEqual(run().status, 0);
  marks([...required, 'recorder-default-off', 'recorder-no', 'recorder-restart-off']);
  assert.equal(run().status, 0);
});

test('package comparison checks bytes and links without following framework loops', async context => {
  const { root } = fixture(context);
  const expected = path.join(root, 'image-app'), actual = path.join(root, 'test-app');
  for (const directory of [expected, actual]) {
    fs.mkdirSync(directory);
    fs.writeFileSync(path.join(directory, 'engine'), 'synthetic engine');
    fs.symlinkSync('.', path.join(directory, 'framework-loop'));
  }
  assert.equal((await compareApps(expected, actual)).pass, true);
  fs.writeFileSync(path.join(actual, 'engine'), 'changed engine');
  await assert.rejects(compareApps(expected, actual), /does not match/);
  fs.writeFileSync(path.join(actual, 'engine'), 'synthetic engine');
  fs.unlinkSync(path.join(actual, 'framework-loop'));
  fs.symlinkSync('engine', path.join(actual, 'framework-loop'));
  await assert.rejects(compareApps(expected, actual), /does not match/);
});
