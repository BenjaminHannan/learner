'use strict';
const fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
// Use HANDS-ACT's LaunchServices pattern so TCC sees Premonition's identity.
function launchCalibration(work,{execute=spawnSync,now=Date.now,pause=()=>Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,250)}={}) {
 const status=path.join(work,'coordinate-result.json'),stdout=path.join(work,'coordinate.out'),stderr=path.join(work,'coordinate.err');
 try {
  for(const file of [stdout,stderr])fs.writeFileSync(file,'',{mode:0o600});
  const child=execute('/usr/bin/open',['-n','-j','-g','-a','/Applications/Premonition.app','--env','ELECTRON_RUN_AS_NODE=1','--stdout',stdout,'--stderr',stderr,'--args',path.join(__dirname,'calibrate.js'),work,status],{encoding:'utf8',timeout:15000});
  if(child.error||child.status!==0)throw Error(child.error?.message||child.stderr||'Premonition calibration launch failed');
  const deadline=now()+240000;
  while(now()<deadline) {
   if(fs.existsSync(status))return JSON.parse(fs.readFileSync(status,'utf8'));
   pause();
  }
  throw Error('Premonition coordinate check did not report within four minutes');
 }catch(error){return {passed:false,status:'coords-unverified',reason:error.message};}
}
module.exports={launchCalibration};
