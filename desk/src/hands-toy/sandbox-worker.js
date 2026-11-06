'use strict';
const {Sandbox}=require('./sandbox');let sandbox=new Sandbox();const timer=setInterval(()=>{const f=sandbox.render();if(process.connected)process.send({pixels:f.pixels.toString('base64'),status:JSON.stringify(sandbox.outcome())});},1000/30);
process.on('message',m=>{if(m.op!=='manual')return;const p=m.packet||{};if(['click','drag','type','scroll','sparks'].includes(p.reset))sandbox=new Sandbox({task:p.reset});else sandbox.receive(p);});process.on('disconnect',()=>{clearInterval(timer);process.exit(0);});
