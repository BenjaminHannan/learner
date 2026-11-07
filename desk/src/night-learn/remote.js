'use strict';
// HANDS-PC owns its folder. Consume its optional handoff, never write there.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),{createHash}=require('node:crypto');
function chooseCheckpoint(paths) {
 const priority=file=>path.basename(file)==='candidate.pt'?3:/^candidate.*\.pt$/.test(path.basename(file))?2:/^(old|no-intent)\.pt$/.test(path.basename(file))?-1:0;
 return paths.filter(file=>{try{return fs.statSync(file).isFile();}catch{return false;}}).sort((a,b)=>priority(a)-priority(b)||fs.statSync(a).mtimeMs-fs.statSync(b).mtimeMs).at(-1)||null;
}
function handoff(dir,{runner}={}) {
 const out={checkpoint:null,checkpointSha256:null,train:null,cleanup:null,managesCleanup:false,notes:[]},rejected=new Set();
 if(fs.existsSync(dir)) {
  for(const name of ['remote-training.json','report.json','integration-result.json']) {
   try {const r=JSON.parse(fs.readFileSync(path.join(dir,name),'utf8'));
    const cp=r.checkpoint||r.checkpointPath||r.startingCheckpoint;
    if(typeof cp==='string'&&path.isAbsolute(cp)&&fs.existsSync(cp)) {
     const digest=createHash('sha256').update(fs.readFileSync(cp)).digest('hex');
     if(r.checkpointSha256&&digest!==r.checkpointSha256){rejected.add(cp);out.notes.push(name+': declared starting-checkpoint hash mismatch; fresh init if no other compatible checkpoint');}
     else{out.checkpoint=cp;out.checkpointSha256=digest;}
    }
    const argv=r.schedulerCommand||r.remoteTrainingCommand||r.trainingCommand,cleanup=r.cleanupCommand;
    if(Array.isArray(argv)&&argv.length&&argv.every(x=>typeof x==='string')) {
     if(r.managesCleanup===true){out.train=argv;out.managesCleanup=true;out.sharedLease=r.sharedLease||null;}
     else if(Array.isArray(cleanup)&&cleanup.length&&cleanup.every(x=>typeof x==='string')){out.train=argv;out.cleanup=cleanup;}
     else out.notes.push(name+': no cleanup contract; local fallback');
    }
   }catch(e){if(e.code!=='ENOENT')out.notes.push(`${name}: ${e.message}`);}
  }
  if(!out.checkpoint) {
   for(const name of ['REPORT.md','report.md','checkpoint-path.txt'])try{
    const report=fs.readFileSync(path.join(dir,name),'utf8');
    const paths=report.match(/(?:\/|~\/)[^\s`"'<>]+\.pt/g)||[];
    const candidates=paths.map(cp=>cp.startsWith('~/')?path.join(os.homedir(),cp.slice(2)):cp);
    out.checkpoint=chooseCheckpoint([...(out.checkpoint?[out.checkpoint]:[]),...candidates].filter(cp=>!rejected.has(cp)));
   }catch(e){if(e.code!=='ENOENT')out.notes.push(name+': '+e.message);}
  }
  if(!out.checkpoint) {
   try{out.checkpoint=chooseCheckpoint(fs.readdirSync(dir).filter(n=>/\.pt$/.test(n)).map(n=>path.join(dir,n)).filter(cp=>!rejected.has(cp)));}
   catch(e){out.notes.push('optional checkpoint directory: '+e.message);}
  }
 }
 // The actual HANDS-PC CLI packs, uploads, downloads and removes its unique
 // PC job directory on success or failure. Never edit or take over its job.
 if(!out.train&&runner&&fs.existsSync(runner)) {
  out.train=[runner,'{dataset}','{output}'];
  out.managesCleanup=true;
 }
 return out;
}
function verifyRemoteTraining(training,output,{managesCleanup=false}={}) {
 if(!training||!Array.isArray(training.train)||!Array.isArray(training.held)||!training.predictions)throw Error('remote result is not trainer-compatible');
 const hashes={};
 for(const name of ['old','candidate','no-intent']) {
  const file=path.join(output,name+'.pt'),expected=training.modelSha256?.[name]||training.modelSha256?.[name+'.pt'];
  if(!/^[a-f0-9]{64}$/.test(expected||'')||createHash('sha256').update(fs.readFileSync(file)).digest('hex')!==expected)throw Error('remote checkpoint hash mismatch: '+name);
  hashes[name]=expected;
 }
 if(managesCleanup) {
  if(training.trainingBackend==='benspc-gpu') {
   if(training.remote?.transport?.pcCleanup?.deleted!==true)throw Error('PC recording-copy deletion was not confirmed');
   if(training.remote?.transport?.sharedLeaseReleased!==true)throw Error('shared GPU lease release was not confirmed');
  }else if(training.trainingBackend!=='mac-cpu-fallback'||training.remote?.fallback!==true)throw Error('managed runner returned an unknown training backend');
 }
 training.modelSha256=hashes;
 return training;
}
function trainWithFallback(config,dataset,output,execute,local,verify=x=>x) {
 if(!config.train)return {training:local(),backend:'local',notes:config.notes};
 const replace=args=>args.map(a=>a.replaceAll('{dataset}',dataset).replaceAll('{output}',output));
 let training,error,cleanupError;
 try {training=verify(JSON.parse(execute(config.train[0],replace(config.train.slice(1)))));}
 catch(e){if(config.managesCleanup&&/Cleanup unconfirmed|No local fallback permitted/i.test(e.message))throw e;error=e.message;training=null;}
 finally {
  if(config.cleanup)try{execute(config.cleanup[0],replace(config.cleanup.slice(1)));}
  catch(e){cleanupError='PC copy cleanup needs retry: '+e.message;}
 }
 const notes=[...config.notes,...(error?[error]:[]),...(cleanupError?[cleanupError]:[]),...(training?.fallbackReason?[training.fallbackReason]:[])];
 const localManaged=training?.trainingBackend==='mac-cpu-fallback'&&training.remote?.fallback===true;
 const remoteCopiesDeleted=config.managesCleanup?(localManaged||training?.remote?.transport?.pcCleanup?.deleted===true):!cleanupError;
 return training?{training,backend:localManaged?'local-fallback':'BensPC',notes,remoteCopiesDeleted}:{training:local(),backend:'local-fallback',notes,remoteCopiesDeleted};
}
module.exports={handoff,trainWithFallback,verifyRemoteTraining};
