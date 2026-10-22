"""One-command full-video mixer: leveled narration + generated music bed (per part) + sparse sound effects -> stereo AAC.
  bash build_mix.sh PROJECT_DIR NARRATION.m4a OUT.m4a        (see build_mix.sh)
Reads everything from files, nothing is hard-coded per part:
  * part order + lengths: content.js (rebuilt from content/*.json in a scratch copy) = 5 s card + scene durations, then the end card
  * speech times: narration/plan.json segments, refined by the real speech energy in the narration file
  * picture events: extract_events.mjs on a scratch build of the full timeline (fallback: scene starts + title cards from content)
Nothing is written into PROJECT_DIR. Fails (exit 1) unless the finished file is within -18..-16 LUFS, true peak <= -1 dBTP and
its duration matches the narration within 0.1 s."""
import argparse, collections, json, os, shutil, subprocess, sys, tempfile, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from alib import SR, db, write_wav, loudnorm_json
import music, sfx as sfxmod, place_rules as pr

# ---- knobs (dB are relative to a bed at -17 LUFS, i.e. "LU under the voice") ----
G_SPEECH, G_GAP = -17.0, -10.0
MERGE, LEAD, HOLD = 0.9, 0.25, 0.2
TAU_DOWN, TAU_UP = 0.10, 0.50
SWELL_DB, SWELL_LEN = 6.0, 3.0        # title-card swell: +6 dB raised-cosine bump over the first 3 s of each part
XFADE = 1.0                           # equal-power crossfade of two beds: +-1 s around each part boundary
END_FADE = 6.0                        # gentle end: the last bed fades out over the last 6 s
SFX_GAIN = {'whoosh': -20, 'pop': -18, 'tick': -22, 'chime': -20, 'riser': -22}
PRIO = {'chime_title': 7, 'whoosh': 6, 'chime': 5, 'riser': 4, 'pop': 2, 'tick': 1}
MIN_GAP, MAX_PER_MIN = 1.5, 6
ROOTS = {'ch00': 0, 'ch01': 7, 'ch03': 2, 'ch04': 5, 'ch05': 0, 'ch06': 7, 'ch07': 2, 'ch08': 5, 'ch09': 9, 'ch11': 7, 'ch12': 2, 'ch14': 0, 'end': 0}
ROOT_CYCLE = [7, 2, 5, 9]             # for part ids not in ROOTS (never equal to the previous part's key)
LUFS_LO, LUFS_HI, TP_MAX, TARGET = -18.0, -16.0, -1.0, -17.0

def log(*a): print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)
def die(msg): print('FAIL:', msg, file=sys.stderr); sys.exit(1)
def run(cmd, **k): return subprocess.run(cmd, check=True, **k)

# ---------------------------------------------------------------- 1. parts
def read_parts(proj, work):
    """returns [(id, start, length, [scene starts])], total.  Uses a scratch copy so the project is never touched."""
    proj_copy = os.path.join(work, 'project')
    shutil.copytree(proj, proj_copy, ignore=shutil.ignore_patterns('narration', 'node_modules', '.git', 'tools'))
    os.makedirs(proj_copy + '/tools', exist_ok=True)
    for f in ('merge.mjs', 'mkindex.mjs'): shutil.copy(os.path.join(proj, 'tools', f), proj_copy + '/tools/' + f)
    try: run(['node', proj_copy + '/tools/merge.mjs'], capture_output=True)
    except Exception as e: log('merge.mjs failed, using the project content.js as is:', e)
    js = ("const vm=require('vm'),fs=require('fs');const w={};vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window:w});"
          "const C=w.CONTENT;const G=C.global||{};const out=[];for(const id of C.order){const ch=C.chapters[id];const sc=[];let card=ch.card!==false?(G.cardSeconds||5):0;"
          "for(const s of ch.scenes||[])sc.push(s.duration);out.push({id,card,scenes:sc});}"
          "console.log(JSON.stringify({parts:out,end:G.endCard?(G.endCard.duration||8):0}));")
    d = json.loads(run(['node', '-e', js, proj_copy + '/content.js'], capture_output=True, text=True).stdout)
    parts, t = [], 0.0
    for p in d['parts']:
        starts, u = [], t
        if p['card']: u += p['card']
        for dur in p['scenes']: starts.append(u); u += dur
        parts.append(dict(id=p['id'], start=t, length=u - t, card=p['card'], scene_starts=starts, root=None)); t = u
    if d['end']: parts.append(dict(id='end', start=t, length=d['end'], card=d['end'], scene_starts=[], root=None)); t += d['end']
    return parts, t, proj_copy

# ---------------------------------------------------------------- 2. speech windows
def decode(path, sr, ch=1):
    r = run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', str(ch), '-ar', str(sr), '-'], capture_output=True)
    return np.frombuffer(r.stdout, dtype='<f4')

def speech_windows(plan, narr, total):
    """per plan segment: the real [start, end] of speech (energy in the narration inside the slot), else the plan window."""
    x = decode(narr, 8000); fr = 80                           # 10 ms frames
    n = len(x) // fr; rms = np.sqrt((x[:n * fr].reshape(n, fr) ** 2).mean(1) + 1e-12)
    act = 20 * np.log10(rms) > -50
    segs = []
    for s in plan['segments']:
        a = max(0, int((s['start'] - 0.15) * 100)); b = min(n, int((s['end'] + 0.3) * 100))
        idx = np.nonzero(act[a:b])[0]
        if len(idx): segs.append((( a + idx[0]) / 100, (a + idx[-1] + 1) / 100))
        else: segs.append((s['start'], s['end']))
    return segs, float(act.mean())

def envelope(segs, total, parts, fps=100):
    n = int(total * fps) + 1; target = np.full(n, G_GAP)
    merged = []
    for a, b in sorted(segs):
        if merged and a - merged[-1][1] < MERGE: merged[-1][1] = max(b, merged[-1][1])
        else: merged.append([a, b])
    for a, b in merged: target[max(0, int((a - LEAD) * fps)): min(n, int((b + HOLD) * fps))] = G_SPEECH
    dn, up = 1 - np.exp(-1 / (fps * TAU_DOWN)), 1 - np.exp(-1 / (fps * TAU_UP))
    g = np.empty(n); cur = G_GAP
    for i in range(n):
        cur += (target[i] - cur) * (dn if target[i] < cur else up); g[i] = cur
    t = np.arange(n) / fps
    for p in parts:                                         # title-card swell
        u = (t - p['start']) / SWELL_LEN; m = (u >= 0) & (u < 1); g[m] += SWELL_DB * np.sin(np.pi * u[m]) ** 2
    return g, merged

# ---------------------------------------------------------------- 3. effects
def sfx_events(proj_copy, parts, total, plan):
    ev = []
    try:
        shutil.copy(os.path.join(HERE, 'extract_events.mjs'), proj_copy + '/extract_events.mjs')
        run(['node', proj_copy + '/tools/mkindex.mjs'], capture_output=True, cwd=proj_copy)
        raw_path = proj_copy + '/raw-events.json'
        run(['node', proj_copy + '/extract_events.mjs', '--dir', proj_copy, '--out', raw_path], capture_output=True, text=True, timeout=600, cwd=proj_copy)
        raw = json.load(open(raw_path)); ev = pr.classify(raw)
        for e in ev: e.pop('_last', None); e.pop('count', None)
        log('picture events extracted:', len(raw), 'tween targets,', len(ev), 'candidates')
    except Exception as e:
        log('WARNING event extraction failed (%s); using scene starts + title cards only' % str(e)[:200])
        ev = [dict(t=s - 0.1, fx='whoosh', scene='?', why='scene start (content)', n=1) for p in parts for s in p['scene_starts']]
    for p in parts:
        ev.append(dict(t=p['start'] + 0.1, fx='chime_title', scene='card', why='title card ' + p['id'], n=1))
        ev.append(dict(t=p['start'] + 0.1, fx='whoosh', scene='card', why='part start ' + p['id'], n=1))
    return ev

def thin(ev, total):
    """priority-greedy: min gap MIN_GAP (a riser occupies the 1.5 s before its end), at most MAX_PER_MIN in any 60 s window"""
    def span(e): return (e['t'] - pr.RISER_LEN, e['t']) if e['fx'] == 'riser' else (e['t'], e['t'])
    kept = []
    for e in sorted(ev, key=lambda e: (-PRIO[e['fx']], e['t'])):
        if e['t'] < 0 or e['t'] > total - 0.5: continue
        a, b = span(e)
        if not all(b + MIN_GAP <= span(k)[0] or span(k)[1] + MIN_GAP <= a for k in kept): continue
        ts = sorted([k['t'] for k in kept] + [e['t']])
        if any(sum(1 for u in ts if w <= u < w + 60) > MAX_PER_MIN for w in ts if w > e['t'] - 60 and w <= e['t']): continue
        kept.append(e)
    kept.sort(key=lambda e: e['t'])
    for e in kept: e['fx'] = 'chime' if e['fx'] == 'chime_title' else e['fx']
    return kept

# ---------------------------------------------------------------- 4. render bed + effects into one float32 stereo memmap
def bed_loop(root, seed, work, cache):
    key = (root, seed)
    if key not in cache:
        y = music.normalise_rms(music.render_loop(root, seed), -24)
        write_wav(work + '/_ref.wav', y); m = loudnorm_json(work + '/_ref.wav')
        cache[key] = (y * db(TARGET - m['input_i'])).astype(np.float32)
    return cache[key]

def part_weight(t, p, i, nparts, total):
    S, E = p['start'], p['start'] + p['length']
    if i == 0: wi = np.sin(np.pi / 2 * np.clip((t - S) / 2.0, 0, 1)) ** 2
    else: wi = np.sin(np.pi / 2 * np.clip((t - (S - XFADE)) / (2 * XFADE), 0, 1))
    if i == nparts - 1: wo = np.cos(np.pi / 2 * np.clip((t - (total - END_FADE)) / END_FADE, 0, 1)) ** 2
    else: wo = np.cos(np.pi / 2 * np.clip((t - (E - XFADE)) / (2 * XFADE), 0, 1))
    return wi * wo

def render(parts, total, g, events, raw_path, work):
    n = int(round(total * SR)); mm = np.memmap(raw_path, dtype='<f4', mode='w+', shape=(n, 2))
    cache, prev_root = {}, None
    for i, p in enumerate(parts):
        root = ROOTS.get(p['id'])
        if root is None: root = next(r for r in ROOT_CYCLE * 2 if r != prev_root and r != ROOTS.get(parts[i - 1]['id'], -1)) if i else 0
        prev_root = p['root'] = root
        loop = bed_loop(root, 1 + (i % 4), work, cache); N = len(loop)
        t_a, t_b = max(0.0, p['start'] - XFADE), min(total, p['start'] + p['length'] + XFADE)
        if i == len(parts) - 1: t_b = total
        i0, i1 = int(t_a * SR), min(n, int(t_b * SR)); s0 = int(round(p['start'] * SR)); B = 20 * SR
        for a in range(i0, i1, B):
            b = min(i1, a + B); t = np.arange(a, b) / SR
            w = part_weight(t, p, i, len(parts), total) * db(np.interp(t, np.arange(len(g)) / 100, g))
            seg = loop[(np.arange(a, b) - s0) % N] * w[:, None].astype(np.float32)
            mm[a:b] += seg
    log('beds rendered; keys:', {p['id']: p['root'] for p in parts})
    fx = {k: f() for k, f in sfxmod.EFFECTS.items()}
    for e in events:
        x = fx[e['fx']] * db(SFX_GAIN[e['fx']]); t0 = e['t'] - (len(x) / SR if e['fx'] == 'riser' else 0)
        a = int(round(t0 * SR))
        if a < 0: x = x[-a:]; a = 0
        x = x[: n - a]; pan = 0.5 + 0.18 * np.sin(e['t'] * 2.399)
        mm[a:a + len(x), 0] += (x * np.sqrt(1 - pan)).astype(np.float32); mm[a:a + len(x), 1] += (x * np.sqrt(pan)).astype(np.float32)
    mm.flush(); del mm

# ---------------------------------------------------------------- 5. mix + verify
def probe(path, field='duration'):
    return float(run(['ffprobe', '-v', 'error', '-show_entries', 'format=' + field, '-of', 'csv=p=0', path], capture_output=True, text=True).stdout)

def channels(path):
    return int(run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=channels', '-of', 'csv=p=0', path], capture_output=True, text=True).stdout)

def add_voice(narr, raw, total, ch):
    """sum the narration into the stem file in place (mono voice goes to both channels at -3 dB so it keeps its own loudness)"""
    n = int(round(total * SR)); mm = np.memmap(raw, dtype='<f4', mode='r+', shape=(n, 2)); B = 30 * SR
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', narr, '-f', 'f32le', '-ac', str(ch), '-ar', str(SR), '-'], stdout=subprocess.PIPE)
    for a in range(0, n, B):
        b = min(n, a + B); need = (b - a) * ch * 4; buf = b''
        while len(buf) < need:
            c = p.stdout.read(need - len(buf))
            if not c: break
            buf += c
        v = np.frombuffer(buf[: len(buf) // (4 * ch) * 4 * ch], dtype='<f4').reshape(-1, ch)
        k = len(v)
        if k: mm[a:a + k] += (v * 0.7071) if ch == 1 else v   # ch==1: broadcast to both columns
    p.stdout.close(); p.wait(); mm.flush(); del mm

def gain_limit(raw, total, gain_db, ceiling=0.708):
    """apply gain in place, then a short smooth look-ahead limit around any sample above the ceiling (rare)"""
    n = int(round(total * SR)); mm = np.memmap(raw, dtype='<f4', mode='r+', shape=(n, 2)); B = 30 * SR; g = db(gain_db); nlim = 0; peak = 0.0
    W = int(0.005 * SR); win = np.hanning(2 * W + 1); win /= win.sum()
    for a in range(0, n, B):
        b = min(n, a + B); x = mm[a:b] * np.float32(g); pk = np.abs(x).max(1); peak = max(peak, float(pk.max()))
        over = np.nonzero(pk > ceiling)[0]
        if len(over):
            need = np.ones(len(x)); need[over] = ceiling / pk[over]; nlim += len(over)
            lo, hi = max(0, over[0] - 2 * W), min(len(x), over[-1] + 2 * W + 1)
            seg = need[lo:hi].copy()                                             # grey dilation (min over +-W) then smoothing
            dil = np.array(seg); 
            for sh in range(1, W + 1):
                dil[sh:] = np.minimum(dil[sh:], seg[:-sh]); dil[:-sh] = np.minimum(dil[:-sh], seg[sh:])
            need[lo:hi] = np.convolve(np.pad(dil, W, constant_values=1.0), win, 'valid')[: hi - lo]
            x = x * need[:, None].astype(np.float32)
        mm[a:b] = x
    mm.flush(); del mm
    return peak, nlim

def measure_raw(raw):
    p = run(['ffmpeg', '-hide_banner', '-nostats', '-f', 'f32le', '-ar', '48000', '-ac', '2', '-i', raw, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True)
    js = json.loads(p.stderr[p.stderr.rindex('{'): p.stderr.rindex('}') + 1]); return {k: float(js[k]) for k in ('input_i', 'input_tp', 'input_lra')}

def encode(raw, out):
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', '48000', '-ac', '2', '-i', raw, '-c:a', 'aac', '-b:a', '128k', '-ar', '48000', '-movflags', '+faststart', out])

def main():
    global T0; T0 = time.time()
    ap = argparse.ArgumentParser(); ap.add_argument('project'); ap.add_argument('narration'); ap.add_argument('out')
    ap.add_argument('--work', help='scratch dir (needs ~1.6 GB for 63 min); default: a temp dir, deleted at the end'); ap.add_argument('--keep', action='store_true')
    ap.add_argument('--events', help='use this sfx placement json instead of extracting (list of {t, fx})')
    a = ap.parse_args()
    proj, narr, out = os.path.abspath(a.project), os.path.abspath(a.narration), os.path.abspath(a.out)
    plan = json.load(open(proj + '/narration/plan.json'))
    work = a.work or tempfile.mkdtemp(prefix='mix-'); os.makedirs(work, exist_ok=True)
    nd = probe(narr)
    parts, ctotal, proj_copy = read_parts(proj, work)
    log(f'narration {nd:.2f} s, plan {plan["total"]:.2f} s, content {ctotal:.2f} s; parts:', ' '.join(f'{p["id"]}@{p["start"]:.0f}+{p["length"]:.0f}' for p in parts))
    if abs(nd - plan['total']) > 0.5: die(f'narration length {nd:.2f} s does not match plan.json total {plan["total"]:.2f} s: wrong narration file or stale plan')
    if abs(ctotal - plan['total']) > 1.0: log(f'WARNING content-derived length {ctotal:.2f} s differs from plan total {plan["total"]:.2f} s (part boundaries may be off)')
    total = nd
    segs, share = speech_windows(plan, narr, total)
    g, merged = envelope(segs, total, parts)
    log(f'speech windows {len(merged)}, speech share {100 * sum(b - a_ for a_, b in merged) / total:.1f} %')
    ev = json.load(open(a.events)) if a.events else sfx_events(proj_copy, parts, total, plan)
    if a.events:
        for e in ev: e.setdefault('why', '')
    events = thin(ev, total)
    per_min = len(events) / (total / 60); log(f'effects kept {len(events)} ({per_min:.2f}/min):', dict(collections.Counter(e['fx'] for e in events)))
    raw = work + '/bed-sfx.f32'; render(parts, total, g, events, raw, work)
    log('rendered stems')
    out_tmp = work + '/mix.m4a'; ch = channels(narr)
    add_voice(narr, raw, total, ch); log('voice added')
    m0 = measure_raw(raw); gain = TARGET - m0['input_i']
    log(f'float mix before levelling: {m0["input_i"]:.2f} LUFS, true peak {m0["input_tp"]:.2f} dBTP; gain {gain:+.2f} dB')
    pk, nl = gain_limit(raw, total, gain); log(f'levelled; sample peak {pk:.3f}, {nl} samples limited')
    for attempt in range(2):
        encode(raw, out_tmp)
        m = loudnorm_json(out_tmp); dur = probe(out_tmp)
        log(f'attempt {attempt + 1}: {m["input_i"]:.2f} LUFS, true peak {m["input_tp"]:.2f} dBTP, LRA {m["input_lra"]:.1f}, duration {dur:.3f} s')
        ok = LUFS_LO <= m['input_i'] <= LUFS_HI and m['input_tp'] <= TP_MAX
        if ok or attempt: break
        d = min(TARGET - m['input_i'], TP_MAX - 0.3 - m['input_tp'])           # fix once: toward -17 LUFS but never above the peak ceiling
        gain_limit(raw, total, d)
    os.makedirs(os.path.dirname(out), exist_ok=True); shutil.copy(out_tmp, out)
    summary = dict(lufs=m['input_i'], true_peak_dbtp=m['input_tp'], lra=m['input_lra'], duration=dur, narration_duration=nd, effects=len(events),
                   effects_per_min=round(per_min, 2), seconds=round(time.time() - T0, 1), keys={p['id']: p['root'] for p in parts})
    json.dump(dict(summary=summary, effects=events), open(out + '.report.json', 'w'), indent=1)
    if not a.keep and not a.work: shutil.rmtree(work, ignore_errors=True)
    print(json.dumps(summary))
    if not ok: die(f'loudness {m["input_i"]:.2f} LUFS / true peak {m["input_tp"]:.2f} dBTP outside {LUFS_LO}..{LUFS_HI} LUFS / <= {TP_MAX} dBTP')
    if abs(dur - nd) > 0.1: die(f'duration {dur:.3f} s differs from narration {nd:.3f} s by more than 0.1 s')
    log('OK')

if __name__ == '__main__': main()
