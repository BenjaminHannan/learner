'use strict';
// Quarantined nightly coordinator. No live policy is ever promoted here.
const fs=require('node:fs'), os=require('node:os'), path=require('node:path'), crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const {createFileDecoder}=require('../screen-learning/video-decoder');
const {compile}=require('./compile');
const {score}=require('./score');
const {readAttempts}=require('./attempts');
const {verifiedCorrection}=require('./corrections');
const {Retention}=require('../hands-toy/retention');
const {handoff,trainWithFallback}=require('./remote');
const home=os.homedir(), ops=path.join(home,'learner-ops'), root=path.join(ops,'night-learn');
const python=path.join(ops,'p2venv/bin/python'), lock=path.join(ops,'bin/realmodel-lock.sh'), ffmpeg='/opt/homebrew/bin/ffmpeg', ffprobe='/opt/homebrew/bin/ffprobe';
const sourceDir=__dirname, nightGate=path.join(sourceDir,'night_gate.py'), sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const write=(p,o)=>fs.writeFileSync(p,JSON.stringify(o,null,2)+'\n',{mode:0o600});
function run(binary,args,options={}) {const r=spawnSync(binary,args,{encoding:'utf8',maxBuffer:32*1024*1024,timeout:binary===lock?undefined:1800000,...options});if(r.error||r.status!==0)throw Error(`${path.basename(binary)} failed: ${r.error?.message||String(r.stderr||'').slice(-1600)||r.status}`);return r.stdout;}
function gate(dryRun=false) {if(!dryRun)run(python,['-c',`import sys;sys.path.insert(0,${JSON.stringify(sourceDir)});import trainer;trainer.production_gate()`],{timeout:10000});}
function readClipFile(recordings,name) {if(typeof name!=='string'||path.basename(name)!==name)throw Error('unsafe clip path');const file=path.join(recordings,name),st=fs.lstatSync(file);if(!st.isFile()||st.isSymbolicLink())throw Error('unsafe clip file');return file;}
function targetDay(date) {const d=new Date(date.getFullYear(),date.getMonth(),date.getDate()-1);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
function localDay(ms) {const d=new Date(ms);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
function writeFrame(image,dest) {
 const r=spawnSync(ffmpeg,['-v','error','-f','rawvideo','-pix_fmt','rgba','-s',`${image.width}x${image.height}`,'-i','pipe:0','-frames:v','1','-y',dest],{input:image.pixels,timeout:15000,maxBuffer:65536});if(r.error||r.status!==0)throw Error('could not save exact frame');fs.chmodSync(dest,0o600);
}
function sourceClips(index,day,calibration,work,recordings) {
 const examples=[],trainedClipTimes={},rejections=[],wallBounds=[];
 const clips=Object.values(index.clips||{}).filter(c=>!c.spent&&!c.audit&&c.app==='whole-display'&&(!day||localDay(c.createdMs)===day)).sort((a,b)=>a.createdMs-b.createdMs);
 for(const clip of clips) {
  try {
   const video=readClipFile(recordings,clip.id+'.mp4'),bytes=fs.readFileSync(video),decoder=createFileDecoder({file:video,expected:{bytes:bytes.length,sha256:sha(bytes)},ffmpeg,ffprobe});
   const rows=fs.readFileSync(readClipFile(recordings,clip.id+'.events.jsonl'),'utf8').split('\n').filter(Boolean).map(JSON.parse);
   // Persist each exact decoded frame once, as the compiler consumes it.
   const saved=new Map(),cachedDecoder={...decoder,readFrame(n){const image=decoder.readFrame(n);if(!saved.has(n)){const file=path.join(work,sha(clip.id+':'+n)+'.png');writeFrame(image,file);saved.set(n,file);}return image;}};
   const out=compile({clip,rows,decoder:cachedDecoder,calibration});rejections.push(...out.rejects.map(r=>({clip:clip.id,...r})));
   const frames=rows.filter(r=>r.type==='frame'),anchor=rows.find(r=>r.type==='clock_anchor');
   if(!frames.length||!anchor)continue;
   trainedClipTimes[clip.id]=frames.at(-1).receiveMonotonicMs-frames[0].receiveMonotonicMs+50;
   wallBounds.push(frames[0].receiveMonotonicMs+anchor.wallTimeMs-anchor.t,frames.at(-1).receiveMonotonicMs+anchor.wallTimeMs-anchor.t+50);
   for(const row of out.examples){const file=saved.get(row.frameOrdinal);examples.push({...row,frame:file,frameFileSha256:sha(fs.readFileSync(file)),clipId:clip.id,clipVideoSha256:decoder.source.sha256,sourceBounds:frames[0].transform?.sourceBounds});}
  }catch(error){rejections.push({clip:clip.id,reason:String(error.message)});}
 }
 return {examples:examples.sort((a,b)=>a.timeMs-b.timeMs),trainedClipTimes,rejections,clipsSeen:clips.length,startMs:wallBounds.length?Math.floor(Math.min(...wallBounds)):0,endMs:wallBounds.length?Math.ceil(Math.max(...wallBounds)):1};
}
function groupEpisodes(rows) {
 const groups=[];
 for(const row of rows){const g=groups.at(-1),first=g?.[0],prev=g?.at(-1);if(!g||g.length>=80||row.timeMs-prev.timeMs>120000||row.timeMs-first.timeMs>300000)groups.push([]);groups.at(-1).push(row);}
 return groups;
}
function retryBackground(request,pause=()=>run('/bin/sleep',['15'])) {
 for(let attempt=0;;attempt++)try{return request();}catch(error){
  if(attempt>=3||!/HTTP Error (429|503)|timed out|no explanation text|Connection refused|invalid Glim explanation|Expecting .*delimiter|Expecting value/.test(error.message))throw error;
  // Release the FIFO ticket before backing off. Each retry takes a new turn.
  pause();
 }
}
function locked(args,dryRun) {return retryBackground(()=>run(lock,['NIGHT-LEARN','/usr/bin/python3',nightGate,...(dryRun?['--dry-run']:[]),...args]));}
function teacher(episode,work,dryRun) {
 gate(dryRun);
 const picks=[0,Math.floor((episode.length-1)/2),episode.length-1].filter((n,i,a)=>a.indexOf(n)===i);
 const input={frames:picks.map(i=>({path:episode[i].frame,timeMs:episode[i].timeMs})),actions:episode.map(e=>e.action)};
 const file=path.join(work,'episode.json');write(file,input);
 const raw=locked(['/usr/bin/python3',path.join(sourceDir,'explain.py'),file],dryRun);
 const explanation=JSON.parse(raw.trim().split('\n').at(-1));
 return {explanation,labelled:episode.map((e,i)=>({...e,intent:explanation.steps[i].intent}))};
}
function runNight({dryRun=false,fixture=false,output:requestedOutput,trainingSteps=100}={}) {
 gate(dryRun);
 const day=targetDay(new Date()),output=requestedOutput||path.join(root,dryRun?'dry-runs':'runs',dryRun?new Date().toISOString().replaceAll(':','-'):day);
 fs.mkdirSync(output,{recursive:true,mode:0o700});const work=fs.mkdtempSync(path.join(output,'work-'));fs.chmodSync(work,0o700);
 let recordings=path.join(ops,'hands-recorder/recordings'),synthetic=false;
 const warnings=[],stages=[];
 try {
  let live=false;try{live=JSON.parse(fs.readFileSync(path.join(ops,'hands-recorder/state.json'))).enabled===true&&Object.keys(JSON.parse(fs.readFileSync(path.join(recordings,'clip-index.json'))).clips||{}).length>0;}catch{}
  if(dryRun&&(fixture||!live)){recordings=path.join(output,'synthetic-recording');run(python,[path.join(sourceDir,'synthetic.py'),recordings]);synthetic=true;}
  let calibration={passed:false,status:'coords-unverified',reason:dryRun?'dry run does not post desktop events':'coordinate probe unavailable'};
  let index={clips:{}};try{index=JSON.parse(fs.readFileSync(path.join(recordings,'clip-index.json')));}catch(e){warnings.push('recording index: '+e.message);}
  const prepared=sourceClips(index,dryRun?null:day,calibration,work,recordings);stages.push('compile');
  const explanations=[],rows=[];
  // Missing Glim is an actual stage failure, not an optional-check failure.
  for(const episode of groupEpisodes(prepared.examples)){const r=teacher(episode,work,dryRun);explanations.push(r.explanation);rows.push(...r.labelled);}
  write(path.join(output,'explanations.json'),explanations);stages.push('Glim');
  let failures=[];
  try{failures=readAttempts(path.join(ops,'hands-attempts/attempts.jsonl')).filter(a=>a.judgedOutcome==='fail'&&localDay(Date.parse(a.finishedAt))===day);}
  catch(e){warnings.push('optional attempt log: '+e.message);}
  const mistakes=[];
  for(const failure of failures){try{const f=path.join(work,'attempt.json');write(f,failure);mistakes.push(JSON.parse(locked(['/usr/bin/python3',path.join(sourceDir,'explain.py'),'--mistake',f],dryRun).trim().split('\n').at(-1)));}catch(e){warnings.push('optional mistake explanation: '+e.message);}}
  const cutoff=prepared.startMs+(prepared.endMs-prepared.startMs)*.8;let correctionsUsed=0;const seen=new Set(rows.map(r=>r.id));
  for(const failure of failures)for(const candidate of failure.correctionCandidates||[])try{const c=verifiedCorrection(path.join(ops,'hands-attempts'),candidate);if(c.timeMs>=prepared.startMs&&c.timeMs<cutoff&&!seen.has(c.id)){rows.push(c);seen.add(c.id);correctionsUsed++;}}catch(e){warnings.push('optional correction: '+e.message);}
  // Tighten sparse bounds to observed actions so even a short, uneven first
  // night has a genuine later holdout. A single action is train-only.
  rows.sort((a,b)=>a.timeMs-b.timeMs);
  const startMs=rows.length?rows[0].timeMs:0,endMs=rows.length>1?rows.at(-1).timeMs:startMs+1;
  const dataset={startMs,endMs,examples:rows,allowSparse:true,trainingSteps};
  const config=handoff(path.join(ops,'aon-notes/hands-pc-20261107'));
  const localStarting=path.join(root,'models/current.pt');
  if(config.checkpoint)dataset.preSleepWeights=config.checkpoint;
  else if(fs.existsSync(localStarting))dataset.preSleepWeights=localStarting;
  const audit=rows.map(({frame,...row})=>row);
  write(path.join(output,'examples.json'),audit);
  const dataFile=path.join(work,'dataset.json');write(dataFile,dataset);
  const local=()=>JSON.parse(run(python,[path.join(sourceDir,'trainer.py'),...(dryRun?['--dry-run']:[]),dataFile,path.join(output,'quarantine')]));
  gate(dryRun);const trained=trainWithFallback(config,dataFile,path.join(output,'quarantine'),run,local),training=trained.training;stages.push('train');
  write(path.join(output,'training.json'),training);
  const result=training.train.length&&training.held.length?score(training,{allowPartial:true}):{pass:false,status:'unmeasured: insufficient held-out click/key actions',rates:null};stages.push('score');
  if(!dryRun){
   try {const exe='/Applications/Premonition.app/Contents/MacOS/Premonition';calibration=JSON.parse(run(exe,[path.join(sourceDir,'calibrate.js'),work],{env:{...process.env,ELECTRON_RUN_AS_NODE:'1'},timeout:120000}).trim().split('\n').at(-1));}
   catch(e){calibration.reason=e.message;}
  }
  write(path.join(output,'coordinates.json'),calibration);stages.push('coordinates');
  const trainIds=[...new Set(training.train.map(r=>rows.find(e=>e.id===r.id)?.clipId).filter(Boolean))];
  let retention={status:'dry-run; no files deleted',trainedIds:trainIds,deleted:0};
  // Preserve the entire held slice and mixed train/held clips for future audit.
  const heldIds=new Set(rows.filter(r=>r.timeMs>=training.cutoffMs).map(r=>r.clipId));
  const eligible=trainIds.filter(id=>!heldIds.has(id));
  if(!dryRun)try{retention={status:'completed',...new Retention(recordings).finishSleep({judged:true,trainedIds:eligible}),trainedIds:eligible};}catch(e){retention={status:'deferred',reason:e.message};warnings.push('retention: '+e.message);}
  stages.push('retention');
  const summary={day,dryRun,source:synthetic?'synthetic recording fixture; not Ben':"Ben's local screen recordings",stages:[...stages,'report'],status:'completed',coordinates:calibration.passed?'verified':'coords-unverified',quarantined:true,promoted:false,
   clipsSeen:prepared.clipsSeen,recordedMs:Object.values(prepared.trainedClipTimes).reduce((a,b)=>a+b,0),examples:prepared.examples.length,train:training.train.length,held:training.held.length,explanations:explanations.length,score:result,models:training.modelSha256,startingCheckpoint:dataset.preSleepWeights||null,baselineWarning:training.baselineWarning||null,backend:trained.backend,remoteCopiesDeleted:trained.remoteCopiesDeleted??null,trainingStepsPerArm:training.trainingStepsPerArm,intentPolicy:training.intentPolicy,dataManifestSha256:sha(JSON.stringify(audit)),limitations:[...new Set(rows.flatMap(r=>r.verificationLimitations||[]))],retention,rejections:prepared.rejections,warnings:[...warnings,...trained.notes],mistakes,correctionsUsed};
  write(path.join(output,'quarantine/manifest.json'),{quarantined:true,promoted:false,coordinates:summary.coordinates,scorePassed:result.pass,modelSha256:training.modelSha256});
  write(path.join(output,'result.json'),summary);
  fs.writeFileSync(path.join(output,'REPORT.md'),`# Night learning ${day}\n\nSource: ${summary.source}.\n\nCompleted: ${summary.stages.join(' → ')}.\n\n${rows.length} examples; ${summary.train} train; ${summary.held} held out.\n\nScore: ${JSON.stringify(result)}\n\nCheckpoint: quarantined, ${summary.coordinates}; never promoted.\n\nRetention: ${JSON.stringify(retention)}\n\nWarnings: ${JSON.stringify(summary.warnings)}\n`,{mode:0o600});
  return summary;
 }catch(error){write(path.join(output,'failure.json'),{status:'failed',stages,error:String(error.stack||error),quarantined:true});throw error;}
 finally {fs.rmSync(work,{recursive:true,force:true});}
}
module.exports={targetDay,localDay,groupEpisodes,sourceClips,retryBackground,runNight};
if(require.main===module){try{console.log(JSON.stringify(runNight({dryRun:process.argv.includes('--dry-run'),fixture:process.argv.includes('--fixture'),output:process.argv.includes('--output')?process.argv[process.argv.indexOf('--output')+1]:undefined})));}catch(error){console.error(String(error.stack||error));process.exitCode=1;}}
