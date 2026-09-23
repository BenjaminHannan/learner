# Newly arrived evidence — key pooling and interface probes

**Shown:** standard-library tabulation of JSONs that appeared after the first evidence audit. This supersedes its local-availability statements. No model or test was run. The historical 30-run table is unchanged.

## Complete saved rosters

| Wave | Arm | N | Stuck | READS | Practised | Held-out | All three | Mean held-out | Total seconds/run |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| claude-keypool-20260919 | control | 40 | 7 | 39 | 33 | 8 | 7 | 0.2624 | 4944.4–5133.9 |
| claude-keypool-20260919 | keypool | 40 | 1 | 39 | 39 | 17 | 17 | 0.4538 | 4894.8–5155.8 |
| claude-keypool-relcut-20260919 | control | 40 | 16 | 40 | 23 | 23 | 23 | 0.6477 | 2672.0–2787.6 |
| claude-keypool-relcut-20260919 | keypool | 40 | 6 | 40 | 34 | 33 | 33 | 0.8113 | 2672.5–2799.6 |

**Shown:** matched-seed discordances (treatment better / worse; exact two-sided McNemar p), descriptive post-arrival analysis, not a new preregistration:

- claude-keypool-20260919, stuck: 7/1; p=0.070312.
- claude-keypool-20260919, all_three: 14/4; p=0.030884.
- claude-keypool-20260919, mean held-out paired difference: +0.1914; actual steps 12250–12251.
- claude-keypool-relcut-20260919, stuck: 13/3; p=0.021271.
- claude-keypool-relcut-20260919, all_three: 14/4; p=0.030884.
- claude-keypool-relcut-20260919, mean held-out paired difference: +0.1636; actual steps 12250–12251.

## Probe C: factual paths

**Shown:** 30 result entries per probe. Both restoration comparisons report bit-identical answers and correctness for every checkpoint. Cast-validity masks remain; these interventions do not remove every observable world variable. A story-blind evaluation also changes the question representation distribution.

| Arm | Condition | One-hop mean | Practised mean | Held-out mean |
|---|---|---:|---:|---:|
| baseline | C0_normal | 0.7918 | 0.7638 | 0.1575 |
| baseline | C1_cards_removed | 0.0621 | 0.0698 | 0.0624 |
| baseline | C2_story_blind_question | 0.4464 | 0.2985 | 0.0721 |
| baseline | C3_both | 0.0632 | 0.0680 | 0.0663 |
| shortcut | C0_normal | 0.6216 | 0.6117 | 0.5715 |
| shortcut | C1_cards_removed | 0.0512 | 0.0567 | 0.0550 |
| shortcut | C2_story_blind_question | 0.4945 | 0.3126 | 0.2448 |
| shortcut | C3_both | 0.0518 | 0.0567 | 0.0585 |

## Probe A and B

| Arm/group | n | Edited key cosine mean | First-card identity changes /512 mean | Card-value subject readout | Card-value object readout | Subject-token subject | Object-token object |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline/stuck | 4 | 0.9970 | 116.7500 | 0.1072 | 0.7250 | 0.9852 | 0.9990 |
| baseline/learned | 11 | 0.9984 | 5.3636 | 0.8959 | 0.9859 | 0.9991 | 0.9994 |
| shortcut/stuck | 7 | 0.9969 | 121.4286 | 0.1630 | 0.5591 | 0.9650 | 0.9969 |
| shortcut/learned | 8 | 0.9990 | 2.3750 | 0.9141 | 0.9071 | 0.9992 | 0.9992 |

**Suggested:** interpret recoverability only for this fitted linear probe and fixed layouts. High key cosine can coexist with rank changes. Probe A changes both the key and contextual question state, so its ranking change does not identify key drift as the sole cause. Probe C establishes loss of performance after cutting card access on this panel, with reversible answers; it neither certifies all factual-path closure nor establishes why story-blind questions hurt.
