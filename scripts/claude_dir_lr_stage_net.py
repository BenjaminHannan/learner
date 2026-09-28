"""Lead 1 plug-in: staged unfreeze at adaptation (head first, then everything).

Same net, same data, same sealed harness. Only the adapt-step Learner changes: for the first
FROZEN_UPDATES = 25% of the 2,048 maze updates only the output head (`head.*`) and stop head
(`halt.*`, loop only) can move; then every weight trains, with no other change (same AdamW,
same 50-step warm-up counted from update 0, same clip, same batches). The rule is the same for
fresh, plain and practised nets. Nothing here touches the source nets or practice.
  --plugin claude_dir_lr_stage_net     (PROTOCOL.md plug-in contract)
Note: the loop's stop head gets no maze loss, so in the frozen stage only `head.*` moves.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_fewex_net import *  # noqa: F401,F403  Net, Practice, tensors, ce_and_exact, train_loss, ...
import claude_fewex_bench as B

FROZEN_UPDATES = 512  # 25% of B.UPDATES * 512 batches = 2,048
HEAD_PREFIXES = ("head.", "halt.")


def set_frozen(net, frozen):
    for name, p in net.named_parameters():
        p.requires_grad = (not frozen) or name.startswith(HEAD_PREFIXES)


class Learner(B.Learner):
    def maze_batch(self, items):
        assert FROZEN_UPDATES % B.UPDATES == 0
        set_frozen(self.net, self.steps < FROZEN_UPDATES)
        super().maze_batch(items)

    def sleep(self, mazes, seed, old):
        set_frozen(self.net, False)  # sleep is unchanged: every weight trains
        return super().sleep(mazes, seed, old)


def _selftest():
    import copy, random, torch
    import claude_fewex_data as D
    global FROZEN_UPDATES
    FROZEN_UPDATES = 8  # two batches, so the test is quick; the real value is 512
    _, banned = D.panels()
    rng, seen = random.Random(5), set()
    items = [D.unique_maze(rng, 9, banned, seen) for _ in range(B.MAZE_BATCH)]
    for arm in ("loop", "plain"):
        torch.manual_seed(1)
        net = Net(arm)
        before = copy.deepcopy(net.state_dict())
        L = Learner(net, 1e-3)
        L.maze_batch(items); L.maze_batch(items)          # updates 0..7: frozen
        after = net.state_dict()
        moved = {k for k in before if not torch.equal(before[k], after[k])}
        assert moved and all(k.startswith(HEAD_PREFIXES) for k in moved), (arm, sorted(moved))
        mid = copy.deepcopy(net.state_dict())
        L.maze_batch(items)                                # update 8..11: everything trains
        moved2 = {k for k in mid if not torch.equal(mid[k], net.state_dict()[k])}
        assert any(not k.startswith(HEAD_PREFIXES) for k in moved2), arm
        assert all(p.requires_grad for p in net.parameters()), arm
        assert L.steps == 12
        print(f"stage plugin selftest ok {arm}: frozen stage moved {sorted(moved)}; after unfreeze {len(moved2)} tensors moved")


if __name__ == "__main__":
    _selftest()
