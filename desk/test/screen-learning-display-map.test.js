'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { displayPointToVideo, displayPointToBacking } = require('../src/screen-learning/display-map');

test('maps global display points into the letterboxed recorded image', () => {
  assert.deepEqual(displayPointToVideo({x:0,y:0},{x:0,y:0,width:1440,height:900}), {x:64,y:0});
  assert.deepEqual(displayPointToVideo({x:720,y:450},{x:0,y:0,width:1440,height:900}), {x:640,y:360});
  assert.deepEqual(displayPointToVideo({x:-100,y:50},{x:-100,y:50,width:2560,height:1440}), {x:0,y:0});
  assert.throws(() => displayPointToVideo({x:-101,y:50},{x:-100,y:50,width:2560,height:1440}));
  assert.throws(() => displayPointToVideo({x:0,y:0},{x:0,y:0,width:0,height:1}));
});

test('backing pixels use global origin and the display scale', () => {
  const display = {bounds:{x:-100,y:50,width:1440,height:900},scaleX:2,scaleY:2};
  assert.deepEqual(displayPointToBacking({x:0,y:75},display), {x:200,y:50});
  assert.throws(() => displayPointToBacking({x:0,y:75},{...display,scaleX:0}));
});
