"""Turn the raw tween list (extract_events.mjs) into a thinned list of sound-effect placements.
  python3 place_rules.py raw-ch04.json out-sfx-ch04.json [--min-gap 1.5]
Rules (all numbers can be tuned at the top):
  scene change   -> whoosh, 0.1 s before the cross-fade starts
  pop            -> a 'pop'-ease tween (chips etc., area >= 4000 px2) or a fade-in of a box/card/vec/track/text block with area >= 10000 px2;
                    items that appear within 0.6 s of each other are one burst = ONE pop, at the burst start
  tick           -> a count-up (at its start), a bar growing, a pulse (emphasis); bursts again merged
  chime          -> end of the LAST count-up (else last bar) of a scene: the 'result lands' moment, one per scene at most
  riser          -> 1.5 s riser ending at the first count/bar of a scene that also has a chime, at most one per 40 s
  never          -> headings, captions, chapter chip, progress bar, arrows/line draws (53 in ch04, too fine), fade-outs, anything under the area limits
  thinning       -> greedy by priority (whoosh > chime > riser > pop > tick), keep an effect only if no kept effect is within MIN_GAP seconds
                    (a riser occupies the 1.5 s before its end).  a lower priority never removes a higher one."""
import json, sys, collections
MIN_GAP = 1.5; BURST = 0.6; POP_AREA = 10000; POP_KIND_AREA = 4000; RISER_LEN = 1.5; RISER_EVERY = 40
SKIP_CLS = {'heading', 'caption', 'ctext', 'chip-ch', 'kicker', 'big', 'rule', 'blurb'}
PRI = {'whoosh': 6, 'chime': 5, 'riser': 4, 'pop': 2, 'tick': 1}

def classify(raw):
    sc_start = {}; cand = []; counts = collections.defaultdict(list)
    scenes = sorted((e['t'], e['scene']) for e in raw if e['cls'].startswith('scene') and 'startAt' in e['props'] and e['kind'] == 'other')
    def scene_of(t):
        s = None
        for t0, sid in scenes:
            if t0 <= t + 1e-6: s = sid
        return s
    for t0, sid in scenes: cand.append(dict(t=t0 - 0.1, fx='whoosh', scene=sid, why='scene change'))
    for e in raw:
        if e['cls'] in SKIP_CLS or e['cls'].startswith('scene') or e['cls'] == 'chip-ch': continue
        k, t = e['kind'], e['t']; s = e['scene'] or scene_of(t)
        if k == 'count': cand.append(dict(t=t, fx='tick', scene=s, why='count-up', dur=e['dur'], count=True))
        elif k == 'grow' and e['cls'] == 'fill': cand.append(dict(t=t, fx='tick', scene=s, why='bar grow', dur=e['dur'], count=True))
        elif k == 'pulse': cand.append(dict(t=t, fx='tick', scene=s, why='pulse'))
        elif k == 'pop' and e['area'] >= POP_KIND_AREA: cand.append(dict(t=t, fx='pop', scene=s, why='pop-ease ' + e['cls']))
        elif k == 'fadein' and e['area'] >= POP_AREA and e['tag'] == 'div': cand.append(dict(t=t, fx='pop', scene=s, why='fade-in ' + e['cls']))
    # bursts: merge same-kind events closer than BURST to the previous one in the burst
    cand.sort(key=lambda c: (c['fx'], c['t'])); merged = []
    for c in cand:
        if merged and c['fx'] in ('pop', 'tick') and merged[-1]['fx'] == c['fx'] and c['t'] - merged[-1]['_last'] <= BURST and c['scene'] == merged[-1]['scene']:
            merged[-1]['_last'] = c['t']; merged[-1]['n'] += 1; continue
        c = dict(c); c['_last'] = c['t']; c['n'] = 1; merged.append(c)
    # chime and riser from the last count/bar of each scene
    by = collections.defaultdict(list)
    for c in cand:
        if c.get('count'): by[c['scene']].append(c)
    extra = []; last_riser = -1e9
    for s in sorted(by, key=lambda s: by[s][0]['t']):
        cs = sorted(by[s], key=lambda c: c['t']); last = cs[-1]
        extra.append(dict(t=last['t'] + last['dur'], fx='chime', scene=s, why='result lands', n=1))
        if cs[0]['t'] - last_riser >= RISER_EVERY:
            extra.append(dict(t=cs[0]['t'], fx='riser', scene=s, why='before reveal', n=1)); last_riser = cs[0]['t']
    return merged + extra

def thin(ev):
    kept = []
    def span(e): return (e['t'] - RISER_LEN, e['t']) if e['fx'] == 'riser' else (e['t'], e['t'])
    for e in sorted(ev, key=lambda e: (-PRI[e['fx']], e['t'])):
        a, b = span(e)
        if all(b + MIN_GAP <= span(k)[0] or span(k)[1] + MIN_GAP <= a for k in kept): kept.append(e)
    return sorted(kept, key=lambda e: e['t'])

if __name__ == '__main__':
    raw = json.load(open(sys.argv[1])); out = sys.argv[2]
    if '--min-gap' in sys.argv: MIN_GAP = float(sys.argv[sys.argv.index('--min-gap') + 1])
    ev = classify(raw); kept = thin(ev)
    for e in kept: e.pop('_last', None); e.pop('count', None); e.pop('dur', None); e['t'] = round(max(e['t'], 0), 3)
    json.dump(kept, open(out, 'w'), indent=0)
    total = max(e['t'] for e in raw if e['t'] < 1e5 and e['dur'] < 1e3)
    mins = total / 60
    print(f'raw tween-targets {len(raw)} ({len(raw)/mins:.0f}/min); candidates {len(ev)} ({len(ev)/mins:.1f}/min); kept {len(kept)} ({len(kept)/mins:.1f}/min), part length ~{total:.0f} s')
    print('kept by effect:', dict(collections.Counter(e['fx'] for e in kept)), 'candidates by effect:', dict(collections.Counter(e['fx'] for e in ev)))
    gaps = [b['t'] - a['t'] for a, b in zip(kept, kept[1:])]
    print('gap between kept effects: min %.2f median %.2f s' % (min(gaps), sorted(gaps)[len(gaps)//2]))
