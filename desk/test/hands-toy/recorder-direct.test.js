'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { Recorder, sourceEventLines } = require('../../src/hands-toy/recorder');

test('source event lines preserve split UTF-8 and recover after bounded invalid rows', () => {
  const rows = [];
  let invalid = 0;
  const parser = sourceEventLines(row => rows.push(row), () => invalid++);
  const encoded = Buffer.from('{"type":"extension","value":"α🙂"}\n');
  for (const byte of encoded) parser.push(Buffer.from([byte]));
  parser.push(Buffer.from('x'.repeat(5000) + '\nnull\n{bad}\n{"type":"frame"}\n'));
  assert.deepEqual(rows, [{ type: 'extension', value: 'α🙂' }, null, { type: 'frame' }]);
  assert.equal(invalid, 2);
  assert.equal(parser.complete(), true);
  parser.push(Buffer.from('{"unfinished":'));
  assert.equal(parser.complete(), false);
});

test('direct recorder inherits encoder input without a JS raw stream and drains exactly', { timeout: 10000 }, async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'recorder-direct-'));
  const encoderFile = path.join(root, 'encoder');
  const sourceFile = path.join(root, 'source');
  const header = '#!' + process.execPath + '\n';
  fs.writeFileSync(encoderFile, header + `
const fs = require('node:fs'), crypto = require('node:crypto');
const hash = crypto.createHash('sha256'); let bytes = 0;
process.stdin.on('data', chunk => { hash.update(chunk); bytes += chunk.length; });
process.stdin.on('end', () => { fs.writeSync(3, JSON.stringify({bytes, sha256:hash.digest('hex')})); fs.writeSync(4, 'detail'); });
`, { mode: 0o700 });
  fs.writeFileSync(sourceFile, header + `
const fs = require('node:fs');
const frame = Buffer.alloc(1280 * 720 * 4, 29);
for (let ordinal = 1; ordinal <= 4; ordinal++) {
  let offset = 0;
  while (offset < frame.length) offset += fs.writeSync(1, frame, offset, frame.length - offset);
  fs.writeSync(3, JSON.stringify({type:'frame',frameId:ordinal,t:ordinal*50,receiveMonotonicMs:ordinal*50})+'\\n');
}
process.stdin.resume();
`, { mode: 0o700 });
  const recorder = new Recorder({ root, releaseApproved: true, nativeHelper: sourceFile, ffmpeg: encoderFile,
    shutdownMs: 2000, retentionOptions: { freeBytes: () => 1e12 } });
  try {
    recorder.enabled = true;
    await recorder.segment();
    const source = recorder.source;
    assert.equal(source.stdout, null);
    assert.equal(recorder.activeSegment.sink, null);
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => { clearInterval(check); reject(Error('source metadata not drained')); }, 4000);
      const check = setInterval(() => {
        if (recorder.frames === 4) { clearTimeout(timer); clearInterval(check); resolve(); }
        else if (!recorder.enabled) { clearTimeout(timer); clearInterval(check); reject(Error(recorder.reason)); }
      }, 10);
    });
    await recorder.pause();
    const clips = Object.values(recorder.retention.data.clips);
    assert.equal(clips.length, 1);
    assert.equal(clips[0].frames, 4);
    assert.equal(clips[0].videoClock.offsetMs, null);
    const encoded = JSON.parse(fs.readFileSync(path.join(root, clips[0].files[0]), 'utf8'));
    const expected = crypto.createHash('sha256');
    for (let ordinal = 0; ordinal < 4; ordinal++) expected.update(Buffer.alloc(1280 * 720 * 4, 29));
    assert.equal(encoded.bytes, 4 * 1280 * 720 * 4);
    assert.equal(encoded.sha256, expected.digest('hex'));
    assert.equal(recorder.encoder, null);
    assert.equal(recorder.source, null);
  } finally {
    await recorder.off();
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('proof mode retains the independently hashed submission transport', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'recorder-proof-'));
  try {
    assert.equal(new Recorder({ root, proofMode: true }).directFrames, false);
    assert.equal(new Recorder({ root }).directFrames, true);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});
