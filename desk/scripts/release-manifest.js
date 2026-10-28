#!/usr/bin/env node
'use strict';
// Writes dist/latest.json for the in-app updater from the zips in dist/ and the version in package.json.
//   node scripts/release-manifest.js "What changed, in one plain sentence."
// Release steps (see docs/UPDATES.md): bump "version" in package.json, build the zips, run this, commit dist/*.zip + dist/latest.json, merge.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const dist = path.join(__dirname, '..', 'dist');
const version = require('../package.json').version;
const RAW = 'https://github.com/BenjaminHannan/learner/raw/main/desk/dist/';
function entry(name) {
  const f = path.join(dist, name);
  if (!fs.existsSync(f)) return undefined;
  const buf = fs.readFileSync(f); // a Git LFS pointer file is ~130 bytes: refuse it, the real zip is needed to hash
  if (buf.length < 1e6) throw new Error(name + ' is ' + buf.length + ' bytes: this looks like a Git LFS pointer, run `git lfs pull` first.');
  return { url: RAW + name, sha256: crypto.createHash('sha256').update(buf).digest('hex'), size: buf.length };
}
const m = { version, notes: process.argv.slice(2).join(' ').slice(0, 300), mac: entry('Premonition-mac-arm64.zip'), win: entry('Premonition-win32-x64.zip') };
if (!m.mac && !m.win) throw new Error('no zips in dist/');
fs.writeFileSync(path.join(dist, 'latest.json'), JSON.stringify(m, null, 2) + '\n');
console.log('wrote dist/latest.json for version ' + version);
