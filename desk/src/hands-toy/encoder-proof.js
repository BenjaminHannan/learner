'use strict';
const fs=require('node:fs'),crypto=require('node:crypto'),{Writable}=require('node:stream'),{execFileSync}=require('node:child_process');
const FRAME_BYTES=1280*720*4,MAX_FRAMES=600,MAX_PROOF_BYTES=256*1024,MAX_FILE_BYTES=64*1024*1024;
const SOURCE_CONTRACT='hands-toy-bgra-frame-v1';
function submission(encoder,args,session){
 const state={session,args:[...args],encoderPid:encoder.pid,inputs:[],partialBytes:0,failed:false,ended:false};let parts=[],bytes=0;
 const sink=new Writable({write(chunk,encoding,callback){
  if(chunk.length>FRAME_BYTES*2){state.failed=true;return callback(Error('chunk limit'));}
  let offset=0;
  const next=()=>{if(offset===chunk.length)return callback();const length=Math.min(FRAME_BYTES-bytes,chunk.length-offset);parts.push(chunk.subarray(offset,offset+length));bytes+=length;offset+=length;if(bytes<FRAME_BYTES)return next();
   if(state.inputs.length>=MAX_FRAMES){state.failed=true;return callback(Error('frame limit'));}
   const frame=Buffer.concat(parts,FRAME_BYTES),entry={ordinal:state.inputs.length+1,rawBytes:FRAME_BYTES,rawSha256:crypto.createHash('sha256').update(frame).digest('hex'),generatedPts:state.inputs.length,generatedTimeBase:'1/20',writeComplete:false};parts=[];bytes=0;state.inputs.push(entry);
   encoder.stdin.write(frame,error=>{if(error){state.failed=true;callback(error);}else{entry.writeComplete=true;next();}});
  };next();
 },final(callback){state.partialBytes=bytes;encoder.stdin.end(callback);}});
 sink.once('finish',()=>{state.ended=true;});sink.on('error',()=>{state.failed=true;});encoder.stdin.on('error',()=>{state.failed=true;});return {state,sink};
}
function recipe(args){
 const prefix=['-nostdin','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','bgra','-video_size','1280x720','-framerate','20','-i','pipe:0','-filter_complex','[0:v]split=2[a][b];[b]crop=192:192[c]'];
 const output=(map,rate,pipe,codec)=>['-map',map,'-fps_mode','passthrough','-c:v',codec,...(codec==='libx264'?['-threads','1']:[]),'-b:v',rate,'-pix_fmt','yuv420p','-t','30','-movflags','frag_keyframe+empty_moov','-f','mp4',pipe];
 return ['h264_videotoolbox','libx264'].some(codec=>JSON.stringify(args)===JSON.stringify([...prefix,...output('[a]','2500k','pipe:3',codec),...output('[c]','200k','pipe:4',codec)]));
}
function validProcess(process){return process&&Number.isSafeInteger(process.pid)&&process.pid>0&&typeof process.command==='string'&&process.command.length>0&&process.command.length<=4096&&Array.isArray(process.args)&&process.args.length<=128&&process.args.every(arg=>typeof arg==='string'&&arg.length<=4096)&&/^[a-f0-9]{64}$/.test(process.sha256)&&process.ownedLaunch===true&&process.exitCode===0&&process.signal===null&&process.closeObserved===true;}
function hashFile(file){
 const fd=fs.openSync(file,'r');try{const stat=fs.fstatSync(fd);if(!stat.isFile()||stat.size<=0||stat.size>MAX_FILE_BYTES)throw Error('output file size');const hash=crypto.createHash('sha256'),buffer=Buffer.allocUnsafe(256*1024);let total=0,read;while((read=fs.readSync(fd,buffer,0,buffer.length,null))!==0){total+=read;if(total>MAX_FILE_BYTES)throw Error('output file size');hash.update(buffer.subarray(0,read));}if(total!==stat.size||fs.fstatSync(fd).size!==stat.size)throw Error('output file changed');return {bytes:total,sha256:hash.digest('hex')};}finally{fs.closeSync(fd);}
}
function finalize({state,code,file,sourceRows,sourceComplete,ffprobe='/opt/homebrew/bin/ffprobe',truncated=false,provenance}){
 if(!state||state.failed||!state.ended||state.partialBytes||truncated||code!==0||sourceComplete!==true||!state.inputs.length||state.inputs.length>MAX_FRAMES)throw Error('incomplete encoder submission');
 const source=provenance?.source,encoder=provenance?.encoder;
 if(typeof state.session!=='string'||!state.session.length||state.session.length>256||provenance?.session!==state.session||!validProcess(source)||!validProcess(encoder)||source.pid===encoder.pid||encoder.pid!==state.encoderPid||JSON.stringify(encoder.args)!==JSON.stringify(state.args)||!recipe(state.args)||source.stopCause!=='stdin-eof'||source.args.filter(arg=>arg==='--capture').length!==1||source.args.filter(arg=>arg==='--proof-session').length!==1||source.args[source.args.indexOf('--proof-session')+1]!==state.session||encoder.mainOutputFile!==file||encoder.mainOutputClosed!==true)throw Error('source or encoder provenance or recipe invalid');
 if(!Array.isArray(sourceRows)||sourceRows.length!==state.inputs.length||sourceRows.length>MAX_FRAMES)throw Error('source frame count mismatch');
 let previousPts=null,previousReceive=-Infinity,previousWrite=-Infinity;
 const inputs=state.inputs.map((entry,index)=>{const row=sourceRows[index];
  if(!row||typeof row!=='object'||Buffer.byteLength(JSON.stringify(row))>4096||row.type!=='frame'||row.sourceContract!==SOURCE_CONTRACT||row.session!==state.session||row.sourcePid!==source.pid||row.frameId!==index+1||row.rawByteCount!==FRAME_BYTES||row.rawSha256!==entry.rawSha256||!entry.writeComplete||entry.ordinal!==index+1||entry.rawBytes!==FRAME_BYTES||entry.generatedPts!==index||entry.generatedTimeBase!=='1/20')throw Error('source frame byte or identity mismatch');
  const {presentationValue:value,presentationTimescale:timescale,presentationFlags:flags,presentationEpoch:epoch,receiveMonotonicMs:receive,writeCompleteMonotonicMs:write}=row;
  if(!Number.isSafeInteger(value)||!Number.isSafeInteger(timescale)||timescale<=0||!Number.isSafeInteger(flags)||flags!==1||!Number.isSafeInteger(epoch)||epoch!==0||!Number.isFinite(receive)||!Number.isFinite(write)||receive<0||write<receive||receive<previousReceive||write<previousWrite)throw Error('invalid source PTS or clock');
  if(previousPts&&BigInt(value)*BigInt(previousPts.timescale)<=BigInt(previousPts.value)*BigInt(timescale))throw Error('nonmonotonic source PTS');previousPts={value,timescale};previousReceive=receive;previousWrite=write;
  return {...entry,sourceFrameId:row.frameId,sourcePTS:{value,timescale,flags,epoch},receiveMonotonicMs:receive,writeCompleteMonotonicMs:write};
 });
 const outputHash=hashFile(file);
 const parsed=JSON.parse(execFileSync(ffprobe,['-v','error','-select_streams','v:0','-show_entries','stream=time_base:frame=pts','-of','json',file],{encoding:'utf8',timeout:5000,maxBuffer:1024*1024}));
 const timeBase=parsed.streams?.[0]?.time_base,match=/^(\d+)\/(\d+)$/.exec(timeBase||'');if(!match||!Number.isSafeInteger(+match[1])||!Number.isSafeInteger(+match[2])||+match[1]<=0||+match[2]<=0||!Array.isArray(parsed.frames)||parsed.frames.length!==inputs.length)throw Error('output frame count or timebase mismatch');
 const tick=+match[1]/+match[2];let previous=-Infinity;const output=parsed.frames.map((frame,index)=>{const pts=frame.pts;if(!Number.isSafeInteger(pts)||pts<=previous||Math.abs(pts*tick-index/20)>tick/2+1e-9)throw Error('output PTS mismatch');previous=pts;return pts;});
 const proof={version:2,sourceContract:SOURCE_CONTRACT,session:state.session,provenance,encoderArgs:state.args,inputTimeBase:'1/20',inputs,output:{...outputHash,timeBase,presentationPts:output},temporalCorrespondence:true,sourceTimePassthrough:false,geometryVerified:false,learningEligible:false};
 const data=Buffer.from(JSON.stringify(proof)+'\n');if(data.length>MAX_PROOF_BYTES)throw Error('proof size limit');return data;
}
module.exports={submission,finalize,recipe,FRAME_BYTES,MAX_PROOF_BYTES};
