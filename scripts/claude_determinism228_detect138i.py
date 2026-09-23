# Exp 228 passive detector (diagnostic only, not an agent to ship).
# 138i unchanged + a passive detector: logs every _src_of() hit where the list
# is NOT the live cached list of the returned notebook (a stale id collision).
import os, sys, json, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fable_loop138i_agent as L138I
import fable_fix170_compose as F170
LOG = os.environ.get("DETECT228_LOG", "/dev/null")
CUR = ["?"]
_orig = F170._src_of
def _det(triples):
    inner = _orig(triples)
    if inner is not None:
        e = F170._TRIPLES.get(id(inner))
        if not (e is not None and e[2] is inner and e[1] is triples):
            fr = [f"{os.path.basename(f.filename)}:{f.lineno}:{f.name}" for f in traceback.extract_stack()[-4:-1]]
            with open(LOG, "a") as fh:
                fh.write(json.dumps({"item": CUR[0], "stack": fr, "n_triples": len(triples)}) + "\n")
    return inner
F170._src_of = _det
DEFAULT_CONFIG138I = L138I.DEFAULT_CONFIG138I
build_agent138i = L138I.build_agent138i
class Loop138iDaemon(L138I.Loop138iDaemon):
    def __init__(self, root, *a, **k):
        CUR[0] = os.path.basename(str(root))
        super().__init__(root, *a, **k)
