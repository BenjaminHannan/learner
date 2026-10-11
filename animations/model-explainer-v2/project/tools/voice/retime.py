"""Give scenes just enough extra time for their narration, and move caption onsets so each caption gets the time its speech needs.
    VOICE_AUDIO_DIR=<clips dir> python3 tools/voice/retime.py [--apply] [--tempo-max 1.0] [--margin 0.3] [--step 0.5] [--max-scene 60]
Without --apply it only prints what would change. With --apply it edits content/chNN.json (scene "duration"; captions become {"at": fraction, "text": ...}),
then run:  node tools/merge.mjs && node tools/audit.mjs && node tools/voice/plan.mjs
A scene needs a change when a clip would have to be sped up by more than --tempo-max to fit its slot. The scene's pictures follow the captions
(the builders use S.capAt(i)), so moving a caption moves its pictures with it. Slot formulas mirror plan.mjs."""
import argparse, json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
AUDIO = os.environ.get("VOICE_AUDIO_DIR") or os.path.join(ROOT, "narration", "audio")
FADE, LEAD, TAIL, EXTRA_LAST, READ_FIRST = 0.4, 0.25, 0.15, 0.3, 0.6


def onsets(d, caps):
    n = len(caps)
    span = ((d - FADE - 0.3) - READ_FIRST) / n
    return [(c["at"] * d if isinstance(c, dict) and c.get("at") is not None else READ_FIRST + i * span) for i, c in enumerate(caps)]


def slots(d, caps):
    on, n, out = onsets(d, caps), len(caps), []
    for i in range(n):
        start = on[i] + LEAD
        end = (on[i + 1] if i < n - 1 else d - FADE) - TAIL
        out.append(end - start + (EXTRA_LAST if i == n - 1 else 0))
    return out


def layout(d, mins):
    """caption onsets in a scene of length d: every caption gets at least its minimum, the rest is shared evenly (water-filling).
    mins[i] = least onset-to-next-onset gap; mins[-1] = least time from the last onset to the scene end. Returns None if it does not fit."""
    n = len(mins)
    if READ_FIRST + sum(mins) > d + 1e-9:
        return None
    total = d - READ_FIRST
    bonus = [0.0] * (n - 1) + [0.7]            # the last caption's share includes the closing fade, as in an even layout
    lo, hi = 0.0, total
    for _ in range(60):
        lam = (lo + hi) / 2
        if sum(max(m, lam + b) for m, b in zip(mins, bonus)) > total:
            hi = lam
        else:
            lo = lam
    gaps = [max(m, lo + b) for m, b in zip(mins, bonus)]
    gaps[-1] += total - sum(gaps)              # absorb rounding
    o, t = [], READ_FIRST
    for g in gaps[:-1]:
        o.append(t); t += g
    o.append(t)
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--tempo-max", type=float, default=1.0)
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--margin", type=float, default=0.3, help="seconds of slack kept between a clip's end and its slot's end")
    ap.add_argument("--max-scene", type=float, default=60.0)
    a = ap.parse_args()
    index = json.load(open(os.path.join(AUDIO, "index.json")))
    order = json.load(open(os.path.join(ROOT, "content", "global.json")))["order"]
    changes, NL = [], {}
    for cid in order:
        path = os.path.join(ROOT, "content", cid + ".json")
        raw = open(path).read(); NL[cid] = raw.endswith("\n"); ch = json.loads(raw)
        dirty = False
        for sc in ch["scenes"]:
            caps = sc["caption"] if isinstance(sc["caption"], list) else [sc["caption"]]
            texts = [c["text"] if isinstance(c, dict) else c for c in caps]
            durs = [index.get(f"{cid}.{sc['id']}.c{i + 1}", {}).get("dur") for i in range(len(caps))]
            if None in durs:
                print("  no clip for", cid, sc["id"]); continue
            d = float(sc["duration"])
            if all(x <= s * a.tempo_max for x, s in zip(durs, slots(d, caps))):
                continue
            n = len(caps)
            mins = []
            for i, (x, t) in enumerate(zip(durs, texts)):
                read = 1.2 + len(t.split()) / 2.8 + 0.05                      # the audit's least reading time
                if i < n - 1:
                    mins.append(max(read, x / a.tempo_max + LEAD + TAIL + a.margin))
                else:
                    mins.append(max(read + 0.7, x / a.tempo_max + 0.5 + a.margin))   # last: from its onset to the scene end
            d2, o = d, None
            while o is None and d2 < 200:
                o = layout(d2, mins)
                if o is None:
                    d2 += a.step
            flag = "  (OVER THE SCENE LIMIT)" if d2 > a.max_scene else ""
            changes.append((cid, sc["id"], d, d2, flag))
            if a.apply:
                sc["duration"] = int(d2) if d2 == int(d2) else d2
                sc["caption"] = [{"at": round(oi / d2, 4), "text": t} for oi, t in zip(o, texts)]
                dirty = True
        if dirty:
            open(path, "w").write(json.dumps(ch, indent=2, ensure_ascii=False) + ("\n" if NL[cid] else ""))
    tot = sum(c[3] - c[2] for c in changes)
    for cid, sid, d, d2, flag in changes:
        print(f"  {cid}.{sid}: {d:g} s -> {d2:g} s (+{d2 - d:g}){flag}")
    first = changes[0][0] if changes else None
    print(f"{len(changes)} scenes change, +{tot:g} s in all; first changed part: {first}")
    if not a.apply:
        print("(dry run; add --apply to edit content/*.json)")


if __name__ == "__main__":
    main()
