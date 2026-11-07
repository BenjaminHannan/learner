'use strict';
// Offline coordinator. It never drives the desktop. All outputs are local.
const fs=require('node:fs'), os=require('node:os'), path=require('node:path'), crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const {createFileDecoder}=require('../screen-learning/video-decoder');
const {compileNative}=require('../screen-learning/native-examples');
const {score}=require('./score');
const {readAttempts}=require('./attempts');
const {verifiedCorrection}=require('./corrections');
const {Retention}=require('../hands-toy/retention');
const home=os.homedir(), ops=path.join(home,'learner-ops'), root=path.join(ops,'night-learn'), recordings=path.join(ops,'hands-recorder/recordings');
const python=path.join(ops,'p2venv/bin/python'), lock=path.join(ops,'bin/realmodel-lock.sh'), ffmpeg='/opt/homebrew/bin/ffmpeg', ffprobe='/opt/homebrew/bin/ffprobe';
const sourceDir=__dirname, nightGate=path.join(sourceDir,'night_gate.py'), sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const write=(p,o)=>fs.writeFileSync(p,JSON.stringify(o,null,2)+'\n',{mode:0o600});
function run(binary,args,options={}) {const r=spawnSync(binary,args,{encoding:'utf8',maxBuffer:8*1024*1024,timeout:binary===lock?undefined:1800000,...options});if(r.error||r.status!==0)throw Error(`${path.basename(binary)} failed: ${r.error?.message||String(r.stderr||'').slice(-1200)||r.status}`);return r.stdout;}
function gate() { run(python,['-c',`import sys;sys.path.insert(0,${JSON.stringify(sourceDir)});import trainer;trainer.production_gate()`],{timeout:10000}); }
function readClipFile(name) { if(typeof name!=='string'||path.basename(name)!==name)throw Error('unsafe clip path');const file=path.join(recordings,name),st=fs.lstatSync(file);if(!st.isFile()||st.isSymbolicLink())throw Error('unsafe clip file');return file; }
function targetDay(date) { const d=new Date(date.getFullYear(),date.getMonth(),date.getDate()-1);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
function localDay(ms) {const d=new Date(ms);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
function writeFrame(decoder, row, dest) {
 const image=decoder.readFrame(row.frameOrdinal);if(sha(image.pixels)!==row.frameSha256)throw Error('frame changed');
 const r=spawnSync(ffmpeg,['-v','error','-f','rawvideo','-pix_fmt','rgba','-s',`${image.width}x${image.height}`,'-i','pipe:0','-frames:v','1','-y',dest],{input:image.pixels,timeout:15000,maxBuffer:65536});if(r.error||r.status!==0)throw Error('could not save exact frame');
 fs.chmodSync(dest,0o600);
}
function sourceClips(index,day,calibration,work) {
 const examples=[], trainedClipTimes={}, wallBounds=[], clips=Object.values(index.clips||{}).filter(c=>!c.spent&&!c.audit&&c.app==='whole-display'&&localDay(c.createdMs)===day).sort((a,b)=>a.createdMs-b.createdMs);
 for(const clip of clips) {
  const videoName=clip.files?.find(x=>x===clip.id+'.mp4'),eventsName=clip.files?.find(x=>x===clip.id+'.events.jsonl'),proofName=clip.files?.find(x=>x===clip.id+'.proof.json');
  if(!videoName||!eventsName)continue;
  try {
   const video=readClipFile(videoName),bytes=fs.readFileSync(video),decoder=createFileDecoder({file:video,expected:{bytes:bytes.length,sha256:sha(bytes)},ffmpeg,ffprobe});
   const ledger=fs.readFileSync(readClipFile(eventsName),'utf8'),rows=ledger.split('\n').filter(Boolean).map(line=>JSON.parse(line));
   const proof=proofName?JSON.parse(fs.readFileSync(readClipFile(proofName),'utf8')):null;
   const out=compileNative({clip,rows,proof,decoder,calibration});
   if(!out.examples.length)continue;
   const frames=rows.filter(r=>r.type==='frame'),anchor=rows.find(r=>r.type==='clock_anchor');trainedClipTimes[clip.id]=frames.at(-1).receiveMonotonicMs-frames[0].receiveMonotonicMs+50;wallBounds.push(frames[0].receiveMonotonicMs+anchor.wallTimeMs-anchor.t, frames.at(-1).receiveMonotonicMs+anchor.wallTimeMs-anchor.t+50);
   for(const row of out.examples) {const file=path.join(work,sha(row.id)+'.png');writeFrame(decoder,row,file);examples.push({...row,frame:file,frameFileSha256:sha(fs.readFileSync(file)),clipId:clip.id});}
  }catch(error){fs.appendFileSync(path.join(root,'rejections.log'),JSON.stringify({clip:clip.id,reason:String(error.message),at:new Date().toISOString()})+'\n',{mode:0o600});}
 }
 return {examples:examples.sort((a,b)=>a.timeMs-b.timeMs),trainedClipTimes,clipsSeen:clips.length,startMs:Math.floor(Math.min(...wallBounds)),endMs:Math.ceil(Math.max(...wallBounds))};
}
function groupEpisodes(rows) {
 const groups=[];
 for(const row of rows) {const g=groups.at(-1), first=g?.[0],prev=g?.at(-1);if(!g||g.length>=80||row.timeMs-prev.timeMs>120000||row.timeMs-first.timeMs>300000)groups.push([]);groups.at(-1).push(row);}
 return groups;
}
function teacher(episode,work) {
 gate();
 const picks=[0,Math.floor((episode.length-1)/2),episode.length-1].filter((n,i,a)=>a.indexOf(n)===i);
 const input={frames:picks.map(i=>({path:episode[i].frame,timeMs:episode[i].timeMs})),actions:episode.map(e=>({kind:e.action.kind}))};
 const file=path.join(work,'episode.json');write(file,input);
 const raw=run(lock,['NIGHT-LEARN','/usr/bin/python3',nightGate,'/usr/bin/python3',path.join(sourceDir,'explain.py'),file]);
 const explanation=JSON.parse(raw.trim().split('\n').at(-1));
 const intents=new Map();for(const step of explanation.steps)if(!intents.has(step.actionIndex))intents.set(step.actionIndex,step.intent);
 const labelled=episode.flatMap((e,i)=>intents.has(i)?[{...e,intent:intents.get(i)}]:[]);
 return {explanation,labelled};
}
function health() {const r=spawnSync(lock,['NIGHT-LEARN','/usr/bin/python3',nightGate,'/usr/bin/curl','-fsS','--max-time','3','http://127.0.0.1:18080/health'],{stdio:'ignore'});if(r.error)throw r.error;return r.status===0;}
function runNight() {
 gate();
 const day=targetDay(new Date()), output=path.join(root,'runs',day);
 let calibration;try{calibration=JSON.parse(fs.readFileSync(path.join(root,'calibration.json'),'utf8'));}catch{throw Error('scratch display calibration is missing');}
 if(calibration.passed!==true||calibration.errorPx>10)throw Error('scratch display calibration has not passed');
 fs.mkdirSync(output,{recursive:true,mode:0o700});const work=fs.mkdtempSync(path.join(root,'work-'));fs.chmodSync(work,0o700);
 let started=false;
 try {
  const index=JSON.parse(fs.readFileSync(path.join(recordings,'clip-index.json'),'utf8'));
  const prepared=sourceClips(index,day,calibration,work);
  if(prepared.examples.length<2)throw Error('not enough proven native examples');
  if(!health()){gate();run(lock,['NIGHT-LEARN','/usr/bin/python3',nightGate,path.join(ops,'assistant/serve.sh'),'--yes']);started=true;}
  const explanations=[], rows=[];
  for(const episode of groupEpisodes(prepared.examples)){const r=teacher(episode,work);explanations.push(r.explanation);rows.push(...r.labelled);}
  const failures=readAttempts(path.join(ops,'hands-attempts/attempts.jsonl')).filter(a=>a.judgedOutcome==='fail'&&localDay(Date.parse(a.finishedAt))===day);
  const mistakes=[];
  for(const failure of failures){gate();const f=path.join(work,'attempt.json');write(f,failure);mistakes.push(JSON.parse(run(lock,['NIGHT-LEARN','/usr/bin/python3',nightGate,'/usr/bin/python3',path.join(sourceDir,'explain.py'),'--mistake',f]).trim().split('\n').at(-1)));}
  if(rows.length<2)throw Error('Glim did not supply enough step intents');
  const startMs=prepared.startMs,endMs=prepared.endMs,cutoff=startMs+(endMs-startMs)*.8;
  let correctionsUsed=0;const seen=new Set(rows.map(r=>r.id));
  for(const failure of failures)for(const candidate of failure.correctionCandidates){
   try{const correction=verifiedCorrection(path.join(ops,'hands-attempts'),candidate);
    if(correction.timeMs>=startMs&&correction.timeMs<cutoff&&!seen.has(correction.id)){rows.push(correction);seen.add(correction.id);correctionsUsed++;}}
   catch(error){fs.appendFileSync(path.join(root,'rejections.log'),JSON.stringify({attempt:failure.attemptId,reason:String(error.message),at:new Date().toISOString()})+'\n',{mode:0o600});}
  }
  const held=rows.filter(r=>r.timeMs>=cutoff),train=rows.filter(r=>r.timeMs<cutoff);
  if(!train.length||!held.length)throw Error('both time slices need examples');
  const evalHash=sha(JSON.stringify(held.map(r=>({id:r.id,timeMs:r.timeMs,frameSha256:r.frameSha256,intent:r.intent,action:r.action}))));
  const dataset={startMs,endMs,examples:rows};
  const current=path.join(root,'models/current.pt'),liveRoot=path.join(ops,'hands-policy');
  try {const manifest=JSON.parse(fs.readFileSync(path.join(liveRoot,'current.json'),'utf8')),runtime=path.join(liveRoot,'current.ts');
    if(manifest.approved===true && manifest.nativeActionPolicy===true && /^[a-f0-9]{64}$/.test(manifest.sha256||'') && /^[a-f0-9]{64}$/.test(manifest.weightsSha256||'') && sha(fs.readFileSync(runtime))===manifest.sha256 && sha(fs.readFileSync(current))===manifest.weightsSha256)dataset.preSleepWeights=current;
  }catch {/* No verified compatible live baseline; never claim P2. */}
  const dataFile=path.join(work,'dataset.json');write(dataFile,dataset);
  gate();const training=JSON.parse(run(python,[path.join(sourceDir,'trainer.py'),dataFile,path.join(output,'quarantine')]));
  const result=score(training);
  const previous=training.hasPreviousModel===true;
  const summary={day,p1:{status:Object.values(prepared.trainedClipTimes).reduce((a,b)=>a+b,0)>=3600000&&explanations.length>=5?'PASS':'NOT MET',recordedMs:Object.values(prepared.trainedClipTimes).reduce((a,b)=>a+b,0),requiredMs:3600000,examples:prepared.examples.length,explanations:explanations.slice(0,5)},p2:{status:previous?(result.pass?'PASS':'FAIL'):'NOT MEASURED: no compatible pre-sleep model',score:previous?result:null,diagnosticUntrainedScore:previous?null:result,evalSetSha256:evalHash,models:training.modelSha256},p3:{decision:'rollback',reason:'candidate runtime is not yet integrated with the live HANDS worker',awakeWeightChanges:false},mistakes,correctionsUsed};
  write(path.join(output,'result.json'),summary);
  // The existing retention rule only runs after a real comparison was judged.
  if(previous){const trainIds=[...new Set(train.map(r=>r.clipId).filter(Boolean))];new Retention(recordings).finishSleep({judged:true,trainedIds:trainIds});}
  return summary;
 } finally {
  fs.rmSync(work,{recursive:true,force:true});
  if(started){try{gate();run(lock,['NIGHT-LEARN','/usr/bin/python3',nightGate,path.join(ops,'assistant/stop.sh')]);}catch{/* Keep an active user or another model job safe. */}}
 }
}
module.exports={targetDay,localDay,groupEpisodes,runNight};
if(require.main===module){try{const result=runNight();console.log(JSON.stringify({day:result.day,p1:result.p1.status,p2:result.p2.status,p3:result.p3.decision}));}catch(error){console.error(String(error.stack||error));process.exitCode=1;}}
