# Width pilot: bid to the coordinator and spec request (2026-10-17)

From the size-versus-stall session (`beautiful-model`). This goes to the coordinator under Ben's funding rule of Oct 17. Nothing is booked, rented or queued. All code named here is a draft until the coordinator reviews it.

## 1. Blocker: the v2 spec is not reachable from this session

The goal says to follow the v2 spec's staging and gates exactly. The spec is `hidden_files/deep3-work/deep3-stage3-pilot-v2.md`; the synthesis is `hidden_files/deep3-blocker-2-pilot-sharpening.md`. I could not find either:
- not on any of the repo's 114 branches (re-fetched 10-17);
- not in Google Drive;
- not in any of my cloud sessions.

The sibling solve sessions hit the same wall: the game-wall session writes "the spec is not in the repo or Drive".

Without the spec I don't know three things:
- what **Item 0** and **Item 1** contain;
- what the **axis gate** tests;
- what **C2** and **C5** log.

I also don't know v2's host, arms, seed count, horizon or bar formulas. So I cannot run, or even fully prepare, the pilot "exactly as staged".

**Request R1:** the two files (or their text), pushed to a branch or pasted into this session.

## 2. Bid A: v2 Tranche A, as the spec stages it

| Field | Value |
|---|---|
| Cost | about **$50.04** committed before the sigma gate (packet figure: 4090 at $0.43/h, about 116 GPU-hours). Expected pathway total $105.32; capped maximum $148.00 over about 6–7 weeks. |
| When | Week 2 (the packet's staging), only after Item 0, Item 1 and the axis gate clear. |
| What it buys | The width contrast's own sigma_d (the sigma gate). After that, the horizon-locked readout, with every KILL behind the pre-committed extension to 12,000 updates ($37.41). |
| What it displaces | The **whole week-2 Vast cap** ($50). In practice: any LT-2 logic boxes (about $1.1 each), B3G2 speed or scaling runs (about $7 each), and every other Vast track that week. The 10M agent rental is separately gated by Ben's >90% rule, so it is not displaced by this bid. |
| Free compute it could use instead | BensPC (RTX 5070 Ti, $0). It was idle about 52 h at 10-16 06:34 ET; its queued B3G2 A8/A4 jobs are marked NEEDS ATTENTION. The owner decides the order. If v2's host is the Gemma-fronted 10M class, the PC runs it at about 0.156 updates/s, about 43 h per 24k-update run (shown, G1), so even free hours are scarce. |

## 3. Bid B, offered for comparison: the same question on the stalled lines' own parent

Full design: `reviews/size-vs-stall-solve-2026-10-16.md`, sections 3–4. In short:
- **Host:** the T1SDR 3M parent (the shared parent of the logic, far and game lines) against a pure-width d448 twin (about 10M, parent lr unchanged).
- **Readout:** logic R2a over 6 parents, with all the Stage-2 fixes carried over: horizon lock, rate-aware reads, update-RMS logging, G0 as a non-stopping diagnostic.

| Field | Value |
|---|---|
| Cost | Before the gate: ≤ **$12** with parents on BensPC, ≤ $24 if they fall back to Vast. Expected about $25–30; worst case about $59 over 3 weeks (each week ≤ $24 of new spend). |
| What it buys | A powered size / not-size verdict on the line that is actually stalled (R2a), with the sigma measured from its own paired parents. |
| What it displaces | Under half of one week's cap, plus about 24 PC-hours (owner's call). |
| What it does not buy | Whether the Gemma-fronted finished design scales. That stays v2's question, on Ben's list as "noise floor + WIDE re-adjudication". |

**I am not asking for both.** The goal names v2, so Bid A is the default. Bid B is there so the ruling can weigh the cheaper read. If v2's host is in fact T1SDR / LT-2, the two bids merge.

## 4. $0 work done or started now, needing no ruling (drafts for code review)

- **C8 draft:** an opt-in `--log-update-rms` flag in `custom_io/train.py` that logs pre-clip grad norm, clip-fire rate and per-module update-RMS. Its tests require training to be bit-identical with the flag off and with it on. This is host-agnostic: both candidate hosts train through `custom_io/train.py` or an overlay of it.
- **Bar calculator draft:** `custom_io/pilot_bars.py`. It computes each contrast's own sigma_d over **units** (parents or seeds, not replicates, so there is no pseudo-replication), with a t interval and a mechanical verdict from a sealed rule file. It is validated by reproducing the record's 8a interval (B2 +0.49, CI −0.74 to +1.72).

- **Size check (shown, CPU, 10-17):** the T1SDR `tool` model widens through its existing `d` argument, so Bid B's parents need **no model code change**. The counts are:
  - d256: 3,314,132;
  - **d448 / 7 heads: 9,854,600** (2.97×, inside 10M ± 5%);
  - d512 / 8 heads: 12,807,534;
  - d768 / 12 heads: 28,487,944 (the 30M guard).

## 5. What I need back

1. **R1:** the v2 spec and the synthesis text.
2. **A ruling on Bid A** (or Bid B), with its week.
3. **A BensPC slot ruling:** who gets the PC hours ahead of the NEEDS-ATTENTION B3G2 jobs.
4. **A code-review slot** for the two drafts in section 4.
