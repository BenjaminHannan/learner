# Width pilot v2: open asks for the coordinator (2026-10-18)

The pilot is blocked only on the rulings below. Each item says what is asked, where the evidence is, and what it unblocks. **Nothing is booked; no spend is approved.**

## Rulings asked, in the order they unblock

| # | Ask | Evidence | Unblocks |
|---|---|---|---|
| 1 | ~~Freeze Item 0~~ **GRANTED (Q73)** | `reviews/width-pilot-item0-runcard-2026-10-17.md` | — |
| 2 | **Axis gate 2(b): Ben's (Q74)**, bundled with the bid choice. Base depth is 2 distinct blocks (Q48), so 2(a) fails. Width-first or depth-first | Amendment §C (totals for width-first and width-then-depth printed) | Item 1 booking; Tranche A |
| 3 | **Code review** (Q75: slots granted under Q4 / Q52 / Q71; drafts stay DRAFT until each passes) of four drafts, now including the `/code-review` fixes (99cba1a47; 49 tests pass together; findings and verdicts reported in session 10-18) | PR [BenjaminHannan/learner#78](https://github.com/BenjaminHannan/learner/pull/78): `custom_io/train.py` `--log-update-rms`; `custom_io/pilot_bars.py`; `domain/far/learn_probe.py` C8 (5ce1889) and `--diary-data` (6d8c8d3) | Item 1 booking |
| 4 | **Extended Item 1 bid: YES in principle (Q60 stands; Q76)**, prerequisite refresh accepted, on-demand Vast 4090 only. Books when 2(b) and the code reviews land: about $1.4–2.1, hard stop $3, one Vast 4090; buys measured parent and join seconds per update at d256 and d384; displaces 3–4% of one week's Vast cap | Amendment §D (prerequisites updated 10-18) | Re-issued §7 from measured numbers, then Tranche A |
| 5 | ~~Define the bands~~ **ACCEPTED (Q77)**: in-context pooled fleet numbers, an Item 0 check only | Run card (d), per-piece section | — |
| 6 | **TEST-11 wording (note, no action required for the pilot).** As worded it cannot be satisfied on HO, because depth is confounded with piece type. (j) is answered NO under the playbook's branch: factor (2) UNMEASURED, Item 8 Phase A only, C4 OUT | Run card (j) | — |

## Goes to Ben, not the coordinator

- The A / B / C bid choice (`reviews/width-pilot-bid-2026-10-17.md`, `reviews/width-pilot-bid-C-2026-10-17.md`). For Bid C, also which fixed B2 to use.

## After the rulings (this session's next steps, in order)

1. Item 1 runs inside its hard stop; measured numbers are filed.
2. §7 is re-issued from the measured numbers. Bid A is re-priced (the Q53 condition), and Tranche A is bid against the weekly cap.
3. Pre-registration checklist. Bars are written in house form before any verdict run, sized from the contrast's own sigma_d at the sigma gate.
4. Tranche A, then the gates as the spec stages them. Every KILL is horizon-locked behind the 12,000-update extension.
