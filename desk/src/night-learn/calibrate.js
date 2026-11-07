'use strict';
// Invoked only in Premonition's signed executable. Never requests permissions.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {spawnSync}=require('node:child_process');
const {NativeSession}=require('../computer-control/native');
const {createFileDecoder}=require('../screen-learning/video-decoder');
const {coordinateMap}=require('./coordinate-map');
const {createHash}=require('node:crypto');
const sha=b=>createHash('sha256').update(b).digest('hex');
const ops=path.join(os.homedir(),'learner-ops'),recordings=path.join(ops,'hands-recorder/recordings');
const python=path.join(ops,'p2venv/bin/python');
function analyze(args) {const r=spawnSync(python,[path.join(__dirname,'coordinate-image.py'),...args],{encoding:'utf8',timeout:10000});if(r.status!==0)throw Error(r.stderr||r.error);return JSON.parse(r.stdout);}
async function calibrate(work) {
 let native;
 try {
  if(!process.execPath.startsWith('/Applications/Premonition.app/'))throw Error('Premonition executable required');
  if(JSON.parse(fs.readFileSync(path.join(ops,'hands-recorder/state.json'))).enabled!==true)throw Error('recording not live');
  native=await NativeSession.start();
  if((await native.command('idle')).seconds<1200)throw Error('Ben is active; no probe posted');
  const shot=await native.command('look');
  const geometry=spawnSync('/usr/bin/swift',[path.join(__dirname,'../screen-learning/display-geometry.swift')],{encoding:'utf8',timeout:30000});
  if(geometry.status!==0)throw Error('display backing scale unavailable');
  const display=JSON.parse(geometry.stdout).find(d=>String(d.id)===String(shot.displayId));
  if(!display)throw Error('captured display geometry unavailable');
  const before=path.join(work,'coordinate-screen.png');fs.writeFileSync(before,Buffer.from(shot.png,'base64'),{mode:0o600});
  const spot=analyze(['spot',before]);
  const point={x:shot.bounds.x+spot.x*shot.bounds.width/shot.size.width,y:shot.bounds.y+spot.y*shot.bounds.height/shot.size.height};
  if(Math.hypot(spot.x-shot.cursor[0]*shot.size.width,spot.y-shot.cursor[1]*shot.size.height)<50)throw Error('probe spot overlaps old cursor');
  if((await native.command('idle')).seconds<1200)throw Error('Ben returned; no probe posted');
  const began=Date.now();await native.command('grant');
  await native.command('send',{kind:'mouse',state:'move',...point});await native.command('end');await native.close();native=null;
  // Wait for the recorder to finalize its current 30-second segment. No second move.
  const deadline=Date.now()+45000;
  while(Date.now()<deadline) {
   const index=JSON.parse(fs.readFileSync(path.join(recordings,'clip-index.json')));
   for(const clip of Object.values(index.clips||{}).filter(c=>c.createdMs>began-40000)) {
    const name=clip.files?.find(n=>n===clip.id+'.events.jsonl');if(!name)continue;
    const rows=fs.readFileSync(path.join(recordings,name),'utf8').split('\n').filter(Boolean).map(JSON.parse);
    const anchor=rows.find(r=>r.type==='clock_anchor');if(!anchor)continue;
    const e=rows.find(r=>r.type==='mouse'&&r.kind==='mouse_move'&&Math.hypot(r.x-point.x,r.y-point.y)<2&&Math.abs(r.t+anchor.wallTimeMs-anchor.t-began)<3000);if(!e)continue;
    const file=path.join(recordings,clip.id+'.mp4'),bytes=fs.readFileSync(file);
    const decoder=createFileDecoder({file,expected:{sha256:sha(bytes),bytes:bytes.length},ffmpeg:'/opt/homebrew/bin/ffmpeg',ffprobe:'/opt/homebrew/bin/ffprobe'});
    const frames=rows.filter(r=>r.type==='frame');const a=frames.findLastIndex(f=>f.receiveMonotonicMs<e.t-100),b=frames.findIndex(f=>f.receiveMonotonicMs>e.t+150);
    if(a<0||b<0)continue;
    const files=[];
    for(const [label,i] of [['before',a],['after',b]]) {
     const f=decoder.readFrame(i+1),dest=path.join(work,'coordinate-'+label+'.png');
     const r=spawnSync('/opt/homebrew/bin/ffmpeg',['-v','error','-f','rawvideo','-pix_fmt','rgba','-s',`${f.width}x${f.height}`,'-i','pipe:0','-frames:v','1','-y',dest],{input:f.pixels,timeout:10000});if(r.status!==0)throw Error('coordinate frame decode failed');files.push(dest);
    }
    const bounds=frames[a].transform.sourceBounds,mapping=coordinateMap(point,display,bounds,decoder.index[a]),expected=mapping.videoPixels;
    return {...analyze(['measure',...files,String(expected.x),String(expected.y)]),event:e,clipId:clip.id,sourceBounds:bounds,
     mapping,videoSha256:sha(bytes),beforeFrame:a+1,afterFrame:b+1};
   }
   await new Promise(r=>setTimeout(r,1000));
  }
  throw Error('probe event/frame not found in finalized live recording');
 } catch(error){return {passed:false,status:'coords-unverified',reason:error.message};}
 finally {if(native)await native.close();}
}
module.exports={calibrate};
if(require.main===module) {
 const complete=result=>{
  if(process.argv[3]){const file=process.argv[3];fs.writeFileSync(file+'.tmp',JSON.stringify(result)+'\n',{mode:0o600});fs.renameSync(file+'.tmp',file);}
  console.log(JSON.stringify(result));
 };
 calibrate(process.argv[2]).then(complete).catch(error=>complete({passed:false,status:'coords-unverified',reason:error.message}));
}
