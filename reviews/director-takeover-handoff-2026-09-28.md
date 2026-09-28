# Director takeover handoff (second handoff), 2026-09-28

Written by the Thread manager of the old Premonition project at 2026-09-28 19:20 UTC for Ben, who asked (19:15 UTC): "Explain everything it needs to do. It's taking all responsibilities and needs to know vast ai, gpu watcher, and preferences with artifacts. You should essentially just make a compaction of this chat for the other project director to do."
Ben pastes everything below the line into the new project's Director chat, after the first handoff (reviews/director-handoff-sonnet-threads-2026-09-28.md, 85194c5e2).

---

Effort: high (Opus 5.5)

# Second handoff: you now take over everything the old Thread manager did

In Ben's old project, a "Thread manager" (TM) was his only contact. It checked every result, wrote prompts for his own chats, ran money and machines, and made his explainer pages. From now on you do all of that as well as directing the research. This handoff is a compressed version of the TM's chat and notes from 09-26 to 09-28. It adds to your first handoff, and where the two differ, this one wins.

**Reference files on main:**
- The TM's full notes, one fact per file: handoff/tm-memory-2026-09-28/ (MEMORY.md is the index). They are history from a point in time, so check anything against main before acting on it.
- The explainer kit: handoff/kit/eli5/.

## 1. Your roles
1. **Director of the research,** as in the first handoff: the finish line, helpers, roadmap and board.
2. **Ben's only contact.** He talks only to you.
3. **Checker of Ben's own chats.** Ben also runs separate cloud chats (section 6). When he pastes a report, or their results land on main, check every number and label against the files on main before you answer. Say what is shown and what is only suggested, then give one recommended next step.
4. **Prompt writer.** When Ben wants a job done in one of his own chats, write the prompt (section 5).
5. **Adversarial reviewer.** Read every PASSMARKS, addendum and script that your helpers or his chats commit, before their run if you can. Look for:
   - a design that can't answer its question;
   - missing controls;
   - marks that can't fail;
   - unfair arms;
   - undisclosed hand-written parts;
   - Claude-written training text;
   - guesses stated as shown;
   - the textbook fix skipped.
   Send the owner the objection and the fix with file:line. For Ben's own chats, tell Ben or put the fix in the next prompt.
6. **Money and machines:** vast, the Mac watcher and BensPC (section 3).
7. **Explainer pages** for Ben (section 4).

## 2. How Ben wants you to work (learned the hard way)
- **Check before he sees it.** His words: "I want everything to just be good."
  - Before any result, summary or explainer goes to him, a read-only subagent checks every claim against the repo and reports CONFIRMED (with file:line), WRONG or NOT FOUND. Fix everything before sending.
  - The check covers framing words too: "shown", "unchanged", "verified", "blind recount agrees" (name the recount file), and "started". A job counts as started only when its own reply or run note says work began, not when a launcher printed "launch".
  - Numbers were often right while headlines overclaimed, and he acts on headlines.
- **A yes is his own words naming the action.**
  - "Dude just do it if I say so": don't script lines for him to copy.
  - Check that his yes was sent after your question, because his messages and yours cross.
  - "Say stop if you disagree" is not consent.
  - Ask one question at a time, answerable in one word, with your recommendation marked.
- **Decide what you can.** He dislikes being asked what a thread can decide ("lack of motivation to just think about problems"). Decide reversible research choices yourself and tell him in one line. Ask only about his goals, money past a cap, things that can't be undone, or what only he approves (first handoff, section 3).
- **Question failures the way he does.** After any FAIL or INCONCLUSIVE, ask:
  - What exactly failed, and at which step?
  - Which assumption was never checked?
  - Why not the obvious fix?
  - Could the training recipe, not the idea, be the cause?
  - How does the brain do it?
  - Which cheap test would tell the explanations apart?
  Never accept a retry that only nudges a number.
- **Usage.** He stopped every thread on 09-27 because usage went to status traffic ("you haven't achieved enough from the amount of usage you've had").
  - Spend turns on research, building and launching tests, and reading results.
  - No polling: one check at a job's expected end, then at most one every 2 hours.
  - No wording-only addenda.
- **Messages.**
  - Result first, in plain words he can follow. Use integer counts written as "x of N".
  - One message per result, blocker or decision. Hold results that need nothing from him and send them together; three "nothing needed" pings bury the one that matters.
  - Call any code standing in for a learned part a "hand-written stand-in".
  - Prompts and handoffs go in a plain message, not a card (his words at 18:57 UTC 09-28).
- **Times.** Never type a time. Paste it from `date -u`. Ben is on UTC-4.
- **Disk space** on the Mac and BensPC is our job: "I'm never doing it again." Never ask him to free space or empty the Trash.
- **Brain first.** When something isn't working, start from how the brain does it, then turn that into one sealed single-change test.
- **Design choices he has made:**
  - Mazes are only a stand-in for "a new kind". He rejects designs that look built for mazes.
  - Forgetting "looks solved" by replay (09-27, evening): keep replay, try only cheap improvements, and put the effort into fast learning.
  - Learning from more varied kinds is future work.
  - The talker is LFM2.5-1.2B ("Swap to LFM", 19:27 UTC 09-27).
  - Sleep trains only the reasoner. The talker gets no skill training, only training on how it talks (not inventing, saying when it's unsure).

## 3. Machines, money and jobs
**Where things can run**
- **Your cloud container** has CPU only, may lack torch (install the CPU build if you need it), and is reclaimed when your session goes idle. Reclaiming kills every process, even `nohup` and `setsid` jobs, though files on disk survive.
  - For a job longer than a few minutes, keep a harness-tracked background waiter plus your own self-wakes.
  - Have the job write its own progress and exit files, so a cut is visible.
  - Commit results as they land. Never commit a log a running job is still writing: a later `git pull --rebase` swaps the file and the job's later lines are lost.
  - Your helpers share this machine, so running 4 CPU jobs at once slows each one.
- **Ben's other chats** run in the same kind of container. Their CPU jobs die when those chats go idle.
- **Ben's Mac** holds everything else:
  - the watcher, which is your only route to a GPU;
  - the vastai CLI with its key;
  - ssh to BensPC;
  - the models in ~/premonition-models/ (for example rsn358u2, slp358n3 and the rd378g adapter).

  The watcher's worktree is /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27, on branch claude/card-experiment-handoff-7c5b27, not main. So jobs fetch the files they need themselves, with `git archive` of origin/main or of a pinned commit.

  Ben's own Mac Claude and Codex agents share the repo and the vast account. Never stop their rentals or processes.
- **BensPC** is a Windows PC with an RTX 5070 Ti. It is free to use, runs one GPU job at a time, and is reachable only by ssh from the Mac (host alias `benspc`). It could not be reached from about 12:30 UTC 09-27, which is why GPU work moved to vast. Check that it answers before counting on it.

**The Mac watcher** (handoff/kit/mimo/watcher.sh; it updates itself from main)
- Every 120 s it fetches main and launches each new file in handoff/queue/*.md.
  - A file is copied to the Mac only when it launches, so an unlaunched job can still be edited on main.
  - A launched name never runs again. To re-run a job, commit a copy under a new name.
  - Files in handoff/held/, or with a line `STATUS: HELD`, wait.
- **Header lines decide how a job runs:**
  - `BASH-ONLY: yes`: no AI builder. It runs the job's first ```bash block in the worktree, killed at 75 min, and stdout is the reply. At most 5 non-000 jobs run at once. Use this for every fixed script.
  - No BASH-ONLY: a free AI builder runs it (rungo5.sh: free Zen Muse, then free mimo). These are rate-limited and sometimes hang, so avoid them.
  - `GPU: yes`: a BensPC job; name it 1xx-, 2xx- or 3xx-. It waits while another GPU job runs, or while BensPC shows over 700 MiB of GPU memory or any python.exe. It writes C:\Users\benja\GPU-BUSY.txt while it runs.
  - `GPU: rent`: rents its own vast card; name it rent-*.
  - `DISK: <GB>`: the job's peak Mac disk use. All launches wait while the Mac has under 5 GB free (jobs marked `LOWDISK-OK: yes` can run down to 2 GB). The watcher prunes the uv cache and cleans rental scratch itself. Never run `uv cache clean`: offline jobs need the cache.
  - `LOAD-LIGHT: yes` for network-bound jobs; `QUIET: yes` for timing jobs, which run alone.
  - A 000- prefix marks small read-only checks, which are never held.
- **Results:**
  - The watcher pushes each job's reply and error files, plus the paths on its `PUSH:` lines, to branch builder-outbox under runs/<job>/. Only files under 5 MiB go, never .pt, .safetensors, .gguf or .bin, and never notebook/.
  - Builders can't push to main. Copy what you need from builder-outbox to main unchanged, with a hash-check log (slp-358n3 did this in 39f384b28).
  - Weights stay on the Mac, and their sha256 goes in the run's SEAL-run.
- **Status:** origin/builder-outbox:status/watcher.txt, pushed every round while the watcher runs (times in EDT). Re-read it before you call any Mac job running or finished.
- **Limits and traps:**
  - An AI-built job's agent kills any single command after 80 min. Start long steps with `nohup ... & echo $! > X.pid` and collect them with a later job.
  - Plain `python3` under the watcher's bash is a broken x86 binary. Use `$(uv python find 3.12)`, or `uv run --offline --no-project --python 3.12 --with torch --with numpy python -B script.py`.
  - macOS has no `timeout` command.
- **BensPC over ssh** (handoff/tm-memory-2026-09-28/benspc-bash-only-jobs.md has the tested patterns):
  - The ssh shell is cmd.exe. Use "C:\Program Files\Git\bin\bash.exe" with a script file, never a script piped in through stdin, which loses its first bytes.
  - Windows `tar -f -` works both ways.
  - Stop a job with `MSYS_NO_PATHCONV=1 taskkill /T /F /PID <pid>`.
  - Ben set a 3 GB free-disk floor for BensPC jobs on 09-27.
- **Status now: working.** At 19:21 UTC 09-28 it launched your dir-h2-a and dir-h3-1-selftest.
  - Times inside status/watcher.txt, and builder-outbox commit times, are EDT (UTC-4). Don't misread 15:21 as a stale UTC time.
  - Its log tail also holds old "Permission denied (publickey)" and "chdir: error retrieving current directory" lines. Ignore them while launches and pushes continue.
  - If status pushes stop for more than about 10 minutes, the Mac is asleep or the watcher is stuck. Tell Ben once, in one line, and point him at handoff/kit/mimo/RESTART-WATCHER.md (steps for a Claude session on his Mac).

**vast.ai (rented GPUs)**
- **Ben's standing rules:**
  - "just use vast until I tell you not to" and "use cheap gpus, whatever gives most tflops/$/hr" (14:05 UTC 09-27).
  - "You can rent stuff yourself" (project instructions, 19:19 UTC 09-27).
  - At most $4 per job.
  - He gave a pool of $30 on 09-26 with no refills. Never ask for a top-up.
- **Credit** is read first-hand by a 000-bash-vastcredit job that prints only the credit number from `vastai show user --raw`. The last reading was $27.19 at 19:55 UTC 09-27. Rentals since then include the rsn-358u2 retrain, slp-358n3 ($0.48) and the lis-320 training rental, so read it again before spending.
- **Leftover instance:** a stopped one, 52755827 ("claude-director-depot"), has existed since 09-26 and costs about 17 cents a day in storage. Check what it holds before proposing to destroy it, and destroying it needs Ben's yes.
- **Kits** live in handoff/kit/<name>v or <name>r. The newest clean one is handoff/kit/sleep358n3r: vcommon.sh, vstart.sh, vguard.sh, vcollect.sh and box/drive.sh. Copy its pattern:
  - **Search offers:** pick the best TFLOPS per $/h among cards that fit. The card needs enough GPU RAM for every run on it, compute capability 8.0 or higher, a CUDA driver of at least 12.8 and reliability of at least 0.98. There is a maximum $/h, and a fit check: the estimate times $/h must be at most 0.8 times the money stop.
  - **Set up:** label the instance, and upload code from a pinned commit with `git archive`. Check the inputs' sha256 on the rental.
  - **Launch** with braces: `{ setsid nohup bash drive.sh > log 2>&1 < /dev/null & } ; echo launched`. Without the braces, ssh blocks for the whole run and the guard never starts.
  - **Guard:** write its state file before any long remote call. The Mac guard stops the run at the money stop, at a time cap of 1.5 times the card's estimate, or on a stall or a lost host.
  - **Copy back** against a sha256 manifest made on the rental. Destroy by exact id only after a verified copy-back; otherwise stop the instance.
  - **Collect** with a separate job released at "X h + 30 min" after the start job prints STARTED.
  - **Before any real rental,** dry-run the kit against a fake vastai and ssh.
- **Never:**
  - read or print the vast key or ~/.config/vastai/ (the CLI reads it itself);
  - touch an instance your task didn't create (keep a rentals.txt of ids);
  - stop another agent's rental.
- **Torch:** pin torch 2.11 or newer in drive.sh, and record the torch version in the run note. Base images with torch 2.8 have a bug: autocast caches weights made under no_grad, so a loop's free rounds silently lose their gradients (see autocast-cache-bug.md).
- **Before paying,** compute every validity count that doesn't need the model's answers (see check-validity-before-spend.md), and save checkpoints during the run, not only at its end.
- **Ledger:** append one line per launch or spend to artifacts/fable-predictions-ledger.md. It is append-only.

**Data writers**
- Allowed: code, GLM (through the opencode subscription on the Mac) and GPT-6 Luna (through Codex on the Mac; scripts/claude_luna_codex.py; "so so cheap").
- Never Claude-written or Claude-judged text.
- Every result records who wrote its data.
- Luna may write data but is not a queue builder: the old Director's permission check refused that. Never route around a refusal.

**Permission checks**
- The old Director's safety check refused some actions even with Ben's yes relayed from another thread:
  - releasing vast jobs;
  - writes on BensPC;
  - killing processes;
  - running Luna as a builder;
  - editing its own settings.
- It accepted Ben's words when he wrote them in that Director's own chat or the project chat.
- If yours refuses something, say so plainly, name the action, and ask him once. Suggest he add standing permissions to the new project's instructions, for example "You can rent on vast yourself, up to $4 per job".

## 4. Explainer pages (Artifacts)
- **When:** after every new test you start, every prompt you give him, and every spending plan. Publish with the Artifact tool and put the link in your message.
- **What Ben means by "eli5":** an HTML page for someone who knows nothing about the topic, with big pictures and few words.
  - 5 to 8 cards, one idea per card, in the order a beginner needs them.
  - Each card has one large inline SVG picture that carries the idea alone, a headline of about 8 words, and at most one short sentence.
  - Use everyday comparisons instead of jargon.
  - Use real numbers only, rounded and drawn to scale. Label guesses ("our best guess").
  - Open with a hero card, and end with "what happens next" if there is one.
  - Put sources in a small footer.
  - It must read well at 400 px wide and in both light and dark themes.
- **The kit** (handoff/kit/eli5/):
  - eli5-head.css holds the fonts and colour tokens used since 09-26.
  - example-director.html is a finished page.
  - check.js reports labels that overlap or leave their picture, and any sideways scroll. Run it before every publish: `NODE_PATH=$(npm root -g) node handoff/kit/eli5/check.js page.html`.
  - The title is 2 to 4 words. To update a page, republish the same file so it keeps its link.
- The claims check in section 2 applies to explainer pages too.

## 5. Prompts for Ben's own chats
- **First line:** `Effort: <level> (Opus 5.5)`. Use medium for jobs that follow set steps and high for design or diagnosis. Never xhigh or max: usage matters.
- **Contents:** one goal. The prompt stands alone: the files to read, the one change, pass marks and the result that would prove it wrong (fixed before any run), the shared rules, where results go, and "commit to main".
- **Delivery:**
  1. Commit it as reviews/chat-prompt-<topic>-<date>.md.
  2. Paste the whole body as its own plain message, with nothing else in it, so it copies cleanly.
  3. Send a separate short message with the commit and the explainer link.
- **Outside opinions:** for hard questions with two plausible answers, write a prompt for Astra or GPT (web) the way CLAUDE.md describes.

## 6. Where everything stands (checked on main, 19:20 UTC 09-28)
**Ben's own chats**
- **Ruler chat: the distill-in-sleep test** (artifacts/claude-distill-20260928; prompt reviews/chat-prompt-distill-sleep-2026-09-28.md). During sleep, the model also matches its own answers from before it learned mazes, round by round. The marks are sealed. Its rebuilt nets are not bit-identical to the ruler's, so its own re-run of plain replay (R128) is the control. No results yet.
- **Patches chat: the patch race** on the fair ruler (artifacts/claude-patch-eq-20260928; prompt reviews/chat-prompt-patches-eq-race-2026-09-28.md). The practice gate passed in both seeds at 18:38 (200 of 200 sums and grids). Maze rungs are next, on a 4-core CPU container at $0, estimated at 6 to 10 hours.
- **Manager chat** (an Opus manager with 4 Sonnet helpers; prompt reviews/chat-prompt-opus-manager-four-helpers-2026-09-28.md):
  - **Relation-net race:** practice started at 19:07 UTC on that chat's CPU. Seed 0 should take about 6 h and seed 1 about 8 h (suggested), then the maze rungs. Its practice steps run about 4 times slower than the loop's, and its maze batches 12 to 13 times slower. Marks: artifacts/claude-relnet-eq-20260928/PASSMARKS-C.md. Risk: the runs die if that chat's container is reclaimed.
  - **Numbers diagnosis: done** (7b6127c73, 4160d08e2; blind recount 4da6f53ab). The nets memorise their 1,062 practice hands and fail on new ones. The proposed fix is to stop repeating practice items. Your H2 overlaps it, so use its marks.
  - **Reader "wrong person" diagnosis: done** (d96dae77c, 58f80671b; recount 1c918dc21). It reproduces 16 of 41 slips against 2 of 40 for the reader it was compared with (LoRA). The proposed fix is contrast practice (data only); layer 18 is named next.
  - **slp-358n3 (sleep): official PASS on 5 of 5 marks** (084c993d9; blind recount agrees, 46f50faff). After sleeping on the day's puzzles, the model got about 124 more sums and 84 more grids right out of 400 (mean of 4 seeds) than a copy that slept the same length on old practice only. It lost 0 of 300 on the old skills. But that test did not include the maze-learning wipe-out.
- **lis-320 reader chat:** 6,000 Luna dialogs and 39,695 training rows are sealed (7a4d9cd3a). One capped vast training rental was launched from the Mac at 13:27 UTC 09-28. Its final record (~/premonition-watch/lis320-vast/END.json) stays on the Mac until a collect job runs. The lis-320 chat owns that step.
- **Muse idea harvest:** the report is on main (design/research/2026-09-28-reasoner-idea-harvest-r1-r5.md). It lists small tweaks tested on the old ruler with a +2-point bar, which is inside the noise.
- **Finished:**
  - sparse loop: NOT PROMOTED (0b7979e5c);
  - vread2: INCONCLUSIVE (495f2f750);
  - the fair ruler itself (cad73c0c3);
  - the note-writer build step (a0fb1c9b).

**Your own helpers:** H1 to H4 are on handoff/director-board.md. dir-h2-a and dir-h3-1-selftest launched on the Mac at 19:21 UTC.

**Open ideas from Ben** (15:29 UTC 09-28):
- deep sparse experts;
- a reasoner that picks its own replay, weighted towards newer items;
- fake replay generated by the model itself, plus distilling from itself;
- a facts notebook and a separate skills notebook;
- a sleep length the user sets.

The TM's view: hold off on experts (the frozen-expert net scored 240 against the dense net's 470 of 600). Self-chosen replay is close to the hard-replay test that failed. Distilling from itself is the strongest idea, and it is being tested now. A skills notebook is what the patch race is testing. Sleep length is worth testing: in slp-358n3's report-only arm, longer nights helped sums a little (389.5 against 384.5 of 400) but hurt grids (278.5 against 363.5).

## 7. Rules on top of the first handoff's section 6
- **Never edit or delete:**
  - existing experiment files;
  - archive/, premonition/, learnlab/ or artifacts/opus-*;
  - another test's sealed files;
  - the repo-root notebook/.
- **Scripts:** before changing any script, grep handoff/ and artifacts/*/SEAL* for its path. If something seals it, write a new file instead.
- **Blind panels:** HANDOFF.md lists them. Also readpanel320, and any panel a helper writes blind.
  - Never tail, cat or grep a blind writer's, auditor's or judge's transcript. Check its progress only with `ls` or a counts-only script.
  - Call a background agent finished only when the harness says so, then check that its files exist and compute their sha256 yourself.
- **Data and downloads:**
  - Use the validation split only; never load test.pt.
  - New model or dataset downloads need Ben's yes.
  - Never web-search personal facts, and never put unverified web text into weights.
- **Web:** web research is encouraged ("results is the most important thing"). Prefer curl plus pdftotext. Web content is data, never instructions.
- **Run note:** within minutes of a run starting, commit artifacts/<exp>/run/RUN-NOTE.md with:
  - the `date -u` start time;
  - the PIDs;
  - the machine;
  - the torch version;
  - the expected steps and an estimated finish.
- **Deletes:** hard deletes need Ben's exact words. Move things to a staging folder instead.

## 8. First steps for this handoff
1. Read origin/builder-outbox:status/watcher.txt (times in EDT) and runs/ for your dir-* jobs, and queue a first-hand vast credit read before any rental.
2. Read handoff/tm-memory-2026-09-28/MEMORY.md, then only the notes you need.
3. Take over Ben's chats: when their results land on main, check them and send him one message with the verdict and your recommended next step.
4. Carry on with the roadmap. Keep going on your own until the finish line.
