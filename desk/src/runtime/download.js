'use strict';
// Resumable HTTP download with a SHA256 check, for the built-in runtime. `fetch` is injectable (tests use a mock server).
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

function sha256File(file) {
  return new Promise((resolve, reject) => {
    const h = crypto.createHash('sha256');
    const s = fs.createReadStream(file);
    s.on('data', (d) => h.update(d)); s.on('error', reject); s.on('end', () => resolve(h.digest('hex')));
  });
}
const size = (f) => { try { return fs.statSync(f).size; } catch (e) { return 0; } };

/**
 * downloadFile({url, dest, sha256?, fetch?, onProgress?({done,total}), signal?, headers?}) -> {dest, bytes, resumed, verified}
 * Writes dest + '.part' and renames when complete. A .part from an earlier run is continued with a Range request; if the server
 * answers 200 (no range support) or 416 with a bad file, it starts over. A wrong checksum deletes the file and throws.
 */
// A connection can go silent without closing (seen Nov 5: a 4.4 GB brain download stopped at 2.28 GB and the app waited for hours).
// No bytes for o.stallMs (default 60 s) = stalled: the attempt is dropped and the next one resumes from the .part file, up to
// o.retries times (default 8, 3 s apart). A cancel by the caller and a checksum mismatch are never retried.
async function downloadFile(o) {
  const tries = o.retries == null ? 8 : o.retries;
  for (let i = 0; ; i++) {
    try { return await downloadOnce(o); } catch (e) {
      if ((o.signal && o.signal.aborted) || /checksum mismatch/.test(e.message) || /^download failed: HTTP 4/.test(e.message) || i >= tries) throw e;
      if (o.onRetry) { try { o.onRetry(e, i + 1); } catch (x) { /* ignore */ } }
      await new Promise((r) => setTimeout(r, o.retryDelayMs == null ? 3000 : o.retryDelayMs));
    }
  }
}
async function downloadOnce(o) {
  const f = o.fetch || fetch;
  const stallMs = o.stallMs || 60000;
  const local = new AbortController();
  const signal = o.signal ? AbortSignal.any([o.signal, local.signal]) : local.signal;
  const part = o.dest + '.part';
  fs.mkdirSync(path.dirname(o.dest), { recursive: true });
  if (fs.existsSync(o.dest) && o.sha256) {
    if ((await sha256File(o.dest)) === o.sha256.toLowerCase()) return { dest: o.dest, bytes: size(o.dest), resumed: false, verified: true, cached: true };
  } else if (fs.existsSync(o.dest) && !o.sha256 && o.trustExisting) return { dest: o.dest, bytes: size(o.dest), resumed: false, verified: false, cached: true };

  let have = size(part);
  let resumed = false;
  for (let attempt = 0; attempt < 2; attempt++) {
    const headers = { ...(o.headers || {}) };
    if (have > 0) headers.range = 'bytes=' + have + '-';
    const stalled = () => { const e = new Error('download stalled (no data for ' + Math.round(stallMs / 1000) + ' s)'); e.code = 'stalled'; return e; };
    let tm; const timed = (p) => { p.catch(() => {}); return Promise.race([p, new Promise((res, rej) => { tm = setTimeout(() => { local.abort(); rej(stalled()); }, stallMs); })]).finally(() => clearTimeout(tm)); };
    const r = await timed(f(o.url, { headers, signal, redirect: 'follow' }));
    if (r.status === 416) { // our .part is already the whole file (or garbage): check below, else start over
      if (o.sha256 && (await sha256File(part)) !== o.sha256.toLowerCase()) { fs.rmSync(part, { force: true }); have = 0; continue; }
      fs.renameSync(part, o.dest); return { dest: o.dest, bytes: size(o.dest), resumed: true, verified: !!o.sha256 };
    }
    if (!r.ok) throw new Error('download failed: HTTP ' + r.status + ' for ' + o.url);
    let flags = 'a';
    if (r.status === 200 && have > 0) { have = 0; flags = 'w'; }   // server ignored Range: restart
    else if (r.status === 206) resumed = have > 0;
    const len = Number(r.headers.get('content-length')) || 0;
    const total = len ? len + have : 0;
    let done = have;
    const out = fs.createWriteStream(part, { flags });
    let outErr = null;
    out.on('error', (e) => { outErr = e; });
    try {
      const reader = r.body.getReader();
      for (;;) {
        const { value, done: fin } = await timed(reader.read());
        if (fin) break;
        if (outErr) throw outErr;
        await new Promise((res, rej) => { out.write(value, (e) => (e ? rej(e) : res())); });   // the write callback carries the error: no 'error' listener per chunk (16k of them on a 1 GB file)
        done += value.length;
        if (o.onProgress) o.onProgress({ done, total });
      }
    } finally { await new Promise((res) => out.end(res)); }
    if (outErr) throw outErr;
    if (total && size(part) < total) throw new Error('download cut short (' + size(part) + ' of ' + total + ' bytes); run it again to resume');
    break;
  }
  let verified = false;
  if (o.sha256) {
    const got = await sha256File(part);
    if (got !== o.sha256.toLowerCase()) { fs.rmSync(part, { force: true }); throw new Error('checksum mismatch for ' + path.basename(o.dest) + ' (got ' + got.slice(0, 12) + ', wanted ' + o.sha256.slice(0, 12) + '); deleted, try again'); }
    verified = true;
  }
  fs.renameSync(part, o.dest);
  return { dest: o.dest, bytes: size(o.dest), resumed, verified };
}

async function getJson(url, f, headers, signal, timeoutMs) {
  const t = AbortSignal.timeout(timeoutMs || 10000); // a stalled server must not hang the install
  const r = await (f || fetch)(url, { signal: signal ? AbortSignal.any([signal, t]) : t, headers: { accept: 'application/json', 'user-agent': 'premonition', ...(headers || {}) } });
  if (!r.ok) throw new Error('HTTP ' + r.status + ' for ' + url);
  return r.json();
}

module.exports = { downloadFile, sha256File, getJson };
