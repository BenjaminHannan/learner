'use strict';
const crypto = require('node:crypto');
const { displayPointToVideo, displayPointToBacking } = require('./display-map');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const sameBounds=(a,b)=>!!a&&!!b&&['x','y','width','height'].every(k=>Number.isFinite(a[k])&&a[k]===b[k]);

// Compile only recordings with a matching encoder receipt, measured event clock
// offset and a passing calibration for this exact display layout. The caller
// supplies decoded video through the existing source-bound decoder.
function compileNative({clip, rows, proof, decoder, calibration}) {
  if (!clip || !Array.isArray(rows) || !decoder || !calibration) throw Error('missing native evidence');
  if (calibration.passed !== true || !Number.isFinite(calibration.errorPx) || calibration.errorPx > 10 || calibration.errorPx < 0) throw Error('display calibration not passed');
  const frames = rows.filter(r => r.type === 'frame');
  const anchors = rows.filter(r => r.type === 'clock_anchor');
  const ends = rows.filter(r => r.type === 'source_end');
  if (anchors.length !== 1 || !Number.isFinite(anchors[0].t) || !Number.isFinite(anchors[0].wallTimeMs)) throw Error('wall clock anchor unavailable');
  if (!Array.isArray(decoder.index) || !frames.length || frames.length !== decoder.index.length || frames.length > 600) throw Error('frame mapping unavailable');
  const bounds = frames[0].transform?.sourceBounds;
  if (!bounds || !sameBounds(bounds,calibration.sourceBounds) || !sameBounds(bounds,calibration.display?.bounds) || !Number.isFinite(calibration.display.scaleX) || !Number.isFinite(calibration.display.scaleY)) throw Error('display layout changed since calibration');
  let eventClockOffset = 0, uncertainty, firstPts, frameTimes=[];
  if (proof) {
    if (!Number.isFinite(clip.eventClockOffsetMs) || !Number.isFinite(clip.clockOffsetUncertaintyMs) || clip.clockOffsetUncertaintyMs < 0 || clip.clockOffsetUncertaintyMs > 5) throw Error('event clock offset not measured');
    eventClockOffset=clip.eventClockOffsetMs; uncertainty=clip.clockOffsetUncertaintyMs;
    if (proof.version !== 2 || proof.sourceContract !== 'hands-toy-bgra-frame-v1' || proof.session !== clip.session || proof.temporalCorrespondence !== true || proof.output?.sha256 !== decoder.source?.sha256 || proof.output?.bytes !== decoder.source?.bytes || !Array.isArray(proof.inputs) || proof.inputs.length!==frames.length || ends.length!==1 || ends[0].complete!==true || ends[0].session!==clip.session || ends[0].frameCount!==frames.length) throw Error('encoder proof mismatch');
    const timeBase = /^(\d+)\/(\d+)$/.exec(proof.output.timeBase || '');
    if (!timeBase || !Number(timeBase[1]) || !Number(timeBase[2]) || !Array.isArray(proof.output.presentationPts) || proof.output.presentationPts.length !== frames.length) throw Error('encoded timestamps unavailable');
    for(let i=0;i<frames.length;i++) {
      const f=frames[i],input=proof.inputs[i],entry=decoder.index[i],pts=entry.encodedPts,proofPts=proof.output.presentationPts[i];
      if(f.session!==clip.session || input?.ordinal!==i+1 || input.sourceFrameId!==f.frameId || input.rawSha256!==f.rawSha256 || !/^[a-f0-9]{64}$/.test(f.rawSha256||'') || !pts || !Number.isSafeInteger(pts.value) || !Number.isSafeInteger(pts.timescale) || pts.timescale<=0 || !Number.isSafeInteger(proofPts) || BigInt(pts.value)*BigInt(timeBase[2])!==BigInt(proofPts)*BigInt(timeBase[1])*BigInt(pts.timescale)) throw Error('frame evidence mismatch');
      frameTimes.push(f.receiveMonotonicMs);
    }
  } else {
    const clock=clip.videoClock, measured=clock?.calibration;
    uncertainty=measured?.uncertaintyMs;
    if(clip.sourceGap||clip.truncated||clock?.clock!=='dispatch_uptime_ms'||clock.frameEvents!=='ordinal'||clock.nominalFrameMs!==50||measured?.measured!==true||!Number.isFinite(clock.offsetMs)||!Number.isFinite(uncertainty)||uncertainty<0||uncertainty>10||!Number.isFinite(clock.firstFrameMonotonicMs)||Math.abs(clock.firstFrameMonotonicMs-frames[0].receiveMonotonicMs)>1)throw Error('measured indexed clock mapping unavailable');
    firstPts=decoder.index[0].encodedPts.value/decoder.index[0].encodedPts.timescale;
    for(let i=0;i<frames.length;i++) {
      const pts=decoder.index[i].encodedPts;
      if(!pts||!Number.isSafeInteger(pts.value)||!Number.isSafeInteger(pts.timescale)||pts.timescale<=0)throw Error('encoded timestamps unavailable');
      const elapsed=(pts.value/pts.timescale-firstPts)*1000;
      if(Math.abs(elapsed-i*50)>2)throw Error('encoded ordinal timing mismatch');
      const mapped=clock.firstFrameMonotonicMs+elapsed+clock.offsetMs;
      if(Math.abs(mapped-frames[i].receiveMonotonicMs)>100+uncertainty)throw Error('frame timing drift');
      frameTimes.push(Math.max(mapped,frames[i].receiveMonotonicMs));
    }
  }
  let previous = -Infinity;
  frames.forEach((f,i)=>{
    if(f.frameId!==i+1 || f.generation!==frames[0].generation || f.transitionAmbiguous===true || !sameBounds(f.transform?.sourceBounds,bounds) || !Number.isFinite(f.receiveMonotonicMs) || f.receiveMonotonicMs<=previous || decoder.index[i]?.encodedOrdinal!==i+1)throw Error('frame evidence mismatch');
    previous=f.receiveMonotonicMs;
  });
  const wallOffset = anchors[0].wallTimeMs - anchors[0].t;
  const supported = rows.filter(r => r.source === 'physical_unverified' && ((r.type === 'mouse' && ['mouse_down','scroll'].includes(r.kind)) || (r.type === 'key' && r.kind === 'key_down')));
  const examples = [], rejects = [];
  for (let i = 0; i < supported.length; i++) {
    const event = supported[i];
    if (!Number.isSafeInteger(event.eventTimestampNs) || event.eventTimestampNs < 0) { rejects.push({index:i,reason:'event clock unavailable'}); continue; }
    const time = event.eventTimestampNs / 1e6 + eventClockOffset;
    if (!Number.isFinite(event.t) || Math.abs(event.t-time)>100) { rejects.push({index:i,reason:'event clock does not match uptime'}); continue; }
    let offset = -1;
    for (let j = 0; j < frames.length; j++) if (frameTimes[j] + uncertainty + 5 < time) offset = j;
    if (offset < 0 || time - frameTimes[offset] > 100) { rejects.push({index:i,reason:'pre-action frame unavailable'}); continue; }
    let action;
    if (event.type === 'key') {
      if (!Number.isInteger(event.keyCode) || event.keyCode < 0 || event.keyCode > 255) {rejects.push({index:i,reason:'invalid key'}); continue;}
      action = {kind:'key',keyCode:event.keyCode};
    } else {
      let point;
      try {point=displayPointToVideo({x:event.x,y:event.y},bounds,{width:decoder.index[offset].width,height:decoder.index[offset].height});} catch {rejects.push({index:i,reason:'point outside display'}); continue;}
      const screenPoint = displayPointToBacking({x:event.x,y:event.y},calibration.display);
      if (event.kind === 'scroll') action = {kind:'scroll',x:point.x,y:point.y,dx:0,dy:Number(event.wheel)||0};
      else {
        const eventIndex = rows.indexOf(event);
        const tail = rows.slice(eventIndex+1);
        const nextDown = tail.findIndex(r => r.type === 'mouse' && r.kind === 'mouse_down' && r.button === event.button);
        const endIndex = tail.findIndex(r => r.type === 'mouse' && r.kind === 'mouse_up' && r.button === event.button);
        if (endIndex < 0 || (nextDown >= 0 && nextDown < endIndex)) { rejects.push({index:i,reason:'mouse release unavailable'}); continue; }
        const end = tail[endIndex];
        if (!Number.isSafeInteger(end.eventTimestampNs) || end.eventTimestampNs <= event.eventTimestampNs || end.eventTimestampNs - event.eventTimestampNs > 30e9) { rejects.push({index:i,reason:'invalid mouse release time'}); continue; }
        let endPoint;
        try { endPoint=displayPointToVideo({x:end.x,y:end.y},bounds,{width:decoder.index[offset].width,height:decoder.index[offset].height}); } catch { rejects.push({index:i,reason:'release outside display'}); continue; }
        action = Math.hypot(endPoint.x-point.x,endPoint.y-point.y) >= 4 ? {kind:'drag',x:point.x,y:point.y,endX:endPoint.x,endY:endPoint.y,button:event.button} : {kind:'click',x:point.x,y:point.y,screenX:screenPoint.x,screenY:screenPoint.y,button:event.button};
      }
    }
    const frame = decoder.readFrame(offset+1);
    if (frame.encodedOrdinal !== offset+1 || frame.width !== decoder.index[offset].width || frame.height !== decoder.index[offset].height || frame.pixelFormat !== 'RGBA' || frame.pixels.length !== frame.width*frame.height*4) throw Error('decoded frame mismatch');
    examples.push({id:clip.id+':'+i, timeMs:Math.round(time+wallOffset), monotonicMs:time, frameOrdinal:offset+1, frameSha256:sha(frame.pixels), display:calibration.display, action, verified:true});
  }
  return {examples,rejects};
}
module.exports = {compileNative};
