from collections import Counter
from learnlab.leaks import QAExample, leak_report, words
from learnlab.toy import make_registry, episodes

cap_ctx = lambda e: QAExample("\n".join(l.replace(e.target.place, e.target.place.capitalize()) for l in e.lines), e.question, e.target.place.capitalize())
tr, te = episodes(make_registry(), "train", 400), episodes(make_registry(), "test", 300)
r = leak_report([cap_ctx(e) for e in tr], [cap_ctx(e) for e in te])
print("CLEAN but capitalised answers -> leaking =", r.leaking, r.leaking_detectors, {k: round(v,3) for k,v in r.detectors.items()}, "floor", round(r.floor,3))

# honest dumb strategy the floor ignores: choose the most-mentioned place in context
def mode_place(ex):
    c = Counter(t for t in words(ex.context) if t in {"barn","mill","shed","well","hut","loft","yard","pond"})
    top = max(c.values()); cands = [p for p, n in c.items() if n == top]
    return 1.0 / len(cands) if ex.answer in cands else 0.0
print("clean: most-mentioned-place accuracy (expected) =", round(sum(mode_place(e.example()) for e in te) / len(te), 3), "vs presence floor", round(r.presence_chance if False else leak_report([e.example() for e in tr],[e.example() for e in te]).presence_chance, 3))

# false positives on small clean test sets: how often does a clean slice get flagged?
trx = [e.example() for e in tr]
for n in (20, 40, 80):
    flagged = 0; total = 0; who = Counter()
    for start in range(0, 3000, n):
        test = [e.example() for e in episodes(make_registry(), "test", n, start=start)]
        rr = leak_report(trx, test); total += 1
        if rr.leaking: flagged += 1; who.update(rr.leaking_detectors)
    print(f"clean test n={n}: flagged {flagged}/{total} slices ({flagged/total:.0%}) {dict(who)}")
