'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {due,previousDay}=require('../src/night-learn/scheduler');
test('night scheduler waits until 01:00 and 20 minutes of Mac idle',()=>{
 assert.equal(due(new Date(2026,10,7,0,59),1200),false);
 assert.equal(due(new Date(2026,10,7,1,0),1199),false);
 assert.equal(due(new Date(2026,10,7,1,0),1200),true);
 assert.equal(due(new Date(2026,10,7,7,0),2000),false);
 assert.equal(due(new Date(2026,10,7,1,0),NaN),false);
 assert.equal(previousDay(new Date(2026,0,1,1,0)),'2025-12-31');
});
