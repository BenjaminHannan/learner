'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {verifiedCorrection,canonical}=require('../src/night-learn/corrections');
test('threefold correction requires a matching separately stored receipt and image',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'night-correction-')),sha=x=>crypto.createHash('sha256').update(x).digest('hex');
 try{const action={kind:'click',x:1,y:2},c={attemptId:'a',source:'ben',observation:'image.png',evidence:'evidence.json',action};fs.writeFileSync(path.join(dir,'image.png'),'image');
 const proof={schema:'hands-correction-evidence/v1',attemptId:'a',source:'ben',verified:true,observationSha256:sha('image'),actionSha256:sha(canonical(action)),intent:'open',timeMs:100,display:{bounds:{x:0,y:0,width:100,height:100},scaleX:2,scaleY:2}};
 fs.writeFileSync(path.join(dir,'evidence.json'),JSON.stringify(proof));assert.equal(verifiedCorrection(dir,c).weight,3);
 fs.writeFileSync(path.join(dir,'image.png'),'different');assert.throws(()=>verifiedCorrection(dir,c));assert.throws(()=>verifiedCorrection(dir,{...c,observation:'../outside'}));
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
