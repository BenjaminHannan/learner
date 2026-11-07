'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {compileNative}=require('../src/screen-learning/native-examples');
function fixture(){
 const bounds={x:0,y:0,width:1440,height:900}, sha='a'.repeat(64);
 const frames=[0,1,2].map(i=>({type:'frame',frameId:i+1,session:'s',generation:1,receiveMonotonicMs:100+i*50,rawSha256:sha,transform:{sourceBounds:bounds}}));
 const events=[{type:'clock_anchor',t:0,wallTimeMs:1000},...frames,{type:'mouse',source:'physical_unverified',kind:'mouse_down',x:720,y:450,eventTimestampNs:185000000,t:185,button:0},{type:'mouse',kind:'mouse_up',button:0,x:720,y:450,eventTimestampNs:188000000},{type:'key',source:'physical_unverified',kind:'key_down',keyCode:36,eventTimestampNs:195000000,t:195},{type:'source_end',complete:true,session:'s',frameCount:3}];
 const decoder={source:{sha256:sha,bytes:1},index:frames.map((_,i)=>({encodedOrdinal:i+1,width:1280,height:720,encodedPts:{value:i,timescale:20}})),readFrame(i){return {encodedOrdinal:i,width:1280,height:720,pixelFormat:'RGBA',pixels:Buffer.alloc(1280*720*4)}}};
 return {clip:{id:'c',session:'s',eventClockOffsetMs:0,clockOffsetUncertaintyMs:1},rows:events,proof:{version:2,sourceContract:'hands-toy-bgra-frame-v1',session:'s',temporalCorrespondence:true,output:{sha256:sha,bytes:1,timeBase:'1/20',presentationPts:[0,1,2]},inputs:frames.map((_,i)=>({ordinal:i+1,sourceFrameId:i+1,rawSha256:sha}))},decoder,calibration:{passed:true,errorPx:2,sourceBounds:bounds,display:{bounds,scaleX:2,scaleY:2}}};
}
test('native action labels use the last proven pre-action frame and mapped screen coordinates',()=>{const r=compileNative(fixture());assert.equal(r.examples.length,2);assert.equal(r.examples[0].frameOrdinal,2);assert.deepEqual(r.examples[0].action,{kind:'click',x:640,y:360,screenX:1440,screenY:900,button:0});assert.deepEqual(r.examples[1].action,{kind:'key',keyCode:36});});
test('missing calibration, clock, frame proof, or source end refuses labels',()=>{for(const change of [x=>x.calibration.passed=false,x=>delete x.clip.eventClockOffsetMs,x=>x.proof.inputs[0].rawSha256='b'.repeat(64),x=>x.rows.at(-1).complete=false]){const x=fixture();change(x);assert.throws(()=>compileNative(x));}});

test('a drag includes its release location',()=>{const x=fixture();const up=x.rows.find(r=>r.kind==='mouse_up');up.x=800;const r=compileNative(x);assert.equal(r.examples[0].action.kind,'drag');assert.equal(r.examples[0].action.endX,704);});
test('indexed recorder needs measured offset and refuses clock drift',()=>{
 const x=fixture();x.proof=null;x.clip.videoClock={clock:'dispatch_uptime_ms',firstFrameMonotonicMs:100,nominalFrameMs:50,frameEvents:'ordinal',offsetMs:0,calibration:{measured:true,uncertaintyMs:2}};
 x.rows=x.rows.filter(r=>r.type!=='source_end');assert.equal(compileNative(x).examples.length,2);
 delete x.clip.videoClock.calibration.uncertaintyMs;assert.throws(()=>compileNative(x),/clock mapping/);
 x.clip.videoClock.calibration.uncertaintyMs=2;x.rows.find(r=>r.frameId===3).receiveMonotonicMs=500;assert.throws(()=>compileNative(x),/drift/);
});
