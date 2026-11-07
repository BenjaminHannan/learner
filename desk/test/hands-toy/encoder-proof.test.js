'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto'),{spawn}=require('node:child_process'),{once}=require('node:events'),{PassThrough}=require('node:stream');
const {submission,finalize,recipe,FRAME_BYTES}=require('../../src/hands-toy/encoder-proof');
test('two CPU frames require complete byte, source, launch, recipe and PTS evidence',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'encoder-proof-')),file=path.join(root,'main.mp4'),ffmpeg='/opt/homebrew/bin/ffmpeg';
 try{
  const args=['-nostdin','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','bgra','-video_size','1280x720','-framerate','20','-i','pipe:0','-filter_complex','[0:v]split=2[a][b];[b]crop=192:192[c]','-map','[a]','-fps_mode','passthrough','-c:v','libx264','-threads','1','-b:v','2500k','-pix_fmt','yuv420p','-t','30','-movflags','frag_keyframe+empty_moov','-f','mp4','pipe:3','-map','[c]','-fps_mode','passthrough','-c:v','libx264','-threads','1','-b:v','200k','-pix_fmt','yuv420p','-t','30','-movflags','frag_keyframe+empty_moov','-f','mp4','pipe:4'];
  const child=spawn(ffmpeg,args,{stdio:['pipe','ignore','pipe','pipe','pipe']}),closed=once(child,'close');let errors='';child.stderr.on('data',chunk=>errors+=chunk);const output=fs.createWriteStream(file),outputDone=once(output,'finish');child.stdio[3].pipe(output);child.stdio[4].resume();
  const {state,sink}=submission(child,args,'cpu-test'),raw=Buffer.alloc(FRAME_BYTES*2,127);raw[FRAME_BYTES]=128;
  sink.write(raw.subarray(0,137));sink.write(raw.subarray(137,FRAME_BYTES+41));sink.end(raw.subarray(FRAME_BYTES+41));
  const [code,signal]=await closed;await outputDone;assert.equal(code,0,errors);assert.equal(signal,null);
  const sha=data=>crypto.createHash('sha256').update(data).digest('hex');
  const sourceRows=[0,1].map(index=>({type:'frame',sourceContract:'hands-toy-bgra-frame-v1',session:'cpu-test',sourcePid:process.pid,frameId:index+1,rawByteCount:FRAME_BYTES,rawSha256:sha(raw.subarray(index*FRAME_BYTES,(index+1)*FRAME_BYTES)),presentationValue:100+index*51,presentationTimescale:1000,presentationFlags:1,presentationEpoch:0,receiveMonotonicMs:1000+index*51,writeCompleteMonotonicMs:1001+index*51}));
  const fileHash=async name=>{const hash=crypto.createHash('sha256');for await(const chunk of fs.createReadStream(name))hash.update(chunk);return hash.digest('hex');};
  const common={ownedLaunch:true,exitCode:0,signal:null,closeObserved:true};
  const provenance={session:'cpu-test',source:{...common,sha256:await fileHash(process.execPath),pid:process.pid,command:process.execPath,args:['--capture','--proof-session','cpu-test'],stopCause:'stdin-eof'},encoder:{...common,sha256:await fileHash(ffmpeg),pid:child.pid,command:ffmpeg,args,mainOutputFile:file,mainOutputClosed:true}};
  const opts={state,code,file,sourceRows,sourceComplete:true,provenance};
  const proof=JSON.parse(finalize(opts));assert.equal(proof.temporalCorrespondence,true);assert.equal(proof.sourceTimePassthrough,false);assert.equal(proof.geometryVerified,false);assert.equal(proof.learningEligible,false);assert.deepEqual(proof.inputs.map(entry=>entry.sourcePTS.value),[100,151]);assert.deepEqual(proof.inputs.map(entry=>entry.generatedPts),[0,1]);assert.equal(proof.output.presentationPts.length,2);
  const copy=()=>structuredClone(opts);const rejects=[
   value=>delete value.provenance,value=>value.provenance.session='wrong',value=>value.provenance.source.pid++,value=>value.provenance.encoder.pid++,value=>value.provenance.source.ownedLaunch=false,value=>value.provenance.encoder.closeObserved=false,value=>value.provenance.source.exitCode=1,value=>value.provenance.source.signal='SIGTERM',value=>value.provenance.source.stopCause='forced',value=>value.provenance.encoder.mainOutputClosed=false,value=>value.provenance.source.args.pop(),value=>value.provenance.encoder.sha256='bad',value=>value.provenance.encoder.args[15]='bad',value=>delete value.sourceRows[0].rawSha256,value=>value.sourceRows[0].rawSha256='0'.repeat(64),value=>value.sourceRows[0].rawByteCount--,value=>value.sourceRows[0].session='wrong',value=>value.sourceRows[0].sourcePid++,value=>value.sourceRows[0].sourceContract='wrong',value=>value.sourceRows[1].frameId=1,value=>value.sourceRows[1].presentationValue=100,value=>value.sourceRows[0].presentationTimescale=0,value=>value.sourceRows[0].presentationFlags=0,value=>value.sourceRows[0].presentationEpoch=1,value=>value.sourceRows[0].receiveMonotonicMs=NaN,value=>value.sourceRows[0].writeCompleteMonotonicMs=0,value=>value.sourceRows.pop(),value=>value.state.inputs[0].writeComplete=false,value=>value.sourceComplete=false,value=>value.truncated=true,value=>value.code=1,value=>value.state.partialBytes=1,value=>value.state.failed=true,value=>value.state.ended=false
  ];for(const mutate of rejects){const value=copy();mutate(value);assert.throws(()=>finalize(value));}
  assert.throws(()=>finalize({...opts,provenance:undefined}),/provenance/);const altered=[...args];altered[altered.indexOf('[0:v]split=2[a][b];[b]crop=192:192[c]')]='[0:v]fps=20,split=2[a][b];[b]crop=192:192[c]';assert.equal(recipe(altered),false);
  const oversized=copy();oversized.sourceRows[0].extra='x'.repeat(4097);assert.throws(()=>finalize(oversized),/source frame/);
  fs.truncateSync(file,0);assert.throws(()=>finalize(opts),/output file size/);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('partial frame refuses proof',async()=>{const stdin=new PassThrough();stdin.resume();const {state,sink}=submission({stdin},[],'partial');sink.end(Buffer.alloc(101));await once(sink,'finish');assert.equal(state.partialBytes,101);assert.throws(()=>finalize({state,code:0,sourceComplete:true}),/incomplete/);});
test('proof refuses while encoder stdin finalization remains unfinished',{timeout:2000},async()=>{
 const {Writable}=require('node:stream');let completeEnd;
 const stdin=new Writable({write(chunk,encoding,callback){callback();},final(callback){completeEnd=callback;}}),{state,sink}=submission({pid:123,stdin},[],'delayed-final');const finished=once(sink,'finish');
 try{
  sink.end(Buffer.alloc(FRAME_BYTES));await new Promise(resolve=>setImmediate(resolve));assert.equal(typeof completeEnd,'function');assert.equal(stdin.writableFinished,false);assert.equal(sink.writableFinished,false);assert.equal(state.ended,false);assert.throws(()=>finalize({state,code:0,sourceComplete:true}),/incomplete encoder submission/);
 }finally{completeEnd?.();await finished;}
 assert.equal(stdin.writableFinished,true);assert.equal(sink.writableFinished,true);assert.equal(state.ended,true);
});
