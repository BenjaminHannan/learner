# PROOF: PROBLEM-7 (world model / dreaming), STEP 6, 2026-11-24 ~08:00-08:50 ET
Files changed/added (M1 PROBLEM-7/): PLAN.md (appended amendment), STATUS.md (appended), HANDOFF.md (appended), PROOF.md
(new), forecast4/ (new: forecast4.py, imagine_head6.py, *_draft_linear.py, step6.diff), step6/ (new: IDEAS.md,
BUGHUNT.md, run_step6.sh, wait_and_run.sh), neon/ideas-step6/, neon/bughunt-step6/ (new).
M1 ds-copies/problem-7/step6/patch6.py (new). M3 PROBLEM-7/: wm-harness/forecast4.py + imagine_head6.py edited,
*_draft_linear.py backups, patch6.py, step6/, review-src6/, neon/*-step6/.

## Diff (forecast4/step6.diff: step 5 -> step 6 harness; draft -> pinned harness; draft -> pinned head)
See forecast4/step6.diff (75 lines, sha256 73ebbe2c824d1696e1e19d79795edd44df50655124a2fb5da69b272138e351b6). Key lines:
  - IMG = action_emb, action_in, action_pos, imagine_out params; every other param requires_grad False; one Adam lr 1e-3
  - imagine_out = Sequential(Linear(d,d), GELU, Linear(d,D)) last layer zero; delta = imagine_out(hn[:, :R]) * imagine_scale
  - imagine_alpha removed (al = 1); imagine_scale = per-coordinate std of real train boards

## Commands + exit codes
1. scp patch6.py; ssh m3 'cp ... _draft_linear.py; python3 patch6.py; ast.parse(...)' -> "patched", "ast ok", exit 0
2. ssh m3 neon_gui.sh step6/IDEAS.md neon/ideas-step6 --model gemini-4-neon-xhigh -> SUCCESS 2615 chars, exit 0
3. ssh m3 neon_gui.sh step6/BUGHUNT.md neon/bughunt-step6 --model gemini-4-neon-xhigh --review-dir review-src6
   -> SUCCESS 3814 chars, exit 0, review_left_out_for_size empty
4. Lock check: /tmp/premonition_m3_mps.lock = "69430 1795526251"; pid 69430 alive = PROBLEM-2 `zsh run9.sh`.
   10-min poll (19 x 30 s) -> still "held 69430".
5. ssh m3 'nohup step6/wait_and_run.sh &' -> waiter pid 71046; first attempt logged "LOCK HELD by 69430" (rc 8, retries).
6. Disk: M1 11 GiB free (at floor, nothing large written); M3 25 GiB free.

## Hashes (sha256)
forecast4.py 287668b58dc803bd7cb30db3bbe7a639f43beb817138bd3843e265b854686c94
imagine_head6.py f8b8badabf4127671f04db4488e7dece951866cb7923141c24224293a2e65996
forecast4_draft_linear.py 78ce9efc5aa7df4a299dd33e36034caf0d53827ff9fbb075588cb40cb74af8af
imagine_head6_draft_linear.py 5741e87b879149f6433ebc6edcde40d69d342419bb3e9c8b7ee4f7da4b88e58e
step6/IDEAS.md 6037cafa93a3e586660e21bd1316b76855c710925a2ef6cfd7e5bc3e8036067e
step6/BUGHUNT.md a16511f0348deb077e5694ea9c55ba8ae2f5d8f572b17bbdc141990a007ac5a0
step6/run_step6.sh 98017e19e427081b8df180a4a257e06bbeff78505c8ee43843d5767d4deb7fba
step6/wait_and_run.sh 4e8d8a1d6b0db6cad9b007f1c0738a4e0a0d0939771fc835437d73eb5aee2f1e
neon/ideas-step6/REPLY.md f6a7a72e528a3599ef7effaef8dcfebff76068987ac01e6308dc88b0491843b9
neon/bughunt-step6/REPLY.md df10e78dda547fb0fbf4bd94991d5bd3e12390dad7d004b514408a4b55f637bc

## Tests
No scored run yet (blocked on the MPS lock). No unit tests; ast.parse on both edited files passed.
