'use strict';

// macOS virtual key codes. Text goes as Unicode; shortcuts use these physical keys.
const KEYS = { a:0,s:1,d:2,f:3,h:4,g:5,z:6,x:7,c:8,v:9,b:11,q:12,w:13,e:14,r:15,y:16,t:17,
  '1':18,'2':19,'3':20,'4':21,'6':22,'5':23,'=':24,'9':25,'7':26,'-':27,'8':28,'0':29,
  ']':30,o:31,u:32,'[':33,i:34,p:35,enter:36,return:36,l:37,j:38,"'":39,k:40,';':41,
  '\\':42,',':43,'/':44,n:45,m:46,'.':47,tab:48,space:49,'`':50,backspace:51,delete:51,
  escape:53,esc:53,command:55,cmd:55,shift:56,capslock:57,option:58,alt:58,control:59,ctrl:59,
  left:123,arrowleft:123,right:124,arrowright:124,down:125,arrowdown:125,up:126,arrowup:126,home:115,end:119,pageup:116,pagedown:121,forwarddelete:117,
  f1:122,f2:120,f3:99,f4:118,f5:96,f6:97,f7:98,f8:100,f9:101,f10:109,f11:103,f12:111,f13:105,f14:107,f15:113,f16:106,f17:64,f18:79,f19:80,f20:90 };
const MODIFIERS = new Set(['command','cmd','shift','option','alt','control','ctrl']);
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

function planCombo(combo) {
  if (typeof combo !== 'string' || !combo.trim()) throw Error('key combination required');
  const keys = combo.toLowerCase().split('+').map(s => s.trim());
  if (keys.length > 5 || keys.some(k => !Object.hasOwn(KEYS, k)) || keys.slice(0, -1).some(k => !MODIFIERS.has(k)) || MODIFIERS.has(keys.at(-1))) throw Error('unsupported key combination');
  const codes = keys.map(k => KEYS[k]);
  if (new Set(codes).size !== codes.length) throw Error('duplicate key');
  return codes.map(code => ({ kind:'key', code, down:true })).concat([...codes].reverse().map(code => ({ kind:'key', code, down:false })));
}
function planText(text) {
  if (typeof text !== 'string' || text.length === 0 || text.length > 5000) throw Error('invalid text');
  return Array.from(text).flatMap(char => char === '\n' ? planCombo('enter') : char === '\t' ? planCombo('tab') : [{ kind:'character', text:char }]);
}
function validPoint(x, y) { return Number.isFinite(x) && Number.isFinite(y); }
function actionPlan(action) {
  if (!action || typeof action !== 'object') throw Error('action required');
  const name = action.type, button = action.button || 'left';
  if (name === 'click') {
    const total = action.count ?? 1;
    if (!validPoint(action.x, action.y) || !['left','right','middle'].includes(button) || ![1,2,3].includes(total)) throw Error('invalid click');
    const events = [{ kind:'mouse', state:'move', x:action.x, y:action.y, button }];
    for (let count = 1; count <= total; count++) for (const state of ['down','up']) events.push({ kind:'mouse', state, x:action.x, y:action.y, button, count });
    return events;
  }
  if (name === 'drag') {
    if (!validPoint(action.x, action.y) || !validPoint(action.toX, action.toY) || !['left','right','middle'].includes(button)) throw Error('invalid drag');
    const events = [{ kind:'mouse', state:'move', x:action.x, y:action.y, button }, { kind:'mouse', state:'down', x:action.x, y:action.y, button }];
    for (let i = 1; i <= 12; i++) events.push({ kind:'mouse', state:'move', x:action.x+(action.toX-action.x)*i/12, y:action.y+(action.toY-action.y)*i/12, button });
    events.push({ kind:'mouse', state:'up', x:action.toX, y:action.toY, button }); return events;
  }
  if (name === 'scroll') {
    if (!Number.isInteger(action.dy) || action.dy === 0 || Math.abs(action.dy) > 1200) throw Error('invalid scroll');
    const events = []; let remaining = action.dy;
    while (remaining) { const dy = Math.sign(remaining)*Math.min(120, Math.abs(remaining)); events.push({ kind:'scroll', dy }); remaining -= dy; }
    return events;
  }
  if (name === 'type') return planText(action.text);
  if (name === 'press') return planCombo(action.combo);
  if (name === 'open') {
    if (typeof action.name !== 'string' || !action.name.trim() || action.name.length > 120 || /[\x00-\x1f\x7f]/.test(action.name)) throw Error('invalid app name');
    return [...planCombo('cmd+space'), { pause:600 }, ...planText(action.name.trim()), { pause:500 }, ...planCombo('enter')];
  }
  throw Error('unknown desktop action');
}

async function execute(session, action, signal) {
  const events = actionPlan(action);
  let granted = false;
  try {
    for (const event of events) {
      if (signal?.aborted || session.cancelled) throw Error('control stopped');
      if (event.pause) { if (granted) { await session.command('end'); granted = false; } await pause(event.pause); continue; }
      if (!granted) { await session.command('grant'); granted = true; }
      await session.command('send', event);
    }
  } finally { if (granted && !session.cancelled) { try { await session.command('end'); } catch (_) { /* the watcher already stopped */ } } }
}
module.exports = { actionPlan, execute, planCombo, planText };
