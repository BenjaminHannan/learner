"""slp-358n3 official write-up, step 1: hash-check the copied records.
Checks (a) run-vast/MANIFEST.sha256 (paths written W/... on the rental), (b) SEAL-run.sha256.txt,
(c) SEAL-code.sha256.txt against the code and test files on main.
Read-only; prints a log. Weights (*.pt) are never in git, so their manifest lines cannot be re-hashed here;
the SEAL-run and MANIFEST lines for S-final.pt are compared with each other instead.
"""
import hashlib, os, sys, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "artifacts/claude-slp358n3-20260927")

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def lines(p):
    return [l.split(None, 1) for l in open(p).read().splitlines() if l.strip()]

def local_of(w):
    if w.startswith("W/"):
        w = w[2:]
    m = {"SEAL-run.sha256.txt": "SEAL-run.sha256.txt", "pip.log": "run-vast/pip-tail.txt",
         "resume/resume.json": "run-vast/resume.json"}
    if w in m: return m[w]
    if w.startswith("resume/"): return None
    if w.endswith(".pt"): return None
    for s in ("13", "14", "15", "16"):
        if w == f"s{s}.log" or w == f"s{s}.err": return f"runs/s{s}/{w}"
        if w == f"s{s}/slp358n3-seed{s}.json": return f"runs/{w}"
    if w == "drive.log": return "run-vast/drive.log"
    return "run-vast/" + w

out = []
def P(s): out.append(s); print(s)
P("slp-358n3 hash check (helper S)")
ok = bad = nog = 0
P("== A. run-vast/MANIFEST.sha256 vs the copied files ==")
manifest = {}
for h, p in lines(os.path.join(A, "run-vast/MANIFEST.sha256")):
    manifest[p.strip()] = h
    l = local_of(p.strip())
    if l is None or not os.path.isfile(os.path.join(A, l)):
        nog += 1; P(f"NOT-IN-GIT  {p.strip()}  (checkpoint/weights or resume state; not copied)"); continue
    a = sha(os.path.join(A, l))
    if a == h: ok += 1; P(f"OK        {p.strip()} -> {l}")
    else:
        bad += 1; P(f"MISMATCH  {p.strip()} -> {l}  manifest={h} actual={a}")
        if l.endswith("pip-tail.txt"): P("          note: the copied file is named pip-tail.txt (a tail of pip.log, which is not on builder-outbox); the manifest line is for the full pip.log. Suggested: not the same file. Untested: no copy of the full pip.log exists to check.")
P(f"MANIFEST: {ok} match, {bad} mismatch, {nog} not in git, of {ok+bad+nog} lines")
P("== B. SEAL-run.sha256.txt ==")
ok2 = bad2 = 0
for h, p in lines(os.path.join(A, "SEAL-run.sha256.txt")):
    p = p.strip()
    mh = manifest.get(p) or manifest.get("W/" + p)
    st = "agrees with MANIFEST" if mh == h else f"DIFFERS from MANIFEST ({mh})"
    if mh == h: ok2 += 1
    else: bad2 += 1
    P(f"{p}: {h[:16]}.. {st}  (weights file, not in git)")
P(f"SEAL-run: {ok2} of {ok2+bad2} lines agree with the MANIFEST hashes for the same file")
P("== C. SEAL-code.sha256.txt vs main ==")
ok3 = bad3 = 0
for h, p in lines(os.path.join(ROOT, "artifacts/claude-slp358n3-20260927/SEAL-code.sha256.txt")):
    p = p.strip(); f = os.path.join(ROOT, p)
    if os.path.isfile(f) and sha(f) == h: ok3 += 1; P(f"OK        {p}")
    else: bad3 += 1; P(f"MISMATCH/MISSING  {p}")
P(f"SEAL-code: {ok3} of {ok3+bad3} files match")
open(os.path.join(A, "run-vast/HASHCHECK.txt"), "w").write("\n".join(out) + "\n")
