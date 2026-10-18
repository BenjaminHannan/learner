# Width pilot v2: open asks for the coordinator (2026-10-18)

The pilot is blocked only on the rulings below. Each item says what is asked, where the evidence is, and what it unblocks. **Nothing is booked; no spend is approved.**

## Rulings asked, in the order they unblock

| # | Ask | Evidence | Unblocks |
|---|---|---|---|
| 1 | **Freeze Item 0** ((a)–(k) all recorded against the playbook's pass condition) | `reviews/width-pilot-item0-runcard-2026-10-17.md` | Item 1 booking |
| 2 | **Axis gate 2(b).** Base depth is 2 distinct blocks (Q48), so 2(a) fails. Rule whether the width axis proceeds under 2(b), or redirect to depth | Amendment §C (totals for width-first and width-then-depth printed) | Item 1 booking; Tranche A |
| 3 | **Code review** of four drafts (all tests pass: custom_io C8 bit-identical off/on; `pilot_bars` 19; `learn_probe` C8 7 + diary-data 3 + r1 10) | PR [BenjaminHannan/learner#78](https://github.com/BenjaminHannan/learner/pull/78): `custom_io/train.py` `--log-update-rms`; `custom_io/pilot_bars.py`; `domain/far/learn_probe.py` C8 (5ce1889) and `--diary-data` (6d8c8d3) | Item 1 booking |
| 4 | **Fund the extended Item 1 bid**: about $1.4–2.1, hard stop $3, one Vast 4090; buys measured parent and join seconds per update at d256 and d384; displaces 3–4% of one week's Vast cap | Amendment §D (prerequisites updated 10-18) | Re-issued §7 from measured numbers, then Tranche A |
| 5 | **Define the playbook's "40–42% / 65–67%" bands.** Not reproduced. Nearest measured values: pooled P over HO + HPO = 42.5% (L13); single pieces alone 62–65% | Run card (d), per-piece section | Item 0 check only; not a booking gate unless the coordinator says so |
| 6 | **TEST-11 wording (note, no action required for the pilot).** As worded it cannot be satisfied on HO, because depth is confounded with piece type. (j) is answered NO under the playbook's branch: factor (2) UNMEASURED, Item 8 Phase A only, C4 OUT | Run card (j) | — |

## Goes to Ben, not the coordinator

- The A / B / C bid choice (`reviews/width-pilot-bid-2026-10-17.md`, `reviews/width-pilot-bid-C-2026-10-17.md`). For Bid C, also which fixed B2 to use.

## After the rulings (this session's next steps, in order)

1. Item 1 runs inside its hard stop; measured numbers are filed.
2. §7 is re-issued from the measured numbers. Bid A is re-priced (the Q53 condition), and Tranche A is bid against the weekly cap.
3. Pre-registration checklist. Bars are written in house form before any verdict run, sized from the contrast's own sigma_d at the sigma gate.
4. Tranche A, then the gates as the spec stages them. Every KILL is horizon-locked behind the 12,000-update extension.
