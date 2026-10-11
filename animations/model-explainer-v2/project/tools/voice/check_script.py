"""Gate for narration scripts.
    python3 tools/voice/check_script.py ch04            one chapter (reads narration/script/ch04.json)
    python3 tools/voice/check_script.py                 all chapters that have a script
    python3 tools/voice/check_script.py --script DIR ch04    same, reading DIR/ch04.json instead of narration/script
Fails (exit 1) on: a missing or extra segment id, speech predicted to be longer than its slot, a number that is not in the scene's own text,
a caption number that was left out, text the voice cannot say (see speakify.check_text).
Warns on: a caveat word family present in the caption but absent in the narration (never/only/planned/suggested/...), spelled-out numbers
that are not in the caption."""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from speakify import speakify, check_text  # noqa: E402

NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
SPELLED = re.compile(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|hundred|thousand|million|billion|first|second|third|fourth|fifth|twice|half|double)\b", re.I)
FAMILIES = {
    "negation": r"\b(never|not|no|none|without|isn't|aren't|hasn't|haven't|can't|cannot|won't|doesn't|don't|unbuilt)\b",
    "only": r"\b(only|just|merely)\b",
    "plan": r"\b(planned|plan|plans|planning|will|first run)\b",
    "suggested": r"\b(suggested|suggest|suggests|idea|untested|unproven|unknown|unclear|open|guess|might|may|could|probably)\b",
    "built": r"\b(built|code exists)\b",
    "asof": r"\bas of\b",
    "one": r"\b(one copy|one seed|single|one size|one run|one test|one probe)\b",
    "older": r"\b(older|earlier|old)\b",
    "illustration": r"\b(made-up|made up|example|picture only|illustration|pretend)\b",
    "missed": r"\b(missed|miss|fail|failed)\b",
    "about": r"\b(about|roughly|around|nearly|almost|at most|at least|up to)\b",
    "standin": r"\b(stand-in|stand in|placeholder)\b",
}


def predict_dur(spoken):
    """Seconds the voice (Kokoro af_heart, speed 0.92) takes; fitted on 55 clips, std 0.33 s."""
    letters = len(re.sub(r"[^A-Za-z]", "", spoken))
    sents = len(re.findall(r"[.!?](?:\s|$)", spoken))
    com = len(re.findall(r"[,:;]", spoken))
    return -0.45 + 0.075 * letters + 0.253 * sents + 0.142 * com


def nums(s):
    return {n.replace(",", "").rstrip(".") for n in NUM.findall(s)}


ROUND_RX = re.compile(r"(\d+(?:\.\d+)?)\s+(thousand|million|billion)\b", re.I)
SCALE = {"thousand": 1e3, "million": 1e6, "billion": 1e9}
HEDGE = re.compile(r"\b(about|roughly|nearly|around|almost|just over|just under)\b", re.I)


def rounded_forms(t, source_nums):
    """A big number (100,000 or more) may be spoken rounded to 3 significant figures, introduced with a hedge word:
    134,217,728 -> 'about 134 million'. Returns (digit strings that are such roundings, source numbers they stand for)."""
    said, covered = set(), set()
    for m in ROUND_RX.finditer(t):
        v = float(m.group(1)) * SCALE[m.group(2).lower()]
        for n in source_nums:
            try:
                x = float(n)
            except ValueError:
                continue
            if x >= 100000 and abs(v - x) / x <= 0.006 and m.group(1) != n:
                said.add(m.group(1)); covered.add(n)
    return said, covered


def scene_text(ch, sid):
    for sc in ch["scenes"]:
        if sc["id"] == sid:
            keep = []

            def walk(v, key=None):
                if key in ("src", "notes", "duration", "id", "at", "atMap"):
                    return
                if isinstance(v, str):
                    keep.append(v)
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    keep.append(str(v))
                elif isinstance(v, list):
                    for x in v:
                        walk(x)
                elif isinstance(v, dict):
                    for k, x in v.items():
                        walk(x, k)
            walk(sc)
            return " ".join(keep)
    return ""


def check(cid, sdir=None):
    plan = json.load(open(os.path.join(ROOT, "narration", "plan.json")))["segments"]
    segs = [s for s in plan if s["ch"] == cid]
    path = os.path.join(sdir or os.path.join(ROOT, "narration", "script"), cid + ".json")
    if not os.path.exists(path):
        return [f"{cid}: no script file at narration/script/{cid}.json"], []
    script = json.load(open(path))
    cpath = os.path.join(ROOT, "content", cid + ".json")
    ch = json.load(open(cpath)) if os.path.exists(cpath) else None
    errs, warns = [], []
    ids = {s["id"] for s in segs}
    for i in sorted(ids - set(script)):
        errs.append(f"{i}: missing")
    for i in sorted(set(script) - ids):
        errs.append(f"{i}: not in the plan")
    for s in segs:
        t = script.get(s["id"])
        if t is None or not isinstance(t, str):
            continue
        w = len(t.split())
        cap_n = nums(s["text"])
        sc_n = nums(scene_text(ch, s["scene"])) if (ch and s["scene"] != "card") else cap_n
        got = nums(t)
        said_r, covered_r = rounded_forms(t, cap_n | sc_n)
        if said_r and not HEDGE.search(t):
            errs.append(f"{s['id']}: a rounded big number ({sorted(said_r)}) needs a word like 'about' or 'roughly' in front of it")
        got = got - said_r
        cap_n = cap_n - covered_r
        spoken = speakify(t)
        pred = predict_dur(spoken)
        slot = s.get("slot") or round(s["end"] - s["start"], 2)
        if pred > slot - 0.5:
            errs.append(f"{s['id']}: would take about {pred:.1f} s to say but the slot is {slot:.1f} s (aim for {slot - 1.0:.1f} s or less; about {max(1, round((pred - slot + 1.0) / 0.33))} fewer words)")
        if got - sc_n - cap_n:
            errs.append(f"{s['id']}: number(s) not in this scene's text: {sorted(got - sc_n - cap_n)}")
        if cap_n - got:
            errs.append(f"{s['id']}: caption number(s) left out: {sorted(cap_n - got)}")
        for p in check_text(speakify(t)):
            errs.append(f"{s['id']}: {p}")
        low_cap, low_t = s["text"].lower(), t.lower()
        for fam, rx in FAMILIES.items():
            if re.search(rx, low_cap) and not re.search(rx, low_t):
                warns.append(f"{s['id']}: caveat word family '{fam}' is in the caption but not in the narration")
        sp_new = {m.lower() for m in SPELLED.findall(t)} - {m.lower() for m in SPELLED.findall(s["text"])}
        if sp_new and s["kind"] == "caption":
            warns.append(f"{s['id']}: spelled number word(s) not in the caption: {sorted(sp_new)}")
    return errs, warns


if __name__ == "__main__":
    args = sys.argv[1:]
    sdir = os.path.join(ROOT, "narration", "script")
    if "--script" in args:
        i = args.index("--script")
        sdir = os.path.abspath(args[i + 1])
        args = args[:i] + args[i + 2:]
    want = args
    cids = want or (sorted(f[:-5] for f in os.listdir(sdir) if f.endswith(".json")) if os.path.isdir(sdir) else want)
    bad = 0
    for cid in cids:
        errs, warns = check(cid, sdir)
        print(f"{cid}: {len(errs)} error(s), {len(warns)} warning(s)")
        for e in errs:
            print("  ERROR", e)
        for w in warns:
            print("  warn ", w)
        bad += len(errs)
    sys.exit(1 if bad else 0)
