'use strict';
// Ben Nov 4 "clean this up and make it look prettier": one round button that morphs (send / steer / stop), quiet mic + call icons,
// a hairline box with a soft focus glow, the same size in every state, shorter running words.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const read = (f) => fs.readFileSync(path.join(__dirname, '..', f), 'utf8');

test('one primary button: Stop only while running with an empty box; typed text = the steer arrow; idle = send; asleep = none; learn mode = green arrow', () => {
  const app = read('renderer/app.js');
  const fn = app.slice(app.indexOf('function paintPrimary() {'), app.indexOf('function paintPrimary() {') + 600);
  assert.match(fn, /const stopNow = running && !asleep && !learning && !input\.value\.trim\(\);/);
  assert.match(fn, /\$\('#btnStop'\)\.hidden = !stopNow;/);
  assert.match(fn, /\$\('#btnSend'\)\.hidden = asleep \|\| stopNow;/);
  assert.match(fn, /classList\.toggle\('running', running && !asleep\)/);
  // it repaints on every text change (autosize runs on input and after programmatic clears) and in paintBox / paintSleep
  assert.match(app, /function autosize\(\) \{[^\n]*try \{ paintPrimary\(\); \}/);
  assert.match(app, /function paintBox\(r\) \{[\s\S]{0,700}paintPrimary\(\);\n    if \(window\.LearnButton\) LearnButton\.dress\(\);/);
  assert.match(app, /paintPrimary\(\); \$\('#hint'\)\.hidden = asleep;/);
  assert.ok(!/\$\('#btnStop'\)\.hidden = !r/.test(app), 'setRunning no longer shows Stop by itself');
  assert.match(read('renderer/learnbtn.js'), /stopB\.hidden = true; send\.hidden = false;/);
  // Esc still stops a run
  assert.match(app, /else if \(running\) desk\.agent\.stop\(thread && thread\.id\);/);
});

test('shorter running words', () => {
  const app = read('renderer/app.js');
  assert.match(app, /input\.placeholder = r \? 'Steer Glim…'/);
  assert.match(app, /'Enter to steer · Esc to stop'/);
  assert.ok(!/Add a note to steer the current task/.test(app));
});

test('calm styling: hairline box + soft glow, no amber outline; quiet icon buttons; soft Stop; Call hidden while running; same size', () => {
  const css = read('renderer/app.css');
  const box = /#composer \.box \{([^}]*)\}/.exec(css)[1];
  assert.match(box, /border:1px solid var\(--hair2\)/); assert.match(box, /min-height:3\.3rem/);
  const focus = /#composer \.box:focus-within \{([^}]*)\}/.exec(css)[1];
  assert.ok(!/accent/.test(focus), 'no amber outline on focus');
  const call = /\.callbtn \{([^}]*)\}/.exec(css)[1];
  assert.match(call, /border:0/); assert.match(call, /color:var\(--faint\)/); assert.match(call, /width:2\.4rem; height:2\.4rem/);
  const stop = /\.stop \{([^}]*)\}/.exec(css)[1];
  assert.match(stop, /border:0/); assert.ok(!/danger/.test(stop), 'no pink ring'); assert.match(stop, /width:2\.4rem; height:2\.4rem/);
  assert.match(/\.send \{([^}]*)\}/.exec(css)[1], /width:2\.4rem; height:2\.4rem/);
  assert.match(css, /#composer \.box\.running #btnCall \{ display:none; \}/);
  assert.match(css, /#composer \.box\.learning, #composer \.box\.learning:focus-within \{ border-color:var\(--ok\)/, 'learn mode stays the one special state');
});

test('screenshots of every state, dark and light, are in docs/ui1', () => {
  const dir = path.join(__dirname, '..', 'docs', 'ui1');
  for (const n of ['opener', 'composer-idle-typed', 'composer-running-empty', 'composer-running-typed', 'composer-asleep', 'learnmode-on', 'learnmode-typed', 'learnmode-while-running', 'learn-busy-popover', 'plan-and-chip'])
    for (const th of ['dark', 'light']) assert.ok(fs.existsSync(path.join(dir, n + '-' + th + '.png')), n + '-' + th);
});
