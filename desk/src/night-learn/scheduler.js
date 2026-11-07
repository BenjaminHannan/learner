'use strict';
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawnSync}=require('node:child_process');
const root=path.join(os.homedir(),'learner-ops/night-learn');
function due(now,idleSeconds) {return now.getHours()>=1&&now.getHours()<7&&Number.isFinite(idleSeconds)&&idleSeconds>=1200;}
function idle() {
 const r=spawnSync('/usr/sbin/ioreg',['-c','IOHIDSystem'],{encoding:'utf8',timeout:5000,maxBuffer:1024*1024});
 if(r.status!==0||r.error)throw Error('Mac idle time unavailable');const m=/"HIDIdleTime"\s*=\s*(\d+)/.exec(r.stdout);
 if(!m)throw Error('Mac idle time unavailable');return Number(m[1])/1e9;
}
function previousDay(now) {const d=new Date(now.getFullYear(),now.getMonth(),now.getDate()-1);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
function acquire(dir) {
 try {fs.mkdirSync(dir,{mode:0o700});fs.writeFileSync(path.join(dir,'pid'),String(process.pid),{mode:0o600});return true;}
 catch(e){if(e.code!=='EEXIST')throw e;let pid;try{pid=Number(fs.readFileSync(path.join(dir,'pid'),'utf8'));}catch{return false;}
  if(!Number.isSafeInteger(pid)||pid<=0)return false;try{process.kill(pid,0);return false;}catch(err){if(err.code!=='ESRCH')return false;}
  fs.rmSync(dir,{recursive:true,force:true});return acquire(dir);}
}
function main(){
 const now=new Date();if(!due(now,idle()))return;
 const day=previousDay(now);if(fs.existsSync(path.join(root,'runs',day,'result.json')))return;
 fs.mkdirSync(root,{recursive:true,mode:0o700});const lock=path.join(root,'.schedule-lock');if(!acquire(lock))return;
 try{const r=spawnSync(process.execPath,[path.join(__dirname,'run.js')],{encoding:'utf8',timeout:6*3600000,maxBuffer:1024*1024});
  const status={at:new Date().toISOString(),day,exit:r.status,error:r.error?.message||null,detail:(r.stderr||'').slice(-2000)};
  fs.appendFileSync(path.join(root,'schedule.log'),JSON.stringify(status)+'\n',{mode:0o600});
 }finally{fs.rmSync(lock,{recursive:true,force:true});}
}
module.exports={due,previousDay,acquire};
if(require.main===module){try{main();}catch(e){console.error(String(e.message));process.exitCode=1;}}
