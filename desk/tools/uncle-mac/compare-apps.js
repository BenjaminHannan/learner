'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

async function manifest(root) {
  const entries = [];
  async function visit(relative) {
    const file = path.join(root, relative), stat = fs.lstatSync(file);
    if (stat.isSymbolicLink()) entries.push([relative, 'link', fs.readlinkSync(file)]);
    else if (stat.isDirectory()) {
      entries.push([relative, 'directory']);
      for (const name of fs.readdirSync(file).sort()) await visit(path.join(relative, name));
    } else if (stat.isFile()) {
      const hash = crypto.createHash('sha256');
      for await (const chunk of fs.createReadStream(file)) hash.update(chunk);
      entries.push([relative, 'file', stat.mode & 0o111, stat.size, hash.digest('hex')]);
    } else throw Error('Unsupported package entry: ' + relative);
  }
  await visit('');
  return entries;
}

async function compareApps(imageApp, testApp) {
  const expected = await manifest(imageApp), actual = await manifest(testApp);
  if (JSON.stringify(expected) !== JSON.stringify(actual)) throw Error('Test app does not match the mounted image app.');
  return { pass: true, entries: expected.length };
}

if (require.main === module) compareApps(...process.argv.slice(2)).then(result => console.log(JSON.stringify(result))).catch(error => { console.error(error.message); process.exitCode = 1; });
module.exports = { compareApps };
