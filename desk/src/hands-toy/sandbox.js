'use strict';
const Sparks = require('../games/adapters/sparksquest');
const { rng } = require('../tinynet');
const { now } = require('./lease');
const W=320,H=180, CELL=14, X=80,Y=16;
// RGB renderer. This is the playground's framebuffer, never a screenshot of Ben.
function rect(b,x,y,w,h,c) { for(let r=Math.max(0,Math.floor(y));r<Math.min(H,y+h);r++) for(let q=Math.max(0,Math.floor(x));q<Math.min(W,x+w);q++) { const i=(r*W+q)*3;b[i]=c[0];b[i+1]=c[1];b[i+2]=c[2]; } }
const C={bg:[24,28,38],target:[52,180,250],decoy:[170,70,80],cursor:[255,255,255],me:[240,210,40],spark:[245,55,55],wave:[170,75,235],key:[60,240,130],tray:[55,110,110]};
class Sandbox {
 constructor({task='click',seed=101}={}) {
  this.task=task;this.seed=seed;this.r=rng(seed);this.cursor=[24,24];this.buttons=[];this.keys=[];this.text='';this.typed='';this.focus=false;this.wrong=0;this.dragging=false;this.scroll=0;this.finished=false;this.events=[];this.frameId=0;this.start=now();this.lastGame=0;this.lastJump=false;this.gameTicks=0;
  this.target=[Math.floor(60+this.r()*190),Math.floor(50+this.r()*85),32,24]; this.tray=[235,125,55,40];this.decoy=[35,130,38,24];this.expected='Blue-'+String(seed);this.needScroll=200+Math.floor(this.r()*250);
  if(task==='sparks') this.state=Sparks.init(seed);
 }
 inside(p,box) {return p[0]>=box[0]&&p[0]<box[0]+box[2]&&p[1]>=box[1]&&p[1]<box[1]+box[3];}
 intent() {return {code:this.task==='sparks'?'GOTO':this.task.toUpperCase(),targetPatch:C.target,text:this.expected,stepId:'toy:'+this.task,version:1};}
 receive(p) {
  const receipt=now();this.events.push({frameId:p.frameId,receivedMs:receipt,release:!!p.release}); if(this.events.length>20000)this.events.shift();
  if(p.release){this.keys=[];this.buttons=[];this.dragging=false;return receipt;}
  const prev=this.buttons;this.cursor=[Math.max(0,Math.min(W-1,this.cursor[0]+(p.dx||0))),Math.max(0,Math.min(H-1,this.cursor[1]+(p.dy||0)))];this.buttons=p.buttons||[];this.keys=p.keys||[];
  const down=this.buttons.includes('left')&&!prev.includes('left'),up=!this.buttons.includes('left')&&prev.includes('left');
  if(this.task==='scroll')this.scroll=Math.max(0,this.scroll+(p.wheel||0));
  if(down) {
   if(this.inside(this.cursor,this.target)&&(this.task!=='scroll'||this.scroll>=this.needScroll)) { if(this.task==='click'||this.task==='scroll')this.finished=true; if(this.task==='drag')this.dragging=true; if(this.task==='type')this.focus=true; }
   else {this.wrong++;this.focus=false;}
  }
  if(up&&this.task==='drag'&&this.dragging){this.finished=this.inside(this.cursor,this.tray);this.dragging=false;}
  if(this.task==='type'&&this.focus&&p.character){this.typed+=p.character;this.finished=this.typed===this.expected;}
  return receipt;
 }
 tick(t=now()) {
  if(this.task!=='sparks'||this.finished)return;
  if(!this.lastGame)this.lastGame=t;
  // Advance by elapsed wall time; never slow the game to wait for inference.
  while(t-this.lastGame>=50&&!Sparks.done(this.state,this.gameTicks*50)) {
   const a=this.keys.includes('ArrowUp')?1:this.keys.includes('ArrowDown')?2:this.keys.includes('ArrowLeft')?3:this.keys.includes('ArrowRight')?4:0;
   const jumping=this.keys.includes('Space');const fired=jumping&&!this.lastJump?[{action:'jump',atMs:this.gameTicks*50}]:[];this.lastJump=jumping;
   this.state=Sparks.step(this.state,a,fired,this.gameTicks*50).state;this.gameTicks++;this.lastGame+=50;
  }
  this.finished=Sparks.done(this.state,this.gameTicks*50);
 }
 render() {
  this.tick();const producedMs=now(),b=Buffer.alloc(W*H*3);rect(b,0,0,W,H,C.bg);
  if(this.task==='sparks') {
   const s=this.state;for(let r=0;r<11;r++)for(let c=0;c<11;c++)rect(b,X+c*CELL,Y+r*CELL,13,13,[34,40,52]);
   s.cps.forEach((p,i)=>rect(b,X+p.c*CELL+2,Y+p.r*CELL+2,10,10,i===s.next?C.target:[65,75,90]));
   if(s.key&&!s.keyHeld)rect(b,X+s.key[1]*CELL+3,Y+s.key[0]*CELL+3,8,8,C.key);
   for(const p of s.sp.sparks)rect(b,X+p.c*CELL+3,Y+p.r*CELL+3,8,8,C.spark);
   for(const wave of s.waves){const dt=(this.gameTicks*50-wave.t0)/50,rad=(wave.v0*dt+.5*wave.a*dt*dt)*CELL;for(let a=0;a<360;a+=2){const angle=a*Math.PI/180;rect(b,X+wave.ec*CELL+7+Math.cos(angle)*rad,Y+wave.er*CELL+7+Math.sin(angle)*rad,2,2,C.wave);}}
   rect(b,X+s.sp.me[1]*CELL+3,Y+s.sp.me[0]*CELL+3,8,8,C.me);
   // Visible status bars for progress, key, and life; no hidden state goes to policy.
   rect(b,4,8,Math.max(0,s.sp.lives)*7,5,C.key);rect(b,4,20,s.next*7,5,C.target);if(s.keyHeld)rect(b,4,30,7,5,C.key);
  } else {
   rect(b,...this.decoy,C.decoy);
   if(this.task==='drag')rect(b,...this.tray,C.tray);
   if(this.task!=='scroll'||this.scroll>=this.needScroll)rect(b,...this.target,C.target);
   else rect(b,305,10,5,Math.max(4,120*(1-this.scroll/this.needScroll)),C.target);
   if(this.dragging)rect(b,this.cursor[0]-8,this.cursor[1]-8,16,16,C.target);
   if(this.task==='type')rect(b,this.target[0],this.target[1]+30,Math.min(160,this.typed.length*5),4,C.key);
  }
  rect(b,this.cursor[0]-1,this.cursor[1]-1,3,3,C.cursor);const renderEndMs=now();
  return {pixels:b,width:W,height:H,frameId:++this.frameId,producedMs,renderEndMs,intent:this.intent()};
 }
 outcome(){return {task:this.task,seed:this.seed,success:this.task==='sparks'?Sparks.outcome(this.state).goalDone&&this.state.sp.lives===3:this.finished&&this.wrong===0,wrong:this.wrong,elapsedMs:now()-this.start,...(this.task==='sparks'?{game:Sparks.outcome(this.state)}:{})};}
 // Strong structured reference, explicitly not the pixel policy.
 rule(){const p={dx:0,dy:0,wheel:0,keys:[],buttons:[]};if(this.task==='sparks'){const o=Sparks.observe(this.state,this.gameTicks*50),target=this.state.key&&!this.state.keyHeld&&this.state.cps[this.state.next]?.locked?'KEY':this.state.cps[this.state.next]?.name||'H';const a=Sparks.fallback(o,{code:'GOTO',args:{to:target,guard:'jump'}});if(a)p.keys=[['','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'][a]];return p;}
 const target=this.dragging?this.tray:this.target;p.dx=Math.max(-24,Math.min(24,target[0]+target[2]/2-this.cursor[0]));p.dy=Math.max(-24,Math.min(24,target[1]+target[3]/2-this.cursor[1]));
 if(this.task==='scroll'&&this.scroll<this.needScroll){p.wheel=30;p.dx=0;p.dy=0;return p;}
 if(this.task==='drag'&&this.dragging){if(!this.inside(this.cursor,this.tray))p.buttons=['left'];}
 else if(this.inside(this.cursor,this.target)){if(this.task==='type'&&this.focus){p.character=this.expected[this.typed.length];}else if(!this.buttons.includes('left'))p.buttons=['left'];}
 return p;}
}
module.exports={Sandbox,W,H,C,rect};
