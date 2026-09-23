# Concept toy (ct20-v1.1) — Fable's predictions for the baseline calibration pilot

Written 2026-09-20 before any learner has been fitted or scored on the calibration worlds, and before the v1.1 builds were frozen. Gate definitions: `design/v3/20-concept-toy-preregistration-draft.md` §"wave 1" as amended by `design/v3/20-concept-toy-rulings-1.md` (sha256 40f65045…): tier L = 2.0e8 ops/rung, tier H = 1.0e9 ops/rung, H runs exactly once if a complete valid L is too-hard, control-incompetent or inconclusive. Basis: the builder's provisional step table gives only ~378 (G) / ~262 (T) optimizer updates per fit at tier L with minibatches of four at lr 1e-3.

| # | Statement | Probability |
|---|---|---|
| P76 | Tier L lands in the advance window | 0.07 |
| P77 | Tier L fails the control-competence prerequisite (E_512 ≤ 0.10 on ≥ 5/6 control cases) for at least one arm | 0.75 |
| P78 | Tier H is triggered | 0.88 |
| P79 | The pilot advances (L or H in the advance window) | 0.22 |
| P80 | "Too easy" is declared at either tier | 0.03 |
| P81 | If H runs, G has a lower median C E_512 than T at tier H | 0.65 |
| P82 | If H runs and does not advance, the registered diagnosis is fitting/optimisation (fitting E still poor), not failed generalisation | 0.70 |

Plain reading of my own forecast: I expect the small budget to under-train both baselines, the five-times budget to help but probably not enough, and therefore the most likely pilot outcome to be "not learned by these baselines under either registered budget" — which by Astra's ruling is NOT evidence that the toy is intrinsically too hard.
