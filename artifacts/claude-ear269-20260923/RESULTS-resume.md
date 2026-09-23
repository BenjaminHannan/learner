# Exp 269 RESULTS-RESUME: registered ear wave after the network block (resume agent, 2026-09-23)

## Result: registered FAIL (M6 false asks 2 > bar 1; M1-M5, M7, M8 all PASS)

The blocked run is now complete. Arm B was NOT re-run (it ran once pre-block;
its sealed outputs were reused). Arms A, A265, A261b each ran exactly ONCE on
all 100 blind turns through the sealed pipeline. M1 (27/30 asks, bar 27) and
M2 (12/15 exact, bar 12) pass exactly at their bars; M3, M4, M5, M7, M8 pass;
M6 fails with 2 false asks on non_owner_we turns (bar <= 1). Both false asks
come from the new text check only (P1 our+ownable-noun on facility nouns the
writer filed as non-owner); the divert asked on 0 control turns.

## Marks table, arm A (integer counts)

| Mark | Bar | Got | Pass? | Prediction |
|---|---|---|---|---|
| M1 | group_owner: 0 group-owned saves AND >= 27/30 turns ask whose | 0 saves; ask 27/30 (divert 11 + text-only 16) | PASS | P269.1: 24-29, ~55%: hit top of range |
| M2 | mixed: >= 12/15 turns exactly right | 12/15 | PASS | P269.2: 8-12, ~35%: hit top of range |
| M3 | first_person: 0 hits lost vs A265 | 0 lost (19/19 both) | PASS | P269.3 ~99% |
| M4 | named: 15/15 byte-identical to A265 | 15/15 | PASS | P269.4 ~99% |
| M5 | 0 new wrong saves vs A261b | 0 new | PASS | P269.5 ~99% |
| M6 | false asks on non_owner_we+first_person+named <= 1 | 2 (both non_owner_we, both text-only) | FAIL | P269.6: 0-1, ~85%: missed by 1 |
| M7 | gold hits lost on non_owner_we vs A265 <= 1 | 0 lost (16/16 both) | PASS | P269.6 ~99% |
| M8 | 0 new wrong saves vs A265 | 0 new | PASS | P269.6 ~99% |
| ALL | overall registered PASS | 7/8 marks | FAIL | P269.7 ~20%: fail as predicted-likely |

Per-arm wrong rates (no bars): A 4 wrong / 68 saved (per-fact 0.0588),
4 turns / 100 (per-turn 0.04), hits 64/70. A265 identical (4/68, 4/100,
64/70). A261b 23 wrong / 87 saved (0.2644), 22/100 turns, hits 64/70.
B 25 hits / 70 gold, 0 wrong, 25 saved (from the pre-block run, unchanged).

Per family, arm A (n, TEACH hit/gold, wrong, saved, ask turns, turns_wrong):

| Family | n | hit/gold | wrong | saved | ask | turns_wrong |
|---|---|---|---|---|---|---|
| group_owner | 30 | 0/0 | 3 | 3 | 27 | 3 |
| mixed | 15 | 14/15 | 0 | 14 | 12 | 0 |
| first_person | 20 | 19/20 | 1 | 20 | 0 | 1 |
| named | 15 | 15/15 | 0 | 15 | 0 | 0 |
| non_owner_we | 20 | 16/20 | 0 | 16 | 2 | 0 |
| ALL | 100 | 64/70 | 4 | 68 | 41 | 4 |

Latency (no bar, P269.8 predicted median ~300-450 ms/turn): ear+checker+guard+
groupcheck median 357.78 ms (p90 607.25, max 892.56). Ear infer on BensPC:
median 187.3 ms (p90 288.7, max 384.5), 83/100 beamed. Checker queries:
median 266.8 ms (p90 297.4, max 495.1), 0 fallbacks in 186. Group check
~0.01 ms. Arm B abstains outside first_person/named (report-only).

Panel theta curve for A (recall, wrong): 0.00-0.55: 0.9143, 4; 0.60-0.65:
0.90, 4; 0.70: 0.8857, 4; 0.75: 0.8714, 3; 0.80: 0.80, 2; 0.85: 0.6714, 2;
0.90: 0.2143, 1; 0.95-1.00: 0.0, 0.

## Every move and every miss (integer counts)

Ran once each (ONCE = one inference pass, one query pass, one score):
- Ear inference on BensPC (sealed 257-infer, cuda, ckpt sha ok, tau 9.3,
  k 4): 100/100 turns, 0 errors.
- Checker query build (sealed qbuild, panel mode, local): 100 turns ->
  186 checks (prompt B).
- Checker queries (prompt B, temp 0, see D12 adapter): 186/186 answered,
  0 fallbacks.
- Sealed score (theta 0.25): M1-M8 as above. Arm B: 0 runs this resume
  (pre-block outputs reused: 100/100 items, 25/70 hits, 0 wrong).
- Re-runs of any arm: 0.

Misses, all listed:
- M1: 3/30 group_owner turns got no ask (no divert fire + no text fire;
  sealed reason code `no-ownership-pattern` on all 3). Ask split on the
  other 27: 11 via 265 divert, 16 via text check only.
- M2: 3/15 mixed turns not exactly right; all 3 lack any ask (no divert,
  no text fire). Two of the 3 still saved the other fact (teach 1/1);
  one missed it too (teach 0/1). Zero group saves in all 15.
- M6 (the FAIL): 2 false asks, both non_owner_we, both text-check-only
  (divert 0 there), rule codes `P1 our+doors` and `P1 our+garden`:
  "our" + facility noun fired the sealed P1 ownable-noun rule on turns
  whose gold owns nothing. first_person 0, named 0.
- A wrong saves (4, all checker-guard-passed non-group frames, all also
  saved by A265 hence M8 = 0): relations age, school, hometown (group
  family turns, subject other) and educated_at (first_person turn).
  A261b makes 23 wrong (19 diverted + 4); A adds 0 new (M5 = 0).

## Deviations (D1-D8 from PASSMARKS/RESULTS carry over; new below)

- D9: BensPC rebooted at 02:31:49 local (boot time read from the host);
  SSH+ping 100% loss ~02:30-05:54 (~3.4 h). Resume polled SSH every ~2 min
  05:20-05:54 (18 polls, all DOWN) until ALIVE at 05:54:01. No GPU
  contention then or later (only this resume used the GPU).
- D10: old llama-server PID 26480 was gone (reboot); nothing to stop.
  pythonw 13036 was also gone; no foreign process was ever touched.
  Seals rechecked at close: 15/15 + 2/2 OK (no sealed file changed).
- D11: at 05:57:42 a foreign llama-server (PID 17056) started with the
  brief's flag prose but no model argument, 9 s before my identical
  05:57:51 start (my PID 9184). Both were model-less router stubs
  answering 400 "model name is missing". I stopped ONLY my 9184 (first by
  WMI, confirmed by taskkill; verified gone, 17056 untouched and still
  present at close). I then waited ~25 min: 17056 stayed model-less and
  the GPU idle, so no active task was using the GPU.
- D12 (driver adaptation, reported with code below): the post-reboot
  server build answers /completion with a new wire shape
  ({"top_logprobs": [{"token", "logprob"}]} instead of the sealed
  {"probs": [{"tok_str", "prob"}]} shape) AND its greedy first token on
  Answer:-style prompts is a blank-lines token (~0.997 mass) with YES/NO
  mass at rank 2-4. The sealed client therefore 100%-fallbacks (verified
  on dev checks). Since sealed files cannot be edited, the checker wave
  ran through an UNSEALED adapter (new file, BensPC only, printed below)
  that sends the sealed request bytes and applies the sealed math
  (first-position YES/(YES+NO), same strip/upper match, same fallback
  rule), only adding the new-shape deserialization (prob = exp(logprob)).
  Fidelity proof on dev (dev data only, sealed scorer): rebuilt dev
  checks match the sealed manifest 162/162 keys; 162/162 queries,
  0 fallbacks, median 268.8 ms (dev wave 282.7 ms); save/hold agreement
  at theta 0.25: 160/162; full sealed dev score reproduced EXACTLY
  (every mark and every family row byte-identical to dev269_score.json;
  the 2 flipped checks fall on non-decisive frames). The registered
  panel wave is therefore the sealed measurement through a shape shim.
- D13: my server (PID 4040) added the model file argument and used port
  8082, because the brief's flag prose names no model argument (without
  it the server loads nothing, as D11 showed) and 8081 stayed occupied
  by the foreign stub. Model resident 13972 MiB, matching dev's ~13.7 GB.
  Server stopped by exact PID at the end (taskkill /F worked, unlike the
  pre-reboot session-0 note); nvidia-smi confirmed idle (579 MiB, 1%,
  9.36 W). No other process touched.

## Run provenance (new files, sha256)

- artifacts/claude-ear269-20260923/panel269_earpreds.json
  e454f4d2223bbc27eb4602b0751addf3eedd374a63c014b642d80732c03784c4
- artifacts/claude-ear269-20260923/panel269_q/checks.json
  1f51d562810c031cb8e3826bf59cdadc40e769ca1ea8b33d15864f3f52189786
- artifacts/claude-ear269-20260923/panel269_q/manifest.json
  ff53f63c5cd7322e436ecb46f9ec88c2703a609bda8060f7fb3fbd81462f9041
- artifacts/claude-ear269-20260923/panel269_pyes.json
  c2750bf87e70a223b9340cacfdc2bdb32474f82ca476aecea821457267ba3bb6
- artifacts/claude-ear269-20260923/panel269_score.json
  0c5470b2cf01240a0100efa7f1694077af342ecf1aeefc980037c8b0687598d0
- BensPC staging (C:\Users\benja\smolear235\run269\, all staged bytes
  hash-verified against the repo before running): 9 sealed driver copies
  + panel269_turns.json + panel269_checks.json (186) + 269_qwen_adapter.py
  (below, unsealed) + run products.

Adapter code (the D12 shim; sealed request bytes + sealed math, new-shape
parse only):

    import argparse, json, math, statistics, time, urllib.request
    from pathlib import Path
    def post_completion(url, prompt, timeout=180):
        body = json.dumps({"prompt": prompt, "temperature": 0.0,
                           "n_predict": 1, "n_probs": 10,
                           "cache_prompt": True}).encode("utf-8")
        req = urllib.request.Request(url.rstrip("/") + "/completion",
            data=body, headers={"Content-Type": "application/json"})
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
        return d, (time.perf_counter() - t0) * 1000.0
    def candidates(first):
        if isinstance(first, dict) and "top_logprobs" in first:
            out = []
            for t in first["top_logprobs"] or []:
                try: p = math.exp(float(t.get("logprob", float("-inf"))))
                except (TypeError, ValueError): continue
                out.append((str(t.get("token", "")), p))
            return out
        cand = first.get("probs", first.get("tokens",
                 first if isinstance(first, list) else []))
        if isinstance(cand, dict): cand = cand.get("probs", [])
        out = []
        if isinstance(cand, list):
            for t in cand:
                try: p = float(t.get("prob", 0.0))
                except (TypeError, ValueError): continue
                out.append((str(t.get("tok_str", t.get("text", ""))), p))
        return out
    def p_yes(d):
        text = str(d.get("content", ""))
        cps = d.get("completion_probabilities") or []
        py = pn = 0.0
        if cps:
            for s, p in candidates(cps[0]):
                u = s.strip().upper()
                if u == "YES": py += p
                elif u == "NO": pn += p
        if py + pn > 0: return py / (py + pn), text, False
        s = text.strip().upper()
        if s == "YES": return 1.0, text, True
        if s == "NO": return 0.0, text, True
        return 0.0, text, True

## Note on parallel attempts (added at close)

- A sibling attempt (RESULTS-resume2.md, 05:37, cloud-GPU path) ran while
  BensPC was down and executed 0 arms, 0 servers, 0 scorer runs, so this
  resume's single execution of each ear arm duplicated nothing.
- Both attempts wrote a ledger line numbered P269.10 (theirs first). The
  ledger is append-only, so a P269.11 correction line records that this
  resume's OUTCOME-RESUME line reads as P269.11.

## What it means (plain English)

The final exam is graded. The new text check does its main job: on 30
group-worded turns it asks "whose" 27 times and never saves a group-owned
fact, and on 15 mixed turns it gets 12 exactly right with zero group saves.
It changes nothing it shouldn't: first-person and named turns are
identical to the old system, and it adds zero new wrong saves. It fails on
one thing: it cried wolf twice, asking "whose" on two turns where nothing
was owned (both times fooled by "our" + a building word). The bar allowed
at most one false ask, so the registered verdict is FAIL, by exactly one
extra false ask.

## What it doesn't mean

It does not mean the idea is broken: 7 of 8 marks pass, both headline
marks (M1, M2) pass, and the miss is small and specific (facility nouns
after "our"). It does not mean the old system was better: the old system
asked on only 11 of 30 group turns, the new one on 27. It does not mean
the checker is unreliable: 0 fallbacks in 186 panel queries, and the
adapter reproduced every dev number exactly. It does not mean arm B
matters here: B has no bars and was only a baseline (25/70, 0 wrong).
