'use strict';
// How much memory the graphics card has (Windows), to pick the brain's size: Q8_0 on cards with >= 12 GB, Q4_K_M below.
// Order: PREMONITION_VRAM_GB (testing) -> nvidia-smi -> the display-adapter registry keys (AMD, Intel and NVIDIA drivers
// all write HardwareInformation.qwMemorySize, a 64-bit byte count) -> unknown (null; the caller then takes the safe Q4_K_M).
const { execFile } = require('child_process');
const C = require('./constants');

const GIB = 1024 ** 3;
const run = (cmd, args) => new Promise((resolve) => execFile(cmd, args, { windowsHide: true, timeout: 8000 }, (e, so) => resolve(e ? '' : String(so))));

// `nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits` -> one MiB number per card
function parseNvidiaSmi(text) {
  const mib = String(text || '').split(/\r?\n/).map((l) => Number(l.trim())).filter((n) => Number.isFinite(n) && n > 0);
  return mib.length ? Math.max(...mib) * 1024 * 1024 : 0;
}
// `reg query "HKLM\...\{4d36e968-...}" /s /v HardwareInformation.qwMemorySize` ->
//     HardwareInformation.qwMemorySize    REG_QWORD    0x3faf00000
// (one line per adapter key; the largest wins). Older drivers write a REG_BINARY little-endian value instead.
function parseRegQuery(text) {
  let best = 0;
  for (const line of String(text || '').split(/\r?\n/)) {
    const m = /HardwareInformation\.qwMemorySize\s+(REG_QWORD|REG_BINARY)\s+(\S+)/i.exec(line);
    if (!m) continue;
    let v = 0;
    if (/QWORD/i.test(m[1])) v = Number(BigInt(m[2]));
    else { const hex = m[2].replace(/[^0-9a-f]/gi, ''); for (let i = hex.length - 2; i >= 0; i -= 2) v = v * 256 + parseInt(hex.slice(i, i + 2), 16); }
    if (Number.isFinite(v) && v > best) best = v;
  }
  return best;
}
const REG_KEY = 'HKLM\\SYSTEM\\CurrentControlSet\\Control\\Class\\{4d36e968-e325-11ce-bfc1-08002be10318}';

/** detectVram({exec, env, platform}) -> {bytes, source} ; bytes 0 = unknown */
async function detectVram(o) {
  o = o || {};
  const env = o.env || process.env; const exec = o.exec || run;
  const forced = Number(env.PREMONITION_VRAM_GB);
  if (env.PREMONITION_VRAM_GB != null && env.PREMONITION_VRAM_GB !== '' && Number.isFinite(forced) && forced >= 0) return { bytes: forced * GIB, source: 'env' };
  if ((o.platform || process.platform) !== 'win32') return { bytes: 0, source: 'none' };
  const nv = parseNvidiaSmi(await exec('nvidia-smi', ['--query-gpu=memory.total', '--format=csv,noheader,nounits']));
  if (nv) return { bytes: nv, source: 'nvidia-smi' };
  const reg = parseRegQuery(await exec('reg', ['query', REG_KEY, '/s', '/v', 'HardwareInformation.qwMemorySize']));
  if (reg) return { bytes: reg, source: 'registry' };
  return { bytes: 0, source: 'none' };
}
// 0x3faf00000 bytes reads as 15.92 GiB, so compare against 12 GiB minus a little slack for cards reported a hair under.
function quantFor(bytes) { return bytes >= (C.WIN_Q8_MIN_VRAM_GB - 0.25) * GIB ? 'q8_0' : 'q4_k_m'; }

module.exports = { detectVram, parseNvidiaSmi, parseRegQuery, quantFor, REG_KEY, GIB };
