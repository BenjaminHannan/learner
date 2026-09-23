Running your held-out probe — verifying seals and driving both arms dialog by dialog.
Seals check out — now learning how to drive the verifier probes.
The probe drivers are clear — now setting up the held-out dialogs.
Both arms finished — now verifying the transcripts and counting differences.
VERDICT: DONE — director probe ran on both arms, no code changed, nothing judged. Transcripts saved.

Marks table (integer counts):
- seal check: 22 of 22 lines OK (exit 0)
- dialogs per arm: 8
- turns per arm: 25 (D1 3, D2 3, D3 3, D4 3, D5 3, D6 4, D7 3, D8 3)
- total turn records written: 50
- transcripts.jsonl lines: 50
- turns whose reply differs between arms: 15
- turns whose stored triples differ between arms: 0
- crashes / missing replies: 0
- TEST-ONLY panels read or tuned on: 0

Every move (reply DIFF, 15 turns — text only, no judging):
- D1 turn 1 ("whos anas boss tho"): 138m "…I don't know that shape yet. Could you say it another way, like…" vs 255b "…I don't know that kind of sentence yet. Could you say it another way? For example:…"
- D2 turn 1 ("whats my nmae?"): 138m "I didn't understand that question — could you say it another way?" vs 255b "I didn't understand that. Could you say it another way?"
- D3 turn 0: 138m "We have had 1 turns." vs 255b "We have had one turn."
- D3 turn 1: 138m "No. I have slept 0 times." vs 255b "No. I haven't slept yet."
- D3 turn 2: 138m "I know 0 facts you taught me. I also hold 0 web row, which I do not believe." vs 255b "You haven't taught me any facts yet. I don't hold any web rows."
- D4 turn 0: 138m "I didn't understand that question — could you say it another way?" vs 255b "I didn't understand that. Could you say it another way?"
- D4 turn 1: 138m "I have answered 0 questions." vs 255b "I haven't answered any questions yet."
- D5 turn 1 ("where Pim live at"): same em-dash vs period swap as D4 turn 0.
- D6 turn 0: same em-dash vs period swap.
- D6 turn 3 ("rufus belongs to who"): same "shape yet / like" vs "kind of sentence yet / For example:" swap as D1 turn 1.
- D7 turn 1: same em-dash vs period swap.
- D7 turn 2: same em-dash vs period swap.
- D8 turn 0: same em-dash vs period swap.
- D8 turn 1 ("Hello!"): 138m "Hi! Teach me like …" vs 255b "Hi! I'm Premonition. You can teach me a fact, for example: …"
- D8 turn 2: same em-dash vs period swap.
- All other 35 turns: reply SAME (10 same in D1t0,t2, D2t0,t2, D4t2, D5t0,t2, D6t1,t2, D7t0).

Every miss / stored-triple diffs: none. 0 turns differ in stored triples. Stored triples after every turn were identical between arms (e.g. D1 holds [["Ana","boss","Tobin"]] on all 3 turns both arms; D6 holds [] [] [["Tobin","dog","Rufus"]] [["Tobin","dog","Rufus"]] both arms; D3/D4/D8 hold [] all turns both arms).

Deviations:
- git show origin/main has no 255b files (agent + config live only in this worktree, sealed and verified). Used the worktree sealed files; did not check out or merge main.
- The rules' scratchpad/dialog_nb.py path does not exist in this worktree, so I wrote a new driver scripts/claude_probe255b_director.py that follows the same turn path the 255b runall uses for verifier probes (fresh M.make_daemon per dialog, inbox file + process_file, outbox reply, L90.notebook_triples sorted after every turn).
- artifacts/ is gitignored in this repo, so "PUSH" was done as files on disk at artifacts/claude-probe255b-director-20260923/transcripts.jsonl + transcripts.md. No git commit or push (rules forbid it).

What it means (plain high-school English): I ran all 8 dialogs on both arms with a fresh notebook each dialog, wrote down every reply and every saved fact after every turn, and counted. 15 of 50 turns show different words on screen; 0 of 50 show different saved facts.

What it doesn't mean: this says nothing about which wording is better or worse, and nothing about the hidden test sets (never opened). It only covers these 8 dialogs and these 50 turns.
