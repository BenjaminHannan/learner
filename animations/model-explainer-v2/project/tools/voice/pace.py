"""Pace every scene to its narration (the tutor-video approach): each caption appears when its line starts, the next one follows right after the line ends,
and the scene ends shortly after the last line. Pictures that were keyed to the old caption spacing follow the captions through "atMap" (see kit.js at()).
    VOICE_AUDIO_DIR=<clips dir> python3 tools/voice/pace.py --base DIR_WITH_ORIGINAL_CONTENT [--apply] [--pause 0.9] [--tail 1.2] [--min extent-min.json]
--base is a copy of content/ from BEFORE any narration timing (captions evenly spaced), so the old layout is known and running this again never compounds.
--min is {"chNN.sNN": least_seconds} written by tools/voice/extent.mjs for scenes whose pictures need more time than their speech.
Scene lengths are rounded up to 0.5 s (whole frames). Without --apply it only prints. After --apply:  node tools/merge.mjs && node tools/audit.mjs && node tools/voice/plan.mjs"""
import argparse, json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
AUDIO = os.environ.get("VOICE_AUDIO_DIR") or os.path.join(ROOT, "narration", "audio")
LEAD, FADE = 0.25, 0.4
FIRST = 0.6
SKIP = {"id", "src", "notes", "duration", "illustration", "at", "atMap"}


def words(v):
    if isinstance(v, bool):
        return 0
    if isinstance(v, str):
        return len(v.split())
    if isinstance(v, (int, float)):
        return 1
    if isinstance(v, list):
        return sum(words(x) for x in v)
    if isinstance(v, dict):
        return sum(words(x) for k, x in v.items() if k not in SKIP)
    return 0


def onsets(d, caps):
    n = len(caps)
    span = ((d - FADE - 0.3) - FIRST) / n
    return [(c["at"] * d if isinstance(c, dict) and c.get("at") is not None else FIRST + i * span) for i, c in enumerate(caps)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--pause", type=float, default=0.9, help="silence between one line and the next")
    ap.add_argument("--tail", type=float, default=1.2, help="seconds from the end of the last line to the end of the scene")
    ap.add_argument("--min", help="JSON file {chNN.sNN: least seconds}")
    ap.add_argument("--min-scene", type=float, default=8.0)
    ap.add_argument("--floor", choices=["audit", "labels", "none"], default="labels",
                    help="least scene length for reading what is on screen: audit = the silent-video rule (3 + all words / 2.6); labels = the same rule for the words that are NOT captions "
                         "(the voice reads the captions); none = speech only")
    ap.add_argument("--label-rate", type=float, default=2.6, help="words per second assumed for reading labels")
    a = ap.parse_args()
    index = json.load(open(os.path.join(AUDIO, "index.json")))
    order = json.load(open(os.path.join(ROOT, "content", "global.json")))["order"]
    extent = json.load(open(a.min)) if a.min and os.path.exists(a.min) else {}
    old_total = new_total = 0.0
    rows = []
    for cid in order:
        path = os.path.join(ROOT, "content", cid + ".json")
        raw = open(path).read(); nl = raw.endswith("\n")
        ch = json.loads(raw)
        base = {s["id"]: s for s in json.load(open(os.path.join(a.base, cid + ".json")))["scenes"]}
        for sc in ch["scenes"]:
            b = base[sc["id"]]
            bcaps = b["caption"] if isinstance(b["caption"], list) else [b["caption"]]
            texts = [c["text"] if isinstance(c, dict) else c for c in bcaps]
            n = len(texts)
            durs = [index[f"{cid}.{sc['id']}.c{i + 1}"]["dur"] for i in range(n)]
            d_old = float(b["duration"])
            a_old = [o / d_old for o in onsets(d_old, bcaps)]
            o = [FIRST]
            for i in range(n - 1):
                gap = max(durs[i] + a.pause, 1.3 + len(texts[i].split()) / 2.8)    # speech plus a pause; never less than the audit's reading time
                o.append(o[-1] + gap)
            need = o[-1] + LEAD + durs[-1] + a.tail
            probe = dict(b); probe["caption"] = texts if a.floor == "audit" else []
            floor = 0 if a.floor == "none" else 3 + words(probe) / a.label_rate
            need = max(need, floor, a.min_scene, extent.get(f"{cid}.{sc['id']}", 0))
            d_new = math.ceil(need * 2) / 2
            b_new = [x / d_new for x in o]
            old_total += d_old; new_total += d_new
            rows.append((cid, sc["id"], d_old, d_new))
            if a.apply:
                sc["duration"] = int(d_new) if d_new == int(d_new) else d_new
                sc["caption"] = [{"at": round(bi, 4), "text": t} for bi, t in zip(b_new, texts)]
                maps = [[round(x, 4), round(y, 4)] for x, y in zip(a_old, b_new)]
                if all(maps[i][0] < maps[i + 1][0] and maps[i][1] < maps[i + 1][1] for i in range(len(maps) - 1)):
                    sc["atMap"] = maps
                else:
                    sc.pop("atMap", None)
        if a.apply:
            open(path, "w").write(json.dumps(ch, indent=2, ensure_ascii=False) + ("\n" if nl else ""))
    for cid, sid, d0, d1 in rows:
        if abs(d1 - d0) >= 6 or d1 > 55:
            print(f"  {cid}.{sid}: {d0:g} -> {d1:g}")
    print(f"scenes {len(rows)}: {old_total / 60:.1f} min -> {new_total / 60:.1f} min ({(new_total - old_total) / 60:+.1f})")
    if not a.apply:
        print("(dry run; add --apply)")


if __name__ == "__main__":
    main()
