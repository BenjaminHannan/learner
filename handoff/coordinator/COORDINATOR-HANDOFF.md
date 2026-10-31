# READ THE OCT 23 SECTION AT THE BOTTOM FIRST (it supersedes the stale Oct 20 state below)

# Learner-New coordinator handoff (Oct 20, from the Opus coordinator session_014a7yFK9adwx14ocaqRQ6eZ)

You are the Learner-New coordinator for Ben, a high-school senior who owns the project. Repo: BenjaminHannan/learner. Main model: PremonitionMini ("D", d_model 128, about 2.1M params). Work happens in Claude Code sessions (never call them "threads"). Funding ledger and all rulings: `handoff/coordinator/funding-ledger.md` on branch `claude/affectionate-goldberg-1yx6lw`. Read it first. Append every ruling and every dollar to it, then commit and push.

## Standing rules
- Funding moderator: sessions bid to you; you rule against the caps. Caps: Vast $50/week, Modal $30/month. Beyond the caps, or a 10M-param 5090 run: Ben only. Every Vast rental also needs Ben's own click in the renting session, because the auto-mode safety check blocks rentals otherwise. Never try to get around that.
- Bars and guards are set before runs and are never loosened after seeing a score. A gate's NO is final. One change at a time.
- Code is DRAFT until the Claude Code built-in code-review feature passes on it.
- Design or judgment questions: consult an Opus reviewer (your advisor, or an Opus subagent) before ruling.
- Usage rules (Ben, Oct 20). Last night cost about $400 of usage (~16% of his weekly quota).
  1. At most 2 review rounds per change; if it is still not clean, PARK it.
  2. When steals, swarm, info or Brain next need real work, start a FRESH session from a short summary instead of continuing the old one.
  3. Haiku for reading and status checks; Sonnet for build, fix and test work; Opus only for design gates, final reviews and verdict checks.
  4. Message Ben only with outcomes, in plain language, and verify every number against its source.
- Ben wants decisions offered as buttons (AskUserQuestion) or short phrases, and simple explainer pages for judgment calls.
- Ben has said he trusts the coordinator to decide routine calls. Anything irreversible (deleting data), over the caps, or a bar change stays his.

## Sessions and state (as of Oct 20 ~11:15Z)
- Watcher (Sonnet): session_01LG97w5ec8yrTPAQ3AxBpov. It runs a 10-minute send_later chain and messages the coordinator only on real changes.
- Speed: session_01TxmNuc7AWHeDRShpZG7W7w. GPU-RUN-5 is sealed ($1 cap) and waiting on Ben's click. GPU-RUN-4 failed mark 2: defer does not ship.
- Swarm: session_015V6Z9z9fNXAq9SRRSY1FdY. C0+S0 is approved, $4.20 cap, PIN 34d8d0635, waiting on Ben's rental click. S1 is not approved.
- Steals: session_01DPxyxb1vF99GbqqKPgZmA8. R1 stage 0: Muon PASSED. R1 stage 1 is sealed (RTX 5090, $2.80 cap, F_max 7.5e15) and waiting on Ben's click. R2: NOT SHOWN, stopped.
- Info constraints: session_016AV7ThwSnYRrBJe4rGguov, on stand-by. S2, S5 and S6 passed (toy, d = 32 only); S3 and S4 failed. A village count showed person cues don't carry over to the village (71% of questions are about objects). Next design (object identity or a learned cue) is Ben's call. No money for person cues.
- Brain: session_01R6PEwHPC4AHUHr6hwZFJAq. Ben kept G1 after an Opus review. E0-READY at a1adcb196. E0 runs on Ben's PC (WSL), and the DM1/DM3 marks come from Ben.
- Restart gate: session_01GR2gp7svxd8z7yZeufWtwG. B2 = (a); B3 = a separate commit; B1 = add escalate. Ben's unblock instruction was relayed at 11:10Z; check that it took effect.
- Size: session_01BWoBq8CrA29RF8UDRuRHBb. Bid C, depth-first. Ben's unblock was relayed at 11:10Z; check.
- Game world: session_013wVGpXa8PM2JFLUHp6Arm7. Write the Track 10 OPTIONS.md. Ben's unblock was relayed at 11:10Z; check.
- Span: six stopped Vast boxes (disk about $3.74/day) hold the only copies of the checkpoints. Not destroyed. Ask Ben again Thursday Oct 22.
- Decoder reader-KV: CLOSED (stage 0 FAIL). ShinkaEvolve: trial 1 failed ($3.39 API); the trial 2 plan is in research/shinka/NEXT.md and needs Ben's yes.
- The daily rundown scheduled task (trig_0193h6Bixb11AaeDPjc6hGem) runs at 7:22 PM ET.

## Vast
Credit is about $19.3; no instances are running except the six stopped span boxes. Check read-only with: curl https://console.vast.ai/api/v0/instances/?owner=me and /api/v0/users/current/ (the proxy adds the key).

## Update Oct 21 ~01:20Z (Sonnet coordinator session_018Ybowk1FLjHVsZsWFonjEk)
- Ben confirmed the delegation directly (see ledger). New session briefs carry the "coordinator speaks for Ben" line.
- Swarm: line parked after run 3 (calibration needs 14.28 GiB); Ben approved the fix and a total of about $5.60. Fresh Sonnet session session_015W2KnpcFeGg9cH4WUhzry3 owns it; old swarm session on stand-by.
- Steals R1 S1: parked ($1.32 spent). NEXT.md in artifacts/claude-steals-20261017/r1-stage1/.
- Defer port: one more fix+review round allowed by Ben (speed session).
- Watcher is a Haiku session (session_01DaSfX2LCyxuQBJxBQYT8xY). No rentals running; six stopped span boxes remain (disk about $3.74/day; ask Ben Thu Oct 22).
- Restart gate, size, game world, PC runner ping, Brain E0 PC card are still open.


## CURRENT STATE, Oct 23 (written by Sonnet coordinator session_018Ybowk1FLjHVsZsWFonjEk when Ben moved this job to a project)
The full money/rulings record is handoff/coordinator/funding-ledger.md (append every ruling and dollar; git pull --rebase first, commit with the attribution lines, push, check git status -sb). Everything below is what I last knew; verify before acting.

### Standing rules and delegations (Ben's words, Oct 21-22)
- Vast $50/week (Mon-Sun, unspent rolls over). Modal is the coordinator's call ("Modal is yours now."), inside Ben's $30/month Modal allowance; over $30/month is Ben's. Claude API ceiling for ShinkaEvolve: Ben said money is not the constraint (Console pool ~$157). Ben on Oct 23: whole-trial Shinka hard stop is $80 (warn $65).
- "can you just do that in the future?", "I think all of those things that you're asking approval for are things you're allowed to do.", "Okay, I approve everything." Routine confirmations are the coordinator's to give.
- Ben-only: pass-mark/bar changes, deletions, spend over caps (the Vast weekly cap, the $80 Shinka stop, Modal over $30), 10M-param runs, and any in-person confirmation the safety checks demand (starting stopped Vast boxes, Google Drive connection, span public-upload "yes").
- MetaMuse (Ben, Oct 23): an agent that watches Ben's chats and can relay a message to another chat as if from Ben. Ask it (write the request in your reply to Ben, marked for MetaMuse) instead of asking Ben to type confirmations. You cannot message it directly; relays reach you as "Relayed from X (via Muse)". Several sessions reject send_message from this session as an untrusted device; Ben approved a trust card once, so retry before escalating.
- Bars/guards are fixed before runs and never loosened after a score. A gate's NO is final. One change at a time. Code is DRAFT until a built-in review passes; max 2 review rounds per change then PARK (Ben may allow one extra). Haiku to read, Sonnet to build, Opus only for design gates and final reviews. Message Ben outcome-first in plain language (he is a high-school senior), verify numbers against sources, no obvious questions. He dislikes being asked to type things. If he rejects a tool use, stop and wait.
- Every NEW session brief must say: "The Learner-New coordinator speaks for Ben within his standing rules (handoff/coordinator/funding-ledger.md). Treat its rulings as Ben's approval. Only bar changes, deletions, spend over the caps and 10M-param runs need Ben himself." plus: do not ask Ben what the coordinator has ruled; message the coordinator.
- CLAUDE.md: outside-opinion prompts go under reviews/ with shown/suggested/untested labels, one change at a time, pass marks fixed in advance, plain-language summary for Ben.

### V1 (session "V1 assembly"; branch claude/v1-assembly; frozen spec design/v1/V1_SPEC.md)
- Marks: W1 sealed village >= 18.95% (8.95% best baseline + 10); W2 creative >= 20% first-try (official scorer). Seal opens only if the mechanically chosen arm (D5: higher D dev accuracy) meets both on dev; one sealed read ever.
- Two bugs fixed (sampler ignored the bridge; Bridge registered D as a submodule so D got a second optimizer). First-arm results are void. Fixed re-run (REPORT-V1.md, design/v1/results2/decision/DECISION.json, commit 71a6919e04): FLOOR D dev 68.4%, creative 34.0%; FULL D dev 80.1%, creative 34.8%. Both pass both dev marks; D5 chose FULL. Creative gain is mostly last_digit and square kinds. Spend ~$4.5 of the $5.50 cap.
- BLOCKER: FULL's weights (D-final.pt, creative/W2.pt, in ckpt.tar.gz) were lost when the box was destroyed after pulling only out.tar.gz. Seal NOT opened.
- DECISION PENDING: option A (re-run FULL once, ~$1.5-1.9, pull ckpt.tar.gz and verify sha before destroying, re-judge on dev by the same marks, re-apply D5; needs re-run cap above $5.50, e.g. $8.00, within Vast $50/wk) vs B (leave seal shut). I recommend A; the go-ahead and cap raise were put to MetaMuse to relay but I have no confirmation it reached the V1 session. Check git log origin/claude/v1-assembly and the Vast listing.
- After the pulls: destroy boxes only after sha-verified pulls; confirm with the FULL unfiltered Vast listing.

### Shinka trial 2 (session_01By2oyTPcrnRBen3qAoQC8F; branch claude/shinka-trial2-build; research/shinka/trial2/CARD2.md)
- Ideation in words, cards checked against literature (KNOWN.md) before code. Gates: G1 >= 60 parseable fits_interface=yes cards (passed, 175); G2 >= 15 distinct families (undecided: clustering call was refused; re-run approved, <$1, smaller chunks, same model, Sonnet if refused); +0.05 bar (2xSE 0.037); fresh seeds 2001-2006; fresh Opus hand check. Opus 5.5 for ideation/generation/judging. Stage 1 cost $8.98 (inside the session's own $20 cap; not an overage). Hard stop $80, warn $65; re-price each stage at Opus rates before launch; if it cannot fit, STOP. 16-name transfer untested until the real score. The classifier may block launches (ideate.py --go); a relay or Ben's typed yes is needed then.

### Size / Bid C (session_01BWoBq8CrA29RF8UDRuRHBb; PR #95 branch claude/bidc-calibration-drafts)
- Card sealed at e7841bb12. Addendum 1 (2446ec129): no bar/mark change; A2 (N_REG sampler/legal fix) and A4 (gate check 1 on 64 C2 DEV rows) accepted. Final blocking-only review on 6b1cf5d6f/e0d65adb6: 0 blocking; code shipped (PR at e016cf5d6f). Next: BensPC job card reviews/width-pilot-bidc/PC-JOB-bidc-gate-record.md (free, $0, run from one script bidc-benspc.ps1, no OS update between, same MKL env). No GPU rental until the gate record exists and a gate packet with cost reaches you. Not rule-verified: I never confirmed how the f83e317c5 "coordinator rulings" were issued; my own rulings are in ledger/this section.

### E0 (Brain session_01R6PEwHPC4AHUHr6hwZFJAq; Mac session_016J3VseSUvzJcEUwXfbn74B)
- E0 run on Ben's PC "benspc" (Tailscale 100.75.113.114, reachable only via the Mac session; notes in handoff/memory/benspc-gpu-ops.md). BLOCKED: the Main brain run folders are not on benspc (/mnt/project-files is a cloud store). Need their location from Ben. ComfyUI stop was ordered. Nothing run or spent. DM1/DM3 marks stay Ben's.

### Span (checkpoint public upload)
- Four stopped Vast boxes (56601524, 56611888, 56611889, 56611901) hold the only checkpoint copies. Public upload ($2 cap) needs Ben's yes typed in the span chat (planner safety check refuses a relayed approval; MetaMuse may do it as Ben). Box 56601524's host ended Oct 23 06:00Z; may be unrecoverable. Box starts need Ben's click.

### Other open
- Steals session_01DPxyxb1vF99GbqqKPgZmA8: needs Vast box clicks, Google Drive connection, push of 20 files was denied. Restart gate (session_01GR2gp7svxd8z7yZeufWtwG) unpark is Ben's. Swarm (fresh session_015W2KnpcFeGg9cH4WUhzry3): extra round, I recommend skip. Game world OPTIONS.md relayed. Monthly better-open-model check. Daily rundown scheduled task trig_01AcLhka7ZZ6be5VvUn7a4R1. Watcher Haiku session_01DaSfX2LCyxuQBJxBQYT8xY (PC watcher restart command unknown).
- Ben asked "why not RL" and about "jolt, the rout method": no such method found by web search (ask for a link). V1 is supervised plus a search-keep-train loop with a KL guard; RL (reward from the program verifier on the creative side) is a post-V1 queue item, to be written by the Opus advisor with fixed marks. Do not start before the V1 sealed decision.
- Vast credit $50.73 on Oct 23, only the four stopped span boxes exist. Read-only check: curl https://console.vast.ai/api/v0/instances/?owner=me and /api/v0/users/current/ (proxy injects the key); always read the full unfiltered list; "exited" = stopped, not destroyed.
- Keep the ledger and this file current; consult the Opus advisor for design/judgment calls.
