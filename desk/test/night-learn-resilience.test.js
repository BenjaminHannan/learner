'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {compile}=require('../src/night-learn/compile');
const {handoff,trainWithFallback}=require('../src/night-learn/remote');
const {score}=require('../src/night-learn/score');
test('unmeasured coordinates and clock allow bound quarantined examples',()=>{
 const bounds={x:-400,y:80,width:800,height:400},pixels=Buffer.alloc(800*400*4);
 const rows=[{type:'clock_anchor',t:0,wallTimeMs:1000},{type:'frame',receiveMonotonicMs:10,transform:{sourceBounds:bounds}},{type:'mouse',kind:'mouse_down',source:'physical_unverified',t:35,eventTimestampNs:35e6,x:-200,y:180,button:0},{type:'mouse',kind:'mouse_up',eventTimestampNs:38e6,x:-200,y:180,button:0}];
 const decoder={index:[{width:800,height:400}],readFrame(){return {pixels};}};
 const result=compile({clip:{id:'c'},rows,decoder,calibration:{passed:false}});
 assert.equal(result.examples.length,1);assert.deepEqual(result.examples[0].action,{kind:'click',x:200,y:100});assert.deepEqual(result.limitations,['coords-unverified','clock-unverified']);
});
test('missing HANDS-PC is optional; failed remote training cleans copies before local fallback',()=>{
 assert.equal(handoff('/no-such-night-learn-report').train,null);const calls=[];
 const r=trainWithFallback({train:['remote','{dataset}'],cleanup:['cleanup','{output}'],notes:[]},'/data','/out',(bin,args)=>{calls.push([bin,...args]);if(bin==='remote')throw Error('offline');},()=>({status:'quarantine'}));
 assert.deepEqual(calls,[['remote','/data'],['cleanup','/out']]);assert.equal(r.backend,'local-fallback');
});
test('handoff reads compatible-start path and optional remote argv',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'night-handoff-'));
 try{const cp=path.join(dir,'candidate.pt');fs.writeFileSync(cp,'checkpoint');fs.writeFileSync(path.join(dir,'report.json'),JSON.stringify({checkpoint:cp,remoteTrainingCommand:['remote','{dataset}'],cleanupCommand:['cleanup','{dataset}']}));assert.equal(handoff(dir).checkpoint,cp);assert.deepEqual(handoff(dir).train,['remote','{dataset}']);}finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('click-only first night reports missing key evidence and stays quarantined',()=>{
 const r=score({train:[{id:'t',timeMs:1}],held:[{id:'h',timeMs:2,kind:'click',x:10,y:20}],predictions:Object.fromEntries(['old','candidate','noIntent'].map(a=>[a,{h:{x:10,y:20}}]))},{allowPartial:true});
 assert.equal(r.pass,false);assert.equal(r.rates.candidate.key,null);assert.equal(r.rates.candidate.click,1);
});
