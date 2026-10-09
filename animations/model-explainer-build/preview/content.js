window.CONTENT = {
  "global": {
    "cardSeconds": 5,
    "endCard": {
      "duration": 10,
      "title": "That is the whole machine",
      "blurb": "Reader, thinker, calculator, stop switch, talker: what each part does, how it learns, how we test it, and what is still not proven."
    }
  },
  "order": [
    "ch01",
    "ch03",
    "ch04",
    "ch05",
    "ch06",
    "ch09"
  ],
  "chapters": {
    "ch01": {
      "kicker": "Part 1 of 14",
      "title": "One question, start to finish",
      "blurb": "We follow one made-up question through every part of the model, step by step. Plain words first. Real numbers only where a source gives them.",
      "accent": "thinker",
      "scenes": [
        {
          "id": "s01",
          "duration": 22,
          "heading": "Where we are: five parts",
          "caption": [
            "This chapter follows one question through the whole model.",
            "The model has five parts: reader, thinker, calculator, stop switch and talker.",
            "None of these parts has been tested all together yet."
          ],
          "chip": "never tested all together",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 (lines 15-20)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 6 (lines 123-124)"
          ],
          "notes": "Map drawn by S.modelMap with all five parts; the map labels are drawn by the kit, not in this file."
        },
        {
          "id": "s02",
          "duration": 26,
          "heading": "The question we will follow",
          "caption": [
            "Here is the question. We made it up as an example.",
            "The model works on letters, so every letter gets its own box.",
            "The question has 71 characters, spaces included."
          ],
          "question_a": "Tom has 12 apples. He gives away 5,",
          "question_b": "then buys 3. How many does he have?",
          "tag": "made-up example",
          "chars_note": "71 characters, spaces included (our count).",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (line 42, question text)",
            "animations/storyboards-2026-10-09.md idea 1 (line 53: example is made up)"
          ],
          "notes": "Two letter rows: row A is characters 0-34, row B is characters 36-70. The space at the break is not drawn."
        },
        {
          "id": "s03",
          "duration": 30,
          "heading": "Step 1: the reader reads once",
          "question_a": "Tom has 12 apples. He gives away 5,",
          "caption": [
            "A borrowed reader reads the whole question once. Its name is EmbeddingGemma 2.",
            "Frozen means our practice never changes it.",
            "Each letter gets a list of 768 numbers from the reader.",
            "The reader has 271,002,624 numbers. We did not set them."
          ],
          "reader_numbers": 271002624,
          "labels": [
            "Reader",
            "borrowed, frozen",
            "768 numbers per letter",
            "numbers we did not set"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 reader row (line 31: 768 numbers, 271,002,624, borrowed frozen)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 1 (lines 43-45)"
          ],
          "notes": "Shading in the vector strips is decoration only. The chunk grouping is not drawn: we did not show the real tokenisation."
        },
        {
          "id": "s04",
          "duration": 24,
          "heading": "The letter window sees neighbours",
          "question_a": "Tom has 12 apples. He gives away 5,",
          "caption": [
            "A small learned window lets each letter see 4 letters on each side.",
            "It is ours, learned from scratch in our practice.",
            "Every reader tested without it lost the letter puzzles."
          ],
          "labels": [
            "centre letter",
            "4 letters each side"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 letter window row (line 33: 4 letters each side)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 7 Q3 (lines 177-178: kept; cipher_map 100% down to 2.5-10%)"
          ],
          "notes": "The 4-letter window is the stated design. The cipher numbers are from sec. 7 Q3, which cites RESULTS-EG2."
        },
        {
          "id": "s05",
          "duration": 24,
          "heading": "Zoom out: what one round is",
          "caption": [
            "The thinker is the part that loops. One lap around the question is one round.",
            "In each round it looks at the whole question, passes notes, and thinks.",
            "The same weights run every round. Only its notes change."
          ],
          "labels": [
            "Look",
            "Pass notes",
            "Think"
          ],
          "chips": [
            "learned"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 (lines 16-18)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 thinker row (line 34: same weights every round)"
          ],
          "notes": "The loop is a picture of the design. Round counter is driven by the scene timeline."
        },
        {
          "id": "s06",
          "duration": 24,
          "heading": "Round 1: look, and no call yet",
          "question_a": "Tom has 12 apples. He gives away 5,",
          "caption": [
            "In round 1 the thinker looks at every letter and passes notes.",
            "Nothing is calculated yet, so the call slot stays empty.",
            "In the tested model, the first call comes after round 2."
          ],
          "labels": [
            "Round 1",
            "Thinker",
            "Call slot: empty"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 2 (lines 46-47: no call after round 1)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 60-61: first call follows round 2 in T1SDR and H1)"
          ],
          "notes": "Tested model here means T1SDR, which was tested. H1 has the same timing on paper but has not been run."
        },
        {
          "id": "s07",
          "duration": 26,
          "heading": "Round 2: the call writer picks",
          "caption": [
            "After round 2 the call writer reads the thinker's first control vector.",
            "It picks one of 8 operations, or writes no call. No call is a choice.",
            "The 8 are add, sub, mul, div, mod, min, max and cmp."
          ],
          "ops": [
            "add",
            "sub",
            "mul",
            "div",
            "mod",
            "min",
            "max",
            "cmp"
          ],
          "labels": [
            "no call",
            "not an op"
          ],
          "chips": [
            "tested"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 call writer row (line 35)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 calculator row (line 37: 8 operations)"
          ],
          "notes": "The call writer shown is the tested T1SDR one. Group 2 later writes the whole call as letters."
        },
        {
          "id": "s08",
          "duration": 31,
          "heading": "Copying 12 and 5 from the question",
          "question_a": "Tom has 12 apples. He gives away 5,",
          "caption": [
            "The numbers are copied, not typed. A learned pointer finds the last digit of each number.",
            "The code copies one letter at a time to the left, until a learned stop head says stop.",
            "Some steps are still hand-written code, such as the flip."
          ],
          "call": "sub 12 5",
          "labels": [
            "pointer: learned",
            "stop head: learned",
            "flip: hand-written"
          ],
          "chips": [
            "learned",
            "hand"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 2 (lines 48-50: pointer, copy, stop head)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 table (lines 96-98: span copy, last letter first)"
          ],
          "notes": "Letter indexes for the question row A: '1' of 12 is index 8, '2' is index 9, '5' is index 33. The copy goes from 9 back to 8, then stops at the space at index 7."
        },
        {
          "id": "s09",
          "duration": 25,
          "heading": "Why use a calculator at all",
          "caption": [
            "The calculator is an ordinary program. It is outside the model.",
            "The model writes its request as text, and gets the answer back as text.",
            "With the calculator switched off, program questions scored 0.0 points out of 100."
          ],
          "request": "sub 12 5",
          "zero_score": 0,
          "labels": [
            "Calculator",
            "points out of 100"
          ],
          "chips": [
            "hand"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 1 (lines 106-107: program questions score 0.0 with calculator off; MARKS-D0-T1 Record 13)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (line 76: calculator allowed as a tool)"
          ],
          "notes": "The reason 'exact sums are easy for code and hard to learn' is our reasoning (suggested), not a measured result. It is not shown on screen as a fact."
        },
        {
          "id": "s10",
          "duration": 26,
          "heading": "The calculator replies: 12 minus 5 is 7",
          "caption": [
            "The calculator gets sub 12 5 and sends back 7, as plain text.",
            "The reply is read by the letter window only.",
            "The question is not read again. The reply goes into the notes."
          ],
          "request": "sub 12 5",
          "reply": "sub 12 5 = 7",
          "labels": [
            "Calculator",
            "Thinker's notes"
          ],
          "chips": [
            "hand"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 3 (lines 51-52)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 5 (lines 120-122: replies read by the letter window only)"
          ],
          "notes": "The calculator and the Gemma reader have never run together. This picture combines them; see the legend scene."
        },
        {
          "id": "s11",
          "duration": 31,
          "heading": "Round 3: a second call",
          "question_b": "then buys 3. How many does he have?",
          "caption": [
            "Round 3 now also sees sub 12 5 = 7.",
            "The call writer writes add 7 3: the 7 from the reply, the 3 from the question.",
            "The calculator returns 10, and add 7 3 = 10 joins the notes."
          ],
          "call2": "add 7 3",
          "reply2": "add 7 3 = 10",
          "reply1": "sub 12 5 = 7",
          "labels": [
            "Round 3",
            "reply: 10",
            "notes"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 4 (line 53)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 call writer row (line 35: numbers copied from the question or an earlier reply)"
          ],
          "notes": "Index of '7' in the reply line 'sub 12 5 = 7' is 11. Index of '3' in question row B is 10."
        },
        {
          "id": "s12",
          "duration": 29,
          "heading": "Later rounds: calls and pauses",
          "caption": [
            "Some rounds have nothing to calculate, so they write no call.",
            "In the tested model, calls come after rounds 2 to 8 only.",
            "The newest version can call in any round from 2 to 32. Built, not tested."
          ],
          "call1": "sub 12 5",
          "call2": "add 7 3",
          "labels": [
            "picture only",
            "empty box = no call",
            "rounds not recorded",
            "rounds 9 to 32: no call"
          ],
          "chips": [
            "untested"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 54-56: rounds with no call)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 60-65: call timing; B3 any round built, untested)",
            "animations/storyboards-2026-10-09.md idea 1 (line 54: rounds 3 and 4 are an illustration)"
          ],
          "notes": "How many rounds this question uses is not recorded in any file. Rounds shown after 3 are a picture only."
        },
        {
          "id": "s13",
          "duration": 26,
          "heading": "The stop switch: done or not",
          "caption": [
            "After each round a small learned switch asks: is it done yet?",
            "It must run at least 1 round, and at most 32. The 32 is a safety limit.",
            "One stop covers the whole answer. It is built, but never tested yet."
          ],
          "labels": [
            "min 1",
            "max 32",
            "done?",
            "illustration"
          ],
          "chips": [
            "learned",
            "untested"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 stop row (line 36: at least 1 round, at most 32; built, never run)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 5 and lines 66-67 (one stop for the whole answer)"
          ],
          "notes": "The switch turning on at round 4 is an illustration. No file records a stop round for this question."
        },
        {
          "id": "s14",
          "duration": 25,
          "heading": "The talker writes the answer",
          "caption": [
            "The talker copies 10 from the last reply, where the thinker points.",
            "It adds no thinking of its own, so the answer is just the copied 10.",
            "Today's talker is a stand-in. The English talker, about 25M numbers, is planned."
          ],
          "answer": "10",
          "last_reply": "add 7 3 = 10",
          "labels": [
            "Talker",
            "English talker: planned"
          ],
          "chips": [
            "placeholder"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 6 (line 57)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 talker row (line 38: about 25M planned; small stand-in today)"
          ],
          "notes": "The answer 10 is the made-up example's answer. It is not a test result."
        },
        {
          "id": "s15",
          "duration": 28,
          "heading": "What is tested",
          "caption": [
            "Green: the Gemma reader, tested once at the 3M size.",
            "Green: the calculator helper matched the old model over 6 copies.",
            "Amber: calls in any round, stop switch. Built, never tested.",
            "Grey: the English talker. A placeholder, not built yet.",
            "Open question: a few answers use zero thinking rounds."
          ],
          "labels": [
            "never tested all together"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 2 (lines 109-110: one seed, seed 400, 3M)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 1 (lines 106-108: T1SDR matched B2 over 6 seeds)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 2 (lines 111-112: zero-round answers, cause not settled)",
            "animations/storyboards-2026-10-09.md idea 1 (line 64: legend wording)"
          ],
          "notes": "The earlier 6-copy Gemma test (EGE) missed its zero-round check (sec. 2 line 31). This scene does not claim it passed. 'Copies' means seeds."
        },
        {
          "id": "s16",
          "duration": 22,
          "heading": "Recap: three things to remember",
          "caption": [
            "The reader reads once. The thinker thinks in rounds. The calculator does the sums.",
            "The stop switch says when done. The talker writes the answer.",
            "Now we open each box, one at a time."
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 (lines 15-20)",
            "animations/storyboards-2026-10-09.md idea 1 (line 64: legend)"
          ],
          "notes": "Still final picture: the full five-part map with all parts lit."
        }
      ]
    },
    "ch03": {
      "kicker": "Part 3 of 14",
      "title": "The reader: giving every letter a meaning",
      "blurb": "The reader is a borrowed part. It reads the question once and gives every letter a meaning in context.",
      "accent": "reader",
      "scenes": [
        {
          "id": "s01",
          "duration": 24,
          "heading": "Where we are: the reader comes first",
          "caption": [
            "The question enters the reader first. It reads the whole question one time.",
            "Picture only: a translator who already knows English well. We borrowed him, and we cannot change him."
          ],
          "illustration": "picture only",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 and sec. 2 (Reader row)",
            "kit GLOSSARY.md (shared translator picture)"
          ],
          "notes": "Map is S.modelMap with highlight reader. Order of the five parts follows GLOSSARY.md."
        },
        {
          "id": "s02",
          "duration": 26,
          "heading": "Letters versus word pieces",
          "caption": [
            "Gemma cuts text into word pieces, called tokens.",
            "Our thinker works on letters, one spot for each letter."
          ],
          "example": "Tom has 12 apples.",
          "illustration": "made-up example: where the cuts fall is a picture only, not Gemma's real cut",
          "src": [
            "architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 1 (why, in plain words)"
          ],
          "notes": "Only the sentence is real. The token boxes are drawn by hand and are labelled as a made-up example."
        },
        {
          "id": "s03",
          "duration": 24,
          "heading": "Measured: about 3 letters per token",
          "caption": [
            "On our skill questions, one token covers 3.08 letters.",
            "On web text in 279-letter chunks, one token covers 4.27 letters."
          ],
          "labels": {
            "skills": "skill questions",
            "web": "web text, 279-letter chunks"
          },
          "numbers": {
            "skills": 3.08,
            "web": 4.27
          },
          "chip": "tested",
          "chip_label": "measured by count",
          "src": [
            "architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 2 table, rows 1 and 2 (my count 10-09, Gemma tokenizer.json at 914f7f89)"
          ],
          "notes": "A ratio (letters per token), not a score out of 100. The sec. 1 text rounds these to 3.1 and 4.3; the table values 3.08 and 4.27 are shown (table used)."
        },
        {
          "id": "s04",
          "duration": 26,
          "heading": "The reader reads once, then copies meaning",
          "caption": [
            {
              "at": 0.05,
              "text": "Gemma reads the whole question one time."
            },
            {
              "at": 0.4,
              "text": "Each token gets a row of 768 numbers that holds its meaning in context."
            },
            {
              "at": 0.7,
              "text": "Each letter takes the row of the token it sits in."
            }
          ],
          "labels": {
            "token": "one token",
            "row": "768 numbers",
            "letter": "one letter"
          },
          "illustration": "shaded cells are decoration; only the 768 count is a fact",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Reader row, line 31)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 1"
          ],
          "notes": "768 is Gemma's width. Older page architecture/model-deep-dive.html line 69 says 256 numbers per letter; that is the earlier design and is not shown."
        },
        {
          "id": "s05",
          "duration": 27,
          "heading": "The borrowed reader: 271,002,624 numbers",
          "caption": [
            "The reader holds 271,002,624 numbers, all set before our work began.",
            "134,217,728 of them are a word table; 136,784,896 are a transformer with its projection.",
            "It is frozen: our practice never changes it. Its own reading limit is 8,192 tokens, which is not our limit."
          ],
          "labels": {
            "table": "word table 134,217,728",
            "tf": "transformer 136,784,896",
            "frozen": "borrowed, frozen"
          },
          "src": [
            "custom-io/models/eg.py line 6 (text backbone 271,002,624 = 134,217,728 word table + 136,784,896 transformer and its 512 to 768 projection)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Reader row)",
            "architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 2 (8,192-token model card)"
          ],
          "notes": "Sum checked by hand: 134,217,728 + 136,784,896 = 271,002,624. Borrowed and frozen is shown as a teal text label, not a status chip."
        },
        {
          "id": "s06",
          "duration": 21,
          "heading": "The converter plug: 768 numbers in",
          "caption": [
            "One linear layer changes Gemma's 768 numbers into the thinker's width.",
            "At width 256 it has 196,864 learned numbers; at width 512 it has 393,728."
          ],
          "labels": {
            "in": "768 in",
            "out": "thinker width"
          },
          "chip": "learned",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Gemma adapter row, line 32)",
            "custom-io/models/ledger.py lines 284-294 (eg_proj applied to Gemma's state)"
          ],
          "notes": "Our check: 768 times 256 plus 256 bias = 196,864; 768 times 512 plus 512 = 393,728. Matches the source."
        },
        {
          "id": "s07",
          "duration": 40,
          "heading": "Four parts added into one letter row",
          "caption": [
            "Part one: which letter it is. A learned row of numbers.",
            "Part two: where it sits in the question. A learned table, with 2,000 rows in B3 and 280 in G1.",
            "Part three: how far its letter sits from the end of its word. The count is hand-written; the row it picks is learned.",
            "Part four: Gemma's meaning, through the converter plug, is added on top. Then the window reads the sum."
          ],
          "labels": {
            "char": "which letter",
            "pos": "where in question",
            "place": "place in word",
            "gemma": "Gemma meaning",
            "sum": "added together"
          },
          "chip": "hand-written",
          "chip_label": "place count only",
          "chip_target": "place",
          "src": [
            "custom-io/models/reader.py lines 1-3 (docstring: E_char + E_pos + E_place) and lines 72-80 (order: char + pos, then place, then extra added)",
            "custom-io/models/ledger.py lines 280-294 (read(): eg_proj(ln_eg(H)) passed as extra)",
            "custom-io/g8a/caps_b3.json (max_prompt 2000)",
            "custom-io/g8a/caps_g.json (max_prompt 280)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (place code row; group 2 replaces the count)"
          ],
          "notes": "Order checked in code this round: Gemma's projection is added after the three parts and before the conv window (reader.py 72-80; ledger.py 280-294). Only the place COUNT is hand-written; the place ROW is learned. Disagreement (5) is closed."
        },
        {
          "id": "s08",
          "duration": 30,
          "heading": "The letter window: each letter sees 4 each side",
          "caption": [
            "Two small learned layers read the summed row. They are ours, not borrowed.",
            "Each layer looks 2 letters left and 2 right, so together a letter sees 4 letters each side.",
            "The window adds about 0.7M numbers at width 256 and about 2.6M at width 512."
          ],
          "labels": {
            "l1": "layer 1: 2 each side",
            "l2": "layer 2: 2 more each side"
          },
          "chip": "learned",
          "chip_label": "learned, ours",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (letter window row, line 33)",
            "custom-io/models/reader.py line 5 and lines 46-63 (two blocks, kernel 5, receptive field plus or minus 4)"
          ],
          "notes": "The window is learned, not borrowed. Exact counts from code (my count, not shown): about 656,896 at width 256 and 2,624,512 at width 512; the on-screen 0.7M and 2.6M are the source's rounded values."
        },
        {
          "id": "s09",
          "duration": 28,
          "heading": "Without the window, cipher puzzles fall",
          "caption": [
            "Cipher puzzles are one kind of question in our test set.",
            "With the window, Gemma plus letters scores 97.5 and 95.0 out of 100 on two copies.",
            "Without the window, Gemma plus letters scores 5.0 and 2.5. Letters alone score 12.5 and 2.5."
          ],
          "labels": {
            "with": "with window",
            "without": "without window"
          },
          "numbers": {
            "ewith1": 97.5,
            "ewith2": 95,
            "wo1": 5,
            "wo2": 2.5,
            "r0a": 12.5,
            "r0b": 2.5
          },
          "chip": "tested",
          "chip_label": "2 copies, one kind",
          "src": [
            "custom_io/results/RESULTS-EG2.md lines 120-121 (in-distribution cipher_map; copies 200 and 201)",
            "custom_io/results/44-egr-s200/EGR_s200/RESULT.json (eg_embed true, reader_layers 0: Gemma plus letters, no window)",
            "custom_io/results/46-r0ege-s200/R0_s200/RESULT.json (reader_layers 0, no eg_embed: letters alone, no window)"
          ],
          "notes": "Arms checked in the result files: EGR = Gemma plus letters with zero window layers; R0 = letters alone with zero window layers. Disagreement (1): the brief and FINISHED sec. 2 say 100% down to 2.5-10%; the results file says 97.5/95.0 with the window, 5.0/2.5 (EGR) and 12.5/2.5 (R0). Source used."
        },
        {
          "id": "s10",
          "duration": 24,
          "heading": "The position table: how far the text can be",
          "caption": [
            "Sampled bAbI test questions: 32% are longer than 280 letters.",
            "Only 1% are longer than 2,000 letters, the limit for B3."
          ],
          "numbers": {
            "sample": 4000,
            "over280": 32,
            "over2000": 1
          },
          "labels": {
            "sample": "4,000 test questions",
            "a": "over 280 letters",
            "b": "over 2,000 letters"
          },
          "chip": "tested",
          "chip_label": "counted in FINISHED sec. 7",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 7 Q2 (lines 173-176; 200 per task, bAbI test split)"
          ],
          "notes": "Counts from FINISHED sec. 7 (its own sample; my recount not done). Not a score."
        },
        {
          "id": "s11",
          "duration": 24,
          "heading": "A hand-written pattern marks the numbers",
          "illustration": "picture only: the marked cells are not a real question",
          "caption": [
            "A plain pattern, written by hand, finds the numbers in the question.",
            "It records where each number is, not its value.",
            "It has 16 slots in T1SDR, 91 in G1, and 240 in the B3 build."
          ],
          "labels": {
            "regex": "hand-written pattern",
            "slots": "16 / 91 / 240 slots"
          },
          "chip": "hand-written",
          "chip_label": "hand-written",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (number finder row, line 89; ledger.py:206)",
            "custom-io/g8a/caps_g.json (n_num 91)",
            "custom-io/g8a/caps_b3.json (n_num 240)"
          ],
          "notes": "Planned replacement N1 (learned) is in B3 group 2, not built as a result. 16 (T1SDR) is from FINISHED sec. 4 only, not re-checked in code."
        },
        {
          "id": "s12",
          "duration": 22,
          "heading": "Calculator replies: read by the window only",
          "caption": [
            "The reply, like sub 12 5 = 7, is read by the letter window.",
            "Gemma does not read replies. It read the question once.",
            "Suggested reasoning: a reply carries nothing Gemma would add."
          ],
          "example": "sub 12 5 = 7",
          "chip": "untested",
          "chip_label": "built, never run",
          "illustration": "suggested reasoning",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 5 (lines 120-122; labelled suggested)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 3"
          ],
          "notes": "B3 group 1 builds this way; it has never been run. The reply path is suggested, not measured."
        },
        {
          "id": "s13",
          "duration": 32,
          "heading": "The gain: +2.67 points out of 100",
          "caption": [
            "On pooled-5, the reader version beats the same model without it by 2.67 points out of 100.",
            "Pooled-5 is 6,040 test questions kept aside, five kinds together.",
            "It was ahead in all 6 copies (seeds) tested at the 3M size."
          ],
          "numbers": {
            "gain": 2.67,
            "held": 6040,
            "copies": 6
          },
          "labels": {
            "ege": "with Gemma: 75.9 to 77.2",
            "b2": "without: 73.0 to 74.7"
          },
          "warning": "6-copy result files are not in this repo; not re-checked",
          "chip": "tested",
          "chip_label": "3M size, 6 copies",
          "src": [
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md line 18 (6-seed confirm on q33 data, +2.67, ahead on 6 of 6)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 line 31 (EGE +2.67, 6 of 6 seeds)",
            "architecture/TOKENS-EXPERIMENT-2026-10-09.md line 26 and line 44 (EGE 6 seeds 75.88-77.19; plain B2 73.00-74.74)"
          ],
          "notes": "Disagreement (2): custom_io/results/RESULTS-EG2.md lines 116-118 says the 6-seed EGE confirm is NOT JUDGED (seeds 202-207 missing); only EGE_s200 and EGE_s201 result files exist in this repo. The 6-of-6 figure is from FINISHED and the growth spec, shown with the warning line. Not re-checked by a result file."
        },
        {
          "id": "s14",
          "duration": 28,
          "heading": "Caveats: the leak warning light",
          "caption": [
            "A leak means some answers are right with zero rounds of thinking.",
            "The zero-round leak mean is 6.59, above the limit of 4.62. That mark was missed.",
            "On seed 200, the reader version scored 18.09 with zero rounds. Another version scored 1.40. The cause is not settled."
          ],
          "numbers": {
            "leak": 6.59,
            "limit": 4.62,
            "ege": 18.09,
            "other": 1.4
          },
          "chip": "untested",
          "chip_label": "caveat, not settled",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 line 31 (leak mean 6.59 against a limit of 4.62)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 2 (lines 110-112, 18.09 vs 1.40)"
          ],
          "notes": "The 2-copy screen also failed its variant and leak marks (TOKENS sec. 2). The 1.40 comparison is labelled 'another version' because the code name B2V is not defined in the glossary."
        },
        {
          "id": "s15",
          "duration": 20,
          "heading": "Open question: tokens instead of letters",
          "illustration": "picture only: the boxes show the idea, not a measured run",
          "caption": [
            "Test TK would let the thinker read one spot per token, not per letter.",
            "The code and a PC job file exist, but no result is recorded here. Chapter 12 covers it."
          ],
          "chip": "untested",
          "chip_label": "built, never tested",
          "src": [
            "architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 8 (no build at 10:15 AM ET; conflict)",
            "custom-io/train.py lines 229-230 (tok_think code present)",
            "custom-io/queue_local/8aTK-pc-3.txt (job file exists; no result file found)"
          ],
          "notes": "Disagreement (3): the brief says TK is built and never run; TOKENS sec. 8 says no build had started. Code and a job file exist in the repo, no result was found. Amber chip used. The 3.1 and 5.4 earlier word-piece losses were dropped (ch12 owns them, unverified here)."
        },
        {
          "id": "s16",
          "duration": 24,
          "heading": "Recap: what to remember",
          "caption": [
            "The reader is borrowed and frozen. It reads the question once.",
            "Each letter gets a meaning in context, plus a window of 4 letters each side.",
            "Without the window, the Gemma version falls to 5.0 and 2.5 out of 100 on cipher puzzles."
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 and sec. 5",
            "custom_io/results/RESULTS-EG2.md lines 120-121"
          ],
          "notes": "Recap only; every number repeats an earlier scene."
        }
      ]
    },
    "ch04": {
      "kicker": "Part 4 of 14",
      "title": "The thinker: rounds of looking and passing notes",
      "blurb": "The thinker is the part that does the thinking. It works in rounds: it looks at the question, passes notes, and thinks again.",
      "accent": "thinker",
      "scenes": [
        {
          "id": "s01",
          "duration": 24,
          "heading": "Where we are: the thinker",
          "caption": [
            "This is the thinker, the second part of the model. It does the thinking.",
            "It is ours. It starts from scratch and learns only from our practice.",
            "The planned size is about 100 million numbers. That size has never been tested."
          ],
          "chip": "never tested at 100M",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 (about 100M planned) and sec. 2 (Thinker row: yes, from scratch; shape untested at 100M)"
          ]
        },
        {
          "id": "s02",
          "duration": 27,
          "heading": "Picture only: a team of note-takers",
          "caption": [
            "Picture only. Think of a small team of note-takers sitting around one question.",
            "Each round, every note-taker looks at the whole question again.",
            "Then they pass notes to each other and write down what they now believe.",
            "The same team, with the same habits, every round."
          ],
          "tag": "picture only",
          "labels": {
            "q": "The question",
            "n": "Note-taker"
          },
          "src": [
            "kit/GLOSSARY.md (thinker row: the shared picture; no numbers)"
          ]
        },
        {
          "id": "s03",
          "duration": 30,
          "heading": "Vectors: 8 control, 36 memory",
          "caption": [
            "A vector is a list of numbers, like a note card with a row of numbers.",
            "The thinker keeps 8 control vectors. They steer the work.",
            "It also keeps 36 memory vectors, where its notes are kept.",
            "Older builds had 17 vectors: 8 control and 9 memory."
          ],
          "chip": "built, never tested",
          "labels": {
            "ctrl": "8 control vectors",
            "mem": "36 memory vectors",
            "old": "Older build: 8 + 9 = 17"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Thinker row: 8 + 36 under the B3 caps; T1SDR and H1 had 8 + 9 = 17)",
            "custom_io/g8a/caps_b3.json (n_reg 36)",
            "custom_io/models/ledger.py line 71 (N_CTRL 8)",
            "custom_io/g8a/caps.py line 24 (TODAY n_reg 9, the older 17)"
          ]
        },
        {
          "id": "s04",
          "duration": 27,
          "heading": "Control vector 0 drives the call writer",
          "caption": [
            "After each round, the call writer reads control vector 0.",
            "It either writes a request for the calculator, like sub 12 5, or writes nothing.",
            "The numbers in the request are copied from the question or an earlier reply."
          ],
          "chip": "tested in the older design",
          "labels": {
            "c0": "Control vector 0",
            "cw": "Call writer",
            "slip": "sub 12 5",
            "none": "or nothing"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1, and sec. 2 (Call writer row: shown in T1SDR)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 item 2 (tool.py:329-374 copies the numbers)"
          ]
        },
        {
          "id": "s05",
          "duration": 36,
          "heading": "Do the other controls matter?",
          "caption": [
            "Controls 2 to 7 feed no output. They only pass information along through attention.",
            "In an older build, switching them off at test time cost 1.6 points on the main test.",
            "On the multi-step test they cost 7.8 points: 99.4 fell to 91.6.",
            "This is one copy (seed 200) of an older design. It is a hint, not proof."
          ],
          "tag": "one copy, older design",
          "labels": {
            "on": "All controls on",
            "off": "Controls 2 to 7 off",
            "axis": "Multi-step test, points out of 100"
          },
          "values": {
            "on": 99.4,
            "off": 91.6
          },
          "src": [
            "architecture/model-deep-dive.html, Thinker section (zeroing controls 2-7: 1.6 on pooled-5, 7.8 on chains, 99.4 to 91.6, seed s200; older 17-vector design)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Thinker row: output heads read control 0; older design)"
          ]
        },
        {
          "id": "s06",
          "duration": 28,
          "heading": "Round step 1: look at everything",
          "caption": [
            "Each letter of the question is one box. A borrowed reader, Gemma, has already given each letter its meaning.",
            "Each note vector looks at every letter. In later rounds it also looks at every calculator reply.",
            "The shading inside each note is a picture only, not real numbers."
          ],
          "tag": "picture only",
          "labels": {
            "q": "Tom has 12 apples.",
            "look": "Look"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Thinker row: every letter and every calculator reply) and sec. 3 item 1 (Gemma reads the question once)",
            "custom_io/models/ledger.py, class CBlock (cross-attention to the letters and replies)"
          ]
        },
        {
          "id": "s07",
          "duration": 42,
          "heading": "Round steps 2 and 3: compare, then think",
          "caption": [
            "Step 2: the note vectors look at each other. In code this is called self-attention.",
            "Each note reads the other notes and keeps what matters from them.",
            "The letters are not compared with each other inside the thinker.",
            "Step 3: each note goes through a small network. It widens to 4.8 times its width, then squeezes back.",
            "Then the notes go on to the next round."
          ],
          "labels": {
            "compare": "Compare notes",
            "think": "Think: small network",
            "widen": "Widen 4.8 times"
          },
          "src": [
            "custom_io/models/ledger.py, class CBlock (self-attention; MLP with hidden = mlp x width)",
            "custom_io/g8a/configs.py line 35 (100M rung: width 512, 8 heads, mlp 4.8, 21 blocks)",
            "architecture/important-links-2026-10-09.md sec. 1, lines 12-14 (letters do not compare inside the thinker)",
            "architecture/running-summary-2026-10-08.md line 22 (notes talk to each other, then pass through an MLP)"
          ]
        },
        {
          "id": "s08",
          "duration": 24,
          "heading": "Same blocks, every round",
          "caption": [
            "One look, compare and think unit is a block. The same blocks run in every round.",
            "The weights do not change between rounds. Same team, same habits.",
            "A round stamp, a learned tag for the round number, is added to the notes each round."
          ],
          "chip": "older design tested",
          "tag": "round stamp",
          "src": [
            "custom_io/models/ledger.py, forward loop (the same self.core blocks each round; step_emb[t] added each round)",
            "custom_io/models/b3.py line 144 (B3 adds step_emb[ts] before each think)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Thinker row: same weights every round)"
          ],
          "labels": {
            "block": "Block"
          }
        },
        {
          "id": "s09",
          "duration": 37,
          "heading": "Why more rounds help",
          "caption": [
            "For Tom's apple question, round 2 writes sub 12 5, copying 12 and 5 from the question.",
            "The calculator replies 7. The reply is read and added to the notes.",
            "Round 3 sees that reply, then writes add 7 3. The calculator replies 10.",
            "The talker copies 10 as the answer. This is a worked example, traced from the code."
          ],
          "chip": "traced from code, never run in B3",
          "labels": {
            "r2": "Round 2: sub 12 5",
            "r2r": "Reply: 7",
            "r3": "Round 3: add 7 3",
            "r3r": "Reply: 10",
            "ans": "Answer: 10"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 items 2-6 (tool.py:329-374, tool.py:155-170, tool.py:368-374)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 header (B3 group 1 changes are built but have never run)"
          ]
        },
        {
          "id": "s10",
          "duration": 26,
          "heading": "The bell: when to stop",
          "caption": [
            "After each round, a tiny learned switch asks: is this settled, or should it think more?",
            "It must think at least 1 round. It can never go past 32 rounds.",
            "It learns from a settled label: stop once no later round would have been right."
          ],
          "chip": "built, never run",
          "labels": {
            "min": "At least 1",
            "max": "At most 32"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Learned stop row) and sec. 3 item 5",
            "custom_io/models/tool_h1.py line 20 (at least 1 round, hard cap 32) and line 42 (CAP = 32)"
          ]
        },
        {
          "id": "s11",
          "duration": 26,
          "heading": "One block: 4,624,281 numbers",
          "caption": [
            "A block is one look, compare and think unit, built from attention and a small network.",
            "Counting every learned number in one block at width 512 gives 4,624,281.",
            "Our arithmetic: 21 blocks alone give 97.1 million. 30 blocks would give about 139 million."
          ],
          "chip": "our arithmetic",
          "labels": {
            "b21": "21 blocks",
            "b30": "30 blocks"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 9 (their count; 100M = 21 blocks at width 512)",
            "custom_io/models/ledger.py, class CBlock (layer sizes; we recounted by hand: 4,624,281 exactly at width 512, mlp 4.8)",
            "custom_io/g8a/configs.py line 35 (100M rung: width 512, 8 heads, mlp 4.8, 21 blocks)"
          ],
          "notes": "Computed by hand: 21 x 4,624,281 = 97,109,901; 30 x 4,624,281 = 138,728,430. Per block: LayerNorms 4,096 + q 262,656 + kv 525,312 + o 262,656 + qkv 787,968 + p 262,656 + fc 1,260,441 + out 1,258,496.",
          "values": {
            "block": 4624281,
            "b21": 21,
            "b30": 30
          }
        },
        {
          "id": "s12",
          "duration": 32,
          "heading": "The size ladder (counts from the build)",
          "caption": [
            "The thinker grows in four steps, named 3M, 10M, 30M and 100M for their rough size.",
            "These are counts from the build. No B3 run at these sizes has happened yet.",
            "At the 100 million step the whole model is 373.1 million numbers, with the borrowed reader counted."
          ],
          "chip": "counted, not trained yet",
          "note": "Plus 271,002,624 borrowed reader numbers (frozen, never changed)",
          "labels": {
            "r3": "3M",
            "r10": "10M",
            "r30": "30M",
            "r100": "100M"
          },
          "values": {
            "r3": 4039957,
            "r10": 9832977,
            "r30": 29789693,
            "r100": 102116618
          },
          "src": [
            "animations/model-explainer-build/sources/pr-56-b3-group1-and-token-test.md line 15 (sizes at caps_b3; 'Runs: none yet' line 17)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 (373.1M whole at 100M; ladder 3M, 10M, 30M, 100M) and sec. 2 (271,002,624 frozen reader)"
          ]
        },
        {
          "id": "s13",
          "duration": 37,
          "heading": "Long text: is the thinker cheap?",
          "caption": [
            "Every letter against every letter: 81 times 81 is 6,561 checks.",
            "The notes look at letters instead: 44 notes, each looking at 81 letters and 27 slots, is 4,752 checks per round.",
            "Over 8 rounds, the older count, that is about 38,000. At 81 letters, no work is saved.",
            "Its gain is structure, not speed. Whether it helps on much longer text is untested."
          ],
          "chip": "suggested, arithmetic",
          "labels": {
            "all": "All pairs, 81 letters",
            "round": "Notes, one round",
            "eight": "Notes, 8 rounds"
          },
          "values": {
            "all": 6561,
            "round": 4752,
            "eight": 38016
          },
          "notes": "Computed by hand: 81 x 81 = 6,561; 44 x (81 + 27) = 4,752; 4,752 x 8 = 38,016 (the source says about 38,000).",
          "src": [
            "architecture/important-links-2026-10-09.md sec. 2, lines 22-24 (6,561; 4,752; about 38,000; at this length the thinker does not save work)",
            "architecture/important-links-2026-10-09.md sec. 1, lines 12-14 (letters do not compare inside the thinker)",
            "architecture/running-summary-2026-10-08.md line 48 (questions average 81 letters)"
          ]
        },
        {
          "id": "s14",
          "duration": 30,
          "heading": "First test: thinking on, then off",
          "caption": [
            "In the first finished test, one copy at the smallest size scored 73.01 points out of 100, with thinking on.",
            "With thinking switched off (zero rounds), the same copy scored 0.66 points.",
            "That is one copy at one size. Chapter 9 explains the test and its checks."
          ],
          "chip": "one copy, 3M, older design",
          "labels": {
            "on": "Thinking on",
            "off": "Thinking off",
            "axis": "Points out of 100"
          },
          "values": {
            "on": 73.01,
            "off": 0.66
          },
          "src": [
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md addendum G, line 188 (3M seed 400: 4,410 of 6,040; thinker-off 0.66)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 2 and item 7 (that design had the calculator inside, 12 fixed rounds)"
          ]
        },
        {
          "id": "s15",
          "duration": 40,
          "heading": "Not known yet, and what to remember",
          "caption": [
            "Not known: the thinker has never been tested at 100 million numbers.",
            "Not known: the block design has never been run. An older probe showed 16 rounds cost 1.2 to 1.9 points, on one seed.",
            "Experts are a separate idea. Chapter 12 covers them.",
            "Remember: the thinker looks, passes notes and thinks, in rounds. The same blocks run every round. A learned bell says when to stop."
          ],
          "chip": "not tested yet",
          "labels": {
            "r": "Recap"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (shape untested at 100M), sec. 5 item 13 (depth cost, open risk), sec. 5 item 10 (experts)",
            "no-hardcoding/INPUT-UNITS-2026-10-07.md line 39 (16 rounds cost 1.2-1.9 points, one seed; FINISHED cites line 31, see notes.md)"
          ]
        }
      ]
    },
    "ch05": {
      "kicker": "Part 5 of 14",
      "title": "Asking the calculator for help",
      "blurb": "The model can ask an ordinary calculator for exact sums. It writes the question as plain text, and the calculator writes back the answer as plain text.",
      "accent": "call",
      "scenes": [
        {
          "id": "s01",
          "duration": 22,
          "heading": "Where we are: the calculator sits outside",
          "caption": [
            "This part is about the call writer and the calculator.",
            "Rule (project rules, Oct 7): hand-written code may run only as an outside tool that the model chooses to call."
          ],
          "labels": {
            "call": "call writer",
            "calc": "calculator"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (parts table) and sec. 4 (rules dated 10-07)"
          ]
        },
        {
          "id": "s02",
          "duration": 24,
          "heading": "Why a calculator? Code adds exactly",
          "caption": [
            "Code adds two numbers exactly, every time.",
            "A learned network has to learn each sum from practice.",
            "So the model writes its sum as a slip of text and hands it to a calculator."
          ],
          "labels": {
            "slip": "call: sub 12 5",
            "back": "reply: 7",
            "calc": "calculator",
            "why": "our reasoning, not a measured result"
          },
          "src": [
            "GLOSSARY.md (call writer and calculator pictures)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (hand code only as a tool)"
          ],
          "notes": "The 'why' sentences are our reasoning and are labelled on screen."
        },
        {
          "id": "s03",
          "duration": 26,
          "heading": "Each round, the call writer reads one vector",
          "caption": [
            "After every round, the call writer reads the thinker's first control vector.",
            "It writes one of nine choices: no call, or one of the eight operations."
          ],
          "labels": {
            "v0": "control vector 0",
            "none": "no call",
            "ops": "8 operations",
            "cw": "call writer",
            "pic": "picture only: the shading is decoration"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (call writer row)",
            "custom_io/models/tool.py:15 (op head on control token 0; NOOP = no call)",
            "custom_io/models/progparse.py:12 (NOOP plus 8 operations)"
          ],
          "notes": "The code header calls control vector 0 'control token 0'. Same first vector."
        },
        {
          "id": "s04",
          "duration": 42,
          "heading": "The eight operations, one line each",
          "caption": [
            "Eight operations. Each example uses made-up numbers 12 and 5."
          ],
          "ops": [
            {
              "name": "add",
              "meaning": "add the two",
              "ex": "add 12 5 = 17"
            },
            {
              "name": "sub",
              "meaning": "first minus second",
              "ex": "sub 12 5 = 7"
            },
            {
              "name": "mul",
              "meaning": "multiply",
              "ex": "mul 12 5 = 60"
            },
            {
              "name": "div",
              "meaning": "divide, only if exact",
              "ex": "div 12 5 = ?"
            },
            {
              "name": "mod",
              "meaning": "left over after dividing",
              "ex": "mod 12 5 = 2"
            },
            {
              "name": "min",
              "meaning": "the smaller one",
              "ex": "min 12 5 = 5"
            },
            {
              "name": "max",
              "meaning": "the bigger one",
              "ex": "max 12 5 = 12"
            },
            {
              "name": "cmp",
              "meaning": "1 if first bigger, 0 if same, -1 if less",
              "ex": "cmp 12 5 = 1"
            }
          ],
          "src": [
            "custom_io/models/progparse.py:12 and :23-33 (ex: exact semantics; DIV only when exact)",
            "custom_io/models/tool.py:95-103 (calc: '?' when it cannot run)",
            "example results computed by hand from those lines, with made-up numbers 12 and 5"
          ],
          "notes": "12 divided by 5 is not whole, so div gives '?'. mod 12 5 = 2 because 12 = 2 x 5 + 2. cmp returns 1, 0 or -1 as in progparse ex."
        },
        {
          "id": "s05",
          "duration": 45,
          "heading": "Copying digits: a pointer, a step left, a stop",
          "question": "Tom has 12 apples.",
          "caption": [
            "To write the 12 in a call, a learned pointer lands on its last digit, the 2.",
            "The copy then steps one letter left and copies the 1.",
            "A learned stop head says when to stop, or at the start of the text.",
            "The copy trick was used for 98% of written operands and 91.5% of answers, on every T1SDR seed.",
            "That is how often the copy was used, not how often it was right."
          ],
          "labels": {
            "ptr": "pointer",
            "stop": "stop head",
            "out": "written last digit first",
            "chip": "tested at 3M",
            "d2": "2",
            "d1": "1"
          },
          "bars": [
            {
              "label": "operands copied",
              "value": 98
            },
            {
              "label": "answers copied",
              "value": 91.5
            }
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 2 (lines 46-50): worked Tom example and copy rule",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (span copy row): 98% of written operands and 91.5% of answers on every T1SDR seed",
            "custom_io/models/tool.py:222-247 (span copy: one letter left until the learned stop head says stop)"
          ],
          "notes": "The 98% and 91.5% are shares of uses, not accuracy. FINISHED sec. 4 is the only source found; the raw per-seed file was not located in custom_io/results."
        },
        {
          "id": "s06",
          "duration": 30,
          "heading": "A number not in the text: 21 cells",
          "caption": [
            "Some numbers are not in the question. The 10 from add 7 3 is one of them.",
            "It is built one letter at a time, into 21 cells, last digit first. The code flips the text afterwards."
          ],
          "labels": {
            "cells": "21 cells: 20 for the longest 64-bit whole number, 1 for the end mark",
            "first": "0 goes in first, then 1",
            "z": "0",
            "o": "1"
          },
          "src": [
            "custom_io/models/tool.py:84 (CELLS = 21, with its comment: longest int64 string 20 characters, then end mark)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 2 (21 slots, last digit first) and step 4 (add 7 3 = 10)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (last letter first row)"
          ],
          "notes": "tool.py header line 15 says 11 cells: a stale comment; CELLS = 21 is the code. The 10 is from the project's worked Tom example."
        },
        {
          "id": "s07",
          "duration": 27,
          "heading": "The calculator: plain Python, no learned numbers",
          "caption": [
            "The calculator is ordinary Python code. It has 0 learned numbers.",
            "It reads the call as text and writes the reply as text. A call it cannot run gets a question mark."
          ],
          "labels": {
            "in": "call in: sub 12 5",
            "out": "reply out: 7",
            "bad": "div 12 5 gives ?",
            "calc": "calculator",
            "tag": "hand code, allowed as a tool"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (calculator row: size 0)",
            "custom_io/models/tool.py:95-103 (calc)",
            "custom_io/models/progparse.py:23-33 (ex)"
          ]
        },
        {
          "id": "s08",
          "duration": 37,
          "heading": "The reply goes into the notes, not the question",
          "caption": [
            "After round 2 the call writer writes sub 12 5, and the calculator replies.",
            "The reply line, sub 12 5 = 7, is read by the letter window and added to the notes.",
            "The question is not read again. In round 3 the call writer writes add 7 3, and the reply is 10."
          ],
          "labels": {
            "q": "question: not read again",
            "notes": "thinker's notes",
            "r": "reply",
            "cw": "call writer",
            "calc": "calculator",
            "rd2": "round 2",
            "rd3": "round 3",
            "r1": "sub 12 5 = 7",
            "r2": "add 7 3 = 10"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 steps 2-4 (lines 46-53): worked Tom example",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (letter window row) and sec. 5 item 5 (replies read by the letter window only)",
            "custom_io/models/tool.py:155-170, 368-374 (reply read as a short string; thinker keeps its vectors)"
          ]
        },
        {
          "id": "s09",
          "duration": 34,
          "heading": "Timing today: calls follow rounds 2 to 8",
          "caption": [
            "In the tested design, the first call follows round 2.",
            "Call k follows round k plus 1, up to call 7 after round 8.",
            "Rounds 9 to 32 cannot call."
          ],
          "labels": {
            "r2": "round 2, then call 1",
            "r8": "round 8, then call 7",
            "none": "rounds 9-32: no call",
            "chip": "tested in T1SDR (3M)",
            "rounds": [
              "1",
              "2",
              "3",
              "4",
              "5",
              "6",
              "7",
              "8"
            ],
            "calls": [
              "call 1",
              "call 2",
              "call 3",
              "call 4",
              "call 5",
              "call 6",
              "call 7"
            ]
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 60-62)",
            "custom_io/models/tool.py:338, 350 (call timing; no call after round 8 in the tested code)"
          ]
        },
        {
          "id": "s10",
          "duration": 35,
          "heading": "Built, not run: any round, and a tape of 16",
          "caption": [
            "The project owner chose any time for when a call may follow.",
            "The group 1 build lets a call follow any round from 2 to 32.",
            "The tape holds 16 calls.",
            "In training, 1 row in 4 gets 0, 1 or 2 extra thinking rounds before each call."
          ],
          "labels": {
            "any": "rounds 2 to 32",
            "tape": "tape: 16 slots",
            "gap": "1 in 4 rows",
            "chip": "built, never run",
            "pic": "picture only: 4 filled slots are an example"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 60-65) and sec. 7 Q1 (answered 9:30 AM ET 10-09)",
            "custom_io/models/b3.py:6-10 (any_round, gap_p, think-only rounds 0-2)",
            "custom_io/models/b3.py:26 (TAPE_MIN = 16)",
            "custom_io/g8a/configs.py:95 (B3_G1 gap_p=0.25)"
          ]
        },
        {
          "id": "s11",
          "duration": 39,
          "heading": "Still hand-written, and what group 2 changes",
          "caption": [
            "Some parts are still ordinary code a person wrote. Four of them are shown here as brown chips.",
            "The operation name comes from a fixed list of 8, so a new tool could not be called yet.",
            "Group 2 writes the whole call as letters, operation name included.",
            "It is built as code and has never run."
          ],
          "labels": {
            "ops": "operation from a fixed list of 8",
            "num": "number finder (regex)",
            "copy": "copy rules: start, step left, stop",
            "flip": "last letter first, text flipped",
            "chip": "built, never tested",
            "g2call": "sub 12 5"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (hand code table: op word, number finder, span copy rules, last letter first; group 2 row)",
            "custom_io/models/ledger.py:206 (number finder regex)",
            "custom_io/models/tool.py:188, 191-197, 222-247 (last letter first; span copy rules)"
          ],
          "notes": "FINISHED sec. 4 lists more hand parts than the four shown (word splitter, 108-character list, worked steps, layout codes, operand slots)."
        },
        {
          "id": "s12",
          "duration": 45,
          "heading": "The evidence: 6 copies, calculator outside",
          "caption": [
            "Each copy starts from its own random start.",
            "The calculator-outside model (T1SDR) was compared with the same model with the calculator inside (B2).",
            "Pooled-5, 6,040 questions kept aside: plus 0.62 points, likely range minus 0.23 to plus 1.46.",
            "All six copies were within 1.0 of B2 on pooled-5.",
            "Chain-5, 1,000 multi-step questions: 99.6 to 99.8 with the calculator outside, mean 99.72. Inside: 99.4 to 99.7.",
            "With the calculator switched off, program questions score 0.0."
          ],
          "labels": {
            "ob": "B2: calc inside",
            "out": "T1SDR: calc outside",
            "chip": "tested at 3M, 6 copies",
            "ticks": [
              "-1",
              "0",
              "1",
              "2"
            ]
          },
          "numline": {
            "min": -1,
            "max": 2,
            "mean": 0.62,
            "lo": -0.23,
            "hi": 1.46
          },
          "src": [
            "architecture/MARKS-D0-T1-2026-10-07.md Record 13 (lines 198-205): pooled-5 +0.62, CI -0.23 to +1.46; 6 of 6 copies within 1.0; tool off 0.0",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 1: chain-5 99.6-99.8, mean 99.72; B2 99.4-99.7",
            "GLOSSARY.md (pooled-5: 6,040 kept-aside questions; chain-5: 1,000 multi-step questions)"
          ],
          "notes": "Record 13 is relayed, not rechecked. The chain-5 per-copy values appear only in FINISHED sec. 5 item 1. The 6,040 and 1,000 counts are from GLOSSARY.md."
        },
        {
          "id": "s13",
          "duration": 35,
          "heading": "Check 1: the swap test",
          "caption": [
            "In the swap test, add and sub are swapped inside the calculator.",
            "The pass line: 99% or more of the rows must follow the swap.",
            "Five copies: 99.28 to 99.87, all at 99 or more.",
            "The sixth copy's saved model was lost, so it is not scored."
          ],
          "labels": {
            "swap": "add and sub swapped",
            "pass": "pass line: 99",
            "lost": "copy F: not scored",
            "chip": "tested on 5 of 6 copies"
          },
          "vals": [
            {
              "label": "A",
              "value": 99.87
            },
            {
              "label": "B",
              "value": 99.28
            },
            {
              "label": "C",
              "value": 99.4
            },
            {
              "label": "D",
              "value": 99.74
            },
            {
              "label": "E",
              "value": 99.61
            }
          ],
          "src": [
            "architecture/MARKS-D0-T1-2026-10-07.md Record 13 (line 201): mark 5 values for seeds 200-204; seed 205 unscored",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 1 (swap holds on 5 of 6 copies; checkpoint lost)"
          ],
          "notes": "Copies A-F are seeds 200-205 in order (our labels). Seed 205 is F and is unscored. The 99% pass line is the Amendment 12 definition in the marks file."
        },
        {
          "id": "s14",
          "duration": 43,
          "heading": "Check 2: the leak test, missed then cleared",
          "caption": [
            "The leak score: right answers with zero rounds, in points out of 100.",
            "The sealed limit was 5. Five of six copies read above it, from 5.07 to 5.59.",
            "The plain model without the calculator read 3.09 to 3.75 on the same check.",
            "The leak mark was missed as sealed. The project owner cleared it on Oct 9.",
            "One other zero-round read, loops 0, was 12.94 on one copy, against 10.81 for B2."
          ],
          "labels": {
            "lim": "sealed limit: 5",
            "chip": "missed, then cleared by owner"
          },
          "vals": [
            {
              "label": "A",
              "value": 5.59
            },
            {
              "label": "B",
              "value": 5.15
            },
            {
              "label": "C",
              "value": 5.59
            },
            {
              "label": "D",
              "value": 5.07
            },
            {
              "label": "E",
              "value": 5
            },
            {
              "label": "F",
              "value": 5.59
            }
          ],
          "src": [
            "architecture/MARKS-D0-T1-2026-10-07.md Record 13 (line 202): donor 5.59/5.15/5.59/5.07/5.00/5.59; B2 3.09-3.75; loops:0 on s201 12.94 vs B2 10.81",
            "architecture/MARKS-D0-T1-2026-10-07.md Record 13 (line 203): owner cleared mark 4, 8:21 AM ET 10-09",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (calculator row: leak mark cleared 8:21 AM ET 10-09)"
          ],
          "notes": "Copies A-F are seeds 200-205 in order (our labels). The leak limit is 5 (mark 4). The loops:0 read is on copy B (seed 201). Five values are above 5; E is exactly 5.00, which is at the limit."
        },
        {
          "id": "s15",
          "duration": 40,
          "heading": "What is tested, and what is not",
          "caption": [
            "Tested: the calculator outside the model, at 3M, over six copies (swap check on five).",
            "Never run together: the Gemma reader with the outside calculator.",
            "Built, never run: calls at any round.",
            "Remember: the model writes calls as text. The calculator replies as text. A copy trick, with a learned stop, writes most digits."
          ],
          "labels": {
            "t": "tested: calc outside, 3M",
            "n": "never run: Gemma with calc",
            "b": "built, never run: any round",
            "rem1": "Calls are text.",
            "rem2": "The calculator replies in text.",
            "rem3": "A copy trick, with a learned stop, writes most digits."
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (calculator row), sec. 5 item 6 (Gemma and calculator never run together), sec. 3 (any-round built, untested)",
            "architecture/MARKS-D0-T1-2026-10-07.md Record 13 (6 copies; mark 5 on 5)"
          ]
        }
      ]
    },
    "ch06": {
      "kicker": "Part 6 of 14",
      "title": "Deciding when it is done",
      "blurb": "The model stops thinking on its own. A small learned switch looks after each round and decides whether the thinking is finished. This part is built, but it has never been run.",
      "accent": "stop",
      "scenes": [
        {
          "id": "s01",
          "duration": 28,
          "heading": "Where we are: the stop switch",
          "caption": [
            "The model thinks in rounds, one lap at a time.",
            "The stop switch decides when the thinking is finished.",
            "It is built, but it has never been run."
          ],
          "chip": "built, never run",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 (one paragraph) and sec. 2 (Learned stop row, line 36: built, never run)"
          ]
        },
        {
          "id": "s02",
          "duration": 30,
          "heading": "The problem: a fixed dial is a guess",
          "caption": [
            "The older design gave every question the same number of rounds, set by hand.",
            "Easy questions waste rounds. Hard questions may need more."
          ],
          "dial": "12 rounds, set by hand",
          "easy": "easy question",
          "hard": "hard question",
          "picture": "picture only: one fixed dial for every question",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (table row: fixed number of rounds, 8 in T1SDR, 12 in G1, line 94)"
          ]
        },
        {
          "id": "s03",
          "duration": 32,
          "heading": "Evidence: fewer rounds scored lower",
          "caption": [
            "We turned the dial down on one trained copy, with no new practice.",
            "Points out of 100, on 6,040 questions kept aside.",
            "Trained at 12 rounds it scored 73.01. With 2 rounds, 29.30. With 1 round, 20.00. With 0 rounds, 0.66."
          ],
          "bars": [
            {
              "label": "0 rounds",
              "value": 0.66
            },
            {
              "label": "1 round",
              "value": 20
            },
            {
              "label": "2 rounds",
              "value": 29.3
            },
            {
              "label": "12 rounds (trained)",
              "value": 73.01
            }
          ],
          "chip": "tested: one copy, 3M size",
          "note": "older design: calculator inside, 12 fixed rounds",
          "src": [
            "animations/source-g1-3m-s400.json G-B2 (full pooled5 73.01, right 4410 of 6040; by_thinking_rounds loops:0 0.66, loops:1 20.0, loops:2 29.3; trained_rounds 12)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 2 (73.01 with thinker on, 0.66 with it off, 3M seed 400)"
          ],
          "notes": "Points are scores out of 100 (right / 6,040 x 100). The 0 to 2 round rows are the same trained copy with its dial turned down (loops:K), no new practice."
        },
        {
          "id": "s04",
          "duration": 30,
          "heading": "Hard questions need more rounds",
          "caption": [
            "Chain-5 is the multi-step test, on the same trained copy.",
            "On pooled-5, 1 round scored 20.00. On chain-5 it scored 0.0. At 2 rounds, chain-5 scored 1.1.",
            "At the full setting chain-5 scored 99.9. Easy and hard questions need different amounts of thinking."
          ],
          "bars": [
            {
              "label": "1 round",
              "value": 0
            },
            {
              "label": "2 rounds",
              "value": 1.1
            },
            {
              "label": "full setting",
              "value": 99.9
            }
          ],
          "chip": "tested: one copy, 3M size",
          "note": "chain-5 score out of 100, same older design",
          "src": [
            "animations/source-g1-3m-s400.json G-B2 chain5 (loops:0 0.0, loops:1 0.0, loops:2 1.1, intact 99.9); by_thinking_rounds loops:1 20.0 (pooled-5)"
          ],
          "notes": "The source file's key for the full setting is 'intact'; the chain-5 count is not in that file, so no count is shown."
        },
        {
          "id": "s05",
          "duration": 28,
          "heading": "Too many rounds can cost points",
          "caption": [
            "One older probe, on one copy only: the in-distribution score stopped rising at 8 rounds.",
            "Sixteen rounds scored 1.2 to 1.9 points below fewer rounds.",
            "So too few rounds hurt, and too many may hurt too."
          ],
          "big": "1.2 to 1.9 points lower",
          "eight": "8 rounds: score stops rising",
          "sixteen": "16 rounds: lower",
          "chip": "tested: one copy, one probe",
          "src": [
            "no-hardcoding/INPUT-UNITS-2026-10-07.md line 39 (16 rounds cost 1.2-1.9 points; in_dist saturates at 8 rounds; one seed); line 12 (same claim)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 13 (line 149)"
          ],
          "notes": "fast-slow-2026-10-08.md sec. 2 says 1.6 to 1.9 worse than 8 rounds. The cited range here is 1.2 to 1.9 from INPUT-UNITS line 39; the difference is logged in notes.md."
        },
        {
          "id": "s06",
          "duration": 34,
          "heading": "After each round, a tiny head says stop or go",
          "caption": [
            "After every round, a small head reads the thinker's notes.",
            "It gives a number from 0 to 1. At 0.5 or more, the thinking stops.",
            "It always runs at least 1 round, and never more than 32.",
            "The head is 257 numbers at width 256, and 513 at width 512."
          ],
          "thinker": "thinker",
          "head": "stop head",
          "line": "0.5 = stop line",
          "picture": "picture only: the meter is not a real run",
          "chip": "built, never tested",
          "src": [
            "custom_io/models/tool_h1.py lines 10 (stop = Linear(d,1), 257 params at d=256), 42-44 (CAP = 32, P_STOP = 0.5)",
            "custom_io/models/tool_h1.py lines 19-20 (run rule: first round with sigmoid >= 0.5, at least 1 round, cap 32)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Learned stop row: width + 1, 257 at 256, 513 at 512, never run)"
          ]
        },
        {
          "id": "s07",
          "duration": 30,
          "heading": "One stop for the whole answer",
          "caption": [
            "There is one stop for the whole answer, not one stop per call.",
            "Built, not tested: a call to the calculator may follow any round from round 2 up to 32.",
            "In training, about a quarter of rows add 0 to 2 extra thinking rounds before a call."
          ],
          "round": "round",
          "call": "call",
          "bell": "stop",
          "picture": "made-up example: no real run",
          "chip": "built, never tested",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 60-66: calls inside the thinking; one stop for the whole answer)",
            "architecture/B3-GROUP1-BUILD-2026-10-09.md sec. 3 (lines 53-54: gap_p 0.25, gaps g in {0,1,2})",
            "custom_io/models/tool_h1.py lines 5-17 (one stop, not one per call)"
          ]
        },
        {
          "id": "s08",
          "duration": 30,
          "heading": "How it is taught: the settled label",
          "caption": [
            "Training gives every round a label: stop, or keep going.",
            "The label says stop when the answer is right now, or when no later round is right.",
            "So the head also learns to stop on questions it cannot solve."
          ],
          "rowA": "made-up row A: first right at round 4",
          "rowB": "made-up row B: never right",
          "go": "go",
          "stop": "stop",
          "picture": "made-up example: no real run",
          "chip": "built, never tested",
          "src": [
            "custom_io/models/tool_h1.py lines 52-57 (def settled: label = right now, or no later round is right)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 item 5 (lines 54-56)"
          ]
        },
        {
          "id": "s09",
          "duration": 35,
          "heading": "The fix: count the label only in full batches",
          "caption": [
            "Problem: a row first right at round 10 looks never right inside an 8-round batch.",
            "Then the label says stop at round 1, so the head learned to stop too early.",
            "Fix: the stop loss counts only in batches that run all 32 rounds: about 1 batch in 4."
          ],
          "short": "8-round batch: not counted",
          "full": "32-round batch (12 of 32 shown): counted",
          "go": "go",
          "stop": "stop",
          "picture": "made-up example: no real run",
          "chip": "fix applied before any run",
          "src": [
            "custom_io/models/tool_h1.py lines 13-16 (a batch of n < 32 rounds cannot see later rounds; stop loss counted only when n >= 32, about 1 batch in 4, about half of all trained rounds)",
            "big-run/PLAN.md Amendment 1:25 PM ET (audit B13-2; applied before any B3 run; line 236)"
          ],
          "notes": "The made-up row (first right at round 10) is an illustration of the mechanism, not a stop round from any real question."
        },
        {
          "id": "s10",
          "duration": 28,
          "heading": "The risk: a stop that fires too early",
          "caption": [
            "The label only sees the rounds a row actually ran.",
            "So a stop that fires early is never shown a later right answer.",
            "The first run will report how often rows stop early, and the answers on those rows."
          ],
          "chip": "first run planned",
          "ran": "made-up example: rounds it ran",
          "go": "go",
          "stop": "stop",
          "unseen": "later rounds: never seen",
          "early": "early stop",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 66-69: risk, suggested; B3 3M readout reports it)",
            "big-run/PLAN.md addendum 12:25 PM ET (line 230: early-stop share reported, not gated)"
          ]
        },
        {
          "id": "s11",
          "duration": 40,
          "heading": "How it will be judged: marks set in advance",
          "caption": [
            "These marks were written before any run. They are targets, not results.",
            "Easy questions must use at most half the rounds of the longest ones (11 steps in the code; the plan says 12).",
            "Always-32 means the same model forced to think all 32 rounds. Practised questions: within 1 of it. Longer chains: within 2.",
            "It fails if it never stops early, or if longer chains fall more than 5 below always-32."
          ],
          "barA": "1-step questions: rounds (target)",
          "barB": "longest questions: rounds (target)",
          "target": "target, not a result",
          "chip": "plan only",
          "src": [
            "big-run/PLAN.md sec. 5 row 5 (line 74: practised within 1, longer chains within 2 of always-32, rounds on 1-step <= half those on 12-step, fails if it never stops early)",
            "big-run/PLAN.md B3-4 (line 226: average rounds within 10% of the cap of 32 on every family; longer chains more than 5 below the lesion)",
            "big-run/PLAN.md sec. 5 note (b) (line 234: n_res is 11 under caps_b3, so read '12-step' as 11-step)"
          ],
          "notes": "The PLAN does not state the unit of 'within 1'. The same model with the stop ignored is the loops:32 lesion (free, no extra training). The 'always-32' label is our wording. Dashed bars are empty on purpose: no result exists."
        },
        {
          "id": "s12",
          "duration": 33,
          "heading": "If it fails: the stop cannot be switched off",
          "caption": [
            "No build switch turns the stop off. The switches cover Gemma and calls, not the stop.",
            "The nearest model without a stop is T1SDR, which uses a fixed 8 rounds.",
            "The stop has never run. The first run is planned after the G1 test."
          ],
          "chip": "built, never run",
          "sw1": "switch: Gemma reads the question",
          "sw2": "switch: calls at any round",
          "noSw": "stop: no switch",
          "fallback": "no stop: T1SDR, fixed 8 rounds",
          "src": [
            "custom_io/models/b3.py docstring lines 1-17 (switches: eg_embed, any_round; the stop is part of H1R)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (line 94: fixed rounds, 8 in T1SDR, 12 in G1) and sec. 2 (first run after G1)"
          ],
          "notes": "The brief said the stop can only be removed by running T1SDR. The code shows no stop switch; H1R is T1SDR plus the learned stop (b3.py docstring line 1). T1SDR is named here as the nearest model without a stop. No source found calls it the fallback, so the video does not say that."
        },
        {
          "id": "s13",
          "duration": 30,
          "heading": "Fast and slow: one thinker, not two",
          "caption": [
            "Some people call few rounds fast thinking, and many rounds slow thinking.",
            "We think one looped thinker does both. There is no separate fast and slow model (suggested).",
            "To remember: the stop switch decides, the cap is 32, and the stop is built but not yet run."
          ],
          "one": "one looped thinker",
          "fast": "fast: few rounds",
          "slow": "slow: many rounds",
          "chip": "idea (suggested)",
          "src": [
            "architecture/fast-slow-2026-10-08.md sec. 1 (short answer, suggested) and sec. 5 (no new test proposed)",
            "custom_io/models/tool_h1.py lines 42-44 (cap 32, stop line 0.5)"
          ]
        }
      ]
    },
    "ch09": {
      "kicker": "Part 9 of 14",
      "title": "Does the thinking really do the work?",
      "blurb": "We turn the thinking down, round by round, and break other parts on purpose, to see whether the answers fall with it.",
      "accent": "thinker",
      "scenes": [
        {
          "id": "s01",
          "duration": 20,
          "heading": "Where we are: the thinker",
          "caption": [
            "This part is the thinker, a team of note-takers that works in rounds.",
            "We claim the thinking does the work. This chapter tests that claim."
          ],
          "note": "One round = one lap: look at the whole question, pass notes, think.",
          "src": [
            "animations/model-explainer-build/kit/GLOSSARY.md (thinker, round)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 and 2 (Thinker row: 'same weights every round')"
          ]
        },
        {
          "id": "s02",
          "duration": 21,
          "heading": "A score with nothing to compare",
          "caption": [
            "Our model scored 73.01 points out of 100 on 6,040 questions kept aside.",
            "That is 4,410 right. But is it the thinking that earns them?"
          ],
          "score": 73.01,
          "unit": "points out of 100",
          "right": 4410,
          "rightLabel": "right, out of 6,040",
          "chip": "tested: one copy, smallest size",
          "src": [
            "animations/source-g1-3m-s400.json (G-B2 full: right 4410, of 6040, pooled5 73.01)",
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md sec. 12 (addendum G): 73.01 (4,410/6,040), 3M s400",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 2: 'Shown on one seed'"
          ],
          "notes": "Tested once: 3M size (3,544,913 numbers it learned), seed 400, run on the project's own PC. Re-added from the raw RESULT.json (branch claude/8a-g-pc-results) by me: 1170+863+1178+715+484 = 4410 right of 1360+1200+1360+800+1320 = 6040; 100 x 4410/6040 = 73.01."
        },
        {
          "id": "s03",
          "duration": 22,
          "heading": "What the 6,040 questions are",
          "caption": [
            "To score it, we use 6,040 questions kept aside.",
            "They come in five kinds, from familiar to new.",
            "They add up to 6,040. The test is called pooled-5."
          ],
          "total": 6040,
          "kinds": [
            {
              "label": "Familiar",
              "n": 1360
            },
            {
              "label": "New answers",
              "n": 1200
            },
            {
              "label": "New sentence frames",
              "n": 1360
            },
            {
              "label": "New words",
              "n": 800
            },
            {
              "label": "New wording",
              "n": 1320
            }
          ],
          "src": [
            "custom-io/gpt-b2-leak-and-credit-2026-10-05.md 'Data and metrics' (dev splits: in_dist same templates; answer unseen answer values; frame new sentence frames; vocab new words; variant new wordings; pooled-5 = 6,040 rows)",
            "repo branch origin/claude/project-thread-qtxfp4: custom_io/PASS-MARKS.md line 26 (pooled-5 = in_dist + answer + frame + vocab + variant, 6,040 rows)",
            "branch claude/8a-g-pc-results results/8a-g/pc/8aG1d-pc/8aG1d-3M-s400/B2/RESULT.json final_eval.{in_dist,answer,frame,vocab,variant}.n = 1360, 1200, 1360, 800, 1320"
          ],
          "notes": "The per-kind question counts are the n fields of the raw file; they sum to 6040. 'Familiar templates' is in_dist (same templates as practice, new questions)."
        },
        {
          "id": "s04",
          "duration": 28,
          "heading": "Turning the thinking down",
          "caption": [
            {
              "at": 0.02,
              "text": "Trained with 12 rounds, it scores 73.01 at 12."
            },
            {
              "at": 0.2,
              "text": "Turn the dial down, with no new practice: 2 rounds scores 29.30."
            },
            {
              "at": 0.4,
              "text": "1 round: 20.00."
            },
            {
              "at": 0.58,
              "text": "0 rounds, no thinking at all: 0.66. Just 40 right out of 6,040."
            }
          ],
          "ticks": [
            0,
            12,
            24
          ],
          "scoreHead": "points out of 100",
          "rows": [
            {
              "label": "12 rounds",
              "rounds": 12,
              "value": 73.01
            },
            {
              "label": "2 rounds",
              "rounds": 2,
              "value": 29.3
            },
            {
              "label": "1 round",
              "rounds": 1,
              "value": 20
            },
            {
              "label": "0 rounds",
              "rounds": 0,
              "value": 0.66
            }
          ],
          "src": [
            "animations/source-g1-3m-s400.json (G-B2 trained_rounds 12; by_thinking_rounds loops:0 40 right 0.66; loops:1 1208 right 20.0; loops:2 1770 right 29.3)",
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md sec. 12 (addendum G): thinker-off (loops:0) 0.66; spec sec. 3 mark 3 defines loops:0 as zero rounds",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 table ('Fixed number of rounds ... 12 in G1')",
            "branch claude/8a-g-pc-results B2/RESULT.json config.cfg.n_loops = 12; lesions loops:0/1/2"
          ],
          "notes": "0.66, 73.01 are in the spec; 29.30, 20.00 and the right-counts 1,770 / 1,208 / 40 are re-added from the raw RESULT.json files (sum of correct over in_dist, answer, frame, vocab, variant, divided by 6,040). The 12-round row is the model as trained ('full'); the raw file has no separate loops:12 entry."
        },
        {
          "id": "s05",
          "duration": 27,
          "heading": "More rounds: no gain",
          "caption": [
            "Now turn the dial past its practice, to 24 rounds.",
            "The score does not rise: 72.57, which is 27 fewer right (4,410 minus 4,383).",
            "The finished design adds a learned stop switch to choose the rounds."
          ],
          "ticks": [
            0,
            12,
            24
          ],
          "scoreHead": "points out of 100",
          "rows": [
            {
              "label": "12 rounds",
              "rounds": 12,
              "value": 73.01
            },
            {
              "label": "24 rounds",
              "rounds": 24,
              "value": 72.57
            }
          ],
          "chip": "stop switch: built, never tested",
          "src": [
            "animations/source-g1-3m-s400.json (loops:24: 4383 right, 72.57)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Learned stop row: 'built, never run'; at least 1, at most 32 rounds) and sec. 5 item 13 (depth has a known cost)"
          ],
          "notes": "27 = 4,410 minus 4,383, my subtraction (right answers at 12 rounds minus at 24 rounds). 24 = twice the 12 trained rounds (the raw file's 2 x n_loops lesion)."
        },
        {
          "id": "s06",
          "duration": 31,
          "heading": "Multi-step questions need rounds most",
          "caption": [
            "A second test, called chain-5: 1,000 multi-step questions kept aside.",
            "Each step needs its own round, so cutting rounds hurts most.",
            "1 round: 0.0. 2 rounds: 1.1. 12 and 24 rounds: 99.9."
          ],
          "example": "Tom has 12 apples. He gives away 5, then buys 3.",
          "illustration": "made-up example",
          "scoreHead": "points out of 100",
          "rows": [
            {
              "label": "0 rounds",
              "value": 0
            },
            {
              "label": "1 round",
              "value": 0
            },
            {
              "label": "2 rounds",
              "value": 1.1
            },
            {
              "label": "12 rounds",
              "value": 99.9
            },
            {
              "label": "24 rounds",
              "value": 99.9
            }
          ],
          "src": [
            "animations/source-g1-3m-s400.json (chain5: intact 99.9, loops:0 0.0, loops:1 0.0, loops:2 1.1, loops:24 99.9)",
            "architecture/model-deep-dive.html 'How we score it' (chain-5: 1,000 multi-step questions) and 'Rounds 1 to 7: one calculator step each' (example needs two steps, one per round)",
            "custom-io/gpt-b2-leak-and-credit-2026-10-05.md (chain-5 = 5 multi-step arithmetic families, 1,000 rows)"
          ],
          "notes": "Not the separate 'multistep' subset (480 rows per split). The Tom example is made up (deep-dive: 'Made up for this page'); its two steps are an illustration of one step per round, in the older design page's words. 12 rounds = the model as trained (chain5 'intact').",
          "stepsLabel": "two steps, two rounds"
        },
        {
          "id": "s07",
          "duration": 32,
          "heading": "Break the notes, the answer breaks",
          "caption": [
            "A lesion test: break one part, and see if the answer breaks.",
            "Give the talker another question's notes: the score falls to 4.19.",
            "Shuffle the notes between questions: 6.80."
          ],
          "labels": {
            "thinker": "Thinker",
            "notes": "notes",
            "talker": "Talker",
            "a": "A",
            "b": "B"
          },
          "illustration": "picture only",
          "cards": [
            {
              "title": "Another question's notes",
              "was": 86.03,
              "to": 4.19,
              "sub": "was 86.03, on 1,360 questions",
              "extra": "55.15 gave the other's answer"
            },
            {
              "title": "Notes shuffled",
              "was": 73.01,
              "to": 6.8,
              "sub": "was 73.01, on 6,040 questions"
            }
          ],
          "wiring": "Wiring check: shows plumbing, not good reasoning.",
          "src": [
            "branch claude/8a-g-pc-results B2/RESULT.json lesions.donor.in_dist (exact 4.19, donor_match 55.15, n 1360) and lesions.shuffle_state (pooled-5 411/6040)",
            "branch origin/claude/project-thread-qtxfp4 custom_io/README.md ('donor-swap lesion': same-family donor whose answer differs) and custom_io/models/base.py lines 20-21, 38, 55-56 (shuffle_state = notes rolled by one row across the batch)",
            "custom_io/PASS-MARKS.md lines 53-57 ('Wiring checks (hold by construction; they show the plumbing, not reasoning)')",
            "animations/model-explainer-build/chapters-out/ch09/g1-3m-s400-extract.json"
          ],
          "notes": "Same model and seed as the rest of the chapter (G-B2, 3M, seed 400), not the older design numbers in model-deep-dive.html (3.8% / 7.9%). 86.03 and 4.19 are on the 1,360 familiar-template questions only (the donor test's in_dist split; 1,170 right intact, 57 right with a donor's notes, 750 of 1,360 gave the donor's answer). 6.80 = 411/6040, intact 73.01. Shuffle is the notes rolled by one row (each question gets the next question's notes).",
          "scoreHead": "points out of 100"
        },
        {
          "id": "s08",
          "duration": 28,
          "heading": "Break the calculator, the answer breaks",
          "caption": [
            "Swap add and subtract inside the calculator, and the answers follow.",
            "Of 831 answers the swap changes, 830 followed it.",
            "Switch it off: the score is 0.0 on 2,085 questions that need it."
          ],
          "labels": {
            "thinker": "Thinker",
            "calc": "Calculator",
            "talker": "Talker",
            "add": "add",
            "sub": "subtract"
          },
          "illustration": "picture only",
          "cards": [
            {
              "title": "Add and subtract swapped",
              "value": 99.9,
              "sub": "830 of 831 followed the swap"
            },
            {
              "title": "Calculator off",
              "was": 100,
              "to": 0,
              "sub": "was 100.0"
            }
          ],
          "src": [
            "branch claude/8a-g-pc-results B2/RESULT.json extra.opswap (n_affected 831, swap_match 99.88, stays_intact 0.0) and extra.noexec (n 2085, intact 100.0, program_families 0.0)",
            "branch origin/claude/project-thread-qtxfp4 custom_io/models/ledger.py lines 640-695 (how noexec program rows and opswap affected rows are chosen) and custom_io/PASS-MARKS.md lines 66-67, 434-445",
            "animations/model-explainer-build/chapters-out/ch09/g1-3m-s400-extract.json"
          ],
          "notes": "830 of 831 = 99.88, shown as 99.9. 'Answers the swap changes' = chain-5 rows the intact model got right, answered by a calculator result, where swapping add and subtract changes that result (ledger.py swap_stats: aff). 'Questions that need it' = rows whose right answer is a calculator result (noexec program rows, n 2085): 100.0 with the calculator on, 0.0 off.",
          "scoreHead": "points out of 100"
        },
        {
          "id": "s09",
          "duration": 30,
          "heading": "A small leak with no thinking",
          "caption": [
            "At zero rounds a model should score near zero. Some runs did not.",
            "An earlier version, copy 200: with the borrowed Gemma reader 18.09, without it 1.40.",
            "Our copy 400: 0.96 here, 0.66 on all 6,040. Cause not settled."
          ],
          "subtitle": "points out of 100, zero rounds, familiar questions",
          "markLabel": "pass mark",
          "mark": 5,
          "rows": [
            {
              "label": "No Gemma, copy 200",
              "value": 1.4
            },
            {
              "label": "Gemma, copy 200",
              "value": 18.09
            },
            {
              "label": "This model, copy 400",
              "value": 0.96
            }
          ],
          "src": [
            "repo branch origin/claude/project-thread-qtxfp4 custom_io/PASS-MARKS.md addendum 14 (lines 339-367: 'read 18.09 at loops:0 in_dist (mark 5 limit 5; B2V 1.40)'; 'cause ... wrong'; loops:0 score varies widely across runs)",
            "custom_io/results/RESULTS-EG2.md (EGE seed 200 loops0 18.09; plain B2 1.40)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 items 2 and 4 ('cause not settled')",
            "branch claude/8a-g-pc-results B2/RESULT.json lesions.loops:0.in_dist: 13 right of 1360 = 0.96"
          ],
          "notes": "All three bars are the zero-round score on the familiar-template questions (in_dist, 1,360 questions per copy), not the 6,040-question pooled-5 (0.66). The seed-200 numbers come from the earlier version of the model (8 rounds, older settings), before the G1 fix; the seed-400 copy is G1 (12 rounds). 'Gemma' = EGE, B2 with the borrowed reader in front; 'No Gemma' = B2V on the same seed. 0.96 = 13/1360 (my division). Mark 5 = 'loops:0 in_dist <= 5' in PASS-MARKS addendum 4/14; big-run PLAN scorecard row 2 uses the same idea ('thinker-off <= half the full score')."
        },
        {
          "id": "s10",
          "duration": 37,
          "heading": "Side by side with a plain model",
          "caption": [
            "Ours scores 5.9 points more than the plain model (our subtraction: 73.01 minus 67.12).",
            "But it takes 2.7 times longer to train (our division: 6.51 by 2.38 hours).",
            "Add a calculator to the plain model, no retraining: 69.62 and 99.0. Gap: 3.39 points (our subtraction)."
          ],
          "heads": {
            "ours": "Ours, with thinker",
            "plain": "Plain model",
            "calc": "Plain + calculator"
          },
          "headSubs": {
            "ours": "3,544,913 numbers",
            "plain": "3,495,936 numbers",
            "calc": "added afterwards"
          },
          "table": [
            {
              "label": "Main test, of 100",
              "dec": 2,
              "ours": 73.01,
              "plain": 67.12,
              "calc": 69.62
            },
            {
              "label": "Multi-step, of 100",
              "dec": 1,
              "ours": 99.9,
              "plain": 91,
              "calc": 99
            },
            {
              "label": "Training hours",
              "dec": 2,
              "ours": 6.51,
              "plain": 2.38,
              "calc": null
            }
          ],
          "src": [
            "animations/source-g1-3m-s400.json (G-B2 3,544,913; 6.51 h; 73.01; chain5 99.9. G-PT 3,495,936; 2.38 h; 67.12; chain5 91.0)",
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md sec. 2 (G-PT: plain step model with the same Gemma front) and sec. 6 addendum A (sizes)",
            "branch claude/8a-g-pc-results PT/RESULT.json lesions.calc (pooled-5 4205/6040 = 69.62) and chain5.calc (99.0)",
            "custom_io/README.md and custom_io/models/plain_tf_steps.py line 2 ('calc' lesion: a calculator fills each a op b = while decoding, same weights, no retraining)"
          ],
          "notes": "5.9 = 73.01 - 67.12 = 5.89 (my subtraction). 2.7 = 6.51 / 2.38 = 2.735 (my division; the speed ratio 2.80 / 1.02 = 2.745 also gives 2.7). 3.39 = 73.01 - 69.62 (my subtraction). 69.62 = 4205/6040 summed from PT/RESULT.json lesions.calc over the five splits. The plain model writes its worked steps out as text and then the answer (plain_tf_steps_g, 4 layers, width 256). One copy, seed 400, 3M."
        },
        {
          "id": "s11",
          "duration": 28,
          "heading": "What this does not show",
          "caption": [
            "One copy at the smallest size is a first result, not proof.",
            "This is the older design, with 12 fixed rounds. It says nothing yet about bigger sizes."
          ],
          "rows": [
            {
              "kind": "tested",
              "label": "tested once",
              "text": "Smallest size, one copy"
            },
            {
              "kind": "placeholder",
              "label": "to come",
              "text": "Second copy and the 10M size"
            },
            {
              "kind": "untested",
              "label": "never tested",
              "text": "The finished design (learned stop)"
            },
            {
              "kind": "untested",
              "label": "unsettled",
              "text": "Why zero-round answers happen",
              "color": "warn"
            }
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 items 2, 4, 7 (G1 tests today's model: calculator inside, 12 fixed rounds; 'shown on one seed') and sec. 2 (Learned stop: built, never run)",
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md sec. 12-13 (addenda G, H: seed 401 and the 10M arms not yet in) and sec. 3 (mark 1 needs both sizes)",
            "big-run/PLAN.md scorecard row 2 ('shown at 3M, one seed ... Not yet at 10M, nor with Gemma and the outside calculator joined')"
          ],
          "notes": "Seed 401 (3M) and the 10M arms were still running or queued in the project notes of Oct 9; no result file for them existed on branch claude/8a-g-pc-results. 'Open question' chip is warn-orange on purpose."
        },
        {
          "id": "s12",
          "duration": 17,
          "heading": "What to remember",
          "caption": "Three things to remember.",
          "lines": [
            "Less thinking, lower score: 73.01 to 0.66.",
            "Multi-step answers fall first: 99.9 to 0.0 at one round.",
            "One copy, smallest size: first result, not proof."
          ],
          "src": [
            "animations/source-g1-3m-s400.json",
            "scenes s02 to s11 of this chapter"
          ],
          "scoreHead": "points out of 100"
        }
      ]
    }
  }
};
