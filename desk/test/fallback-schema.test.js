'use strict';
const test=require('node:test'), assert=require('node:assert/strict');
const {extractFallbackCalls,streamChat}=require('../src/llm');
const {TOOL_DEFS,buildTools}=require('../src/prompt');
const xml=(name,args)=>'<function='+name+'>'+Object.entries(args).map(([k,v])=>'<parameter='+k+'>'+v+'</parameter>').join('')+'</function>';
const args=(s,tools)=>JSON.parse(extractFallbackCalls(s,tools).calls[0].arguments);
test('actual ask_user and browser_type schemas preserve JSON choices and literal string text',()=>{
 const defs=buildTools();
 assert.deepEqual(args(xml('ask_user',{question:'Choose',options:'["Yes","No"]'}),defs),{question:'Choose',options:['Yes','No']});
 assert.deepEqual(args(xml('browser_type',{id:'7',text:'42',enter:'true'}),defs),{id:7,text:'42',enter:true});
 assert.deepEqual(args(xml('browser_type',{id:'7',text:'true'}),defs),{id:7,text:'true'});
 assert.deepEqual(args(xml('browser_type',{id:'7',text:'001234'}),defs),{id:7,text:'001234'});
 assert.equal(TOOL_DEFS.ask_user.function.parameters.properties.options.type,'array');
});
test('object and array shapes parse only when correct, invalid input is preserved',()=>{
 const defs=[{type:'function',function:{name:'custom',parameters:{type:'object',properties:{arr:{type:'array'},obj:{type:'object'}}}}}];
 assert.deepEqual(args(xml('custom',{arr:'[1,{"x":2}]',obj:'{"key":[3]}'}),defs),{arr:[1,{x:2}],obj:{key:[3]}});
 assert.deepEqual(args(xml('custom',{arr:'[1,',obj:'[1]'}),defs),{arr:'[1,',obj:'[1]'});
 assert.deepEqual(args(xml('custom',{arr:'null',obj:'null'}),defs),{arr:'null',obj:'null'});
});
test('missing schemas and unknown properties retain existing coercion',()=>{
 assert.deepEqual(args(xml('custom',{a:'42',b:'true'})),{a:42,b:true});
 assert.deepEqual(args(xml('custom',{a:'42',b:'true'}),[{type:'function',function:{name:'other',parameters:{properties:{a:{type:'string'}}}}}]),{a:42,b:true});
});
function fetchSse(delta){return async()=>new Response('data: '+JSON.stringify({choices:[{delta}]})+'\n\ndata: [DONE]\n\n',{status:200,headers:{'content-type':'text/event-stream'}})}
test('streamChat supplies actual schemas to textual XML fallback',async()=>{
 const old=global.fetch; global.fetch=fetchSse({content:xml('ask_user',{question:'Choose',options:'["Yes","No"]'})});
 try {const out=await streamChat({gatewayUrl:'http://mock.invalid/v1',model:'m',messages:[],tools:buildTools()});assert.deepEqual(JSON.parse(out.toolCalls[0].arguments),{question:'Choose',options:['Yes','No']});} finally{global.fetch=old}
});
test('native structured tool calls retain exact arguments, even when schema differs',async()=>{
 const old=global.fetch, raw='{"id":7,"text":42}';global.fetch=fetchSse({tool_calls:[{index:0,id:'call1',function:{name:'browser_type',arguments:raw}}]});
 try {const out=await streamChat({gatewayUrl:'http://mock.invalid/v1',model:'m',messages:[],tools:buildTools()});assert.equal(out.toolCalls[0].arguments,raw);}finally{global.fetch=old}
});
