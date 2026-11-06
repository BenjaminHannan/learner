'use strict';
const fs=require('node:fs'),path=require('node:path'),{Recorder}=require('./lib/recorder');
const base=__dirname,fake=process.argv.includes('--fake'),state=path.join(base,'state.json'),pidFile=path.join(base,'recorder.pid'),recordings=path.join(base,fake?'fake-recordings':'recordings');
const old=fs.existsSync(state)?JSON.parse(fs.readFileSync(state,'utf8')):{};
if(!fake&&old.enabled!==true){console.log('OFF: run ./recorderctl start only after the lead gives the go.');process.exit(0);}
if(fs.existsSync(pidFile)){const p=Number(fs.readFileSync(pidFile));try{process.kill(p,0);throw Error('recorder already running');}catch(e){if(e.code!=='ESRCH')throw e;}}
fs.writeFileSync(pidFile,String(process.pid),{mode:0o600});let ending=false;
const r=new Recorder({root:recordings,fake,releaseApproved:!fake&&old.enabled===true,nativeHelper:path.join(base,'Hands Recorder.app/Contents/MacOS/hands-recorder')});
async function stop(){if(ending)return;ending=true;fs.writeFileSync(state,JSON.stringify({enabled:false}));clearInterval(heartbeat);try{await r.off();}finally{if(fs.existsSync(pidFile)&&Number(fs.readFileSync(pidFile))===process.pid)fs.unlinkSync(pidFile);fs.writeFileSync(path.join(base,'status.json'),JSON.stringify({...r.status(),stopped:true,at:new Date().toISOString()}));process.exit(0);}}
process.on('SIGTERM',stop);process.on('SIGINT',stop);process.on('uncaughtException',e=>{console.error(e);stop();});process.on('unhandledRejection',e=>{console.error(e);stop();});
const heartbeat=setInterval(()=>{fs.writeFileSync(path.join(base,'status.json'),JSON.stringify({...r.status(),at:new Date().toISOString()}));if(!fake){let enabled=false;try{enabled=JSON.parse(fs.readFileSync(state)).enabled===true;}catch(e){}if(!enabled)stop();}},500);
r.on().then(()=>console.log(fake?'FAKE recording active':'Local recording active')).catch(e=>{console.error(e.message);stop();});
