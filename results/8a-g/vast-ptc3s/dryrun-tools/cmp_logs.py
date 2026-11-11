"""Compare the marker lines of two box logs (the frozen script's and the new script's, both with PROFILE unset): usage cmp_logs.py OLD NEW
Kept: lines starting with '=== ', CMD, CHILD-ENV, QUEUE-ENV, RESULT-SUMMARY, part ck, CKFULL|, CKDONE|, RBEGIN| (name only), REND|, 'queues ', 'versions', 'curriculum', 'big build'.
Normalised: timestamps, 'up_min=N', durations in seconds, absolute scratch paths of this session, the sha256 / size of tar blocks (they hold file times)."""
import re
import sys

KEEP = ('=== ', 'CMD ', 'CHILD-ENV', 'QUEUE-ENV', 'RESULT-SUMMARY', 'part ck', 'CKFULL|', 'CKDONE|', 'RBEGIN|', 'REND|', 'versions', 'curriculum', 'big build', 'src-ptc')


def norm(ln):
    ln = re.sub(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', 'TS', ln)
    ln = re.sub(r'^RBEGIN\|([^|]+)\|[0-9a-f]{64}\|\d+', r'RBEGIN|\1|SHA|SIZE', ln)
    ln = re.sub(r'^(CKFULL\|[^|]+)\|[0-9a-f]{64}', r'\1|SHA', ln)
    ln = re.sub(r'(train_s|wall_s)": \d+', r'\1": N', ln)
    ln = re.sub(r'steps_per_s": [0-9.]+', 'steps_per_s": X', ln)
    ln = re.sub(r'/tmp/claude-0/[^ ]*/venv/bin/python', 'python', ln)
    return ln.rstrip()


def keep(path):
    out = []
    for ln in open(path, errors='replace'):
        if ln.startswith(KEEP):
            out.append(norm(ln))
    return out


a, b = keep(sys.argv[1]), keep(sys.argv[2])
print('marker lines: old %d, new %d' % (len(a), len(b)))
import difflib
d = [x for x in difflib.unified_diff(a, b, 'old', 'new', lineterm='', n=0)]
print('diff lines: %d' % len(d))
for x in d[:80]:
    print(x[:300])
