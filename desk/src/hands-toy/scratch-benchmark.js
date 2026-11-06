'use strict';
// Explicit, bounded desktop-only measurement. No keyboard text saved; no release flag changed.
const fs = require('node:fs'), path = require('node:path'), { spawn } = require('node:child_process');
function startScratchBenchmark(base, executable) {
  const root = fs.mkdtempSync(path.join(base, 'scratch-desktop-'));
  fs.chmodSync(root, 0o700);
  const files = ['screen.mp4', 'detail.mp4'].map(n => path.join(root,n));
  for (const file of files) fs.closeSync(fs.openSync(file,'wx',0o600));
  const result = { root, enabled:true, done:false, frames:0, bytes:0, screenOnly:true, seconds:120 };
  const env = {...process.env}; delete env.ELECTRON_RUN_AS_NODE;
  const encoder = spawn('/opt/homebrew/bin/ffmpeg', ['-nostdin','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','bgra','-video_size','1280x720','-framerate','20','-i','pipe:0','-filter_complex','[0:v]split=2[a][b];[b]crop=192:192[c]','-map','[a]','-c:v','h264_videotoolbox','-b:v','2500k','-pix_fmt','yuv420p','-movflags','frag_keyframe+empty_moov','-f','mp4','pipe:3','-map','[c]','-c:v','h264_videotoolbox','-b:v','200k','-pix_fmt','yuv420p','-movflags','frag_keyframe+empty_moov','-f','mp4','pipe:4'], {stdio:['pipe','ignore','pipe','pipe','pipe']});
  const source = spawn(executable, ['--glim-recorder-native','--scratch-benchmark'], {env,stdio:['pipe','pipe','pipe','pipe']});
  result.sourcePid=source.pid; result.encoderPid=encoder.pid;
  const began=Date.now(); let buffer='', errors='', stopped=false, fallback;
  let finish; const done = new Promise(resolve => { finish=resolve; });
  const stop = () => {if(stopped)return;stopped=true;source.kill('SIGTERM');encoder.stdin.end();fallback=setTimeout(()=>encoder.kill('SIGKILL'),3000);};
  source.stdout.pipe(encoder.stdin);encoder.stdin.on('error',()=>{});
  source.stderr.on('data',()=>{});
  source.stdio[3].on('data', chunk => {buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i);buffer=buffer.slice(i+1);try{const event=JSON.parse(line);if(event.type==='frame')result.frames++;if(event.type==='source_error'){result.error=event.reason;stop();}}catch{result.error='invalid native metadata';stop();}}});
  for(const [fd,file] of [[3,files[0]],[4,files[1]]])encoder.stdio[fd].on('data',chunk=>{const st=fs.statfsSync(root);if(result.bytes+chunk.length>128*1024**2 || st.bavail*st.bsize-chunk.length<10*1024**3){result.error='disk backstop';stop();return;}fs.appendFileSync(file,chunk);result.bytes+=chunk.length;});
  encoder.stderr.on('data',d=>{errors=(errors+d).slice(-2000);});
  const timer=setTimeout(stop,120000);
  const monitor=setInterval(()=>{const st=fs.statfsSync(root);if(st.bavail*st.bsize<10*1024**3){result.error='disk backstop';stop();}},250);
  source.on('exit',code=>{if(code && !stopped)result.error='capture exited '+code;encoder.stdin.end();});
  for(const child of [source,encoder])child.on('error',error=>{result.error=error.message;stop();});
  encoder.on('exit',code=>{clearTimeout(timer);clearInterval(monitor);stop();clearTimeout(fallback);result.elapsedSeconds=(Date.now()-began)/1000;result.encoderCode=code;if(code)result.error=errors||'encoder failed';result.enabled=false;result.done=true;result.bytesPerMinute=result.bytes*60/result.elapsedSeconds;for(const file of files)fs.unlinkSync(file);fs.rmdirSync(root);result.scratchDeleted=!fs.existsSync(root);fs.writeFileSync(path.join(base,'DESKTOP-BENCHMARK.json'),JSON.stringify(result,null,2),{mode:0o600});finish();});
  return {result,stop,done};
}
module.exports={startScratchBenchmark};
