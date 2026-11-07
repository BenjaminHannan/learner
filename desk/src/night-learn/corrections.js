'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
function canonical(v){if(Array.isArray(v))return '['+v.map(canonical).join(',')+']';if(v&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';return JSON.stringify(v);}
function localFile(root,name) {
 if(typeof name!=='string'||path.basename(name)!==name||!name)throw Error('unsafe correction reference');
 const file=path.join(root,name),st=fs.lstatSync(file);if(!st.isFile()||st.isSymbolicLink()||st.size>32*1024*1024)throw Error('unsafe correction file');return file;
}
// Evidence is a separate local receipt, not a model's proposed fix. The
// producer remains responsible for who is allowed to issue such receipts.
function verifiedCorrection(root,candidate) {
 const image=localFile(root,candidate.observation), receipt=JSON.parse(fs.readFileSync(localFile(root,candidate.evidence),'utf8'));
 const imageSha256=hash(fs.readFileSync(image)),actionSha256=hash(Buffer.from(canonical(candidate.action)));
 if(receipt.schema!=='hands-correction-evidence/v1'||receipt.attemptId!==candidate.attemptId||receipt.source!==candidate.source||receipt.verified!==true||receipt.observationSha256!==imageSha256||receipt.actionSha256!==actionSha256||typeof receipt.intent!=='string'||!receipt.intent.trim()||!Number.isSafeInteger(receipt.timeMs)||!receipt.display||!receipt.display.bounds||!['x','y','width','height'].every(k=>Number.isFinite(receipt.display.bounds[k]))||receipt.display.bounds.width<=0||receipt.display.bounds.height<=0||!Number.isFinite(receipt.display.scaleX)||receipt.display.scaleX<=0||!Number.isFinite(receipt.display.scaleY)||receipt.display.scaleY<=0)throw Error('correction receipt mismatch');
 return {id:`correction:${candidate.attemptId}:${actionSha256}`,timeMs:receipt.timeMs,frame:image,frameSha256:imageSha256,frameFileSha256:imageSha256,intent:receipt.intent,action:candidate.action,display:receipt.display,weight:3,verified:true,verifiedCorrection:true};
}
module.exports={verifiedCorrection,canonical};
