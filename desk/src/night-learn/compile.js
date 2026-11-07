'use strict';
// Quarantined compilation. Layout/clock measurements improve confidence but
// are not admission gates. Exact encoded pixels remain source-hash bound.
const {createHash}=require('node:crypto');
const {displayPointToVideo}=require('../screen-learning/display-map');
function compile({clip,rows,decoder,calibration}) {
 const frames=rows.filter(r=>r.type==='frame'), anchor=rows.find(r=>r.type==='clock_anchor');
 if(!frames.length||!anchor||!Number.isFinite(anchor.wallTimeMs)||!Number.isFinite(anchor.t))throw Error('recording frame/clock index unavailable');
 const bounds=frames[0].transform?.sourceBounds;
 if(!bounds)throw Error('recording display bounds unavailable');
 const limitations=[];
 if(calibration?.passed!==true)limitations.push('coords-unverified');
 if(clip.videoClock?.calibration?.measured!==true&&!Number.isFinite(clip.eventClockOffsetMs))limitations.push('clock-unverified');
 if(frames.length!==decoder.index.length)limitations.push('frame-count-mismatch');
 const offset=clip.eventClockOffsetMs||0, wallOffset=anchor.wallTimeMs-anchor.t;
 const actions=rows.filter(r=>r.source==='physical_unverified'&&((r.type==='key'&&r.kind==='key_down')||(r.type==='mouse'&&['mouse_down','scroll'].includes(r.kind))));
 const examples=[],rejects=[];
 for(let i=0;i<actions.length;i++) {
  const e=actions[i],t=Number.isSafeInteger(e.eventTimestampNs)?e.eventTimestampNs/1e6+offset:e.t;
  let ordinal=-1;
  for(let j=0;j<Math.min(frames.length,decoder.index.length);j++)if(frames[j].receiveMonotonicMs<t-5)ordinal=j;
  if(ordinal<0||t-frames[ordinal].receiveMonotonicMs>250){rejects.push({index:i,reason:'no nearby pre-action frame'});continue;}
  const size=decoder.index[ordinal];let action;
  try {
   if(e.type==='key') {if(!Number.isInteger(e.keyCode)||e.keyCode<0||e.keyCode>255)throw Error('invalid key');action={kind:'key',keyCode:e.keyCode};}
   else {
    const p=displayPointToVideo(e,bounds,size);
    if(e.kind==='scroll')action={kind:'scroll',...p,dx:0,dy:Number(e.wheel)||0};
    else {
     const tail=rows.slice(rows.indexOf(e)+1),up=tail.find(r=>r.type==='mouse'&&['mouse_down','mouse_up'].includes(r.kind)&&r.button===e.button);
     if(!up||up.kind!=='mouse_up')throw Error('missing release');
     const q=displayPointToVideo(up,bounds,size);
     action=Math.hypot(q.x-p.x,q.y-p.y)>=4?{kind:'drag',...p,endX:q.x,endY:q.y}:{kind:'click',...p};
    }
   }
   const frame=decoder.readFrame(ordinal+1);
   examples.push({id:clip.id+':'+i,timeMs:Math.round(t+wallOffset),frameOrdinal:ordinal+1,frameSha256:createHash('sha256').update(frame.pixels).digest('hex'),action,verified:true,verificationLimitations:limitations,clipId:clip.id});
  }catch(error){rejects.push({index:i,reason:error.message});}
 }
 return {examples,rejects,limitations};
}
module.exports={compile};
