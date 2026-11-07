'use strict';

const fs = require('node:fs');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { performance } = require('node:perf_hooks');

const ceilings = Object.freeze({ maxBytes: 64 * 1024 * 1024, maxFrames: 600, maxWidth: 1280, maxHeight: 720, timeoutMs: 10000 });
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

function createFileDecoder({ file, expected, ffmpeg, ffprobe, limits = {} }) {
  let started = performance.now();
  const caps = {};
  if (!limits || typeof limits !== 'object' || Array.isArray(limits)) throw new Error('invalid limits');
  for (const key of Object.keys(limits)) if (!(key in ceilings)) throw new Error('unknown limit');
  for (const [key, ceiling] of Object.entries(ceilings)) {
    const value = limits[key] === undefined ? ceiling : limits[key];
    if (!Number.isSafeInteger(value) || value <= 0 || value > ceiling) throw new Error(`invalid limit ${key}`);
    caps[key] = value;
  }
  if (typeof file !== 'string' || !file || typeof ffmpeg !== 'string' || !ffmpeg || typeof ffprobe !== 'string' || !ffprobe || !expected || !Number.isSafeInteger(expected.bytes) || expected.bytes <= 0 || expected.bytes > caps.maxBytes || !/^[a-f0-9]{64}$/.test(expected.sha256)) throw new Error('invalid source binding or executable');
  const remaining = () => {
    const value = Math.floor(caps.timeoutMs - (performance.now() - started));
    if (value <= 0) throw new Error('elapsed timeout');
    return value;
  };
  const snapshot = () => {
    remaining();
    const before = fs.lstatSync(file);
    if (!before.isFile() || before.isSymbolicLink() || before.size !== expected.bytes) throw new Error('invalid or changed source');
    const fd = fs.openSync(file, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0));
    try {
      const opened = fs.fstatSync(fd);
      if (!opened.isFile() || opened.dev !== before.dev || opened.ino !== before.ino || opened.size !== expected.bytes) throw new Error('changed source');
      const hash = crypto.createHash('sha256');
      const chunk = Buffer.allocUnsafe(Math.min(1024 * 1024, expected.bytes));
      let total = 0;
      while (total < expected.bytes) {
        remaining();
        const count = fs.readSync(fd, chunk, 0, Math.min(chunk.length, expected.bytes - total), total);
        if (!count) throw new Error('truncated source');
        hash.update(chunk.subarray(0, count));
        total += count;
      }
      const after = fs.fstatSync(fd);
      const pathAfter = fs.lstatSync(file);
      if (!pathAfter.isFile() || pathAfter.isSymbolicLink() || after.dev !== before.dev || after.ino !== before.ino || pathAfter.dev !== before.dev || pathAfter.ino !== before.ino || after.size !== before.size || after.mtimeMs !== before.mtimeMs || after.ctimeMs !== before.ctimeMs || hash.digest('hex') !== expected.sha256) throw new Error('changed source');
      remaining();
      return `${before.dev}:${before.ino}:${before.size}:${before.mtimeMs}:${before.ctimeMs}`;
    } finally { fs.closeSync(fd); }
  };
  const run = (binary, args, maxBuffer) => {
    const result = spawnSync(binary, args, { encoding: null, maxBuffer, timeout: remaining(), windowsHide: true });
    remaining();
    if (result.error || result.status !== 0 || result.signal) throw new Error(`media process failed: ${result.error?.message || result.status || result.signal}`);
    return result.stdout;
  };
  const sourceArgs = ['-protocol_whitelist', 'file,pipe', '-enable_drefs', '0', '-use_absolute_path', '0', '-f', 'mov', '-i', file];
  const binding = snapshot();
  const output = run(ffprobe, ['-v', 'error', ...sourceArgs, '-show_streams', '-show_frames', '-show_entries', 'stream=index,codec_type,codec_name,width,height,time_base:frame=media_type,stream_index,pts,width,height', '-of', 'json'], 2 * 1024 * 1024);
  if (snapshot() !== binding) throw new Error('source mutation');
  let probe;
  try { probe = JSON.parse(output.toString('utf8')); } catch { throw new Error('invalid probe output'); }
  if (!Array.isArray(probe.streams) || probe.streams.length !== 1 || !Array.isArray(probe.frames)) throw new Error('unsupported streams');
  const stream = probe.streams[0];
  if (stream.codec_type !== 'video' || stream.codec_name !== 'h264' || !Number.isSafeInteger(stream.index)) throw new Error('unsupported codec');
  const timeBase = /^([1-9]\d*)\/([1-9]\d*)$/.exec(stream.time_base || '');
  if (!timeBase || !Number.isSafeInteger(Number(timeBase[1])) || !Number.isSafeInteger(Number(timeBase[2]))) throw new Error('invalid time base');
  const numerator = Number(timeBase[1]);
  const timescale = Number(timeBase[2]);
  const validSize = (width, height) => Number.isSafeInteger(width) && width > 0 && width <= caps.maxWidth && Number.isSafeInteger(height) && height > 0 && height <= caps.maxHeight;
  if (!validSize(stream.width, stream.height) || probe.frames.length < 1 || probe.frames.length > caps.maxFrames) throw new Error('frame limits exceeded');
  let previous = null;
  const index = probe.frames.map((frame, position) => {
    const pts = typeof frame.pts === 'number' ? frame.pts : /^-?\d+$/.test(frame.pts || '') ? Number(frame.pts) : NaN;
    const value = pts * numerator;
    if (frame.media_type !== 'video' || frame.stream_index !== stream.index || !Number.isSafeInteger(pts) || !Number.isSafeInteger(value) || (previous !== null && value <= previous) || !validSize(frame.width, frame.height) || frame.width !== stream.width || frame.height !== stream.height) throw new Error('invalid frame index or PTS');
    previous = value;
    return Object.freeze({ encodedOrdinal: position + 1, encodedPts: Object.freeze({ value, timescale }), width: frame.width, height: frame.height });
  });
  Object.freeze(index);
  const implementation = Object.freeze({ id: 'local-ffmpeg-file-decoder', version: '1', sha256: digest(fs.readFileSync(__filename)) });
  remaining();
  return Object.freeze({ schema: 'screen-video-decoder/v1', source: Object.freeze({ sha256: expected.sha256, bytes: expected.bytes }), implementation, index, readFrame(ordinal) {
    started = performance.now();
    if (!Number.isSafeInteger(ordinal) || ordinal < 1 || ordinal > index.length) throw new Error('invalid ordinal');
    if (snapshot() !== binding) throw new Error('source mutation');
    const entry = index[ordinal - 1];
    const size = entry.width * entry.height * 4;
    const pixels = run(ffmpeg, ['-v', 'error', '-xerror', ...sourceArgs, '-map', '0:v:0', '-vf', `select=eq(n\\,${ordinal - 1})`, '-fps_mode', 'passthrough', '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgba', 'pipe:1'], size + 65536);
    if (snapshot() !== binding) throw new Error('source mutation');
    if (pixels.length !== size) throw new Error('truncated decoded frame');
    return { encodedOrdinal: ordinal, encodedPts: { ...entry.encodedPts }, width: entry.width, height: entry.height, pixelFormat: 'RGBA', pixels: Buffer.from(pixels) };
  } });
}

module.exports = { createFileDecoder };
