'use strict';
// HANDS-PC owns its folder. Consume its optional handoff, never write there.
const fs=require('node:fs'),path=require('node:path');
function handoff(dir) {
 const out={checkpoint:null,train:null,cleanup:null,notes:[]};
 if(!fs.existsSync(dir))return out;
 for(const name of ['remote-training.json','report.json','integration-result.json']) {
  try {const r=JSON.parse(fs.readFileSync(path.join(dir,name),'utf8'));
   const cp=r.checkpoint||r.checkpointPath||r.startingCheckpoint;
   if(typeof cp==='string'&&path.isAbsolute(cp)&&fs.existsSync(cp))out.checkpoint=cp;
   const argv=r.remoteTrainingCommand||r.trainingCommand;
   const cleanup=r.cleanupCommand;
   if(Array.isArray(argv)&&argv.length&&argv.every(x=>typeof x==='string')&&Array.isArray(cleanup)&&cleanup.length&&cleanup.every(x=>typeof x==='string')){out.train=argv;out.cleanup=cleanup;}
   else if(argv)out.notes.push(`${name}: remote command requires argv and cleanupCommand; local fallback`);
  }catch(e){if(e.code!=='ENOENT')out.notes.push(`${name}: ${e.message}`);}
 }
 if(!out.checkpoint) {
  const cps=fs.readdirSync(dir).filter(n=>/\.pt$/.test(n)).sort();
  if(cps.length)out.checkpoint=path.join(dir,cps.at(-1));
 }
 return out;
}
function trainWithFallback(config, dataset, output, execute, local) {
 if(!config.train)return {training:local(),backend:'local',notes:config.notes};
 const replace=args=>args.map(a=>a.replaceAll('{dataset}',dataset).replaceAll('{output}',output));
 let training,error;
 try {training=JSON.parse(execute(config.train[0],replace(config.train.slice(1))));}
 catch(e){error=e.message;}
 finally { // PC copies must be removed on success AND failure, before fallback.
  execute(config.cleanup[0],replace(config.cleanup.slice(1)));
 }
 return training?{training,backend:'BensPC',notes:config.notes}:{training:local(),backend:'local-fallback',notes:[...config.notes,error]};
}
module.exports={handoff,trainWithFallback};
