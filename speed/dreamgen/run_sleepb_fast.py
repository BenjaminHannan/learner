"""Run backbone/sleep/brain/sleepb.py unchanged but with fastgen installed (opt-in wrapper). Usage: python speed/dreamgen/run_sleepb_fast.py <sleepb args>
Env: FASTGEN_SEG (8), FASTGEN_PAD (1), FASTGEN_DEDUPE (1)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BR = ROOT / "backbone" / "sleep" / "brain"
for p in (BR, BR.parent, ROOT / "backbone", Path(__file__).resolve().parent):
    sys.path.insert(0, str(p))
import fastgen  # noqa: E402

import sleepb  # noqa: E402

if __name__ == "__main__":
    sys.argv = [str(BR / "sleepb.py")] + sys.argv[1:]
    fastgen.install(sleepb, compact=True, seg=int(os.environ.get("FASTGEN_SEG", 8)), pad_multiple=int(os.environ.get("FASTGEN_PAD", 1)),
                    dedupe=os.environ.get("FASTGEN_DEDUPE", "1") == "1")  # patches Lang.generate and sleepb.generate_p
    sleepb.main()
