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
