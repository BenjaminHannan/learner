from collections import Counter
from learnlab.leaks import leak_report
from learnlab.toy import make_registry, episodes
for ntrain, ntest in ((400, 300), (400, 150)):
    flagged = 0; total = 0; worst = 0.0
    for k in range(12):
        tr = [e.example() for e in episodes(make_registry(), "train", ntrain, start=10000 * k)]
        te = [e.example() for e in episodes(make_registry(), "test", ntest, start=10000 * k)]
        r = leak_report(tr, te); total += 1; flagged += r.leaking
        worst = max(worst, max(r.detectors.values()) - r.floor)
    print(f"clean train={ntrain} test={ntest}: flagged {flagged}/{total} independent seeds; worst detector-floor = {worst:.3f} (margin 0.10)")
