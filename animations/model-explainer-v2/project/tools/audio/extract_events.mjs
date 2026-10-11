// Prototype: list every GSAP tween start in the built page with its kind, so sound effects can be placed automatically.
//   node events.mjs --dir PROJECT_DIR --out events.json
import fs from 'node:fs'; import path from 'node:path'; import { createRequire } from 'node:module';
const argv = process.argv.slice(2); const arg=(k,d)=>{const i=argv.indexOf(k);return i>=0?argv[i+1]:d;};
const dir = path.resolve(arg('--dir','.')); const out = arg('--out','events.json');
const require = createRequire(process.env.PLAYWRIGHT_DIR || '/opt/node22/lib/node_modules/');
const { chromium } = require('playwright');
const b = await chromium.launch(); const p = await b.newPage({ viewport:{width:1920,height:1080} });
p.on('pageerror',e=>console.error('pageerror',e.message));
await p.goto('file://'+dir+'/index.html');
await p.waitForFunction(()=>window.__timelines&&window.__timelines.main&&window.__TOTAL,null,{timeout:60000});
const data = await p.evaluate(()=>{
  const tl=window.__timelines.main, ev=[], scenes={};
  for (const sc of document.querySelectorAll('.scene')) scenes[sc.id.replace(/^sc-/,'')]={};
  for (const tw of tl.getChildren(true,true,false)) {
    let ts; try{ts=tw.targets();}catch(e){continue;}
    const start=tw.globalTime(0), dur=tw.duration(); if(!isFinite(start)) continue;
    const v=tw.vars||{};
    for (const el of ts) {
      if(!(el instanceof Element)) { if (v.onUpdate) ev.push({t:+start.toFixed(3),dur:+dur.toFixed(3),kind:'count',props:['value'],scene:null,cls:'',tag:'obj',area:0,w:0,h:0,text:''}); continue; }
      const sc = el.classList.contains('scene')?el:el.closest('.scene');
      const r = el.getBoundingClientRect();
      const props = Object.keys(v).filter(k=>!['duration','ease','delay','onUpdate','overwrite','stagger','immediateRender'].includes(k));
      let kind='other';
      if (v.onUpdate) kind='count';
      else if ('strokeDashoffset' in v) kind='draw';
      else if ('scaleX' in v || 'scaleY' in v) kind='grow';
      else if (typeof v.ease==='string' && v.ease.startsWith('back') ) kind='pop';
      else if ('autoAlpha' in v && v.autoAlpha===1 && dur<=0.005) kind='type';
      else if ('autoAlpha' in v && v.autoAlpha===1) kind='fadein';
      else if ('autoAlpha' in v && v.autoAlpha===0) kind='fadeout';
      else if ('x' in v||'y' in v) kind='move';
      else if ('scale' in v) kind='pulse';
      ev.push({ t:+start.toFixed(3), dur:+dur.toFixed(3), kind, props, scene: sc?sc.id.replace(/^sc-/,''):null,
        cls:(el.getAttribute('class')||'').slice(0,40), tag:el.tagName.toLowerCase(), area: Math.round(r.width*r.height), w:Math.round(r.width), h:Math.round(r.height),
        text:(el.textContent||'').trim().slice(0,24) });
    }
  }
  return ev;
});
await b.close();
fs.writeFileSync(out, JSON.stringify(data));
console.log('tween-target events:', data.length, '->', out);
