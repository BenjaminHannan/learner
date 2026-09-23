Building the 138nb follow-up — verifying the one-change wrapper and proving no regressions.
I've mapped the current system and the required one-line label change — now digging into the runners to scope the build.
Plan confirmed — now building the 30-dialog reproduction set to lock in the baseline.
Reproduction confirmed: 25 subject answers with no label, 0 with label. Now building the one-change wrapper.
Wrapper works exactly as specified. Now writing the config and test drivers.
Drivers drafted — now the scorer and blind-panel runners.
Panel spec retrieved — it defines the exact row format I need. Checking how the previous run wired the table panel.
M6 runner done — now the blind-panel arm runner.
All drivers parse and the scorer hash checks out. Starting pilots.
Dev pilot clean: all 27 diffs are exactly the label append, nothing else. Piloting the M2 driver on small pieces.
Driver validated — the one pilot move is exactly the expected label gain. Launching the full pilot.
M2 pilot: 719/720 identical, 1 move (the label gain). Now M3 suite pilots.
All pilot data collected. Assembling predictions.
18/18 probe changes are pure label appends, 0 writes. Now M4/M5 pilots.
M5 pilot delta −0.166 ms. Validating the whole pilot through the scorer.
The scorer section looks correct. Verifying with the allowed set added.
One scorer bug: multi-subject replies trip the ghost check. Inspecting then fixing.
All pilot marks pass. Building the final predictions file with reasons.
Seal 11/11 OK. Appending ledger predictions.
Registered M2–M5 all pass. Verifying the seal is untouched.
Panel is ready. Copying it unchanged and verifying the seal.
Fidelity 70/70. Scoring both arms with the sealed scorer.
M1 evidence secured. Running M6 (tablepanel221, once per arm).
M6 passes: 0 wrong, 80→84 right, gains are exactly the four 190 rows. Securing the counts.
All marks complete. Writing RESULTS.md.
## Verdict: PASS — 138nb does exactly the one change, nothing else

138nb = 138n + one outermost reply-text rule (`scripts/claude_fix138nb_label.py`): a reply answered by stage `loop190-reverse` that names a subject gains ` (worked out backwards)`. All of M1–M6 pass. Full details: `artifacts/claude-merge138nb-20260923/RESULTS.md`.

### Marks table (integer counts)

| Mark | Result | Counts |
|---|---|---|
| M1 invpanel138nb, blind 70 items | PASS (driver deviation D1, no bar affected) | 138nb wrong **0**; question writes **0** (qw = only the 4 teach_control statement turns, same ids both arms); whose_R **14/14** (138n 2); lives_born **10/10** (138n 0); has_as **6/6** (138n 2); verb_backwards **9/9**, lost **0**; my_backwards **4/4** (138n 1); no_match **8/8**; unknown_value **4/4**; forward_control **10/10** byte-identical; teach_control **4/4** byte-identical |
| M2 720 dev/case vs 138n | PASS | moved **1** (221/D11, predicted); unpredicted **0**; predicted-wrong **0**; predicted-not-moved **0** |
| M3 suites + probes vs 138n | PASS | sessions152 **0**; bench **0**; marks123 **0**; rt136 **16** (13 allowed C019–C031 + 3 reply-only C076/C079/C115); direct-vs-138n **0/145**; rt143 **0** moves, **0** flips (n=124); probes **18** reply changes (all predicted), **0** writes, **0** ghosts, **0** dup fails |
| M4 smoke + bench x3 | PASS | differing fields **4** (.agent .config .label .seconds); bench identical **4/4** |
| M5 latency | PASS | median 138n 2.687 ms, 138nb 2.565 ms, delta **−0.121 ms** (bar ≤ +2 ms) |
| M6 tablepanel221, 91 items, registered scorer | PASS | 138nb wrong **0** (138n 0); right **80 → 84**; lost **0**; gained **4**; 190-subject candidates **4/4** right; question writes **0** |

### Every move (categories and ids only, no item text)

- M1 gained 29 (label gains): i138nb-001, 002, 003, 005, 006, 008, 009, 010, 011, 012, 013, 014, 015, 016, 017, 018, 019, 020, 021, 022, 023, 024, 027, 028, 029, 030, 041, 043, 044. Lost: none. Wrong either arm: none.
- M2 (1, label138nb): 221/D11.
- M3 probes (18, all pure label appends, 226 source lines unchanged): p3-dialogs:d04:t02, d04:t05, d12:t04; p3c-restart2:d01:t04, d01:t05; v-dialogs:d00:t05, d01:t04, d05:t02, d05:t04, d05:t05, d05:t06, d05:t07, d06:t08, d10:t07, d12:t04, d13:t06; v-supp:d00:t05, d01:t05.
- M6 gained 4: p221-060#1, p221-063#1, p221-064#1, p221-069#1 (exactly the diagnosed rows).

### Misses: none (0 unpredicted, 0 new wrong, 0 write changes anywhere)

### Deviations

- **D1 (driver-only, sealed file untouched, no re-seal/re-run):** my M1 runner serialises stored triples as character lists, so teach_control "right" reads 0/4 on both arms (writer's base rows read 4/4). No bar uses those fields — byte-identity 4/4 verified, qw flags match base 70/70, n-arm replies reproduce base rows 70/70. One-line diff stated in RESULTS.md, file unchanged.
- Panel SPEC read pre-seal for row-format fields only; build was fixed before and untouched by it. Panel seal 5/5 OK from repo root; 138nb seal 11/11 OK after the run; panelmap SHA-OK. M1/M6 rows+logs stayed in /tmp; only ids+counts copied in. M6 context: 138n scores 80 here vs 79 in the cloud re-run (full vs stubbed router; bars compare within-run only). Step 1 repro: 36 dev dialogs, 25 subject-answers with no label on 138n; post-build pilot 82 turns / 27 diffs, all exactly the label.

### What it means / doesn't mean (plain high-school English)

- Means: backwards answers that were right but unlabeled now carry the label (M1 36→65 right, M6 80→84 right, 0 wrong), and literally nothing else changed — 719/720 dev cases identical, all suites/probes/sleep/bench/latency within bars.
- Doesn't mean: 138n's FAIL is rewritten (it stays FAIL); teaches, abstains, and source lines are byte-identical (the label never lands on an abstain or a write).

### PUSH

Not pushed: OPUS-RULES forbids commits/pushes and this environment blocks `git push`. Ready as listed: `artifacts/claude-merge138nb-20260923` (+ copied-in `artifacts/claude-invpanel138nb-20260923`), `scripts/claude_fix138nb_label.py`, `scripts/claude_loop138nb_agent.py`, `scripts/claude_138nb_*.py/.sh`, `artifacts/fable-predictions-ledger.md` (P138nb.1–5 appended).
