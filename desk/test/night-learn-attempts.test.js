'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {readAttempts}=require('../src/night-learn/attempts');
test('reads complete failures and leaves missing evidence unknown',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'night-attempt-test-')),p=path.join(dir,'log');
 try{const a={schema:'hands-attempt/v1',attemptId:'a',request:'open',steps:[],outcome:{result:'fail',evidence:'check'}};const b={...a,attemptId:'b',outcome:{result:'fail'}};
 fs.writeFileSync(p,JSON.stringify(a)+'\n'+JSON.stringify(b)+'\n{"partial":');const rows=readAttempts(p);
 assert.deepEqual(rows.map(r=>r.judgedOutcome),['fail','unknown']);
 fs.writeFileSync(p,JSON.stringify(a)+'\n'+JSON.stringify(a)+'\n');assert.throws(()=>readAttempts(p));
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
