'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');

const GiB = 1024 ** 3;
const MAX_CAPS = Object.freeze({ total: 12 * GiB, daily: 3 * GiB, keep: 2 * GiB, minFree: 10 * GiB, ageMs: 7 * 86400000 });
const GUIDANCE = Object.freeze([
  'If you say Yes, open System Settings → Privacy & Security.',
  'In Screen & System Audio Recording and Input Monitoring, turn on Premonition (the app named Glim). No sound is recorded.',
  'If your Mac asks, quit Premonition and open it again. Giving Mac permission alone does not turn recording on.',
  'Pictures can show private things on your screen. Turn recording off before opening anything you do not want saved.'
]);

function diskCaps(freeBytes) {
  const available = Number.isFinite(freeBytes) && freeBytes >= 0 ? freeBytes : 0;
  const total = Math.min(MAX_CAPS.total, Math.floor(Math.max(0, available - MAX_CAPS.minFree) / 5));
  return { ...MAX_CAPS, total, daily: Math.floor(total / 4), keep: Math.floor(total / 6) };
}

class RecorderSetup {
  constructor(root, { freeBytes, clock = Date.now } = {}) {
    this.root = root;
    this.file = path.join(root, 'recorder-consent.json');
    this.clock = clock;
    this.freeBytes = freeBytes || (() => { const disk = fs.statfsSync(root); return Number(disk.bavail) * Number(disk.bsize); });
  }
  choice() {
    try {
      if (!fs.lstatSync(this.file).isFile()) return null;
      const saved = JSON.parse(fs.readFileSync(this.file, 'utf8'));
      return saved.version === 1 && typeof saved.choice === 'boolean' ? saved.choice : null;
    } catch (_) { return null; }
  }
  status() {
    let free = 0;
    try { free = this.freeBytes(); } catch (_) {}
    return { choice: this.choice(), enabled: false, available: false, caps: diskCaps(free), guidance: [...GUIDANCE] };
  }
  choose(choice) {
    if (typeof choice !== 'boolean') throw Error('Please choose Yes or No.');
    fs.mkdirSync(this.root, { recursive: true, mode: 0o700 });
    try { if (!fs.lstatSync(this.file).isFile()) throw Error('The recording choice file is not safe.'); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
    const temporaryPath = this.file + '.' + randomUUID() + '.tmp';
    try {
      const temporary = fs.openSync(temporaryPath, 'wx', 0o600);
      try { fs.writeFileSync(temporary, JSON.stringify({ version: 1, choice, enabled: false, chosenAt: this.clock() }) + '\n'); }
      finally { fs.closeSync(temporary); }
      fs.renameSync(temporaryPath, this.file);
    } finally { if (fs.existsSync(temporaryPath)) fs.unlinkSync(temporaryPath); }
    return this.status();
  }
}

module.exports = { RecorderSetup, diskCaps, MAX_CAPS, GUIDANCE, GiB };
