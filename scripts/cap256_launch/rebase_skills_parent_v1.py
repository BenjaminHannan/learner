"""Make a skills-pretrained checkpoint usable as the English pilot's seed-0 parent.

Only the 'update' counter (5120 + skills updates) is reset to the pilot's PARENT_UPDATE (5120) so the unchanged
pilot trainer accepts it; weights, Adam state, participation and RNG are untouched. Writes a new file; the
source is never modified.
usage: rebase_skills_parent_v1.py SRC.pt DST.pt  -> prints the new sha256
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import english_pilot_common_v1 as common  # noqa: E402
import english_pilot_runtime_v1 as runtime  # noqa: E402


def main():
    import torch
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    if dst.exists():
        raise SystemExit('destination exists: ' + str(dst))
    saved = torch.load(src, map_location='cpu', weights_only=True)
    was = saved['update']
    saved['update'] = runtime.PARENT_UPDATE
    dst.parent.mkdir(parents=True, exist_ok=True)
    torch.save(saved, dst)
    print('rebased update %s -> %s; sha256 %s' % (was, runtime.PARENT_UPDATE, common.digest(dst)))


if __name__ == '__main__':
    main()
