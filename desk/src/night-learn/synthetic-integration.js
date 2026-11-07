'use strict';
// Explicit integration command; avoids putting model training in node --test.
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict'),{spawnSync}=require('node:child_process');
const {sourceClips}=require('./run'),{score}=require('./score');
const output=process.argv[2];if(!output)throw Error('output directory required');fs.mkdirSync(output,{recursive:true,mode:0o700});
const python=path.join(os.homedir(),'learner-ops/p2venv/bin/python'),src=__dirname;
function run(args){const r=spawnSync(python,args,{encoding:'utf8',maxBuffer:16*1024*1024,timeout:600000});if(r.status!==0)throw Error(r.stderr||r.error);return r.stdout;}
const recording=path.join(output,'recording'),work=path.join(output,'frames');fs.mkdirSync(work,{recursive:true});run([path.join(src,'synthetic.py'),recording]);
const prepared=sourceClips(JSON.parse(fs.readFileSync(path.join(recording,'clip-index.json'))),null,{passed:false},work,recording);
assert.equal(prepared.examples.length,400,JSON.stringify(prepared.rejections));
const examples=prepared.examples.map(e=>({...e,intent:'Click the blue save button to save the document'}));
const data=path.join(output,'dataset.json');fs.writeFileSync(data,JSON.stringify({startMs:examples[0].timeMs,endMs:examples.at(-1).timeMs,examples,trainingSteps:80}));
const result=JSON.parse(run([path.join(src,'trainer.py'),'--dry-run',data,path.join(output,'models')]));const scored=score(result);
const report={source:'synthetic MP4s and fabricated event clock metadata; 400 distinct action identities, jittered click locations; fixed nonzero intent',examples:400,train:result.train.length,held:result.held.length,trainingSteps:80,score:scored,models:result.modelSha256};
fs.writeFileSync(path.join(output,'result.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
assert.ok(result.held.length>=50);assert.equal(scored.pass,true);assert.ok(scored.rates.candidate.click>scored.rates.old.click);assert.ok(scored.rates.candidate.click>scored.rates.noIntent.click);
