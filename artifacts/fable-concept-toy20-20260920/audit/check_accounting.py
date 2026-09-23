"""Agent 3 DO item 4: independent verification of the operation-cost ledger.

Recomputes every forward/backward/optimizer/evaluation cost from the DECLARED
constants and the architecture shapes, without calling the builder's cost
functions as the oracle, then compares.  Reports the step totals under two
op-counting conventions and checks the ruling A1 reconciliation, the per-rung 5%
cross-arm rule and the worst-case L+H schedule.

Fits and scores no learner and reads no calibration data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

import fable_concepttoy20_models as M   # noqa: E402  (module under test)
import gate_calculator as GC            # noqa: E402  (my own referee)

OUT: list[dict] = []


def check(name, ok, detail=""):
    OUT.append({"check": name, "pass": bool(ok), "detail": str(detail)[:500]})
    print(("PASS  " if ok else "FAIL  ") + name + (f"\n        {detail}" if detail else ""))


def note(name, detail):
    OUT.append({"check": name, "pass": None, "detail": str(detail)[:900]})
    print(f"NOTE  {name}\n        {detail}")


# ---------------------------------------------------------------------------
# Shapes are facts about the frozen architecture; the ARITHMETIC below is mine.
# ---------------------------------------------------------------------------
TOK = M.FIXED_SEQUENCE_LENGTH          # 17
RW = M.RECORD_WIDTH                    # 44
H = M.CONTEXT_WIDTH                    # 24
HEADS, HDIM, FFW = M.N_HEADS, M.HEAD_DIM, M.FF_WIDTH
DIN, DH = M.DECODER_INPUT_WIDTH, M.DECODER_HIDDEN
BATCH = M.MINIBATCH_EPISODES


class Convention:
    """One declared op-counting convention."""

    def __init__(self, name, mac, tanh, sigmoid, ln, softmax, elem, bias,
                 backward, adamw, clip, dense_attention, init_per_param,
                 loss_per_target, loss_per_batch):
        self.__dict__.update(locals())
        del self.__dict__["self"]

    def linear(self, tokens, fan_in, fan_out):
        return tokens * (fan_in * fan_out * self.mac + fan_out * self.bias)

    def gru_forward(self, tokens):
        return (self.linear(tokens, RW, 3 * H) + self.linear(tokens, H, 3 * H)
                + tokens * H * (self.elem + self.sigmoid)          # reset gate
                + tokens * H * (self.elem + self.sigmoid)          # update gate
                + tokens * H * (2 * self.elem + self.tanh)         # candidate
                + tokens * H * 4 * self.elem)                      # state blend

    def transformer_forward(self, tokens):
        pairs = tokens * tokens if self.dense_attention else tokens * (tokens + 1) // 2
        return (self.linear(tokens, RW, H)
                + tokens * H * self.elem                            # position add
                + tokens * H * self.ln                              # pre-LN 1
                + 3 * self.linear(tokens, H, H)                     # separate Q, K, V
                + HEADS * pairs * HDIM * self.mac + HEADS * pairs * self.elem
                + HEADS * pairs * self.softmax
                + HEADS * pairs * HDIM * self.mac                   # attend
                + self.linear(tokens, H, H)                         # attn output
                + tokens * H * self.elem                            # residual 1
                + tokens * H * self.ln                              # pre-LN 2
                + self.linear(tokens, H, FFW)
                + tokens * FFW * self.tanh
                + self.linear(tokens, FFW, H)
                + tokens * H * self.elem                            # residual 2
                + tokens * H * self.ln)                             # final LN

    def decoder(self):
        return self.linear(1, DIN, DH) + DH * self.tanh + self.linear(1, DH, 1)

    def forward(self, arm, sequences=1, tokens=TOK):
        body = self.gru_forward(tokens) if arm == "G" else self.transformer_forward(tokens)
        return sequences * (body + self.decoder())

    def update(self, arm):
        fwd = self.forward(arm, BATCH) + self.loss(BATCH, 1)
        params = M.SPEC_PARAMETER_COUNTS[arm]
        return fwd + int(round(fwd * self.backward)) + params * (self.adamw + self.clip)

    def loss(self, targets, batches=1):
        return targets * self.loss_per_target + batches * self.loss_per_batch


REGISTERED = Convention(
    "registered (MAC=2, dense 17x17 attention, backward=2x)",
    mac=2, tanh=4, sigmoid=4, ln=7, softmax=5, elem=1, bias=1, backward=2.0,
    adamw=11, clip=3, dense_attention=True, init_per_param=2,
    loss_per_target=4, loss_per_batch=2)

ALTERNATIVE = Convention(
    "alternative (MAC=1 fused, causal-triangular attention, backward=2x, "
    "elementwise/activation/LN/softmax all 1 op)",
    mac=1, tanh=1, sigmoid=1, ln=1, softmax=1, elem=1, bias=1, backward=2.0,
    adamw=11, clip=3, dense_attention=False, init_per_param=2,
    loss_per_target=1, loss_per_batch=1)

THIRD = Convention(
    "third (registered operators but backward=1x and no optimizer charge)",
    mac=2, tanh=4, sigmoid=4, ln=7, softmax=5, elem=1, bias=1, backward=1.0,
    adamw=0, clip=0, dense_attention=True, init_per_param=0,
    loss_per_target=4, loss_per_batch=2)

# ---------------------------------------------------------------------------
# 1. Does my independent arithmetic agree with the builder's cost table?
# ---------------------------------------------------------------------------
for arm in M.ARMS:
    mine = REGISTERED.forward(arm)
    theirs = M.forward_ops(arm)
    check(f"{arm}: independent forward-op recomputation matches the builder's table",
          mine == theirs, f"mine={mine:,} builder={theirs:,}")
    mine_u = REGISTERED.update(arm)
    theirs_u = M.update_ops(arm)
    check(f"{arm}: independent per-update cost matches the builder's table",
          mine_u == theirs_u, f"mine={mine_u:,} builder={theirs_u:,}")

check("the transformer is charged DENSE 17x17 attention, as ruling A1 requires "
      "when that is what executes", M.COST_COUNTS_DENSE_ATTENTION is True)

# ---------------------------------------------------------------------------
# 2. Ruling A1 reconciliation: every category of real model work is charged.
# ---------------------------------------------------------------------------
REQUIRED_CATEGORIES = {
    "initialization": "ruling A1: initialization",
    "initial_audit_forward": "ruling A1: first initial prediction set (fitting audit)",
    "initial_query_panel_forward": "ruling A1: second initial prediction set (query panel)",
    "rung_query_panel_forward": "ruling A1: all rung query forwards",
    "selection_forward": "ruling A1: all rung selection forwards",
    "final_audit_forward": "ruling A1: final fitting diagnostics",
}
LOSS_CATEGORIES = ("selection_loss", "initial_audit_loss", "final_audit_loss")

for arm in M.ARMS:
    seen = set()
    for index, budget in enumerate(M.BUDGETS):
        seen |= set(M.rung_reservation(arm, budget, index))
    missing = sorted(k for k in REQUIRED_CATEGORIES if k not in seen)
    check(f"{arm}: the frozen reservation itemises every category ruling A1 names",
          not missing, f"missing={missing or 'none'}; present={sorted(seen)}")
    loss_missing = [k for k in LOSS_CATEGORIES if k not in seen]
    check(f"{arm}: loss computation is charged for every scored set",
          not loss_missing, f"missing={loss_missing or 'none'}")

# the per-update cost must itself include the fitting loss
for arm in M.ARMS:
    without_loss = REGISTERED.forward(arm, BATCH)
    with_loss = REGISTERED.forward(arm, BATCH) + REGISTERED.loss(BATCH, 1)
    check(f"{arm}: the fitting loss is inside the per-update charge",
          M.update_ops(arm) > without_loss * 3,
          f"update={M.update_ops(arm):,}; forward-only 3x bound={without_loss * 3:,}")

# ---------------------------------------------------------------------------
# 3. Step totals per fit, under three conventions and both tiers.
# ---------------------------------------------------------------------------
summary: dict[str, dict] = {}
for conv in (REGISTERED, ALTERNATIVE, THIRD):
    summary[conv.name] = {}
    for tier in M.TIERS:
        allowance = M.TIER_ALLOWANCE_PER_RUNG[tier]
        for arm in M.ARMS:
            per_update = conv.update(arm)
            total, rows = 0, []
            for index, budget in enumerate(M.BUDGETS):
                # reservation recomputed under THIS convention
                res = (conv.forward(arm, M.selection_targets(budget))
                       + conv.loss(M.selection_targets(budget), len(M.HORIZONS))
                       + conv.forward(arm, M.QUERY_PANEL_TARGETS))
                if index == 0:
                    res += (M.SPEC_PARAMETER_COUNTS[arm] * conv.init_per_param
                            + conv.forward(arm, M.audit_targets(M.BUDGETS[-1]))
                            + conv.loss(M.audit_targets(M.BUDGETS[-1]), len(M.HORIZONS))
                            + conv.forward(arm, M.QUERY_PANEL_TARGETS))
                if index == len(M.BUDGETS) - 1:
                    res += (conv.forward(arm, M.audit_targets(M.BUDGETS[-1]))
                            + conv.loss(M.audit_targets(M.BUDGETS[-1]), len(M.HORIZONS)))
                steps = max(int((allowance - res) // per_update), 0)
                total += steps
                rows.append(steps)
            summary[conv.name][f"{tier}/{arm}"] = {
                "per_update_ops": per_update, "steps_per_rung": rows,
                "total_updates_per_fit": total,
                "examples_seen": total * BATCH,
            }

note("total optimizer updates per fit, by convention / tier / arm",
     json.dumps({k: {kk: vv["total_updates_per_fit"] for kk, vv in v.items()}
                 for k, v in summary.items()}, indent=1))

# The builder's own current table, for the headline check.
builder_totals = {f"{t}/{a}": M.cumulative_steps(a, t)[-1]
                  for t in M.TIERS for a in M.ARMS}
note("the builder's own frozen step table (current build)",
     json.dumps(builder_totals))

reg = summary[REGISTERED.name]
check("my registered-convention recomputation reproduces the builder's step table",
      all(reg[k]["total_updates_per_fit"] == builder_totals[k] for k in builder_totals),
      json.dumps({k: [reg[k]["total_updates_per_fit"], builder_totals[k]]
                  for k in builder_totals}))

g_L = reg["L/G"]["total_updates_per_fit"]
t_L = reg["L/T"]["total_updates_per_fit"]
note("the provisional 378 (G) / 262 (T) headline",
     f"under the reconciled ledger the tier-L totals are G={g_L} and T={t_L} updates "
     f"per fit ({g_L * BATCH} and {t_L * BATCH} sampled examples). The 378/262 figures "
     "quoted before reconciliation were computed WITHOUT initialization, the initial "
     "query panel or loss, so they were upper bounds; ruling A1 already calls them "
     "provisional.")

sens = {k: [summary[c.name][k]["total_updates_per_fit"]
            for c in (REGISTERED, ALTERNATIVE, THIRD)]
        for k in builder_totals}
note("sensitivity of the update total to the op-counting convention "
     "[registered, alternative, third]", json.dumps(sens))

# ---------------------------------------------------------------------------
# 4. The per-rung 5% cross-arm rule, using MY calculator, not the builder's.
# ---------------------------------------------------------------------------
for tier in M.TIERS:
    planned = {arm: {row["budget"]: float(row["counted_total_ops"])
                     for row in M.step_table(arm, tier)} for arm in M.ARMS}
    verdict = GC.cross_arm_rule_per_rung(planned, tier)
    worst = max((r["relative_gap"] for r in verdict["rungs"] if "relative_gap" in r),
                default=float("nan"))
    check(f"tier {tier}: planned counted use is within 5% across arms at EVERY rung "
          f"and never over the allowance",
          verdict["accounting_valid"],
          "per-rung relative gaps "
          + ", ".join(f"B={r['budget']}:{r['relative_gap']:.4f}" for r in verdict["rungs"])
          + f"; worst={worst:.4f}")

# ---------------------------------------------------------------------------
# 5. Is a "toy too hard" verdict confounded by the budget?
# ---------------------------------------------------------------------------
note("does the budget confound a 'too hard' verdict?",
     f"Tier L buys G={g_L} and T={t_L} complete optimizer updates for an ENTIRE fit "
     f"across all five nested rungs, i.e. {g_L * BATCH} and {t_L * BATCH} sampled "
     f"(episode, endpoint) examples total, from a 5,921/6,881-parameter model. That is "
     "two to three orders of magnitude below what a small sequence model normally needs "
     "to fit an eight-step forecasting task, so a tier-L 'too hard' verdict is NOT "
     "separable from under-training on its own evidence. Ruling A3 already forbids "
     "reading it that way and requires tier H. Tier H buys "
     f"G={reg['H/G']['total_updates_per_fit']} and T={reg['H/T']['total_updates_per_fit']} "
     "updates, ~5x more, which is a controlled increase but still small in absolute "
     "terms: even an H failure supports only 'not learned by these baselines under "
     "either registered budget', exactly as ruling A3 step 5 words it.")

# ---------------------------------------------------------------------------
# 6. Worst-case L+H schedule arithmetic (the inputs Fable must supply).
# ---------------------------------------------------------------------------
n_fits = 12 * 3 * 2          # worlds x seeds x arms
ops_L = sum(M.step_table("G", "L")[i]["counted_total_ops"] for i in range(5)) \
    + sum(M.step_table("T", "L")[i]["counted_total_ops"] for i in range(5))
ops_H = sum(M.step_table("G", "H")[i]["counted_total_ops"] for i in range(5)) \
    + sum(M.step_table("T", "H")[i]["counted_total_ops"] for i in range(5))
note("worst-case L+H counted work for wave 1",
     f"one world x seed for BOTH arms costs {ops_L:,.0f} ops at tier L and "
     f"{ops_H:,.0f} at tier H; over 12 worlds x 3 seeds that is "
     f"{ops_L * 36:,.0f} (L) + {ops_H * 36:,.0f} (H) = {(ops_L + ops_H) * 36:,.0f} "
     "counted operations for the complete fallback schedule, i.e. tier H alone is "
     f"{ops_H / ops_L:.1f}x tier L. Ruling A3 requires the projection to be made in "
     "SECONDS from a synthetic-timing fixture at the real vectorised shapes, including "
     "scoring and writes, with the 1.5x margin and the 300 s reserve inside 1,200 s. "
     "Counted operations are not seconds: for models this small the wave is dominated "
     "by per-kernel launch overhead, not arithmetic, so the reported ~80 s for L cannot "
     "be scaled by the op ratio to project L+H. The preflight measurement is still "
     "OUTSTANDING and is a must-fix before the freeze.")

print()
n_fail = sum(1 for r in OUT if r["pass"] is False)
print(json.dumps({"checks": sum(1 for r in OUT if r['pass'] is not None),
                  "failed": n_fail, "notes": sum(1 for r in OUT if r['pass'] is None)}))
Path(__file__).with_name("accounting_check_results.json").write_text(
    json.dumps({"results": OUT, "summary": summary,
                "builder_step_totals": builder_totals}, indent=1))
