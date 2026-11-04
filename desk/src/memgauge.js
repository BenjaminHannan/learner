'use strict';
// Always-on v2, phase 4b: the memory gauge that decides how many bored-mode Motes may run.
//   macOS memory pressure (the same sysctl as the v1 loop: 1 normal, 2 warning, 4 critical) + swap growth (sysctl vm.swapusage)
//   🟢 + Ben away + on AC power -> the full batch      🟢 + Ben busy (or on battery) -> at most 2
//   🟡 -> 1 while Ben is away, 0 while he is busy      🔴 or swap growing -> 0 (everything stops)
//   Ben chatting -> 0, always (Ben first)
const { execFileSync } = require('child_process');

const SWAP_GROW_MB = 256;   // swap that grew this much since the last reading (about 30 s) = "swap growing"
const FULL_BATCH = 4;

// "total = 2048.00M  used = 1234.50M  free = 813.50M  (encrypted)" -> used MB (null when unreadable)
function parseSwap(s) {
  const m = /used\s*=\s*([\d.]+)\s*([KMGT])/i.exec(String(s || ''));
  if (!m) return null;
  const mult = { K: 1 / 1024, M: 1, G: 1024, T: 1024 * 1024 }[m[2].toUpperCase()];
  return Number(m[1]) * mult;
}
function readSwapMB() {
  if (process.platform !== 'darwin') return null;
  try { return parseSwap(String(execFileSync('/usr/sbin/sysctl', ['-n', 'vm.swapusage'], { timeout: 2000 }))); } catch (e) { return null; }
}

// -> 'green' | 'yellow' | 'red'
function gauge({ pressure, swapGrowMB }) {
  const p = Number(pressure) || 1;
  if (p >= 4 || (Number(swapGrowMB) || 0) >= SWAP_GROW_MB) return 'red';
  if (p >= 2) return 'yellow';
  return 'green';
}
const DOT = { green: '🟢', yellow: '🟡', red: '🔴' };

// how many Motes may run now
function budget({ gauge: g, away, onAC, chatting, full }) {
  if (chatting) return 0;
  if (g === 'red') return 0;
  if (g === 'yellow') return away ? 1 : 0;
  if (away && onAC) return full || FULL_BATCH;
  return 2;
}

// keeps the last swap reading so "growing" can be measured
class MemGauge {
  // o: { pressure() -> 1|2|4, swapMB() -> number|null, now, everyMs }
  constructor(o) { this.o = o || {}; this.now = this.o.now || Date.now; this.everyMs = this.o.everyMs || 30000; this.prev = null; this.prevAt = 0; this.grow = 0; }
  read() {
    const now = this.now();
    if (!this.prevAt || now - this.prevAt >= this.everyMs) {
      const s = this.o.swapMB ? this.o.swapMB() : readSwapMB();
      if (s != null) { this.grow = this.prev == null ? 0 : s - this.prev; this.prev = s; }
      this.prevAt = now;
    }
    const pressure = this.o.pressure ? this.o.pressure() : 1;
    return { level: gauge({ pressure, swapGrowMB: this.grow }), pressure, swapGrowMB: Math.round(this.grow) };
  }
}

module.exports = { gauge, budget, parseSwap, readSwapMB, MemGauge, DOT, SWAP_GROW_MB, FULL_BATCH };
