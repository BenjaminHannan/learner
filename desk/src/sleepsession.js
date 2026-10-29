'use strict';
const fs = require('fs');
const path = require('path');

// The trainer outlives the desktop. Keep the user's deadline and model-restoration
// obligation on disk, and only reuse them for the same backend run.
function save(file, session) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = file + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify({ version: 1, ...session }) + '\n');
  fs.renameSync(tmp, file);
}
function read(file) {
  try {
    const s = JSON.parse(fs.readFileSync(file, 'utf8'));
    return s.version === 1 && Number.isFinite(s.startedAt) ? s : null;
  } catch (e) { return null; }
}
function reconcile(session, backend) {
  if (!session) return null;
  // A stopped run still needs the model restored after a desktop restart.
  if (!backend.sleeping) return session;
  if (!Number.isFinite(backend.since) || Math.abs(backend.since - session.startedAt) > 30000) return null;
  return session;
}
function clear(file) { try { fs.unlinkSync(file); } catch (e) { if (e.code !== 'ENOENT') throw e; } }
module.exports = { save, read, reconcile, clear };
