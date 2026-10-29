#!/usr/bin/env node
'use strict';
// Generate the updater feed only after the archives are committed. The feed may
// be committed later: its URLs name the immutable artifact commit, not main.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');
const desk = path.join(__dirname, '..');
const dist = path.join(desk, 'dist');
const localVersion = require('../package.json').version;
const gitEnv = { ...process.env, GIT_NO_LAZY_FETCH: '1', GIT_TERMINAL_PROMPT: '0' };
function git(cwd, ...args) {
  return execFileSync('git', args, { cwd, env: gitEnv, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
}
const root = git(desk, 'rev-parse', '--show-toplevel');
const commit = git(root, 'rev-parse', '--verify', 'HEAD^{commit}');
if (!/^(?:[0-9a-f]{40}|[0-9a-f]{64})$/.test(commit)) throw new Error('HEAD did not resolve to a full commit');
const version = JSON.parse(git(root, 'show', commit + ':desk/package.json')).version;
if (typeof version !== 'string' || !version || localVersion !== version) throw new Error('Local package version does not match the artifact commit');
const objectFormat = git(root, 'rev-parse', '--show-object-format');
if (!['sha1', 'sha256'].includes(objectFormat)) throw new Error('Unsupported Git object format');
const RAW = 'https://github.com/BenjaminHannan/learner/raw/' + commit + '/desk/dist/';
function entry(name) {
  const f = path.join(dist, name);
  if (!fs.existsSync(f)) return undefined;
  const st = fs.statSync(f);
  if (!st.isFile() || st.size < 1e6) throw new Error(name + ' is missing or too small: the real zip, not an LFS pointer, is required.');
  const rel = 'desk/dist/' + name;
  const tree = git(root, 'ls-tree', commit, '--', rel);
  const match = /^(100644|100755) blob ([0-9a-f]+)\t([^\n]+)$/.exec(tree);
  if (!match || match[3] !== rel) throw new Error(name + ' is not committed at ' + commit);
  const oid = match[2];
  const bytes = Number(git(root, 'cat-file', '-s', oid));
  if (!Number.isSafeInteger(bytes) || bytes < 0) throw new Error('Invalid Git blob size for ' + name);
  const sha = crypto.createHash('sha256');
  const blob = crypto.createHash(objectFormat).update('blob ' + st.size + '\0');
  const fd = fs.openSync(f, 'r'), buffer = Buffer.allocUnsafe(1024 * 1024);
  try {
    let n;
    while ((n = fs.readSync(fd, buffer, 0, buffer.length, null)) > 0) { sha.update(buffer.subarray(0, n)); blob.update(buffer.subarray(0, n)); }
    const after = fs.fstatSync(fd);
    if (after.size !== st.size || after.mtimeMs !== st.mtimeMs || after.ino !== st.ino || after.dev !== st.dev) throw new Error(name + ' changed while hashing');
  } finally { fs.closeSync(fd); }
  const digest = sha.digest('hex'), blobOid = blob.digest('hex');
  if (bytes < 1024) {
    const pointer = git(root, 'cat-file', 'blob', oid);
    const lfs = /^version https:\/\/git-lfs\.github\.com\/spec\/v1\noid sha256:([0-9a-f]{64})\nsize ([0-9]+)$/.exec(pointer);
    if (!lfs || lfs[1] !== digest || Number(lfs[2]) !== st.size) throw new Error(name + ' does not match its committed LFS pointer');
  } else if (bytes !== st.size || blobOid !== oid) throw new Error(name + ' does not match its committed Git blob');
  return { url: RAW + name, sha256: digest, size: st.size };
}
const m = { version, notes: process.argv.slice(2).join(' ').slice(0, 300), mac: entry('Premonition-mac-arm64.zip'), win: entry('Premonition-win32-x64.zip') };
if (!m.mac && !m.win) throw new Error('no zips in dist/');
fs.writeFileSync(path.join(dist, 'latest.json'), JSON.stringify(m, null, 2) + '\n');
console.log('wrote dist/latest.json for version ' + version + ' using artifact commit ' + commit);
