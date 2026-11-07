'use strict';
const fs = require('node:fs');
const { correctionCandidates } = require('./data');

// Read only complete log lines; an interrupted write or pending task is unknown.
function readAttempts(file) {
  let text;
  try { const stat=fs.lstatSync(file); if (!stat.isFile() || stat.isSymbolicLink() || stat.size>16*1024*1024) throw Error('unsafe attempt log'); text=fs.readFileSync(file,'utf8'); }
  catch(error) { if (error.code==='ENOENT') return []; throw error; }
  const lines=text.split('\n'); lines.pop();
  const seen=new Set(), output=[];
  for (const line of lines) {
    let row; try {row=JSON.parse(line);} catch {throw Error('invalid complete attempt line');}
    if (row?.schema!=='hands-attempt/v1' || typeof row.attemptId!=='string' || !row.attemptId || seen.has(row.attemptId) || !Array.isArray(row.steps) || typeof row.request!=='string') throw Error('invalid or duplicate attempt');
    seen.add(row.attemptId);
    const outcome = row.outcome?.result === 'fail' && typeof row.outcome.evidence === 'string' && row.outcome.evidence.trim() ? 'fail' : row.outcome?.result === 'pass' && typeof row.outcome.evidence === 'string' && row.outcome.evidence.trim() ? 'pass' : 'unknown';
    output.push({...row, judgedOutcome:outcome, correctionCandidates:correctionCandidates({...row, corrections:Array.isArray(row.corrections)?row.corrections:[]})});
  }
  return output;
}
module.exports = {readAttempts};
