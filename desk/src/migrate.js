'use strict';
// The app was renamed (Premonition Desk -> Premonition), and Electron's userData folder is named after the app, so the
// new folder starts empty. Before 'ready': if the new folder has no settings.json and an old folder does, copy the old one
// over ONCE (the old folder stays as a backup) and leave a marker so it never happens twice.
const fs = require('fs');
const path = require('path');

const OLD_NAMES = ['Premonition Desk', 'premonition-desk'];
const MARKER = 'migrated-from-old-name.txt';
const has = (p) => { try { return fs.statSync(p).isFile(); } catch (e) { return false; } };
const isDir = (p) => { try { return fs.statSync(p).isDirectory(); } catch (e) { return false; } };

// appData: the parent of userData (app.getPath('appData')); newDir: the new userData path.
function migrateUserData(appData, newDir, oldNames) {
  try {
    if (has(path.join(newDir, 'settings.json')) || has(path.join(newDir, MARKER))) return { migrated: false, reason: 'already set up' };
    for (const n of oldNames || OLD_NAMES) {
      const old = path.join(appData, n);
      if (path.resolve(old) === path.resolve(newDir) || !isDir(old)) continue;
      if (!has(path.join(old, 'settings.json')) && !isDir(path.join(old, 'threads'))) continue;
      fs.mkdirSync(newDir, { recursive: true });
      // skip Chromium's caches and locks: only our own data (settings, threads, memory, helpers, ...) matters
      const skip = new Set(['Cache', 'Code Cache', 'GPUCache', 'DawnCache', 'Crashpad', 'SingletonLock', 'SingletonCookie', 'SingletonSocket', 'lockfile']);
      fs.cpSync(old, newDir, { recursive: true, force: false, filter: (src) => !skip.has(path.basename(src)) });
      fs.writeFileSync(path.join(newDir, MARKER), 'Copied from ' + old + ' on ' + new Date().toISOString() + '. The old folder was left in place as a backup.\n');
      return { migrated: true, from: old };
    }
  } catch (e) { return { migrated: false, error: String(e && e.message || e) }; }
  return { migrated: false, reason: 'nothing to migrate' };
}

module.exports = { migrateUserData, OLD_NAMES, MARKER };
