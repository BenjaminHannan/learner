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
test('night adapter calls the actual HANDS-PC CLI without waiting on an owned GPU',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'hands-pc-cli-'));
 try{const runner=path.join(dir,'remote_runner.py');fs.writeFileSync(runner,'runner');
  const config=handoff(dir,{runner,python:'/python'});
  assert.deepEqual(config.train,['/python',runner,'{dataset}','{output}','--no-fallback','--gpu-wait','0','--bench-steps','0']);
  assert.equal(config.managesCleanup,true);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('remote artifacts need matching hashes and confirmed recording-copy deletion',()=>{
 const {verifyRemoteTraining}=require('../src/night-learn/remote'),{createHash}=require('node:crypto');
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'hands-pc-output-'));
 try{const r={train:[],held:[],predictions:{},modelSha256:{},remote:{transport:{pcCleanup:{deleted:true}}}};
  for(const name of ['old','candidate','no-intent']){fs.writeFileSync(path.join(dir,name+'.pt'),name);r.modelSha256[name+'.pt']=createHash('sha256').update(name).digest('hex');}
  assert.equal(verifyRemoteTraining(r,dir,{managesCleanup:true}).modelSha256.candidate,r.modelSha256.candidate);
  r.remote.transport.pcCleanup.deleted=false;assert.throws(()=>verifyRemoteTraining(r,dir,{managesCleanup:true}),/deletion/);
  r.remote.transport.pcCleanup.deleted=true;fs.writeFileSync(path.join(dir,'candidate.pt'),'changed');assert.throws(()=>verifyRemoteTraining(r,dir),/hash mismatch/);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('coordinate probe launches only Premonition through the HANDS-ACT identity path',()=>{
 const {launchCalibration}=require('../src/night-learn/coordinate-run');
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'night-coordinate-launch-'));
 try{
  const r=launchCalibration(dir,{execute:(binary,args)=>{assert.equal(binary,'/usr/bin/open');assert.equal(args[args.indexOf('-a')+1],'/Applications/Premonition.app');assert.ok(args.includes('ELECTRON_RUN_AS_NODE=1'));fs.writeFileSync(args.at(-1),JSON.stringify({passed:false,status:'coords-unverified',reason:'Ben is active'}));return {status:0};}});
  assert.equal(r.passed,false);assert.match(r.reason,/Ben is active/);
  const failed=launchCalibration(dir,{execute:()=>({status:1,stderr:'launch unavailable'})});assert.equal(failed.passed,false);assert.match(failed.reason,/launch unavailable/);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('HANDS-PC Markdown report can supply its actual downloaded starting checkpoint',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'checkpoint-note-test-'));
 try{const cp=path.join(dir,'candidate.pt');fs.writeFileSync(cp,'checkpoint');fs.writeFileSync(path.join(dir,'REPORT.md'),'Starting checkpoint: `'+cp+'`\n');assert.equal(handoff(dir).checkpoint,cp);}finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('Glim teaching episodes cannot mix training frames with later held-out frames',()=>{
 const {teachingEpisodes,actionWindow}=require('../src/night-learn/run');
 const rows=Array.from({length:101},(_,timeMs)=>({timeMs})),{cutoffMs}=actionWindow(rows);
 assert.equal(cutoffMs,80);
 const episodes=teachingEpisodes(rows);assert.deepEqual(episodes.map(e=>e.length),[80,21]);
 assert.ok(episodes.every(e=>e.every(r=>r.timeMs<cutoffMs)||e.every(r=>r.timeMs>=cutoffMs)));
});
test('starting checkpoint selects the trained candidate over old and no-intent controls',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'night-starting-arms-'));
 try{for(const name of ['candidate','old','no-intent'])fs.writeFileSync(path.join(dir,name+'.pt'),name);assert.equal(handoff(dir).checkpoint,path.join(dir,'candidate.pt'));}finally{fs.rmSync(dir,{recursive:true,force:true});}
});
