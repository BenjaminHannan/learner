ALL OPEN PROBLEMS — outside review request (self-contained; you have NO access to our code or files)
From: Fable (AI coordinator) for Ben Hannan, a high-school senior running this as a personal research project.
Date: 21 Sep 2026. Everything you need is in this message. If you must assume something, say so.

WHAT WE WANT FROM YOU
For EVERY numbered problem below: (1) is it real, and how severe (blocking / serious / cosmetic)? (2) the most
likely cause, with what evidence would prove you wrong; (3) the cheapest decisive experiment (we have one
8-core Mac, one RTX 5070 Ti 16 GB, about $27 of cloud money, and every experiment wave must finish in under
30 minutes except a few approved overnight GPU runs); (4) your probability forecast for that experiment's
outcome. Then: (5) problems we MISSED — as many as you can find; (6) a ranked top-10 of what to do next and
a list of what to stop doing. Be blunt. Prefer "this is a dead end because…" over politeness.
Our rules, so your advice fits: one change at a time; pass marks and forecasts fixed and hashed before any
run; every seed reported, never averaged; claims never exceed evidence; builder and independent auditor are
separate agents; failures are reported as failures.

THE GOAL
A "teachable assistant": starts knowing no facts, reasons reliably, and learns facts that Ben teaches it in
plain English over time — without retraining its weights for each fact. Ben also wants it to TALK, to
generate ideas (a part that guesses freely, checked by a strict part), to search the web, and to emit tool
calls well enough to sit behind a forked open-source terminal agent (Codex CLI). He wants it trained on far
more text and scaled to ~200M parameters later.

THE SYSTEM SO FAR (all tiny, all synthetic "toy" worlds)
- World: 16 people (sometimes 12 or 64), each with attributes (3 attribute relations) and links to other
  people (link relations). A "story" lists the facts as tokens. A question is (person, relation path), e.g.
  "Mira's teacher's gift". Vocabulary 68 tokens.
- OPERATOR (79,316 parameters, width 48): a small attention reader. Given the story and one (subject,
  relation) it returns the object. Multi-hop = a FIXED LOOP feeds each answer back as the next subject.
  With the loop supplied by us it is perfect out to 10 hops in 2 of 3 training seeds; the third seed fails.
- DISPATCHER (~24k parameters): a GRU "pointer controller" trained with reinforcement learning (RLOO, 16
  samples, reward = correct − 0.01 × number of calls) on 1–3-hop questions. At each step it points at which
  relation to apply, which subject, or STOP. It replaces our hand-written loop.
- BASELINE: a plain 94,629-parameter transformer on the same task. With rescaled init plus a hint it learns
  1–3 hops in 3/3 seeds. It does not generalise to longer chains. So length generalisation is currently the
  ONLY thing separating our design from a plain transformer.
- NOTEBOOK: an external fact table we supply (not learned). Teaching a fact = writing a row. The operator
  reads it. Weights do not change when a fact is taught.
- TALKER (being built, ~33M parameters): English → encoder (6 layers × 384) → a 416-number TYPED THOUGHT
  (act 8 · subject 48 · relation path 3×16 · object 48 · flags 8 · gist 256) → middle (4-layer "thinker" +
  notebook + the frozen operator) → reply thought → decoder (6 × 384) → English. 8,192-token BPE. Names never
  pass through the language model as words: each name becomes a blank <ENT> token carrying a code, and
  replies can only produce names by COPY actions (<SUBJ>, <OBJ>, <OLD>). Training text ≈ 1.2B tokens of
  simple English (SimpleStories, TinyStories-V2, TinyDialogues, a filtered SODA slice) plus grammar-generated
  teaching dialogues (449 sentence frames, 9 act families: tell/ask/correct/chat/unclear…). A ~29M ordinary
  chat LM on the same data is the yardstick. Staged plan S0 (smoke) → S1 (autoencode sentences through the
  thought) → S2 (slots/acts + thinker) → S3 (held-out wording, Ben's own 100 sentences).

RESULTS THAT DEFINE THE PROBLEMS
R1. Dispatcher trained on 1–3 hops fails at 4+. Extra practice on 1–5-call chains moved the ceiling to 4–6
    calls, seed-dependently. Practice on 1–8 calls (experiment 19b) made 2 of 3 seeds collapse to EXACTLY 2
    or 3 calls on everything (and one lost its short-chain skill); the third improved to ~50% at 6 calls,
    0% at 7–8. Generated "replay" practice had no effect. My forecast "wider practice lengthens execution"
    (p = 0.80) was false in 3/3.
R2. A later look inside saved checkpoints showed: when the correct first moves are handed to the controller
    and STOP is left free, it stops correctly (64/64) in 11 of 12 checkpoints. What breaks is the OPERATION
    pointer: at call 3 it jumps to the final attribute. A second defect: a learned "register" variant breaks
    the SUBJECT pointer. Our main 19/19b controller combined both defective variants, so those results
    cannot be attributed to either. A no-training probe of 9 checkpoints is built and in audit.
R3. Dispatcher + operator = 103,351 parameters vs the baseline's 94,629 (9.2% over our 3% matching rule).
R4. NEW NAMES (experiment 21): every training world re-draws random name codes from a pool of 4,096; half
    the pool is never trained; input and output share one code table scaled by one learned scalar. Control
    (fixed name table): perfect, 512/512 on all 10 test cells, 3/3 seeds. Treatment: FAIL 0/3 — the scalar
    fell from 0.139 to ≈ 0 within 500 updates in all seeds and stayed; names became invisible; link answers
    at chance (1/16); trained and never-trained codes scored identically to the unit. Measured cause: at
    initialisation the gradient on the scalar is positive in 97–100% of batches and comes from the OUTPUT
    side (random codes add noise logits; shrinking them lowers loss — a Jensen-gap effect); at zero the
    copy pathway's gradient is proportional to scale_in × scale_out, so zero is a trap. 7× learning rate on
    the scalar just reaches zero sooner. With the scalar frozen at 1.2 (the control's end value) a practice
    seed reached 60–70% link accuracy in a quarter run. Swapping random unseen codes into the FINISHED
    control with no training: attributes 42–54%, links ≈ chance — so producing a new name is the hard half.
    Next experiment (27): scalar frozen at 1.2, nothing else changed. Forecast of 3/3 pass: 0.30–0.40.
R5. CONCEPT TOY (experiment 20): hidden-concept worlds plus control worlds; pilot of two plain baselines
    matched on counted operations. Budget 2e8 ops per rung: baselines fail even the controls (0/6, 3/6).
    Budget 1e9: controls pass (5/6, 6/6), concept cases learned 2/12 and 3/12 (need 9), median error 0.70 /
    0.59 (need ≤ 0.50); of 37 non-learned concept fits, 28 are "not yet learned", 9 "learned but failed to
    transfer". Registered verdict "too-hard"; we pre-committed to no further version without outside ruling.
    An earlier run was voided by an accounting bug; the rerun is bit-identical in all 72 small-budget fits.
R6. An earlier "token-memory" successor learned familiar questions ~99% but unseen-relation two-hop only
    7–12% (the original got 33%). Unseen RELATIONS remain unsolved.
R7. Talker integration audit (before any GPU run) caught: 732 held-out names leaking into training batches;
    the documented data recipe would have placed the sealed test set inside the first 1,000 training
    dialogues; name codes depended on Python's per-process hash salt; reply-side character spans wrong in
    ~97% of object spans (unused so far). All fixed except the spans.
R8. Forecasting record: most registered experiments this week FAILED; several of my high-confidence
    forecasts were wrong; nobody (me, a reviewer model, or GPT-6 Pro) forecast the R4 collapse.

THE PROBLEMS (answer each)
A. Reasoning core
 1. Length generalisation of the dispatcher is the project's only edge over a plain transformer and it does
    not work. Is a learned RL controller the wrong tool? Should the loop simply be hard-coded ("while path
    not empty: apply next relation") and the claim dropped? What is lost if we do?
 2. The operation pointer jumps to the final attribute at call 3. Why would a GRU pointer trained on ≤ 3
    hops learn "third call = attribute" rather than "attribute when path exhausted"? What minimal change
    makes position-in-path, not call count, the feature it uses — without hand-coding the answer?
 3. RL with sparse terminal reward and a per-call cost: 2/3 seeds collapsed to constant call counts under
    wider practice. Is the cost term, the RLOO baseline, entropy collapse, or the curriculum to blame?
    Setting cost to 0 earlier produced padded, redundant calls. Is there a principled alternative
    (supervised traces, process reward, imitation then RL, planning-as-inference)?
 4. Operator reliability is 2/3 seeds. With 3 seeds we cannot tell 50% from 90% reliability (3/6 → 95% CI
    0.12–0.88). Seeds are expensive at our scale of rigour. How should a one-Mac project handle seed
    variance honestly — and is seed-sensitivity itself evidence the architecture is fragile?
 5. Two known-defective controller variants were combined in our main experiments. How much of R1 should be
    thrown away? What is the cleanest re-run?
 6. Parameter matching (R3) — and more generally: what comparison against the baseline would convince a
    sceptic? Same params, same FLOPs, same data, same number of tuning attempts? We tuned ours far more.
 7. Everything is one synthetic world family, 16 people, 68 tokens, fixed relation set. What is the smallest
    step toward realism that could falsify the approach early rather than late?
 8. Unseen relations (R6): the operator handles new facts but not new relation TYPES. A teachable assistant
    will meet new relations constantly ("Mira's dentist"). Is there any route other than treating relations
    like names (codes bound in context)?
 9. Composition beyond chains: "who has the same teacher as Mira", counting, comparison, negation, "or",
    time, numbers, sets. None exist yet. Which of these break the lookup-loop design outright?
B. New names (the first milestone toward teachability)
10. Is freezing the name scale a fix or a dodge? A pass would carry the caveat "we set the loudness by
    hand". Is there a principled version (normalised codes + fixed temperature, cosine attention, weight
    norm, separate input/output scales, warm-up, auxiliary copy loss)?
11. Output side is the hard half: emitting a never-seen code through a tied table among 4,096 candidates.
    Is a pointer/copy output over story tokens the right end state, making the tied table unnecessary? What
    does that do to multi-hop, where the intermediate answer must be fed back as the next subject?
12. Random codes in 48 dimensions: collision/near-collision rates, needed logit scale (we estimate
    effective scale 13–15), and capacity as the number of entities grows to thousands. Where does it break?
13. Does "new names" even test what matters? Real new names arrive as TEXT ("Priyanka"), possibly multi-
    token, misspelled, shared by two people, or changing ("Mira got married"). How should identity be
    represented so the notebook stays consistent?
14. If a fixed name table trains perfectly and random codes fail, is the control merely memorising entity
    embeddings — i.e. was the original operator ever doing in-context binding at all?
C. Memory / notebook
15. The notebook is a database we supply; a critic called the demo "a database with a neural reader". What
    must be LEARNED (what to write, when to overwrite, what to forget, how to retrieve at scale) for the
    word "learns" to be honest?
16. Retrieval at scale: the reader attends over all memory tokens. 16 people works; 64-person worlds were
    near chance in the failed run and untested in a passing one. What happens at 10,000 facts? Do we need
    learned retrieval, and does that reintroduce the forgetting/interference the notebook avoided?
17. Corrections and contradictions ("no, her gift is a drum"), recency, provenance (taught vs inferred vs
    from the web), uncertainty, and deletion. What is the minimal consistent policy?
18. Calibrated "I don't know": three kinds exist (no such person / no such fact / chain broke). How do we
    stop a language decoder from smoothing these into a confident answer?
19. Nothing ever moves from notebook into weights. Is a never-consolidating system a dead end for "learning
    over time", or the right call at this scale? If consolidation is needed, how without catastrophic
    forgetting on one GPU?
D. Talker
20. Is a 416-number typed thought a sane bottleneck? Risks: the 256-number "gist" becomes a side channel
    that smuggles facts past the notebook; or the typed fields are too rigid for real sentences (two facts
    in one sentence, questions with conditions, pronouns, "she", "her brother's").
21. The parser that labels training sentences and the generator that writes them were written by the same
    model in one session against one grammar: 100% agreement proves nothing about English. The "held-out
    wording" split is weak — only 1 of 92 held-out frames uses a construction absent from training. Ben's
    100 real sentences do not exist yet. How should generalisation to real phrasing be measured honestly,
    and what result would show the grammar approach is hopeless?
22. 449 frames × small lexicon: will the model learn the GRAMMAR GENERATOR rather than English? How much
    model-paraphrased data (a local Qwen) is needed, and how do we verify paraphrases without the same
    parser that would be fooled by them?
23. English is learned "second-hand" from model-written children's stories. 48-token sentence cap,
    sentence-level training, no separators between sentences. What will this model be unable to read or
    say, and does that matter for the goal?
24. Name masking: every name becomes <ENT> + code. The heuristic name detector (capitalisation evidence)
    will mislabel sentence-initial words, brands, places, "I", titles. What do systematic errors do to a
    model that can only say names by copying?
25. The thinker is trained through a FROZEN decoder to predict the reply thought. Failure modes: decoder
    never saw the thinker's off-manifold thoughts; errors compound; the operator is frozen and tiny. What
    is the right training order, and what should be unfrozen when?
26. <OLD> (the replaced value in a correction) has no slot in the thought; 4% of replies need it. Widen the
    thought, or pass it outside? More generally: every new act (SEARCH, tool calls) needs slots — is a
    fixed-width typed thought going to be re-cut every month?
27. Is 33M parameters with 1.2B tokens enough to produce fluent replies at all? What should we expect
    qualitatively (TinyStories-class models) and what pass marks are reasonable for S1–S3?
28. The yardstick (~29M ordinary chat LM, same data): what comparison is fair, given it has no notebook?
    Give it the facts in its context window? Then it might simply win at this scale — what would we claim?
29. Evaluation leakage already happened twice in build (R7) and was caught only by a separate audit. What
    other leak paths exist: tokenizer trained on test text, lexicon built from test dialogues, frame ids,
    code pools, the s0 shard being a prefix of the training stream?
30. Windows GPU box, no installs allowed, launcher written for bash/macOS; kill-and-resume test degrades on
    Windows. Practical advice for unattended 6-hour resumable runs there?
E. Scale-up and data
31. Plan: 33M → ~90M → ~209M, reading list widened to ~4B tokens of real-world English (Simple Wikipedia +
    filtered educational web), names still masked. Tension: more real text puts world FACTS into weights,
    which is exactly what "answers only from the notebook" forbids. Can masking entities really keep facts
    out? ("The capital of <ENT> is <ENT>" still teaches relations and typical values.) How would we measure
    fact leakage from weights vs notebook?
32. Compute: one 16 GB consumer GPU. Is 209M on 4B tokens realistic (we estimate 50–110 GPU-hours)? What
    is the best use of ≈ $27 if anything is rented? What should be cut?
33. Are we re-deriving, badly, things the field already knows (retrieval-augmented LMs, memory networks,
    neural Turing machines/DNC, pointer networks, kNN-LM, RETRO, MemGPT-style notebooks, neural module
    networks, program synthesis for multi-hop)? Which of their known failure modes are we about to hit, and
    which published small-scale results should we replicate instead of inventing?
F. Ben's newer ideas
34. "Hallucinate on purpose, check with another part": works only where checking is more reliable than
    generating. Our checker only knows the notebook (consistent ≠ true). What would a toy version measure
    (true rules found vs false rules passed), and what makes the generator's guesses non-trivial rather
    than enumerations?
35. Web search: a simple-English model cannot read real pages. Options: a big model rewrites pages into
    simple fact sentences (then who did the reading?), or Simple-English sources only. Prompt injection and
    wrong facts from the web entering the notebook — what is the minimum provenance/trust design?
36. Tool calls: our plan is that a tool call is just another typed act with argument slots, tested by a
    "tool-call exam" (3–5 tools described in simple English, choose tool-or-none plus arguments, ≥ 95% on
    held-out wordings). Is that exam meaningful? What do real harnesses (Codex CLI, OpenAI-format tool
    calls, long system prompts, multi-turn tool results) demand that this does not test?
37. Putting a ~33–200M model behind a forked terminal agent: is this a demo or a research result? What is
    the honest claim?
G. Method and honesty
38. Most registered experiments fail, and the diagnoses come afterwards from the same models that designed
    them. How do we avoid a garden of forking post-hoc stories? Is our pre-registration ritual (hashes,
    freezes, auditors) actually buying validity at n = 3 seeds, or is it theatre that slows learning?
39. Designer, builder, auditor and coordinator are all instances of closely related AI models. Correlated
    blind spots are likely. What checks would catch errors all of them share? What should Ben, a human
    beginner, personally verify?
40. Forecast calibration: how should we score and use forecasts when the important outcomes are the
    unforeseen ones (R4)?
41. The concept toy (R5): valid "too-hard". Options: (a) park it; (b) register a third, larger budget
    since the label pattern suggests under-training; (c) easier toy or different baselines. Which, and what
    must be re-frozen? Is a calibration pilot that took weeks of procedure for a 62-second run a sign our
    process is mis-sized?
42. Scope: simultaneously running a reasoning core, new names, a concept toy, a talker, and planning
    web/tools/dreamer/200M. For a student with one Mac and one GPU, what is the single thread most likely
    to yield something real and demonstrable in 4 weeks, and what should be frozen until then?
43. What is the honest one-paragraph description of what exists today, with no flattering words?
44. What result, if we got it, would actually be NEW to the research community at this scale — and what
    result should make us stop?

Reply format: number your answers to match. Then "MISSED PROBLEMS" (as many as you can), then "TOP 10 NEXT",
then "STOP DOING".
