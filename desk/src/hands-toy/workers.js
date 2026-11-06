'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),{spawn}=require('node:child_process');const {Worker,isMainThread,parentPort,workerData}=require('node:worker_threads');
const {Sandbox}=require('./sandbox'),{Lease,now}=require('./lease');
const SIZE=8+320*180*3+192*192*3;
function crop(pixels,cursor){const out=Buffer.alloc(192*192*3);for(let y=0;y<192;y++){const py=Math.floor(cursor[1])+y-96;if(py<0||py>=180)continue;for(let x=0;x<192;x++){const px=Math.floor(cursor[0])+x-96;if(px<0||px>=320)continue;const a=(py*320+px)*3,b=(y*192+x)*3;pixels.copy(out,b,a,a+3);}}return out;}
if(!isMainThread){
 const s=new Sandbox(workerData),fd=fs.openSync(workerData.frameFile,'r+');let lease;
 if(workerData.role==='capture'){
  const timer=setInterval(()=>{const f=s.render(),c=crop(f.pixels,s.cursor),header=Buffer.alloc(8);fs.writeSync(fd,header,0,8,0);fs.writeSync(fd,f.pixels,0,f.pixels.length,8);fs.writeSync(fd,c,0,c.length,8+f.pixels.length);header.writeBigUInt64LE(BigInt(f.frameId));fs.writeSync(fd,header,0,8,0);parentPort.postMessage({frameId:f.frameId,producedMs:f.producedMs,renderEndMs:f.renderEndMs,captureMs:now(),cursor:s.cursor,task:s.task,episode:s.task+':'+s.seed,text:s.expected,textIndex:s.typed.length,textLength:s.expected.length,keys:s.keys,outcome:s.outcome()});},1000/60);
  lease=new Lease({apply:p=>{const receivedMs=s.receive(p);parentPort.postMessage({receipt:true,frameId:p.frameId,receivedMs,release:!!p.release});}});
  parentPort.on('message',m=>{if(m.op==='grant'){parentPort.postMessage({grant:lease.grant({sandbox:true,watcherReady:true,windowId:'sandbox',intentVersion:m.version})});}else if(m.op==='packet')parentPort.postMessage({applied:lease.packet(m.packet),frameId:m.packet.frameId});else if(m.op==='stop')lease.revoke(m.reason);else if(m.op==='close'){clearInterval(timer);lease.close();fs.closeSync(fd);parentPort.close();}});
 }
}else{
 class PixelWorker {
  constructor({artifact,frameFile,python=path.join(os.homedir(),'learner-ops/nb2-venv/bin/python')}){
   this.pending=null;this.child=spawn(python,[path.join(__dirname,'../../tools/hands-toy/policy.py'),'worker',artifact,frameFile],{stdio:['pipe','pipe','pipe']});this.stderr='';let buf='';
   this.ready=new Promise((resolve,reject)=>{this.child.on('error',reject);this.child.stdout.on('data',d=>{buf+=d;let i;while((i=buf.indexOf('\n'))>=0){const line=buf.slice(0,i);buf=buf.slice(i+1);let m;try{m=JSON.parse(line);}catch(e){reject(Error('bad policy protocol'));continue;}if(m.ready)resolve(m);else if(this.pending){const p=this.pending;this.pending=null;clearTimeout(p.timer);m.error?p.reject(Error(m.error)):p.resolve(m);}}});this.child.on('exit',code=>{if(this.pending){clearTimeout(this.pending.timer);this.pending.reject(Error('policy exited '+code));this.pending=null;}reject(Error(this.stderr||'policy exited '+code));});});
   this.child.stderr.on('data',d=>{this.stderr=(this.stderr+d).slice(-2000);});
  }
  predict(frame){if(this.pending)return Promise.resolve({dropped:true,reason:'busy'});return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{if(this.pending){this.pending=null;this.child.kill();reject(Error('policy timeout'));}},2000);this.pending={resolve,reject,timer};this.child.stdin.write(JSON.stringify(frame)+'\n');});}
  close(){this.child.stdin.end();this.child.kill();}
 }
 class CaptureWorker {
  constructor({task,seed,dir}){fs.mkdirSync(dir,{recursive:true,mode:0o700});this.frameFile=path.join(dir,'frame-'+process.pid+'-'+Math.random().toString(16).slice(2));const fd=fs.openSync(this.frameFile,'wx',0o600);fs.ftruncateSync(fd,SIZE);fs.closeSync(fd);this.worker=new Worker(__filename,{workerData:{role:'capture',task,seed,frameFile:this.frameFile}});}
  close(){this.worker.postMessage({op:'close'});return this.worker.terminate().finally(()=>{try{fs.unlinkSync(this.frameFile);}catch(e){if(e.code!=='ENOENT')throw e;}});}
 }
 module.exports={PixelWorker,CaptureWorker,crop,SIZE};
}
