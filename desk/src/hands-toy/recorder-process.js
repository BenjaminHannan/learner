'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const MAX_BYTES = 64 * 1024 * 1024;
const MAX_MS = 5000;

function identity(stat) {
  if (!stat.isFile() || stat.size <= 0n || stat.size > BigInt(MAX_BYTES) || (stat.mode & 0o111n) === 0n) throw Error('invalid executable');
  return [stat.dev, stat.ino, stat.mode, stat.size, stat.mtimeNs, stat.ctimeNs].map(String).join(':');
}

function current(command) {
  const link = fs.lstatSync(command, { bigint: true });
  if (link.isSymbolicLink()) throw Error('symbolic executable');
  return identity(link);
}

async function snapshot(command) {
  const before = current(command);
  const hash = crypto.createHash('sha256');
  let bytes = 0;
  await new Promise((resolve, reject) => {
    const stream = fs.createReadStream(command, { highWaterMark: 256 * 1024 });
    const timer = setTimeout(() => stream.destroy(Error('executable hash timeout')), MAX_MS);
    stream.on('data', chunk => {
      bytes += chunk.length;
      if (bytes > MAX_BYTES) stream.destroy(Error('executable size limit'));
      else hash.update(chunk);
    });
    stream.once('error', error => { clearTimeout(timer); reject(error); });
    stream.once('end', () => { clearTimeout(timer); resolve(); });
  });
  if (current(command) !== before || bytes !== Number(before.split(':')[3])) throw Error('executable changed');
  return { file: before, sha256: hash.digest('hex') };
}

function copy(value, depth = 0, budget = { remaining: 4096 }) {
  if (depth > 8 || --budget.remaining < 0) throw Error('options limit');
  if (value === null || ['string', 'boolean', 'number', 'undefined'].includes(typeof value)) return value;
  if (Array.isArray(value)) {
    if (value.length > 256) throw Error('options size limit');
    const result = [];
    for (let index = 0; index < value.length; index++) {
      const descriptor = Object.getOwnPropertyDescriptor(value, index);
      if (!descriptor || !('value' in descriptor)) throw Error('unsupported option');
      result.push(copy(descriptor.value, depth + 1, budget));
    }
    return Object.freeze(result);
  }
  if (typeof value !== 'object' || Object.getPrototypeOf(value) !== Object.prototype) throw Error('unsupported option');
  const keys = Object.keys(value);
  if (keys.length > 256) throw Error('options size limit');
  const result = Object.create(null);
  for (const key of keys) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (!descriptor || !('value' in descriptor)) throw Error('unsupported option');
    Object.defineProperty(result, key, { value: copy(descriptor.value, depth + 1, budget), enumerable: true });
  }
  return Object.freeze(result);
}

async function prepare(command) {
  if (typeof command !== 'string' || !path.isAbsolute(command) || command.length > 4096 || command.includes('\0')) throw Error('invalid command');
  const prepared = await snapshot(command);
  return Object.freeze({
    launch(spawn, args, options = {}) {
      if (typeof spawn !== 'function' || !Array.isArray(args) || args.length > 128) throw Error('invalid launch');
      const copiedArgs = [];
      for (let index = 0; index < args.length; index++) {
        const descriptor = Object.getOwnPropertyDescriptor(args, index);
        if (!descriptor || !('value' in descriptor) || typeof descriptor.value !== 'string' || descriptor.value.length > 4096 || descriptor.value.includes('\0')) throw Error('invalid launch');
        copiedArgs.push(descriptor.value);
      }
      Object.freeze(copiedArgs);
      const copiedOptions = copy(options);
      const direct = (copiedOptions.shell === undefined || copiedOptions.shell === false) && (copiedOptions.argv0 === undefined || copiedOptions.argv0 === command);
      let valid = false;
      try { valid = direct && current(command) === prepared.file; } catch {}
      const child = spawn(command, copiedArgs, copiedOptions);
      try { valid = valid && current(command) === prepared.file; } catch { valid = false; }
      let pid = null, spawned = false, exited = false, closed = false, failed = !valid, exitCode, exitSignal;
      const observedPid = () => Number.isSafeInteger(child.pid) && child.pid > 0 ? child.pid : null;
      if (!child || typeof child.on !== 'function') throw Error('invalid child');
      child.on('spawn', () => { if (spawned || !(pid = observedPid())) failed = true; spawned = true; });
      child.on('error', () => { failed = true; });
      child.on('exit', (code, signal) => {
        if (!spawned || exited || observedPid() !== pid) failed = true;
        exited = true; exitCode = code; exitSignal = signal;
      });
      child.on('close', (code, signal) => {
        if (!spawned || !exited || closed || observedPid() !== pid || code !== exitCode || signal !== exitSignal) failed = true;
        closed = true;
      });
      return Object.freeze({ child, async evidence() {
        if (failed || !spawned || !exited || !closed || observedPid() !== pid || exitCode !== 0 || exitSignal !== null) return null;
        try {
          const after = await snapshot(command);
          if (failed || observedPid() !== pid || after.file !== prepared.file || after.sha256 !== prepared.sha256) return null;
          return { pid, command, args: [...copiedArgs], sha256: prepared.sha256, ownedLaunch: true, exitCode: 0, signal: null, closeObserved: true };
        } catch { return null; }
      } });
    }
  });
}

module.exports = { prepare, MAX_BYTES, MAX_MS };
