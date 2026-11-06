'use strict';
const fs=require('node:fs'),path=require('node:path'),{createHash}=require('node:crypto');const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const REQUIRED=['T1','T2','T3','T4','T5','T6','T7','T8','T9','T10'];
class Bundles {
 constructor(dir){this.dir=dir;fs.mkdirSync(dir,{recursive:true,mode:0o700});}
 validate(manifest){const files=['candidate.pt','candidate.ts'];for(const [i,n]of files.entries()){const p=path.join(this.dir,n);if(!fs.existsSync(p)||sha(p)!==manifest[i?'export_sha256':'sha256'])throw Error('broken candidate '+n);}let size=0;for(const n of fs.readdirSync(this.dir)){const st=fs.statSync(path.join(this.dir,n));if(st.isFile())size+=st.size;}if(size>1024**3)throw Error('bundle cap');return true;}
 promote(manifest,marks,{heldKeys=0}={}){this.validate(manifest);if(heldKeys||manifest.offline_seatbelt!==true||REQUIRED.some(k=>marks[k]!=='PASS'))throw Error('quarantined: all frozen marks and offline seatbelt required');const next={...manifest,files:{weights:'candidate.pt',runtime:'candidate.ts'},promotedAt:new Date().toISOString()};
 // Bundle files are content-addressed; a single pointer switches encoder + heads + mapping together.
 for(const [src,hash]of [['candidate.pt',manifest.sha256],['candidate.ts',manifest.export_sha256]])fs.copyFileSync(path.join(this.dir,src),path.join(this.dir,hash+path.extname(src)));
 const current=path.join(this.dir,'current.json');if(fs.existsSync(current))fs.copyFileSync(current,path.join(this.dir,'previous.json'));next.files={weights:manifest.sha256+'.pt',runtime:manifest.export_sha256+'.ts'};fs.writeFileSync(current+'.tmp',JSON.stringify(next));fs.renameSync(current+'.tmp',current);return next;}
 rollback(){const prev=path.join(this.dir,'previous.json');if(!fs.existsSync(prev))return false;const p=JSON.parse(fs.readFileSync(prev));for(const [k,h]of [['weights',p.sha256],['runtime',p.export_sha256]]){if(path.basename(p.files[k])!==p.files[k]||sha(path.join(this.dir,p.files[k]))!==h)throw Error('previous bundle corrupt');}const cur=path.join(this.dir,'current.json');fs.copyFileSync(prev,cur+'.tmp');fs.renameSync(cur+'.tmp',cur);return true;}
}
module.exports={Bundles,sha,REQUIRED};
