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
test('interrupted Glim responses retry with a fresh FIFO turn; night/idle refusal does not',()=>{
 const {retryBackground}=require('../src/night-learn/run');let calls=0,pauses=0;
 assert.equal(retryBackground(()=>{if(calls++===0)throw Error('Glim returned no explanation text');return 'real result';},()=>pauses++),'real result');
 assert.equal(calls,2);assert.equal(pauses,1);
 assert.throws(()=>retryBackground(()=>{throw Error('requires 01:00–07:00 and 20 minutes of Mac idle');},()=>assert.fail('must not retry while active')),/20 minutes/);
});
test('optional remote cleanup trouble is reported without stopping local learning',()=>{
 const r=trainWithFallback({train:['remote'],cleanup:['cleanup'],notes:[]},'/data','/out',(bin)=>{throw Error(bin+' offline');},()=>({status:'quarantine'}));
 assert.equal(r.backend,'local-fallback');assert.equal(r.remoteCopiesDeleted,false);assert.match(r.notes.join(' '),/cleanup needs retry/);
});
test('CG global points map through Retina backing scale, display origin and video compositor',()=>{
 const {coordinateMap}=require('../src/night-learn/coordinate-map');
 const bounds={x:-1440,y:100,width:1440,height:900};
 const r=coordinateMap({x:-1200,y:250},{bounds,scaleX:2,scaleY:2},bounds,{width:1280,height:720});
 assert.deepEqual(r.backingPixels,{x:480,y:300});
 assert.ok(Math.abs(r.videoPixels.x-256)<1e-8);assert.ok(Math.abs(r.videoPixels.y-120)<1e-8);
});
