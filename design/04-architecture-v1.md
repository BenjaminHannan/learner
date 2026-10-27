# Step 4 — The architecture, version 1

> **Superseded in part (2026-09-18).** The core, library and learning rules below were replaced by the reasoner/store design in [06](06-premonition-mini-spec.md) and the decisions log ([research/2026-09-18-decisions-log.md](research/2026-09-18-decisions-log.md)). In particular §8 "Learning while awake" no longer holds: weights change only in sleep; cards change any time.


2026-09-18. This puts every agreed decision into one design: [01](01-learning-spec.md) (what "learning" means), [02](02-options.md) (researched options), [03](03-issues-and-decisions.md) (issues, decisions, measured speed). Every piece is a bet until its experiment passes against the simple baselines.

## One picture

```
 BensPC CPU (12 threads, 47 GB)           Mac (M1 Pro)
 ┌──────────────────────────────┐        ┌──────────────────────────┐
 │ VILLAGE WORLD (many at once) │◄───────│ TEACHER: Bonsai 27B      │
 │ grid underneath · narrator · │ phrase │ writes sentence patterns,│
 │ teacher · questions · checker│ banks, │ explanations, stories    │
 └──────────────┬───────────────┘ extras └──────────────────────────┘
                │ one text stream: [world] [teacher] [question] [feedback]
                ▼
 RTX 5070 Ti ───────────────────────────────────────────────────────────
 ┌────────────────────────────────────────────────────────────────────┐
 │ WORKING MEMORY = what the core can see right now:                  │
 │   recent stream  +  recalled episode cards  +  its own [think] notes│
 ├────────────────────────────────────────────────────────────────────┤
 │ CORE (small transformer, 4-28M weights): reads, predicts, thinks,  │
 │ answers, emits "done" when it judges more thinking won't help       │
 │    │ asks by similarity ("what do I know about Nera + where?")      │
 │    ▼                                                                 │
 │ LIBRARY, searched by attention / cosine similarity:                 │
 │   • knowledge slots: ~100M-weight table, learned slowly, only the   │
 │     few slots used get changed (sparse)                              │
 │   • episode cards: written instantly, one exposure, text + key +     │
 │     time + version history                                           │
 │ CHECKER head: "is this answer right, and how sure am I?"             │
 └────────────────────────────────────────────────────────────────────┘
        ▲ every few minutes, no new input
 ┌──────┴─────────────────────────────────────────────────────────────┐
 │ SLEEP: replay cards mixed with old material · teach knowledge slots │
 │ from cards · repair corrections · checked practice · reset dead     │
 │ units · test with card hidden → consolidated                        │
 └────────────────────────────────────────────────────────────────────┘
```

## The parts

### 1. World (village on a grid)
- Each village has a grid of places; people and objects with positions and properties; *universal rules* (moving, carrying, containers) and *per-village rules* (e.g. "glass breaks", "Tavi follows Nera 80% of the time").
- Fresh made-up names in every village, drawn from a syllable pool. Names are "bursty": a few common, most rare. Test villages draw from a separate name pool.
- The **narrator** turns events into sentences using pattern banks written by Bonsai and verified by rule (exact placeholders, no new facts).
- The **teacher** states facts, asks questions, corrects wrong answers, demonstrates made-up rules step by step, and changes facts over time (people move, rules flip) so corrections can be tested.
- The **checker** knows every true answer. Two leak detectors (a word-counter and a shuffled-lines model) run on every test set.
- It runs as many parallel simulator processes on BensPC and must produce about 1.2M tokens/s. Acting (move, pick up, open) is added later in the same world.

### 2. Tokenizer
A subword vocabulary of about 8,000 pieces, trained once on village text plus Bonsai-written simple English, so the language can widen later (#12) without changing it. Names are split into syllable pieces, so a new name is made of familiar pieces.

### 3. Core (the thinker)
A small decoder-only transformer. The default for experiments is ~4M weights; it scales to 12-28M once parts work. It sees a window of 512-1,024 tokens. It always predicts the next token of the stream, which is how it learns from raw observation.

### 4. Library (Ben's attention over knowledge)
One similarity search serves two kinds of slots.
- **Knowledge slots:** memory layers inside the core. Each is a large table (e.g. 262,144 slots). Each token's query picks its top ~32 slots by similarity, and only those are read or changed. Updates favour slots used much more by the new material than by older material, which the literature linked to far less forgetting. This is where slow, general, reusable knowledge lives.
- **Episode cards:** written instantly. Each card holds the episode's text, a **key** (a vector for what it is *about*, e.g. "Nera + where"), a time stamp, importance, source, and links to older versions. Recall is a cosine-similarity search of the current question's key against card keys; the best few cards are pasted into working memory as text.
- **Key rule:** similarity is on the key, not the whole sentence. Same key with a different value is a correction: store the new card and link the old one as history. A different key is a new card.
- The key encoder is part of the core and is trained so a question's key lands near the card that answers it.

### 5. Working memory and thinking
- Working memory = the recent stream + recalled cards + the model's own notes between `[think]` and `[/think]`. It is temporary and discarded after each task.
- **Stopping is the model's own decision:** it emits `done` when it judges the answer good enough. It learns when from its answer being scored at every thinking step (stop where more thinking stopped helping), later refined by reward. A hard cap exists only to prevent infinite loops.

### 6. Checker (checking its own work)
A small head trained on the world's right/wrong feedback about the model's own attempts. It outputs "right or wrong, and how sure". The model also learns checking habits from demonstrations: solve it another way, compare with memory, plug the answer back in. Unsure answers are routed to the teacher, and calibration is measured.

### 7. Gating (what to keep)
- Card write priority = importance × reliability. Importance comes from teacher flags ("remember"), surprise (how badly the core predicted it), reward relevance, and corrections. Reliability: teacher > world > own unchecked output.
- Unflagged items are still stored at low priority, so the model does not depend entirely on the teacher.
- The card store has a fixed budget. Eviction removes low-priority cards and cards already consolidated (history markers survive).
- Surprise also sets the replay order in sleep.

### 8. Learning while awake
- Every token: next-token prediction, with small updates to the core and sparse updates to the used knowledge slots (low step size).
- Teacher facts: an instant card write.
- Answers and feedback: correct answers reinforced; wrong ones pushed down and the correct answer trained; the checker trained on the outcome.
- Following a demonstrated rule: step-by-step imitation (copying), with a copy mechanism that moves names from the instruction into the notes.

### 9. Sleep (offline phase)
Triggered every few minutes of experience or when the card store fills. No new input. In order:
1. **Repair:** corrections first; train the new answer up and the old answer down, editing only the slots that key activates.
2. **Consolidate:** each card acts as a teacher. Generate questions about it, answer with the card visible, and train the model to answer the same with the card hidden, which moves the fact into knowledge slots.
3. **Rehearse:** mix in exact replays from the diary (a permanent text log of episodes), starting at 50% old material; Step 5's experiments tune the ratio.
4. **Practise:** world-generated problems with the checker as referee. Self-made problems count only if the checker is confident. Replay and practice have separate budgets.
5. **Maintain:** reset units that have stopped responding (continual backprop); log health gauges.
6. **Lesion test:** ask each card's question with the card hidden. If answered correctly, the card is marked consolidated and becomes evictable; its history is kept.

### 10. Health gauges (early warning for stiffness)
Dead-unit fraction, weight size, effective rank, and speed on a fresh mini-task versus a new network, logged continuously. A stress test (tasks changing every few thousand steps) runs in Step 2 to compare fixes in minutes.

## Life stages
1. **Childhood:** ordinary next-token training on village streams, plus key-encoder training, instruction imitation and checker training. Hours on the 5070 Ti.
2. **Life:** a continuous stream of villages with awake/sleep cycles and no separate "training" and "use" modes. A life is checkpointed (core, library, cards, diary, optimizer, world state) so it can pause and resume. The temporary working memory is never saved.
3. **Growing up (English track):** village language is widened with Bonsai stories and dialogues, then real child-level text (download confirmed with Ben first), then conversation practice with Bonsai.

## Test bench (read-only)
Tests never train the model: no weight updates and no card writes while testing, and answers are never in the model's input. Measures:

| Ability | Test |
|---|---|
| One-shot facts | recall right after, after delay, after sleep, with the card hidden |
| Corrections | newest answer given; old answer never relapses after more learning |
| Forgetting | old-village scores after new villages |
| Transfer | lessons needed to learn a new village's rules versus a fresh model; this must fall as experience grows |
| Skills | following made-up rules never seen demonstrated |
| Checking | checker calibration |
| Thinking | accuracy versus thinking steps; longer thinking on harder questions |
| Stiffness | health gauges and fresh-task speed |
| Honesty of results | two leak detectors; baselines: a plain network with the same compute and plain text lookup |

## Build order
| Step | Build | Passes when |
|---|---|---|
| 0 | Test bench | Metrics, read-only mode, leak detectors and baselines run on a toy stream |
| 1 | World v0, tokenizer, plain core (childhood) | Village questions answered ≥ 90% from visible text; name gap ≤ 3 points; leak detectors low; forgetting baseline recorded |
| 2 | Continual-training recipe + knowledge slots | The library forgets less than the plain core at the same compute, and the stress test keeps fresh-task speed ≥ 90% of a new network |
| 3 | Episode cards + key search | One-shot facts beat plain lookup when phrasing changes (rewordings, pronouns) |
| 4 | Gating | At a fixed card budget, beats random writes |
| 5 | Sleep | Facts survive with the card hidden; no relapse after corrections; old knowledge holds |
| 6 | Thinking + stop + checker | Beats no-thinking on multi-step questions; thinks longer on harder ones; checker calibrated |
| 7 | Instruction imitation, practice, reward, acting | Follows unseen rules; improves from feedback |
| 8 | A life (overnight) | Transfer improves with experience; health gauges stay healthy |

## What stays from the old project
The test discipline (fresh names, read-only evaluation, answers never in inputs, bit-exact checkpoint restart, W=0-style causal checks for every memory) and the BensPC tooling. The GRU and recurrent transformer stay in `memorylab/` as baselines. The old rule "reading memory never writes" becomes: a recall can *flag* a card for repair, but all changes happen through gating or sleep, and never during tests.
