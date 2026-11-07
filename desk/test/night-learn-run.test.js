'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {groupEpisodes,targetDay}=require('../src/night-learn/run');
test('episode groups split on inactivity and bounded batch size',()=>{
 const rows=[{timeMs:0},{timeMs:100},{timeMs:120101},{timeMs:120102}];
 assert.deepEqual(groupEpisodes(rows).map(x=>x.length),[2,2]);
 assert.deepEqual(groupEpisodes(Array.from({length:81},(_,i)=>({timeMs:i}))).map(x=>x.length),[80,1]);
});
test('night run chooses the previous local calendar day',()=>{
 assert.equal(targetDay(new Date(2026,10,7,1,5)),'2026-11-06');
 assert.equal(targetDay(new Date(2026,0,1,1,5)),'2025-12-31');
});
