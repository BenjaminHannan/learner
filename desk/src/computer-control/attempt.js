'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { randomUUID } = require('node:crypto');

function recover(root) {
  const log = path.join(root, 'attempts.jsonl');
  let written = new Set();
  try { written = new Set(fs.readFileSync(log, 'utf8').split('\n').filter(Boolean).map(line => { try { return JSON.parse(line).attemptId; } catch (_) { return null; } })); } catch (e) { if (e.code !== 'ENOENT') throw e; }
  for (const name of fs.readdirSync(root).filter(n => /^[0-9a-f-]{36}\.pending\.json$/.test(n))) {
    const file = path.join(root, name); let row;
    try { row = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (_) { continue; }
    if (!Number.isInteger(row.ownerPid) || row.ownerPid <= 0) continue;
    try { process.kill(row.ownerPid, 0); continue; } catch (e) { if (e.code !== 'ESRCH') continue; }
    if (!written.has(row.attemptId)) {
      row.finishedAt = new Date().toISOString(); row.outcome = { result:'unknown', evidence:'process interrupted' };
      fs.appendFileSync(log, JSON.stringify(row) + '\n', { mode:0o600 }); written.add(row.attemptId);
    }
    fs.unlinkSync(file);
  }
}

// The complete line follows ATTEMPT-LOG.md. The pending file makes a crash an
// unknown attempt on recovery, never a silent success. The directory is local.
class Attempt {
  constructor(request, root = path.join(os.homedir(), 'learner-ops', 'hands-attempts')) {
    if (!String(request || '').trim()) throw Error('A task from Ben is required');
    this.root = root; fs.mkdirSync(root, { recursive:true, mode:0o700 }); fs.chmodSync(root, 0o700); recover(root);
    this.id = randomUUID(); this.pending = path.join(root, this.id + '.pending.json');
    this.row = { schema:'hands-attempt/v1', attemptId:this.id, ownerPid:process.pid, requestedAt:new Date().toISOString(), request:String(request), steps:[], preparations:[], corrections:[], outcome:{ result:'unknown', evidence:null } };
    this.save();
  }
  save() {
    const temp = this.pending + '.tmp';
    fs.writeFileSync(temp, JSON.stringify(this.row), { mode:0o600 }); fs.renameSync(temp, this.pending);
  }
  step(record) { this.row.steps.push(record); this.save(); return this.row.steps.length - 1; }
  prepare(record) { this.row.preparations.push(record); this.save(); }
  update(i, fields) { Object.assign(this.row.steps[i], fields); this.save(); }
  finish(result = 'unknown', evidence = null) {
    if (this.finished) return;
    this.row.finishedAt = new Date().toISOString(); this.row.outcome = { result, evidence };
    fs.appendFileSync(path.join(this.root, 'attempts.jsonl'), JSON.stringify(this.row) + '\n', { mode:0o600 });
    fs.unlinkSync(this.pending); this.finished = true;
  }
}
module.exports = { Attempt, recover };
