'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');const {Retention}=require('../../src/hands-toy/retention'),{Recorder}=require('../../src/hands-toy/recorder');
const mk=(caps={})=>{const root=fs.mkdtempSync(path.join(os.tmpdir(),'hands-retention-'));let t=Date.now(),free=10000;const r=new Retention(root,{caps:{total:300,daily:1000,keep:60,minFree:10,ageMs:7000,...caps},clock:()=>t,freeBytes:()=>free});const add=(id,n=30,extra={})=>{const files=[id+'.frames',id+'.events',id+'.labels'];for(const f of files)fs.writeFileSync(path.join(root,f),Buffer.alloc(n/3,7));return r.register({id,session:id,files,app:'fake',action:'click',...extra});};return {r,root,add,advance:n=>{t+=n;},low:()=>{free=0;}};};
function mockedRecorder() {
 const {EventEmitter}=require('node:events'),{PassThrough}=require('node:stream');
 const child=new EventEmitter();child.stdio=Array.from({length:5},()=>new PassThrough());child.stderr=child.stdio[2];child.kill=()=>true;
 const container={exports:{}};
 const load=new Function('require','module','exports',fs.readFileSync(require.resolve('../../src/hands-toy/recorder'),'utf8'));
 load(name=>name==='node:child_process'?{...require(name),spawn:()=>child}:name==='./retention'?{Retention}:name==='./encoder-proof'?require('../../src/hands-toy/encoder-proof'):require(name),container,container.exports);
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'recorder-drain-'));
 const recorder=new container.exports.Recorder({root,fake:true,retentionOptions:{freeBytes:()=>1e12}});
 return {recorder,child,root};
}
test('pause drains encoded tail and registers only after child pipes close',async()=>{
 const {recorder,child,root}=mockedRecorder();
 try {
  await recorder.on();const clip=recorder.pending;
  child.stdio[3].write(Buffer.from('head'));
  const stopping=recorder.pause();child.emit('exit',0);
  assert.equal(recorder.retention.status().clips,0);assert.equal(recorder.pending,clip);
  child.stdio[3].write(Buffer.from('tail'));child.stdio[4].write(Buffer.from('detail'));
  assert.equal(fs.readFileSync(path.join(root,clip.files[0]),'utf8'),'headtail');
  child.stdio[3].end();child.stdio[4].end();child.emit('close',0);await stopping;
  assert.equal(recorder.pending,null);assert.equal(recorder.retention.status().clips,1);
  assert.equal(recorder.retention.status().totalBytes,14);assert.equal(recorder.paused,true);
 } finally {child.emit('exit',1);child.emit('close',1);await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});
test('draining cannot exceed the reserved segment budget',async()=>{
 const {recorder,child,root}=mockedRecorder();
 try {
  await recorder.on();const clip=recorder.pending;recorder.segmentBudget=4;
  child.stdio[3].write(Buffer.from('head'));
  const stopping=recorder.pause();child.emit('exit',0);child.stdio[3].write(Buffer.from('tail'));
  assert.equal(clip.truncated,true);assert.equal(recorder.segmentBytes,4);
  assert.equal(fs.readFileSync(path.join(root,clip.files[0]),'utf8'),'head');
  child.emit('close',0);await stopping;assert.equal(recorder.retention.status().totalBytes,4);
 } finally {child.emit('exit',1);child.emit('close',1);await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});
for(const seed of [101,202,303]){
 test('T9 retention seed '+seed+': judged sleep spends clips; keep <= cap; log matches disk',()=>{const {r,root,add}=mk();for(let i=0;i<6;i++)add('c'+seed+'_'+i);assert.throws(()=>r.finishSleep({judged:false,trainedIds:[]}));const ids=Object.keys(r.data.clips);const result=r.finishSleep({judged:true,trainedIds:ids,losses:{[ids[0]]:10}});assert.ok(result.keepBytes<=60);assert.ok(result.clips<=2);const logs=fs.readFileSync(path.join(root,'retention.log'),'utf8').trim().split('\n').map(JSON.parse).filter(x=>x.state==='deleted');assert.equal(logs.length,4);assert.equal(logs.reduce((n,x)=>n+x.bytes,0),120);for(const row of logs){assert.equal(row.reason,'spent');for(const rel of row.paths)assert.equal(fs.existsSync(path.join(root,rel)),false);}assert.equal(Object.values(r.data.clips).reduce((n,c)=>n+r.size(c),0),result.totalBytes);});
 test('T9 untrained preserved except age/space or explicit delete; audit never trained',()=>{const {r,root,add,advance,low}=mk();add('recent');add('held',30,{audit:true});assert.throws(()=>r.finishSleep({judged:true,trainedIds:['held']}),/audit/);r.finishSleep({judged:true,trainedIds:[]});assert.ok(fs.existsSync(path.join(root,'recent.frames')));advance(7001);r.sweep();assert.equal(r.status().clips,0);add('lowdisk');low();assert.equal(r.sweep().clips,0);const rows=fs.readFileSync(path.join(root,'retention.log'),'utf8').trim().split('\n').map(JSON.parse).filter(x=>x.state==='deleted');assert.ok(rows.every(x=>['expired','over-cap'].includes(x.reason)));});
 test('T9 rejects outside, traversal and symlink paths before ANY delete',()=>{const {r,root,add}=mk();const outside=path.join(fs.mkdtempSync(path.join(os.tmpdir(),'hands-outside-')),'ben.txt');fs.writeFileSync(outside,'untouched');add('evil');r.transaction(()=>{r.load();r.data.clips.evil.files.push(outside);r.save();});assert.throws(()=>r.deleteSession('evil'),/outside/);assert.equal(fs.readFileSync(outside,'utf8'),'untouched');assert.ok(fs.existsSync(path.join(root,'evil.frames')));assert.throws(()=>r.checked('../ben.txt'));fs.symlinkSync(path.dirname(outside),path.join(root,'escape'));assert.throws(()=>r.checked('escape/ben.txt'),/symlink/);});
}
test('T9 daily ingestion does not reset after deletion; audit cap; session button',()=>{const {r,add}=mk({daily:90});add('a');add('b');r.deleteSession('a');assert.equal(r.status().dailyBytes,60);add('c');assert.throws(()=>add('d'),/disk/);assert.equal(r.status().dailyBytes,90);const q=mk({keep:20});assert.throws(()=>q.add('audit',30,{audit:true}),/audit/);});
test('T9 real recorder cannot enable before separate lead release; restart defaults OFF',async()=>{const root=fs.mkdtempSync(path.join(os.tmpdir(),'hands-rec-off-'));const r=new Recorder({root});await assert.rejects(()=>r.on(),/separate lead/);assert.equal(r.status().enabled,false);assert.equal(r.event({type:'key',text:'fake-secret'}),false);assert.equal(fs.existsSync(path.join(root,'retention.log')),false);await r.off();assert.equal(new Recorder({root}).status().enabled,false);});
test('T9 recorder has no policy, replay reader, detector, blanking, or action source',()=>{const code=fs.readFileSync(path.join(__dirname,'../../src/hands-toy/recorder.js'),'utf8');assert.doesNotMatch(code,/PixelPolicy|PixelWorker|\.predict\(|\.receive\(|CGEventPost|secret_typed|passwordFocus|blankPixel/);});
test('legacy and extension events do not stop recording; source errors do',async()=>{const root=fs.mkdtempSync(path.join(os.tmpdir(),'ledger-event-'));const recorder=new Recorder({root,fake:true,retentionOptions:{freeBytes:()=>20*1024**3}});recorder.enabled=true;recorder.segmentBudget=1024*1024;recorder.segmentBytes=0;recorder.pending={files:['a','b','events'],frames:0};fs.writeFileSync(path.join(root,'events'),'');assert.equal(recorder.event({type:'key',t:1,text:'legacy'}),true);assert.equal(recorder.event({type:'extension',extra:'preserved'}),true);assert.equal(recorder.event({type:'frame',frameId:3,t:2}),true);assert.equal(recorder.enabled,true);const rows=fs.readFileSync(path.join(root,'events'),'utf8').trim().split('\n').map(JSON.parse);assert.ok(rows.every(row=>row.learningEligible===false));assert.equal(rows[1].extra,'preserved');recorder.event({type:'source_error',reason:'broken'});assert.equal(recorder.enabled,false);assert.equal(recorder.reason,'broken');fs.rmSync(root,{recursive:true,force:true});});
test('transform roundtrip and generation staleness',()=>{const {transformPoint}=require('../../src/hands-toy/recorder');const transform={verified:true,x:-20,y:5,scaleX:2,scaleY:3,uncertaintyPx:0.5,generation:4};const point={x:10,y:12};assert.deepEqual(transformPoint(transform,transformPoint(transform,point,4),4,true),point);assert.throws(()=>transformPoint(transform,point,5),/stale/);});
test('ledger compatibility and conservative alignment',()=>{const {normalizeLedgerEntry,validateEncodedAlignment}=require('../../src/hands-toy/recorder');const transform={verified:true,x:0,y:0,scaleX:1,scaleY:1,uncertaintyPx:0,generation:1};const frames=[1,2].map(frameId=>normalizeLedgerEntry({type:'frame',frameId,t:110+frameId,receiveMonotonicMs:100+frameId,writeCompleteMonotonicMs:110+frameId,presentationValue:frameId,presentationTimescale:20,presentationFlags:1,presentationEpoch:0,generation:1,transitionAmbiguous:false,width:1280,height:720,pixelFormat:'BGRA',transform}));const inputs=frames.map((frame,index)=>({ordinal:index+1,sourceFrameId:frame.frameId,disposition:'submitted',ptsSeconds:index/20}));const probe={timeBaseSeconds:1/10240,frames:inputs.map(input=>({ptsSeconds:input.ptsSeconds}))};const pipeline={temporalFilter:'identity',timestampMode:'passthrough',inputTimeBase:'1/20',output:'main',maxSourceGapMs:75,maxTransformUncertaintyPx:1};const proof={frames,inputs,probe,pipeline,encoderExitCode:0};assert.equal(validateEncodedAlignment(proof).length,2);assert.equal(normalizeLedgerEntry({type:'key',t:1}).learningEligible,false);assert.equal(normalizeLedgerEntry({type:'extension',custom:42}).custom,42);assert.equal(normalizeLedgerEntry(null).learningEligible,false);assert.throws(()=>validateEncodedAlignment({...proof,probe:{...probe,frames:probe.frames.slice(1)}}),/dropped/);assert.throws(()=>validateEncodedAlignment({...proof,probe:{...probe,frames:[probe.frames[0],probe.frames[0]]}}),/PTS/);assert.throws(()=>validateEncodedAlignment({...proof,probe:{...probe,frames:[probe.frames[0],{ptsSeconds:0.06}]}}),/PTS/);assert.throws(()=>validateEncodedAlignment({...proof,frames:[frames[0],{...frames[1],generation:2}]}),/generation/);assert.throws(()=>validateEncodedAlignment({...proof,frames:[frames[0],{...frames[1],frameId:3}]}),/gap/);assert.throws(()=>validateEncodedAlignment({...proof,pipeline:{...pipeline,temporalFilter:'unknown'}}),/pipeline/);});
test('recorder admits only affordable finalized proof into retention',async()=>{
 for(const mode of ['success','failure','cap']){
  const fixture=lifecycleFixture({proofMode:true,proofData:mode==='failure'?null:Buffer.from('{"learningEligible":false}\n')});const {root,recorder}=fixture;try{
   const clip=await finishSyntheticProof(fixture,{beforeClose:()=>{if(mode==='cap')recorder.segmentBudget=recorder.segmentBytes;}});
   const retained=Object.values(recorder.retention.data.clips)[0];assert.equal(retained.files.some(file=>file.endsWith('.proof.json')),mode==='success');assert.equal(fs.existsSync(path.join(root,clip.id+'.proof.json')),mode==='success');
   assert.equal(fixture.calls.length,1);assert.equal(recorder.retention.status().totalBytes,recorder.retention.size(retained));
  }finally{await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
 }
});
function onceStreamEnd(stream){return new Promise(resolve=>{stream.once('end',resolve);stream.resume();});}
function lifecycleFixture({fileSystem=fs,retentionClass=Retention,proofMode=false,proofData=null,prepareProcess,evidenceProcess}={}){
 const {EventEmitter}=require('node:events'),{PassThrough,Writable}=require('node:stream');
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'recorder-lifecycle-'));
 let nextPid=100;const child=()=>{const value=new EventEmitter();value.pid=nextPid++;value.stdio=Array.from({length:5},()=>new PassThrough());value.stdin=value.stdio[0];value.stdin.resume();value.stdout=value.stdio[1];value.stderr=value.stdio[2];value.signals=[];value.kill=signal=>{value.signals.push(signal);return true;};return value;};
 const encoder=child(),source=child(),sink=new Writable({write(chunk,encoding,callback){callback();}}),calls=[],children=[encoder,source];
 const launches=[],records=[],actualCore=require('../../src/hands-toy/encoder-proof');
 const processProof={prepare:async command=>{if(prepareProcess)await prepareProcess(command);return {launch(spawn,args,options){const value=spawn(command,args,options);launches.push({command,args:[...args],options});const record={pid:value.pid,command,args:[...args],sha256:'a'.repeat(64),ownedLaunch:true,exitCode:0,signal:null,closeObserved:true};records.push(record);return {child:value,evidence:async()=>evidenceProcess?evidenceProcess(record):record};}};}};
 const proof={...actualCore,submission:proofMode?actualCore.submission:()=>({state:{},sink}),finalize:options=>{calls.push(options);if(proofData)return proofData;throw Error('unverified');}};
 const container={exports:{}},load=new Function('require','module','exports',fs.readFileSync(require.resolve('../../src/hands-toy/recorder'),'utf8'));
 load(name=>name==='node:child_process'?{...require(name),spawn:()=>children.shift()}:name==='node:fs'?fileSystem:name==='./retention'?{Retention:retentionClass}:name==='./encoder-proof'?proof:name==='./recorder-process'?processProof:require(name),container,container.exports);
 const recorder=new container.exports.Recorder({root,releaseApproved:true,nativeHelper:'/test/direct-helper',ffmpeg:'/test/encoder',proofMode,directFrames:false,shutdownMs:250,retentionOptions:{freeBytes:()=>1e12}});recorder.enabled=true;
 return {root,recorder,encoder,source,sink,calls,children,launches,records,makeChild:child};
}

async function finishSyntheticProof(fixture,{changeTerminal,tail='',rawExtra=false,beforeClose,delayStop=false}={}){
 const {recorder,source,encoder}=fixture;await recorder.segment();const clip=recorder.pending;let stopping=delayStop?null:recorder.off();
 const bytes=Buffer.alloc(1280*720*4,7),frame={type:'frame',frameId:1,t:2,sourceContract:'hands-toy-bgra-frame-v1',session:clip.id,sourcePid:source.pid,rawByteCount:bytes.length,rawSha256:require('node:crypto').createHash('sha256').update(bytes).digest('hex'),receiveMonotonicMs:1,writeCompleteMonotonicMs:2,presentationValue:1,presentationTimescale:20,presentationFlags:1,presentationEpoch:0,generation:1,width:1280,height:720,pixelFormat:'BGRA'};
 const terminal={type:'source_end',sourceContract:'hands-toy-bgra-frame-v1',session:clip.id,sourcePid:source.pid,stopCause:'stdin-eof',complete:true,frameCount:1};
 if(changeTerminal)changeTerminal(terminal);source.stdout.write(bytes);if(rawExtra)source.stdout.write(Buffer.from([1]));source.stdio[3].write(JSON.stringify(frame)+'\n');source.stdio[3].end((terminal.omit?'':JSON.stringify(terminal)+'\n')+tail);source.stdout.end();encoder.stdio[3].end('encoded');encoder.stdio[4].end('detail');await new Promise(resolve=>setImmediate(resolve));if(delayStop)stopping=recorder.off();if(beforeClose)beforeClose();source.emit('exit',0,null);source.emit('close',0,null);encoder.emit('exit',0,null);encoder.emit('close',0,null);await stopping;return clip;
}
for(const method of ['off','pause'])test('graceful '+method+' drains source and encoder tails without signals',{timeout:2000},async()=>{
 const {root,recorder,encoder,source,sink,calls}=lifecycleFixture();const chunks=[];sink._write=(chunk,encoding,callback)=>{chunks.push(Buffer.from(chunk));callback();};
 try{
  await recorder.segment();const clip=recorder.pending;const stopping=recorder[method]();assert.equal(source.stdin.writableEnded,true);assert.equal(encoder.stdin.writableEnded,false);assert.deepEqual(source.signals,[]);assert.deepEqual(encoder.signals,[]);
  source.stdout.write('raw-tail');source.stdio[3].write('{"type":"frame","frameId":1,"t":1}\n');encoder.stdio[3].write('encoded-tail');source.stdout.end();source.stdio[3].end();await new Promise(resolve=>setImmediate(resolve));source.emit('close',0);encoder.emit('close',0);assert.equal(recorder.retention.data.clips[clip.id],undefined);encoder.stdio[3].end();encoder.stdio[4].end();await stopping;
  assert.equal(Buffer.concat(chunks).toString(),'raw-tail');assert.match(fs.readFileSync(path.join(root,clip.files[2]),'utf8'),/"frameId":1/);assert.equal(fs.readFileSync(path.join(root,clip.files[0]),'utf8'),'encoded-tail');assert.equal(calls.length,0);assert.deepEqual(source.signals,[]);assert.deepEqual(encoder.signals,[]);
 }finally{await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});
test('hung graceful drain escalates and refuses the clip',{timeout:2000},async()=>{
 const {root,recorder,encoder,source,calls}=lifecycleFixture();try{await recorder.segment();const clip=recorder.pending;await recorder.off();assert.ok(source.signals.includes('SIGTERM'));assert.ok(source.signals.includes('SIGKILL'));assert.ok(encoder.signals.includes('SIGKILL'));assert.equal(calls.length,0);assert.equal(recorder.retention.data.clips[clip.id],undefined);assert.equal(recorder.enabled,false);}finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('submission and stream failures coordinate bounded shutdown',async()=>{
 for(const target of ['sink','stdin','stdout','encoder','source']){
  const fixture=lifecycleFixture(),{root,recorder,encoder,source,sink}=fixture;try{
   await recorder.segment();const clip=recorder.pending;const stream={sink,stdin:encoder.stdin,stdout:source.stdout,encoder,source}[target];stream.emit('error',Error(target==='sink'?'frame limit':target+' failure'));
   assert.equal(recorder.enabled,false);assert.equal(source.stdout.destroyed,true);await Promise.all([recorder.off(),recorder.off()]);assert.ok(source.signals.includes('SIGKILL'));assert.ok(encoder.signals.includes('SIGKILL'));assert.equal(recorder.pending,null);assert.equal(recorder.retention.data.clips[clip.id],undefined);assert.equal(fs.existsSync(path.join(root,clip.files[0])),false);
   encoder.emit('close',0);source.emit('close',0);assert.equal(recorder.retention.data.clips[clip.id],undefined);
  }finally{fs.rmSync(root,{recursive:true,force:true});}
 }
});
test('source and encoder close races retain only closed encoder output',async()=>{
 const {root,recorder,encoder,source}=lifecycleFixture();try{
  await recorder.segment();const clip=recorder.pending;const stopping=recorder.pause();encoder.emit('exit',0);encoder.stdio[3].write('tail');source.stdout.end();source.stdio[3].end();source.emit('close',0);assert.equal(recorder.retention.data.clips[clip.id],undefined);encoder.stdio[3].end();encoder.stdio[4].end();encoder.emit('close',0);await stopping;assert.ok(recorder.retention.data.clips[clip.id]);encoder.stdio[3].emit('data',Buffer.from('late'));assert.equal(fs.readFileSync(path.join(root,clip.files[0]),'utf8'),'tail');await recorder.off();
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('invalid source metadata is harmless and invalidates proof',async()=>{
 for(const metadata of ['null\n','42\n','"text"\n','{bad}\n','x'.repeat(4100)+'\n','{"type":"extension"}']){
  const {root,recorder,encoder,source,calls}=lifecycleFixture();try{
   await recorder.segment();source.stdio[3].write(metadata);if(metadata.endsWith('\n'))source.stdio[3].write('{"type":"extension","value":7}\n');assert.equal(recorder.enabled,true);source.stdio[3].end();await onceStreamEnd(source.stdio[3]);source.stdout.end();encoder.stdio[3].end();encoder.stdio[4].end();recorder.enabled=false;source.emit('close',0);encoder.emit('close',0);await recorder.segmentDone;assert.equal(calls.length,0);
  }finally{fs.rmSync(root,{recursive:true,force:true});}
 }
});

test('mocked owned caller passes observed process records after complete drain',async()=>{
 const fixture=lifecycleFixture({proofMode:true,proofData:Buffer.from('{"learningEligible":false}\n')});const {root,recorder,calls,records,launches,source,encoder}=fixture;
 try{const clip=await finishSyntheticProof(fixture);assert.equal(calls.length,1);assert.equal(calls[0].sourceComplete,true);assert.equal(calls[0].state.ended,true);assert.equal(calls[0].state.inputs.length,1);assert.equal(calls[0].state.inputs[0].writeComplete,true);assert.deepEqual(calls[0].provenance.source,{...records[1],stopCause:'stdin-eof'});assert.deepEqual(calls[0].provenance.encoder,{...records[0],mainOutputFile:path.join(root,clip.files[0]),mainOutputClosed:true});assert.deepEqual(launches[1].args,['--capture','--proof-session',clip.id]);assert.equal(recorder.retention.data.clips[clip.id].proofStatus,'temporal-only');assert.deepEqual(source.signals,[]);assert.deepEqual(encoder.signals,[]);}finally{await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});

for(const variant of ['missing','incomplete','session','pid','count','cause','contract','duplicate','trailing','raw-extra'])test('owned caller refuses terminal evidence: '+variant,async()=>{
 const fixture=lifecycleFixture({proofMode:true,proofData:Buffer.from('{}\n')});const {root,recorder,calls}=fixture;
 try{const options={changeTerminal:terminal=>{if(variant==='missing')terminal.omit=true;if(variant==='incomplete'){terminal.complete=false;terminal.drainComplete=true;terminal.captureHealth='callback-quiescence-unverified';}if(variant==='session')terminal.session='wrong';if(variant==='pid')terminal.sourcePid++;if(variant==='count')terminal.frameCount++;if(variant==='cause')terminal.stopCause='signal';if(variant==='contract')terminal.sourceContract='unknown';},tail:variant==='duplicate'?'{"type":"source_end"}\n':variant==='trailing'?'x':'',rawExtra:variant==='raw-extra'};const clip=await finishSyntheticProof(fixture,options);assert.equal(calls.length,0);assert.equal(recorder.retention.data.clips[clip.id].proofStatus,'refused');assert.equal(fs.existsSync(path.join(root,clip.id+'.proof.json')),false);assert.equal(recorder.retention.status().clips,1);}finally{await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});

for(const method of ['off','pause','deleteSession'])test(method+' during identity preparation cannot launch late children',async()=>{
 let release;const preparation=new Promise(resolve=>{release=resolve;});const fixture=lifecycleFixture({proofMode:true,prepareProcess:()=>preparation});const {root,recorder,launches,children}=fixture;
 try{const starting=recorder.segment();const id=recorder.pending.id;await recorder[method](id);release();await starting;assert.equal(launches.length,0);assert.equal(children.length,2);assert.equal(recorder.pending,null);assert.equal(recorder.retention.status().clips,0);}finally{release();await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});

test('identity failure and wrapper routing retain ordinary capture without proof',async()=>{
 for(const variant of ['hash-failure','wrapper']){const fixture=lifecycleFixture({proofMode:true,proofData:Buffer.from('{}\n'),prepareProcess:()=>{if(variant==='hash-failure')throw Error('identity unavailable');}});const {root,recorder,launches,calls}=fixture;
  try{if(variant==='wrapper')recorder.nativeHelper=process.execPath;const clip=await finishSyntheticProof(fixture);assert.equal(launches.length,0);assert.equal(calls.length,0);assert.equal(recorder.retention.status().clips,1);assert.equal(fs.existsSync(path.join(root,clip.id+'.proof.json')),false);}finally{await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
 }
});

test('missing and hung process evidence refuse proof and settle OFF',{timeout:2000},async()=>{
 for(const mode of ['missing','hung']){const fixture=lifecycleFixture({proofMode:true,proofData:Buffer.from('{}\n'),evidenceProcess:()=>mode==='hung'?new Promise(()=>{}):null});const {root,recorder,calls}=fixture;
  try{const clip=await finishSyntheticProof(fixture);assert.equal(calls.length,0);assert.equal(recorder.activeSegment,null);assert.equal(recorder.retention.data.clips[clip.id].proofStatus,'refused');}finally{await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
 }
});

test('planned rollover requests EOF before encoder exit',async()=>{
 const fixture=lifecycleFixture({proofMode:true,proofData:Buffer.from('{}\n')});const {root,recorder,source,encoder}=fixture;
 try{await recorder.segment();const rollover=recorder.activeSegment.timers.find(timer=>timer._idleTimeout===29000);assert.ok(rollover);rollover._onTimeout();assert.equal(source.stdin.writableEnded,true);assert.equal(encoder.stdin.writableEnded,false);const clip=await finishSyntheticProof(fixture);assert.equal(recorder.retention.data.clips[clip.id].proofStatus,'temporal-only');assert.deepEqual(source.signals,[]);}finally{await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});

for(const limit of ['daily','total','free'])test('proof admission respects remaining '+limit+' budget',async()=>{
 const fixture=lifecycleFixture({proofMode:true,proofData:Buffer.from('{}\n')});const {root,recorder}=fixture;
 try{const clip=await finishSyntheticProof(fixture,{beforeClose:()=>{if(limit==='daily')recorder.retention.caps.daily=recorder.segmentBytes;if(limit==='total')recorder.retention.caps.total=recorder.segmentBytes;if(limit==='free')recorder.retention.freeBytes=()=>recorder.retention.caps.minFree+2;}});assert.equal(recorder.retention.data.clips[clip.id].proofStatus,'refused');assert.equal(fs.existsSync(path.join(root,clip.id+'.proof.json')),false);assert.equal(recorder.retention.status().clips,1);}finally{await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});

for(const cleanupFails of [false,true])test('partial proof write is never promoted; cleanup failure is accounted: '+cleanupFails,async()=>{
 let proofFd;const fileSystem=new Proxy(fs,{get(target,key){if(key==='openSync')return (file,...args)=>{const descriptor=target.openSync(file,...args);if(typeof file==='string'&&file.endsWith('.proof.partial'))proofFd=descriptor;return descriptor;};if(key==='writeFileSync')return (file,data,...args)=>{if(file===proofFd){target.writeSync(file,Buffer.from('x'));throw Error('proof write failed');}return target.writeFileSync(file,data,...args);};if(key==='unlinkSync')return file=>{if(cleanupFails&&file.endsWith('.proof.partial'))throw Error('proof cleanup failed');return target.unlinkSync(file);};return Reflect.get(target,key);}});
 const fixture=lifecycleFixture({fileSystem,proofMode:true,proofData:Buffer.from('{}\n')});const {root,recorder}=fixture;
 try{const clip=await finishSyntheticProof(fixture);const retained=recorder.retention.data.clips[clip.id];assert.equal(retained.proofStatus,'refused');assert.equal(fs.existsSync(path.join(root,clip.id+'.proof.json')),false);assert.equal(fs.existsSync(path.join(root,clip.id+'.proof.partial')),cleanupFails);assert.equal(retained.files.includes(clip.id+'.proof.partial'),cleanupFails);assert.equal(recorder.retention.status().totalBytes,recorder.retention.size(retained));}finally{await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});

test('proof sidecar follows retention removal on registration failure',async()=>{
 const fixture=lifecycleFixture({proofMode:true,proofData:Buffer.from('{}\n')});const {root,recorder}=fixture;
 try{const clip=await finishSyntheticProof(fixture,{beforeClose:()=>{recorder.retention.register=()=>{throw Error('admission failed');};}});assert.equal(recorder.retention.status().clips,0);for(const file of clip.files)assert.equal(fs.existsSync(path.join(root,file)),false);assert.equal(recorder.enabled,false);}finally{await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});

test('unreadable partial proof remains durably indexed with a conservative byte reservation',async()=>{
 let proofFd,unreadable=true,cleanupFails=true;const proofData=Buffer.alloc(4096,7);
 const fileSystem=new Proxy(fs,{get(target,key){
  if(key==='openSync')return (file,...args)=>{const descriptor=target.openSync(file,...args);if(typeof file==='string'&&file.endsWith('.proof.partial'))proofFd=descriptor;return descriptor;};
  if(key==='writeFileSync')return (file,data,...args)=>{if(file===proofFd){target.writeSync(file,Buffer.from('x'));throw Error('proof write EIO');}return target.writeFileSync(file,data,...args);};
  if(key==='unlinkSync')return file=>{if(cleanupFails&&file.endsWith('.proof.partial'))throw Error('proof unlink EIO');return target.unlinkSync(file);};
  if(key==='statSync')return (file,...args)=>{if(unreadable&&typeof file==='string'&&file.endsWith('.proof.partial'))throw Error('proof stat EIO');return target.statSync(file,...args);};
  return Reflect.get(target,key);
 }});
 const container={exports:{}},load=new Function('require','module','exports',fs.readFileSync(require.resolve('../../src/hands-toy/retention'),'utf8'));
 load(name=>name==='node:fs'?fileSystem:require(name),container,container.exports);
 const retentionClass=container.exports.Retention,fixture=lifecycleFixture({fileSystem,retentionClass,proofMode:true,proofData}),{root,recorder}=fixture;
 try{
  const clip=await finishSyntheticProof(fixture),partial=clip.id+'.proof.partial',saved=JSON.parse(fs.readFileSync(path.join(root,'clip-index.json'),'utf8')).clips[clip.id];
  assert.ok(saved);assert.equal(saved.proofStatus,'refused');assert.equal(saved.partialProofBytes,proofData.length);assert.ok(saved.files.includes(partial));assert.equal(fs.statSync(path.join(root,partial)).size,1);assert.equal(fs.existsSync(path.join(root,clip.id+'.proof.json')),false);assert.equal(recorder.enabled,false);assert.equal(recorder.reason,'proof unlink EIO');
  const ordinaryBytes=saved.files.filter(file=>file!==partial).reduce((total,file)=>total+fs.statSync(path.join(root,file)).size,0),expectedBytes=ordinaryBytes+proofData.length;
  assert.equal(recorder.retention.status().totalBytes,expectedBytes);assert.equal(recorder.retention.status().dailyBytes,expectedBytes);
  const reopened=new retentionClass(root,{freeBytes:()=>1e12});assert.equal(reopened.status().totalBytes,expectedBytes);assert.equal(reopened.status().dailyBytes,expectedBytes);
  unreadable=false;assert.equal(reopened.status().totalBytes,expectedBytes);cleanupFails=false;reopened.deleteSession(clip.id);assert.equal(reopened.status().totalBytes,0);assert.equal(fs.existsSync(path.join(root,partial)),false);
 }finally{unreadable=false;cleanupFails=false;await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});

test('partial proof reservations cannot hide unrelated stat failures or invalid metadata',()=>{
 const {r:retention,root}=mk({total:1e6,daily:1e6,keep:1e6});
 try{
  const id='reserved',files=[id+'.proof.partial'];fs.writeFileSync(path.join(root,files[0]),Buffer.from('x'));
  for(const partialProofBytes of [0,-1,1.5,256*1024+1,'4096'])assert.throws(()=>retention.register({id,files,proofStatus:'refused',partialProofBytes}),/partial proof reservation/);
  assert.throws(()=>retention.register({id,files,proofStatus:'temporal-only',partialProofBytes:4096}),/partial proof reservation/);
  assert.throws(()=>retention.register({id,files:[id+'.other'],proofStatus:'refused',partialProofBytes:4096}),/partial proof reservation/);
  const saved=retention.register({id,files,proofStatus:'refused',partialProofBytes:4096});assert.equal(retention.size(saved),4096);
  fs.appendFileSync(path.join(root,files[0]),Buffer.alloc(5000));assert.equal(retention.size(saved),5001);
  const container={exports:{}},fileSystem=new Proxy(fs,{get(target,key){if(key==='statSync')return (file,...args)=>{if(file.endsWith('.other'))throw Error('unrelated stat EIO');return target.statSync(file,...args);};return Reflect.get(target,key);}}),load=new Function('require','module','exports',fs.readFileSync(require.resolve('../../src/hands-toy/retention'),'utf8'));
  load(name=>name==='node:fs'?fileSystem:require(name),container,container.exports);const reader=new container.exports.Retention(root,{freeBytes:()=>1e12}),other=id+'.other';fs.writeFileSync(path.join(root,other),'ordinary');assert.throws(()=>reader.size({...saved,files:[...files,other]}),/unrelated stat EIO/);
  fs.unlinkSync(path.join(root,files[0]));fs.symlinkSync(path.join(root,other),path.join(root,files[0]));assert.throws(()=>retention.size(saved),/symlink/);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});

test('terminal marker cannot retroactively authorize source EOF',async()=>{
 const fixture=lifecycleFixture({proofMode:true,proofData:Buffer.from('{}\n')});const {root,recorder,calls}=fixture;
 try{const clip=await finishSyntheticProof(fixture,{delayStop:true});assert.equal(calls.length,0);assert.equal(recorder.retention.data.clips[clip.id].proofStatus,'refused');}finally{await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});

test('late process evidence cannot finalize or corrupt a replacement segment',{timeout:2000},async()=>{
 const releases=[];let enter;const entered=new Promise(resolve=>{enter=resolve;});const fixture=lifecycleFixture({proofMode:true,proofData:Buffer.from('{}\n'),evidenceProcess:record=>new Promise(resolve=>{releases.push(()=>resolve(record));enter();})});const {root,recorder,calls,children,makeChild}=fixture;
 try{const finishing=finishSyntheticProof(fixture);await entered;assert.equal(recorder.activeSegment.finalizing,true);await recorder.segment();assert.equal(children.length,0);const first=await finishing;assert.equal(recorder.retention.data.clips[first.id].proofStatus,'refused');recorder.proofMode=false;recorder.enabled=true;children.push(makeChild(),makeChild());await recorder.segment();const replacement=recorder.pending;for(const release of releases)release();await new Promise(resolve=>setImmediate(resolve));assert.equal(recorder.pending,replacement);assert.equal(calls.length,0);assert.equal(fs.existsSync(path.join(root,first.id+'.proof.json')),false);}finally{for(const release of releases)release();await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});
test('synchronous encoder spawn failure settles without admitting a clip',async()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'recorder-spawn-'));try{
  const container={exports:{}},load=new Function('require','module','exports',fs.readFileSync(require.resolve('../../src/hands-toy/recorder'),'utf8'));load(name=>name==='node:child_process'?{...require(name),spawn:()=>{throw Error('spawn failed');}}:name==='./retention'?{Retention}:name==='./encoder-proof'?require('../../src/hands-toy/encoder-proof'):require(name),container,container.exports);
  const instance=new container.exports.Recorder({root:directory,fake:true,shutdownMs:5,retentionOptions:{freeBytes:()=>1e12}});instance.enabled=true;await instance.segment();await instance.off();assert.equal(instance.pending,null);assert.equal(instance.reason,'spawn failed');assert.equal(Object.keys(instance.retention.data.clips).length,0);
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});
test('callbacks from a timed-out segment cannot stop or write into its replacement',{timeout:2000},async()=>{
 const {root,recorder,encoder,source,children,makeChild}=lifecycleFixture();let replacement;
 try{
  await recorder.segment();encoder.emit('error',Error('first segment failed'));await recorder.off();
  recorder.fake=true;recorder.enabled=true;replacement=makeChild();children.push(replacement);await recorder.segment();const clip=recorder.pending;
  for(const child of [encoder,source]){child.emit('error',Error('late failure'));child.emit('exit',1);child.emit('close',1);}
  encoder.stdio[3].emit('data',Buffer.from('old video'));encoder.stdio[4].emit('data',Buffer.from('old detail'));source.stdio[3].emit('data',Buffer.from('{"type":"source_error","reason":"old source"}\n'));
  await new Promise(resolve=>setImmediate(resolve));assert.equal(recorder.enabled,true);assert.equal(recorder.pending,clip);assert.deepEqual(replacement.signals,[]);assert.equal(fs.statSync(path.join(root,clip.files[0])).size,0);assert.equal(fs.statSync(path.join(root,clip.files[2])).size,0);
  replacement.stdio[3].write('new video');const stopping=recorder.pause();replacement.stdio[3].end();replacement.stdio[4].end();replacement.emit('close',0);await stopping;assert.equal(fs.readFileSync(path.join(root,clip.files[0]),'utf8'),'new video');
 }finally{replacement?.emit('close',0);await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});
test('encoded file write errors refuse the clip and settle shutdown',{timeout:2000},async()=>{
 const fileSystem={...fs,appendFileSync(){throw Error('simulated disk write failure');}}, {root,recorder,encoder,source}=lifecycleFixture({fileSystem});
 try{
  await recorder.segment();const clip=recorder.pending;assert.doesNotThrow(()=>encoder.stdio[3].emit('data',Buffer.from('video')));assert.equal(recorder.enabled,false);source.emit('close',0);encoder.emit('close',0);await recorder.off();assert.equal(recorder.retention.data.clips[clip.id],undefined);assert.equal(fs.existsSync(path.join(root,clip.files[0])),false);
 }finally{source.emit('close',0);encoder.emit('close',0);await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});
test('retention failures cannot strand segment settlement',{timeout:2000},async()=>{
 const {root,recorder,encoder,source}=lifecycleFixture();
 try{
  await recorder.segment();recorder.retention.sweep=()=>{throw Error('simulated retention failure');};recorder.retention.transaction=()=>{throw Error('simulated retention lock failure');};source.stdout.end();source.stdio[3].end();encoder.stdio[3].end();encoder.stdio[4].end();source.emit('close',0);assert.doesNotThrow(()=>encoder.emit('close',0));await recorder.segmentDone;assert.equal(recorder.pending,null);assert.equal(recorder.enabled,false);assert.match(recorder.reason,/retention/);
 }finally{source.emit('close',0);encoder.emit('close',0);await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});
test('OFF settles the owned segment even if its state file cannot be written',{timeout:2000},async()=>{
 let refuseState=false;const fileSystem={...fs,writeFileSync(file,...args){if(refuseState&&String(file).endsWith('recorder-state.json'))throw Error('simulated OFF persistence failure');return fs.writeFileSync(file,...args);}};
 const {root,recorder,encoder,source}=lifecycleFixture({fileSystem});
 try{
  await recorder.segment();refuseState=true;await assert.rejects(recorder.off(),/OFF persistence failure/);assert.equal(recorder.activeSegment,null);assert.equal(recorder.pending,null);assert.equal(recorder.enabled,false);assert.ok(source.signals.includes('SIGTERM'));assert.ok(encoder.signals.includes('SIGTERM'));
 }finally{refuseState=false;source.emit('close',0);encoder.emit('close',0);await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});
for(const ingress of ['direct','ledger'])test('event-log disk errors shut down capture through '+ingress,{timeout:2000},async()=>{
 const fileSystem={...fs,appendFileSync(){throw Error('simulated event-log disk failure');}},{root,recorder,encoder,source}=lifecycleFixture({fileSystem});
 try{
  await recorder.segment();const clip=recorder.pending,row={type:'extension',value:7};
  if(ingress==='direct')assert.equal(recorder.event(row),false);else assert.doesNotThrow(()=>source.stdio[3].emit('data',Buffer.from(JSON.stringify(row)+'\n')));
  assert.equal(recorder.enabled,false);assert.equal(source.stdout.destroyed,true);source.emit('close',0);encoder.emit('close',0);await recorder.off();assert.equal(recorder.activeSegment,null);assert.equal(recorder.retention.data.clips[clip.id],undefined);assert.match(recorder.reason,/event-log disk failure/);
 }finally{source.emit('close',0);encoder.emit('close',0);await recorder.off();fs.rmSync(root,{recursive:true,force:true});}
});
