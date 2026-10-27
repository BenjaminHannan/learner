# ct20-v1.1 wave 1, tier L — `calibration-invalid/accounting` diagnosis

Agent 2 (models / training / persistence), 2026-09-20. **Diagnosis only — nothing was
modified, nothing was re-run on `calibration-v1.1`.** Reproduction used `fixture-v1.1`
into a scratch directory. No accuracy, E, prediction, or startup-label value from
`wave1/registered` was opened, printed or summarised; the only registered files read are
`tierL/ledgers/*.jsonl` and the `work`/cost fields of `verdict.json`.

---

## 1. The finding in one line

At the last rung (B=512) the fit executes **two** identical 96-target query panels but
**reserves one**. The unreserved second panel is
`query_panel_ops(arm)` — **17,172,576 ops for G, 23,224,032 for T** — and it is charged to
rung 512, pushing that rung over the 2.0e8 allowance and the fit over 1.0e9.

The extra pass is `final_query_panel`, run after the rung loop on parameters that have not
changed since `query_panel_rung512`. On the fixture its output is **bit-identical** to the
rung-512 panel in **12/12 fits**. It is a duplicate, not additional information.

---

## 2. Line-item breakdown, one G fit and one T fit

World `149e30247f4b35ec`, seed 20001, tier L (`tierL/ledgers/ledger-L-{G,T}-s20001.jsonl`).
"executed non-fitting" is `rung_executed_non_fitting_ops`; "reserved" is
`rung_reserved_ops`; "total" is `rung_counted_total_ops`.

### Arm G (allowance 2.0e8 per rung, 1.0e9 per fit)

| rung | planned steps | reserved | executed non-fitting | executed − reserved | total | ≤ allowance |
|---|---|---|---|---|---|---|
| 32  | 62 | 60,653,101 | 60,653,101 | **0** | 198,883,341 | yes |
| 64  | 81 | 18,245,892 | 18,245,892 | **0** | 198,837,012 | yes |
| 128 | 81 | 19,319,202 | 19,319,202 | **0** | 199,910,322 | yes |
| 256 | 80 | 21,465,822 | 21,465,822 | **0** | 199,827,422 | yes |
| 512 | 66 | 51,518,508 | 68,691,084 | **+17,172,576** | **215,839,404** | **NO** |

Per-fit total 1,013,297,501 against the 1.0e9 allowance.
`rung_unused_reservation_ops` at rung 512 is **−17,172,576** — a negative unused
reservation, which is logically impossible and is the tell.

### Arm T

| rung | planned steps | reserved | executed non-fitting | executed − reserved | total | ≤ allowance |
|---|---|---|---|---|---|---|
| 32  | 39 | 82,024,225 | 82,024,225 | **0** | 199,000,513 | yes |
| 64  | 58 | 24,675,564 | 24,675,564 | **0** | 198,640,300 | yes |
| 128 | 57 | 26,127,090 | 26,127,090 | **0** | 197,092,434 | yes |
| 256 | 57 | 29,030,142 | 29,030,142 | **0** | 199,995,486 | yes |
| 512 | 43 | 69,672,876 | 92,896,908 | **+23,224,032** | **221,870,764** | **NO** |

Per-fit total 1,016,599,497. `rung_unused_reservation_ops` = **−23,224,032**.

### The delta is exactly one query panel, everywhere

Over all **360 ledger rows (72 fits × 5 rungs)** in `wave1/registered/tierL/ledgers/`:

- rungs 32/64/128/256: `executed − reserved = 0.0` in **288/288** rows (the reservation is
  consumed exactly — calibration worlds are large enough to realise the largest-legal
  audit set, so the upper bound is tight);
- rung 512: `+17,172,576` in **36/36** G rows and `+23,224,032` in **36/36** T rows, which
  equals `query_panel_ops(G)` and `query_panel_ops(T)` to the operation;
- over-allowance rows: 72, all at rung 512, none anywhere else.

**Subtracting the one duplicate panel restores the frozen table exactly:**

| | executed | − one panel | frozen `cost` table |
|---|---|---|---|
| G rung 512 | 215,839,404 | **198,666,828** | **198,666,828** |
| T rung 512 | 221,870,764 | **198,646,732** | **198,646,732** |
| G per fit | 1,013,297,501 | **996,124,925** | **996,124,925** |
| T per fit | 1,016,599,497 | **993,375,465** | **993,375,465** |

Nothing else differs. The planning table and the executed charging agree on every other
line item, to the operation.

---

## 3. Where the extra charge is booked, and where the plan omitted it

**Charged here** — `scripts/fable_concepttoy20_models.py`:

- **line 2058** — `final_queries = runner.query_pass("final_query_panel")`. This runs after
  the rung loop closes (line 2053) and after `final_audit` (line 2057). Neither
  `audit_pass` nor `query_pass` updates parameters, so the weights are identical to those
  scored by `query_panel_rung512` at **line 1988**.
- **line 1740** — `query_pass` charges itself through
  `self._charge_evaluation(purpose, sequences=count * self.n_lanes, ...)`, honestly, at the
  real shape (96 targets).
- **lines 1835–1836** — `_purpose_rung_index`: `if purpose.startswith("final_"): return last`
  routes that charge to rung index 4.
- **lines 2062–2072** — the reconciliation loop adds it into
  `rung_executed_non_fitting_ops` for rung 512 and recomputes
  `rung_counted_total_ops` / `rung_within_allowance`.

**Omitted here** — same file, `rung_reservation` (lines 1133–1155):

- **line 1146** — `"rung_query_panel_forward": query_panel_ops(arm)` reserves **one** panel
  per rung, correctly.
- **lines 1152–1154** — the `if index == last:` branch adds only `final_audit_forward` and
  `final_audit_loss`. There is no `final_query_panel_forward` line. The last rung therefore
  budgets for one panel while the code runs two.
- **line 1173** — `steps = int((allowance - reserved) // per_update)` then spends the
  unreserved 17.17M / 23.22M on fitting steps, which is what carries the rung over.

**Where the duplicate is consumed** — **lines 2131–2137**: `query_predictions_final` is
written from `final_queries`, while `query_predictions_by_rung["512"]` is written from
`rung_queries[512]`. The fixture reproduction shows these two dictionaries compare equal in
all 12 fits, so the saved artefact contains the same 96 numbers twice.

---

## 4. Which side departs from the registered convention

**The executed run departs — not the planning table.**

Rulings 1 A1 and rulings 2 R5 register: charge real shapes; **every rung's query scoring is
charged**; reservations are upper bounds and are not consumption. That defines the panel
schedule as *one initial panel plus one panel per rung* = **six panels per fit**. The
planning table implements exactly that, and R5 ratified the resulting step tables
(L 370/254, H 2,163/1,588).

The executed run performs **seven**. The charging machinery is behaving correctly — it
charges a pass that genuinely ran, at its genuine shape, and it correctly reported the
result as over-allowance. The defect is upstream of the accounting: `run_fit` runs an
evaluation pass the registered schedule does not contain, and that pass produces no
information (it re-derives the rung-512 panel from unchanged parameters).

Two consequences follow, and they matter for the fix choice:

1. Deleting the pass is *not* a weakening of the accounting. It removes duplicated work,
   restores the frozen table bit for bit, and changes no step count.
2. Reserving the pass instead would change the frozen step table at the last rung of both
   tiers, which re-opens the freeze.

The cross-arm rule is not implicated: the worst executed per-rung gap is 2.7%, inside the
5% bound, and stays inside it under either fix.

---

## 5. Why the fixture run and the test suite did not catch it

Both the auditor's fixture run and my own suites exercise this path. Both pass. The reason
is that **the fixture worlds are small enough that the reservation slack absorbs the
duplicate panel.**

`audit_targets(512) = 144` and `selection_targets(512) = 48` are *largest-legal upper
bounds* computed from the budget (lines 1104–1114), not from the data. On
`calibration-v1.1` the worlds are large enough that the executed audit realises the full
144-target set, so `executed = reserved` exactly and the slack is **zero**. On
`fixture-v1.1` the same rung executes only about 24 sequences of selection + audit against
the 192 reserved — roughly **30.0M ops of slack for G**. The duplicate panel costs 17.17M,
so the fixture's rung 512 lands at 185,786,724 with
`rung_unused_reservation_ops = +12,880,104` — comfortably inside the allowance, and with a
*positive* unused reservation that looks entirely healthy.

Reproduced just now on `fixture-v1.1` (scratch dir), arm G, world 0, seed 20001:

| rung | reserved | executed non-fitting | total | ≤ allowance |
|---|---|---|---|---|
| 512 | 51,518,508 | 38,638,404 | 185,786,724 | yes |

and the fixture wave's accounting block reports `accounting_valid: true`,
`over_allowance: {}` at every rung, `per_fit_total_by_arm` G 956,412,071 / T 939,668,619,
both under 1.0e9.

So the specific blind spots are:

- **`tests/test_fable_concepttoy20_models.py:1636-1637`** does assert
  `all(row["rung_within_allowance"] ...)` — but only against a small synthetic/fixture
  world, where it is true. The same line also checks
  `entry["rung_unused_reservation_ops"] > 0` for `ledger[0]` only, i.e. rung 32 — the one
  rung that could never show the defect. Had it been asserted for **every** row, the
  negative unused reservation would have failed on any dataset where the audit reservation
  is tight.
- **`scripts/fable_concepttoy20_wave1.py:802-840`** (`executed_cross_arm_check`) forwards
  the per-rung totals to the calculator and reports `accounting_valid` and the gap. It does
  not itself assert `rung_unused_reservation_ops >= 0`, so the driver had no independent
  arithmetic check on the trainer's own books.
- **`tests/test_fable_concepttoy20_wave1.py`** asserts `accounting_valid` and
  `worst_relative_gap <= 0.05` on the fixture — both true there.
- The one component that *did* catch it is the independent calculator,
  `gate_calculator.py:275-277` (`over = {a: v for a, v in by_arm.items() if v > allowance}`)
  plus the per-fit check at line 287. It worked exactly as intended on real data, which is
  the argument for having built it independently.

**General lesson for the freeze:** the trainer's reservations are data-independent upper
bounds, so any test that runs on data smaller than the bound has slack that can hide an
unreserved charge. The invariant that is shape-blind — and that must be asserted on every
row of every ledger — is `rung_executed_non_fitting_ops <= rung_reserved_ops`, i.e.
`rung_unused_reservation_ops >= 0`.

---

## 6. Minimal candidate fixes (proposed, NOT applied)

### Fix 1 — delete the duplicate pass (recommended)

In `scripts/fable_concepttoy20_models.py`, drop line 2058 and source
`query_predictions_final` from the last rung's panel:

```
final_queries = rung_queries.get(BUDGETS[-1])        # replaces query_pass("final_query_panel")
```

Justification: proven bit-identical on the fixture in 12/12 fits, and identical by
construction — no parameter changes between `query_panel_rung512` (line 1988) and line
2058; `query_pass` is pure inference (line 1724-1747).

Consequences:

- **Step tables unchanged**: L G 62/81/81/80/66 (370), L T 39/58/57/57/43 (254),
  H G 421/440/439/438/425 (2,163), H T 306/325/324/323/310 (1,588). **The freeze does not
  move**, and R5's ratification still stands verbatim.
- Executed rung 512 returns to G 198,666,828 / T 198,646,732; per fit G 996,124,925 /
  T 993,375,465 — all inside 2.0e8 and 1.0e9.
- `rung_unused_reservation_ops` becomes 0.0 at every rung, as at rungs 32–256 today.
- **Planned per-rung cross-arm gaps, tier L**: 32 → 0.000589, 64 → 0.000989,
  128 → 0.014096, 256 → 0.000840, 512 → 0.000101. **Tier H**: 0.000557, 0.000243,
  0.000149, 0.000162, 0.000420. All inclusive-≤0.05.
- Cost to the wave: one 96-sequence forward pass per fit is *not* performed — a saving, and
  the only behavioural change is that the artefact stops storing the same panel twice.

### Fix 2 — reserve the second panel instead (only if the auditor rules the final panel must remain a distinct recorded pass)

Add to the `if index == last:` branch of `rung_reservation` (after line 1154):

```
parts["final_query_panel_forward"] = query_panel_ops(arm)
```

Consequences — **this re-opens the frozen step table**, because line 1173 recomputes
`steps` from the larger reservation:

| tier | arm | last-rung steps (now → then) | steps per fit (now → then) | per-fit counted ops |
|---|---|---|---|---|
| L | G | 66 → **58** | 370 → **362** | 995,461,341 |
| L | T | 43 → **35** | 254 → **246** | 992,604,361 |
| H | G | 425 → **417** | 2,163 → **2,155** | 4,992,990,701 |
| H | T | 310 → **302** | 1,588 → **1,580** | 4,993,793,289 |

Resulting planned per-rung cross-arm gaps — **L**: 0.000589, 0.000989, 0.014096, 0.000840,
**0.000645**; **H**: 0.000557, 0.000243, 0.000149, 0.000162, **0.000313**. All inside 5%,
and every rung inside its allowance. But the L tables become 362/246 and H 2,155/1,580,
which contradicts the numbers R5 ratified, so this needs a fresh ruling and a re-freeze.

### Fix 3 — guard, to be applied alongside whichever of 1/2 is chosen

Two additions that would have failed loudly on this run:

- in `scripts/fable_concepttoy20_wave1.py`, make the accounting block require
  `rung_unused_reservation_ops >= 0` on **every** ledger row and refuse the wave otherwise
  (a negative unused reservation means executed work was never budgeted);
- in `tests/test_fable_concepttoy20_models.py:1636`, apply the `> 0` unused-reservation
  assertion to every row rather than `ledger[0]`, and add one shape case whose executed
  audit set equals the largest-legal set, so a calibration-sized world is represented in
  the suite rather than only fixture-sized ones.

---

## 7. What is NOT wrong

For the record, ruled out against the coordinator's candidate list:

- **initial-checkpoint scoring or init ops booked to the last rung** — no. Rung 0's
  reservation and execution match to 0.0 in all 72 fits;
  `initialization`, `initial_audit_*` and `initial_query_panel_forward` are itemised at
  index 0 (lines 1150-1153) and `_purpose_rung_index` routes `initial_*` to 0 (line 1834).
- **fitting-audit loss passes** — no. `final_audit_forward` + `final_audit_loss` are
  reserved at the last rung (lines 1152-1154) and executed at exactly the reserved shape on
  calibration.
- **longer-than-planned sequence shapes in the last rung** — no. The residual after
  removing one panel is 0 ops, not a shape-dependent remainder; if shapes had drifted the
  delta would not be exactly `query_panel_ops(arm)` in 72/72 fits.
- **66/43 computed against a different per-step cost** — no. `update_ops` is G 2,229,520 /
  T 2,999,392, and 66 × 2,229,520 + 51,518,508 = 198,666,828 reproduces the frozen table
  exactly.
- **cross-arm gap** — fine, 2.7% executed worst case, inside the inclusive 5% bound, both
  before and after either fix.
