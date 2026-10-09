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
    "ch00",
    "ch01",
    "ch02",
    "ch03",
    "ch04",
    "ch05",
    "ch06",
    "ch07",
    "ch08",
    "ch09",
    "ch10",
    "ch11",
    "ch12",
    "ch13",
    "ch14"
  ],
  "chapters": {
    "ch00": {
      "kicker": "Start here",
      "title": "What you are about to see",
      "blurb": "This project is building a small language model that thinks in careful steps. This first part shows what it is, how to read the colours and tags, and the words you will need.",
      "accent": "thinker",
      "scenes": [
        {
          "id": "s01",
          "duration": 40,
          "heading": "A research project, not a product",
          "caption": [
            {
              "at": 0.015,
              "text": "This is a research project. It is building a language model: a program that reads text and writes an answer."
            },
            {
              "at": 0.3733,
              "text": "The aim is a model that learns skills and careful step-by-step thinking from only a few examples."
            },
            {
              "at": 0.6856,
              "text": "It is not an app. The project page shows 0 releases, and nothing here is finished."
            }
          ],
          "labels": {
            "stages": [
              {
                "name": "plan only",
                "sub": "an idea on paper"
              },
              {
                "name": "built, never tested",
                "sub": "code, no real run"
              },
              {
                "name": "tested",
                "sub": "a result exists"
              },
              {
                "name": "released",
                "sub": "0 so far"
              }
            ],
            "zero": 0,
            "note": "These four boxes are the status tags you will see all video."
          },
          "src": [
            "creative-roadmap/gpt6pro-creative-roadmap-2026-10-06.md:30-31 (north star and other goals)",
            "memory/MEMORY.md:1 (project goals; CLAUDE.md was not available, see notes)",
            "animations/storyboards-2026-10-09.md:18-28 sec. 2 (research model, not an app; 0 releases, 0 tags, no sign-up)",
            "big-run/PLAN.md:77 (row 8)"
          ],
          "notes": "The four boxes are a picture of the status tags used in this video (glossary). 0 releases: storyboards sec. 2, GitHub shows 0 releases and 0 tags."
        },
        {
          "id": "s02",
          "duration": 26,
          "heading": "What it is trying to reach",
          "caption": [
            {
              "at": 0.0231,
              "text": "First goal: skills and careful step-by-step thinking. Shown at the smallest size, on six of six copies."
            },
            {
              "at": 0.4655,
              "text": "Second goal: learning from only a few examples. Only partly shown so far: brand-new kinds of rule are mostly missed."
            }
          ],
          "labels": {
            "steps": [
              {
                "t": "skills and careful thinking",
                "cl": "shown at 3M, earlier design"
              },
              {
                "t": "learning from few examples",
                "cl": "partly shown"
              }
            ]
          },
          "src": [
            "creative-roadmap/gpt6pro-creative-roadmap-2026-10-06.md:30-31",
            "big-run/PLAN.md:70 (row 1: (a) shown at 3M, B2 ahead of a plain transformer on 6 of 6 seeds; (b) partly, held-out families 0-4%, new kinds about 11%)"
          ],
          "notes": "Goal 1 and the 6-of-6 result belong to the older B2 design at 3M; the video says 'earlier design'."
        },
        {
          "id": "s03",
          "duration": 32,
          "heading": "The bigger goals",
          "caption": [
            {
              "at": 0.0187,
              "text": "Third goal: beat models of the same whole size. First race planned: SmolLM2-360M, a public model with 360 million numbers."
            },
            {
              "at": 0.3981,
              "text": "Models with 1 to 2 billion numbers come only after that, if funded."
            },
            {
              "at": 0.6637,
              "text": "Far goal: play Minecraft like a person. Eyes, hands and a game loop are not built."
            }
          ],
          "labels": {
            "steps": [
              {
                "t": "beat models of its size",
                "cl": "plan only"
              },
              {
                "t": "play Minecraft like a person",
                "cl": "plan only"
              }
            ],
            "later": "1 to 2 billion numbers: if funded"
          },
          "src": [
            "creative-roadmap/gpt6pro-creative-roadmap-2026-10-06.md:30-31",
            "big-run/PLAN.md:77 (row 8: race vs SmolLM2-360M, ahead by >= +3 on sealed sets; 1-2B models 'only after that, if Ben funds'; Minecraft untested; eyes, hands, game loop not built)"
          ],
          "notes": "'If funded' paraphrases 'if Ben funds'. Nothing here is dated."
        },
        {
          "id": "s04",
          "duration": 42,
          "heading": "How far away is the far goal?",
          "caption": [
            {
              "at": 0.0143,
              "text": "The plan's author gives two rough odds. They are a judgment, not a measurement."
            },
            {
              "at": 0.2543,
              "text": "About 1 in 3 that our design out-scales a plain model of the same size. So far there is one clean test, at the smallest size."
            },
            {
              "at": 0.6603,
              "text": "Well under 1 in 10 for the Minecraft goal itself, because eyes, hands and a game loop are not built."
            }
          ],
          "labels": {
            "rowA": "Beats a plain model of its size",
            "rowB": "Plays Minecraft like a person",
            "t0": "0",
            "t1": "1",
            "markA": "about 1 in 3",
            "zoneB": "well under 1 in 10",
            "chip": "judgment, not measured",
            "pic": "Picture of the odds, not data"
          },
          "src": [
            "big-run/PLAN.md:51 ('The 90% bar' paragraph: 'judgment, not measured'; about 1 in 3; well under 1 in 10; one clean 3M rung, 73.01 vs 67.12, a 10M answer still to come)"
          ],
          "notes": "Written by the plan's author on Oct 9. The dashed zone only shows 'below 1 in 10'; its exact size is not given in the source.",
          "illustration": "The scale line and markers are a picture of two judgments, not data."
        },
        {
          "id": "s05",
          "duration": 30,
          "heading": "The problem, in plain words",
          "caption": [
            {
              "at": 0.02,
              "text": "Most AI models are huge. They keep billions of learned numbers (called parameters) and read mountains of text."
            },
            {
              "at": 0.2997,
              "text": "We are testing the opposite: a small, clever design that thinks in rounds, one lap after another."
            },
            {
              "at": 0.5663,
              "text": "When it needs exact arithmetic, it asks an ordinary calculator instead of guessing."
            }
          ],
          "labels": {
            "big": "typical huge model",
            "bigSub": "billions of numbers, mountains of text",
            "small": "small design",
            "lap": "round",
            "calc": "calculator",
            "pic": "picture only"
          },
          "src": [
            "creative-roadmap/gpt6pro-creative-roadmap-2026-10-06.md:30-31 (goal is to beat 1-2B models at the same total size)",
            "architecture/FINISHED-MODEL-2026-10-09.md:15-20 (sec. 1: thinks in rounds, asks an outside calculator)",
            "brief ch00 point 2 (the problem in plain words)"
          ],
          "notes": "The tall stack is a picture of 'huge'; its height is not a measurement. 'Called parameters' is the one allowed use of the word (glossary).",
          "illustration": "The tower of cards is decoration; its height means nothing exact."
        },
        {
          "id": "s06",
          "duration": 42,
          "heading": "The whole machine in one picture",
          "caption": [
            {
              "at": 0.0143,
              "text": "The reader reads the question once and gives each letter a meaning. We borrowed it and cannot change it."
            },
            {
              "at": 0.2234,
              "text": "The thinker thinks in rounds. Its settings were set from scratch by our own practice."
            },
            {
              "at": 0.3952,
              "text": "The calculator is ordinary code, not AI. It gets a request as text and replies with text."
            },
            {
              "at": 0.5856,
              "text": "The stop switch says done. It is built, but was never run."
            },
            {
              "at": 0.7293,
              "text": "The talker writes the final answer. Today it is only a small stand-in."
            }
          ],
          "labels": {
            "jobs": [
              "reads the question",
              "thinks in rounds",
              "does exact sums",
              "says when done",
              "writes the answer"
            ],
            "chip": "stand-in today"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:15-20 and table lines 31-38 (sec. 1-2)"
          ],
          "notes": "Part boxes come from S.modelMap (sub-labels fixed by the kit). Talker: 'today a small stand-in; the English talker is unbuilt' (line 38)."
        },
        {
          "id": "s07",
          "duration": 44,
          "heading": "Borrowed or ours? Counting the numbers",
          "caption": [
            {
              "at": 0.014,
              "text": "Every model is a long list of learned numbers. The borrowed reader has 271,002,624 of them, frozen: our practice never changes them."
            },
            {
              "at": 0.3551,
              "text": "Everything we train is planned at 102.1 million numbers. Add the two: 373.1 million, without the unbuilt English talker."
            },
            {
              "at": 0.656,
              "text": "The calculator adds zero learned numbers: it is plain code. This 100M-size model is planned; it has not been trained yet."
            }
          ],
          "labels": {
            "rows": [
              {
                "label": "Borrowed reader",
                "value": 271
              },
              {
                "label": "Ours, trained",
                "value": 102.1
              },
              {
                "label": "Total, no talker",
                "value": 373.1
              }
            ],
            "unit": "million numbers",
            "big": 271002624,
            "bigSub": "numbers in the borrowed reader",
            "chip": "planned size, not trained yet",
            "note": "Not counted: unbuilt 25 million talker (about 397 million with it)."
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:21-22 (about 397M planned in all, borrowed parts counted; B3 group 1 at the 100M rung, as built, = 373.1M whole = 102.1M trained + 271.0M frozen Gemma, because the 25M English talker is not built)",
            "architecture/FINISHED-MODEL-2026-10-09.md:31 and 37 (reader 271,002,624, borrowed, frozen; calculator 0)"
          ],
          "notes": "271.0 + 102.1 = 373.1, as written in the source (line 22); 373.1 leaves out the unbuilt 25M English talker, and the whole plan is about 397M (line 21), so 373.1 is not called the planned total. The 100M run has not been run; tested sizes are 3M."
        },
        {
          "id": "s08",
          "duration": 41,
          "heading": "One picture for the whole video",
          "caption": [
            {
              "at": 0.0146,
              "text": "One picture runs through the whole video: a student doing a word problem."
            },
            {
              "at": 0.214,
              "text": "A translator reads the question. A team of note-takers thinks it over, round after round."
            },
            {
              "at": 0.4378,
              "text": "The team leader writes a request slip. A pocket calculator hands back a slip with the result."
            },
            {
              "at": 0.686,
              "text": "A little bell rings when they are done. One person writes the final answer. Each colour always means the same part."
            }
          ],
          "labels": {
            "cards": [
              {
                "t": "Reader",
                "p": "a borrowed translator"
              },
              {
                "t": "Thinker",
                "p": "note-takers passing notes"
              },
              {
                "t": "Call writer",
                "p": "writes a request slip"
              },
              {
                "t": "Calculator",
                "p": "pocket calculator"
              },
              {
                "t": "Stop switch",
                "p": "a little bell"
              },
              {
                "t": "Talker",
                "p": "writes the answer"
              }
            ]
          },
          "src": [
            "kit/GLOSSARY.md (the one analogy table)",
            "architecture/FINISHED-MODEL-2026-10-09.md:31-38 (part names)"
          ],
          "notes": "The student analogy is the project's shared teaching picture (glossary), not a measurement.",
          "illustration": "The cards are an analogy, not a diagram of the code."
        },
        {
          "id": "s09",
          "duration": 36,
          "heading": "How sure are we? Three tags",
          "caption": [
            {
              "at": 0.0167,
              "text": "Green: tested. A result file exists. Example: the calculator helper matched the old model over six copies, at the smallest size."
            },
            {
              "at": 0.2825,
              "text": "Amber: built, but never tested. The code exists, but no real training run was ever done. Example: the stop switch."
            },
            {
              "at": 0.5374,
              "text": "Grey: placeholder. It does not exist yet. Example: the English talker."
            }
          ],
          "labels": {
            "rows": [
              {
                "name": "the calculator helper",
                "sub": "matched the old model, 6 copies"
              },
              {
                "name": "the stop switch",
                "sub": "code exists, no real run"
              },
              {
                "name": "the English talker",
                "sub": "about 25M planned, not built"
              }
            ]
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:106 (sec. 5 item 1: T1SDR matched B2 over 6 seeds)",
            "architecture/FINISHED-MODEL-2026-10-09.md:36 (stop switch built, never run)",
            "architecture/FINISHED-MODEL-2026-10-09.md:38 (English talker unbuilt, about 25M planned)",
            "kit/GLOSSARY.md (status chips)"
          ],
          "notes": "Amber is the kit's 'untested' chip (built, never tested)."
        },
        {
          "id": "s10",
          "duration": 35,
          "heading": "Who wrote it? Hand-written or learned",
          "caption": [
            {
              "at": 0.0171,
              "text": "Brown means hand-written: a person typed the code. The calculator is like this. Send it sub 12 5 and it sends back 7."
            },
            {
              "at": 0.3598,
              "text": "Blue means learned: found by the model's own practice, not typed by a person. The thinker's numbers are like this."
            },
            {
              "at": 0.6634,
              "text": "Project rule: everything inside the model is learned. Hand-written code may only run as a tool the model chooses to call."
            }
          ],
          "labels": {
            "call": "sub 12 5",
            "calc": "calculator",
            "reply": "7",
            "vecLabel": "the thinker's numbers",
            "ex": "made-up example",
            "pic": "picture only"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:37 (calculator: hand code, allowed as a tool)",
            "architecture/FINISHED-MODEL-2026-10-09.md:34 (thinker: learned from scratch)",
            "architecture/FINISHED-MODEL-2026-10-09.md:73 (Ben's rules 10-07: everything inside the model is learned; hand code only inside a tool the model calls)",
            "kit/GLOSSARY.md:26 (call `sub 12 5`, reply `7`, shown as `sub 12 5 = 7`); architecture/FINISHED-MODEL-2026-10-09.md:18 (calculator call such as `sub 12 5`)"
          ],
          "notes": "'sub 12 5 = 7' is the project's own example line (glossary); it is not a measured result.",
          "illustration": "The shaded strip is decoration: the shading means nothing."
        },
        {
          "id": "s11",
          "duration": 25,
          "heading": "Two words: vector and round",
          "caption": [
            {
              "at": 0.024,
              "text": "A vector is a list of numbers, like a note card. The reader turns each letter into one."
            },
            {
              "at": 0.498,
              "text": "A round is one lap: look at the whole question, pass notes, think. The thinker does several laps."
            }
          ],
          "labels": {
            "word": "cat",
            "vecLabel": "one letter, one note card",
            "steps": [
              "look",
              "pass notes",
              "think"
            ],
            "lap": "round",
            "pic": "picture only"
          },
          "src": [
            "kit/GLOSSARY.md (vector, round)",
            "architecture/FINISHED-MODEL-2026-10-09.md:31 (each letter gets the 768-number state of the Gemma token it sits in)"
          ],
          "notes": "The shading of the strip is decoration. The lap counter 1 to 3 only illustrates; real runs use more rounds.",
          "illustration": "The shaded strip and the 1-2-3 lap counter are illustrations."
        },
        {
          "id": "s12",
          "duration": 32,
          "heading": "Two more words: call and reply",
          "caption": [
            {
              "at": 0.0187,
              "text": "A call is a request to the calculator, written as text. Here, sub 12 5 means: take 5 away from 12."
            },
            {
              "at": 0.3835,
              "text": "The reply is the calculator's answer, also text: 7. Together they read sub 12 5 = 7."
            },
            {
              "at": 0.6883,
              "text": "The model writes calls itself. It may also write nothing, when no exact arithmetic is needed."
            }
          ],
          "labels": {
            "callL": "call",
            "calcL": "calculator",
            "replyL": "reply",
            "call": "sub 12 5",
            "reply": "7",
            "line": "sub 12 5 = 7",
            "ex": "made-up example"
          },
          "src": [
            "kit/GLOSSARY.md:26 (call, reply)",
            "architecture/FINISHED-MODEL-2026-10-09.md:35 and 37 (call writer picks 1 of 8 operations or no call; calculator replies as text)"
          ],
          "notes": "The numbers 12, 5 and 7 are the glossary's example, not a result."
        },
        {
          "id": "s13",
          "duration": 28,
          "heading": "Two more words: practice and kept aside",
          "caption": [
            {
              "at": 0.0214,
              "text": "Practice: the model tries a question, is told the right answer, and every setting is nudged a tiny bit. One nudge is one update."
            },
            {
              "at": 0.5462,
              "text": "Questions kept aside are never used in practice. They are saved for the exam, so the score is fair."
            }
          ],
          "labels": {
            "steps": [
              "try",
              "told the answer",
              "nudge"
            ],
            "upd": "update",
            "practice": "practice pile",
            "aside": "kept-aside pile",
            "pic": "picture only"
          },
          "src": [
            "kit/GLOSSARY.md (practice / training, update, held-out / kept aside)"
          ],
          "notes": "Counts of cards and updates are illustrative only.",
          "illustration": "The cards and the update counter are a picture, not real counts."
        },
        {
          "id": "s14",
          "duration": 36,
          "heading": "Score and copy",
          "caption": [
            {
              "at": 0.0167,
              "text": "A score is points out of 100: the share of questions answered right. Here, 73.01 points on 6,040 questions kept aside."
            },
            {
              "at": 0.2825,
              "text": "A copy is one separate run of the model from its own random start. Six copies are six chances to see the same result."
            },
            {
              "at": 0.5811,
              "text": "Careful: 73.01 is one copy, at the smallest size, on an earlier design."
            }
          ],
          "labels": {
            "num": 73.01,
            "outOf": "points out of 100",
            "over": "6,040 questions kept aside",
            "chip": "tested",
            "copies": [
              "A",
              "B",
              "C",
              "D",
              "E",
              "F"
            ],
            "copyW": "copy",
            "copyNote": "picture only",
            "careful": "one copy, 3M, earlier design"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:109-110 (sec. 5 item 2: G1 first finished run, 3M, seed 400: 73.01 thinker on)",
            "big-run/PLAN.md:70 and :51 (G-B2 73.01 vs G-PT 67.12 on one seed)",
            "kit/GLOSSARY.md:62 and :78 (pooled-5 = the 6,040 questions kept aside, five kinds pooled into one score out of 100); kit/GLOSSARY.md (score, seed/copy)",
            "big-run/PLAN.md:223 (pooled-5 on the 6,040 dev rows; G1's 3M lead for G-B2 over G-PT was +5.9 on one seed, i.e. 73.01 vs 67.12)"
          ],
          "notes": "73.01 is seed 400 at 3M (G1 first finished run). Other chapters call it the older 12-round design; here 'earlier design'.",
          "illustration": "The six copy boxes are a picture of the idea; they are not six real results."
        },
        {
          "id": "s15",
          "duration": 35,
          "heading": "The plain model: our yardstick",
          "caption": [
            {
              "at": 0.0171,
              "text": "A plain model is an ordinary model of the same size, trained on the same practice. It is the yardstick we compare against."
            },
            {
              "at": 0.3742,
              "text": "On the same 6,040 questions kept aside, the plain model scored 67.12 and ours scored 73.01."
            },
            {
              "at": 0.6365,
              "text": "Careful: this is one copy, at the smallest size, on an earlier design. We do not claim it holds at bigger sizes."
            }
          ],
          "labels": {
            "rows": [
              {
                "label": "Ours",
                "value": 73.01
              },
              {
                "label": "Plain",
                "value": 67.12
              }
            ],
            "unit": "points out of 100",
            "chip": "tested",
            "care": "one copy, 3M, earlier design"
          },
          "src": [
            "big-run/PLAN.md:70 (G-B2 73.01 vs G-PT 67.12 on one seed)",
            "big-run/PLAN.md:51 (one clean 3M rung, 73.01 vs 67.12, a 10M answer still to come)",
            "architecture/FINISHED-MODEL-2026-10-09.md:109-110",
            "kit/GLOSSARY.md:62 and :78 (pooled-5 = the 6,040 questions kept aside)",
            "big-run/PLAN.md:223 (pooled-5 on the 6,040 dev rows; G1's 3M lead for G-B2 over G-PT was +5.9 on one seed)"
          ],
          "notes": "No difference is computed in the video. The 6,040 size is the pooled-5 held-out set (glossary lines 62 and 78; PLAN line 223)."
        },
        {
          "id": "s16",
          "duration": 44,
          "heading": "What the video contains: chapters 1 to 5",
          "caption": [
            {
              "at": 0.0136,
              "text": "Chapter 1 follows one question through all five parts, from the first letter to the final answer."
            },
            {
              "at": 0.1954,
              "text": "Chapter 2: what we are trying to prove, and the rules of the game."
            },
            {
              "at": 0.3504,
              "text": "Chapter 3: how the borrowed reader gives each letter a meaning."
            },
            {
              "at": 0.4786,
              "text": "Chapter 4: how the thinker works in rounds of looking and passing notes."
            },
            {
              "at": 0.6247,
              "text": "Chapter 5: how a call asks the calculator for exact sums."
            }
          ],
          "labels": {
            "rows": [
              {
                "id": "ch01",
                "title": "One question, start to finish"
              },
              {
                "id": "ch02",
                "title": "What we are trying to prove"
              },
              {
                "id": "ch03",
                "title": "The reader: giving every letter a meaning"
              },
              {
                "id": "ch04",
                "title": "The thinker: rounds of looking and passing notes"
              },
              {
                "id": "ch05",
                "title": "Asking the calculator for help"
              }
            ]
          },
          "src": [
            "kit/briefs/ch00.md:14-16 (brief point 6: the 14 chapters after this one, ch01 to ch14, with plain titles taken from content/global.json order and the briefs)",
            "chapters-out/ch01, ch03, ch04, ch05, ch06, ch09 (chNN/chNN.json delivered chapter titles; ch08 is not delivered yet)"
          ],
          "notes": "Titles of ch01, ch03, ch04, ch05 are the delivered chapter titles; ch02 uses the brief title (brief titles differ slightly for ch01, ch03, ch04, ch05, ch06, ch09; delivered titles used)."
        },
        {
          "id": "s17",
          "duration": 38,
          "heading": "What the video contains: chapters 6 to 10",
          "caption": [
            {
              "at": 0.0158,
              "text": "Chapter 6: how the stop switch decides it is done. Built, never tested."
            },
            {
              "at": 0.1849,
              "text": "Chapter 7: how the talker writes the answer. Today only a placeholder."
            },
            {
              "at": 0.3437,
              "text": "Chapter 8: how the model learns, one small nudge at a time."
            },
            {
              "at": 0.5025,
              "text": "Chapter 9: if we turn the thinking down, does the score fall?"
            },
            {
              "at": 0.6613,
              "text": "Chapter 10: how the tests are kept fair."
            }
          ],
          "labels": {
            "rows": [
              {
                "id": "ch06",
                "title": "Deciding when it is done",
                "cl": "never tested"
              },
              {
                "id": "ch07",
                "title": "The talker",
                "cl": "placeholder"
              },
              {
                "id": "ch08",
                "title": "How it learns"
              },
              {
                "id": "ch09",
                "title": "Does the thinking really do the work?"
              },
              {
                "id": "ch10",
                "title": "How we test fairly"
              }
            ]
          },
          "src": [
            "kit/briefs/ch00.md:14-16 (brief point 6: the 14 chapters after this one, ch01 to ch14, with plain titles taken from content/global.json order and the briefs)",
            "chapters-out/ch01, ch03, ch04, ch05, ch06, ch09 (chNN/chNN.json delivered chapter titles; ch08 is not delivered yet)",
            "architecture/FINISHED-MODEL-2026-10-09.md:36, :38 (stop switch never run; English talker unbuilt)"
          ],
          "notes": "ch06 and ch09 use delivered titles; ch07, ch08, ch10 use the brief titles (brief titles differ slightly for ch06 and ch09; delivered titles used)."
        },
        {
          "id": "s18",
          "duration": 28,
          "heading": "What the video contains: chapters 11 to 14",
          "caption": [
            {
              "at": 0.0214,
              "text": "Chapter 11: sleep, a night study session. Research only so far."
            },
            {
              "at": 0.2229,
              "text": "Chapter 12: ideas built or planned, none of them proven yet."
            },
            {
              "at": 0.4244,
              "text": "Chapter 13: does a bigger model help?"
            },
            {
              "at": 0.5697,
              "text": "Chapter 14: what is proven, what is not, and what comes next."
            }
          ],
          "labels": {
            "rows": [
              {
                "id": "ch11",
                "title": "Sleep",
                "cl": "research only"
              },
              {
                "id": "ch12",
                "title": "Ideas being tried",
                "cl": "not yet proven"
              },
              {
                "id": "ch13",
                "title": "Does bigger help?"
              },
              {
                "id": "ch14",
                "title": "Where we stand"
              }
            ]
          },
          "src": [
            "kit/briefs/ch00.md:14-16 (brief point 6: the 14 chapters after this one, ch01 to ch14, with plain titles taken from content/global.json order and the briefs)",
            "chapters-out/ch01, ch03, ch04, ch05, ch06, ch09 (chNN/chNN.json delivered chapter titles; ch08 is not delivered yet)",
            "big-run/PLAN.md:70 (sleep lifts first try with our scripts, never on the finished design)"
          ],
          "notes": "ch11 to ch14 use the brief titles (those chapters were not delivered when this was written)."
        },
        {
          "id": "s19",
          "duration": 31,
          "heading": "Our promise to you",
          "caption": [
            {
              "at": 0.0194,
              "text": "Every number in this video comes from a project file. Look for the small file tag beside it."
            },
            {
              "at": 0.349,
              "text": "Pictures that only illustrate carry a tag: picture only, or made-up example. They are never measurements."
            },
            {
              "at": 0.6478,
              "text": "What is not proven stays amber or grey. Nothing here is released, and no future date is promised."
            }
          ],
          "labels": {
            "num": 67.12,
            "tag": "big-run/PLAN.md, line 70",
            "chipA": "picture only",
            "chipB": "made-up example",
            "chipC": "built, never tested",
            "chipD": "plan only",
            "rel": "released: 0"
          },
          "src": [
            "big-run/PLAN.md:70 (67.12 is the plain model's score)",
            "animations/storyboards-2026-10-09.md:18-28 (0 releases)",
            "brief ch00 point 7 (the honesty promise)"
          ],
          "notes": "The file tag shows how every number in the video is checked against its source."
        },
        {
          "id": "s20",
          "duration": 30,
          "heading": "What to remember",
          "caption": [
            {
              "at": 0.02,
              "text": "This is a research project, not a product. Nothing is finished or released."
            },
            {
              "at": 0.2849,
              "text": "Five parts do the work: reader, thinker, calculator, stop switch, talker. Some are tested; some are not."
            },
            {
              "at": 0.6146,
              "text": "Every claim wears its status, and the far goal is far. Now, chapter 1: one question, start to finish."
            }
          ],
          "labels": {
            "cards": [
              {
                "n": "1",
                "t": "Research, not a product"
              },
              {
                "n": "2",
                "t": "Five parts, one machine"
              },
              {
                "n": "3",
                "t": "Every claim wears its status"
              }
            ]
          },
          "src": [
            "animations/storyboards-2026-10-09.md:18-28",
            "architecture/FINISHED-MODEL-2026-10-09.md:15-20, :31-38",
            "big-run/PLAN.md:51"
          ],
          "notes": "Recap only; no new numbers."
        }
      ]
    },
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
    "ch02": {
      "kicker": "Part 2 of 14",
      "title": "The goal and the rules of the game",
      "blurb": "What the team wants this model to become, and the rules it set for itself so that its results can be trusted.",
      "accent": "thinker",
      "scenes": [
        {
          "id": "s01",
          "duration": 27,
          "heading": "The goal: think first, then talk",
          "caption": [
            {
              "at": 0.026,
              "text": "The model should think first and talk second."
            },
            {
              "at": 0.206,
              "text": "It should learn from a few examples."
            },
            {
              "at": 0.373,
              "text": "It should beat models of its whole size."
            },
            {
              "at": 0.554,
              "text": "One day, it should beat Minecraft like a person."
            }
          ],
          "labels": {
            "g1": "Think first",
            "g2": "Learn from few examples",
            "g3": "Beat its whole size",
            "g4": "Minecraft, like a person",
            "c1": "tested, 3M, earlier design",
            "c2": "partly shown",
            "c3": "never tested",
            "c4": "plan only"
          },
          "src": [
            "big-run/PLAN.md line 70 (scorecard row 1: think first, talk second; learns from a few examples; B2 +20.3 over a plain transformer, 6 of 6 seeds, 3M)",
            "big-run/PLAN.md line 77 (row 8: beat models of its whole size; Minecraft; untested)"
          ],
          "notes": "Row 1 (a) skills is shown at 3M for the earlier design B2; (b) few examples is partly shown; (c) talking is untested. Row 8 is untested. Minecraft is a plan only."
        },
        {
          "id": "s02",
          "duration": 34,
          "heading": "The race, in three steps",
          "caption": [
            {
              "at": 0.021,
              "text": "Step one: race SmolLM2-360M, a rival with 360 million numbers."
            },
            {
              "at": 0.177,
              "text": "Pass mark: ahead by 3 points or more on questions kept aside, and ahead on bAbI."
            },
            {
              "at": 0.396,
              "text": "Rivals with 1 to 2 billion numbers come only later."
            },
            {
              "at": 0.553,
              "text": "The race has never run: the English talker it needs is not built."
            }
          ],
          "labels": {
            "s1": "Race a 360 million rival",
            "s2": "Then 1 to 2 billion",
            "s3": "Far goal: Minecraft",
            "c1": "never run",
            "c2": "later, if funded",
            "c3": "plan only",
            "pass": "ahead by 3+ points"
          },
          "src": [
            "big-run/PLAN.md line 77 (row 8: ahead of SmolLM2-360M by >= +3 on sealed sets and ahead on bAbI; 1-2B only after that, if funded; eyes, hands, game loop not built)",
            "big-run/PLAN.md line 284 (R4: race the 350M-600M size class first)",
            "whole-model-roadmap/whole-model-roadmap-2026-10-06.md lines 85-86 (the race against 350M-600M models is the first gate)"
          ],
          "notes": "Source says 1-2B models only after the size-class race, if the project owner funds it. No money amount shown."
        },
        {
          "id": "s03",
          "duration": 34,
          "heading": "Whole size counts everything",
          "caption": [
            {
              "at": 0.021,
              "text": "Size counts every number that runs, borrowed ones too."
            },
            {
              "at": 0.191,
              "text": "As built: the borrowed reader holds 271,002,624 numbers, and our learned parts hold 102.1 million."
            },
            {
              "at": 0.426,
              "text": "Together that is 373.1 million."
            },
            {
              "at": 0.553,
              "text": "Planned, parts rounded: reader about 271 million, thinker about 100, talker about 25. The plan says about 397 million."
            }
          ],
          "labels": {
            "reader": "reader, borrowed",
            "learned": "learned by us",
            "pr": "reader",
            "pt": "thinker",
            "pk": "talker",
            "tot1": "as built",
            "tot2": "planned (parts rounded)",
            "c1": "counted, not trained yet",
            "c2": "talker not built"
          },
          "nums": {
            "reader": 271,
            "learned": 102.1,
            "total": 373.1,
            "pr": 271,
            "pt": 100,
            "pk": 25,
            "planned": 397
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md lines 21-23 (about 397M planned = reader about 271M + thinker about 100M + talker about 25M; 373.1M whole as built = 102.1M trained + 271.0M frozen Gemma; talker not built)",
            "architecture/FINISHED-MODEL-2026-10-09.md line 31 (reader 271,002,624)",
            "architecture/FINISHED-MODEL-2026-10-09.md lines 130-131 (size counts every weight that runs, borrowed included)"
          ],
          "notes": "373.1 is as written in the source (271.0 + 102.1). The planned row is the source's own rounded split (reader about 271M, thinker about 100M, talker about 25M, about 397M in all); the three rounded parts add to 396, so the screen says 'parts rounded' beside the 397. It is not 373.1 plus 25, because the plan counts the thinker as about 100M. big-run/PLAN.md line 26 says about 398M; FINISHED-MODEL (source of truth) says about 397M, so 397 is shown. Not trained at the 100M rung yet. Bar lengths are drawn to scale of the millions shown."
        },
        {
          "id": "s04",
          "duration": 34,
          "heading": "The size bar: gain more from size",
          "caption": [
            {
              "at": 0.021,
              "text": "The team's rule: with more numbers, our design must gain more than a plain model does."
            },
            {
              "at": 0.233,
              "text": "A plain model is a standard model of the same whole size, practised the same way."
            },
            {
              "at": 0.445,
              "text": "The check climbs a ladder of sizes."
            },
            {
              "at": 0.563,
              "text": "Not shown yet for the finished design: earlier runs had a bug, so they do not count."
            }
          ],
          "labels": {
            "ours": "our design",
            "plain": "plain model",
            "size": "size",
            "score": "score",
            "r1": "3M",
            "r2": "10M",
            "r3": "30M",
            "r4": "100M",
            "pic": "picture only, not measured",
            "c1": "not shown yet"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md lines 125-129 (item 7: the finished design must pass the size bar itself; earlier 8a ladder runs had the register bug and do not count either way)",
            "memory/MEMORY.md line 18 (scaling bar: gain more from extra parameters than the plain model)",
            "big-run/PLAN.md line 72 (scorecard row 3: untested for the model as specified)",
            "whole-model-roadmap/whole-model-roadmap-2026-10-06.md lines 438-439 (every claim is against a plain model of the same whole size, same data)"
          ],
          "notes": "The two lines are an illustration. The real earlier numbers belong to a later part."
        },
        {
          "id": "s05",
          "duration": 34,
          "heading": "Inside: learned. Outside: hand code",
          "caption": [
            {
              "at": 0.021,
              "text": "The team's rule: everything inside the model is learned."
            },
            {
              "at": 0.159,
              "text": "Hand-written code may run only as a tool the model chooses to call, like the calculator."
            },
            {
              "at": 0.371,
              "text": "A deployed model must do its own learning, sleeping (night study), stopping and picking."
            },
            {
              "at": 0.563,
              "text": "Not finished: some hand-written steps are still on the answer path."
            }
          ],
          "labels": {
            "frame": "the model: all learned",
            "r": "reader",
            "t": "thinker",
            "cw": "call writer",
            "s": "stop switch",
            "k": "talker",
            "calc": "calculator",
            "call": "call",
            "reply": "reply",
            "c1": "hand-written, outside tool",
            "c2": "borrowed",
            "warn": "some hand-written steps still inside"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md lines 71-77 (rules of 10-07; the calculator, Gemma and safety caps are allowed and stay)",
            "no-hardcoding/PLAN-AND-MARKS-2026-10-07.md lines 19-23 (hand code only inside a tool the model calls; the deployed model does the rest itself)",
            "big-run/PLAN.md line 73 (scorecard row 4: red today; hand-written parts left)"
          ],
          "notes": "The reader is borrowed and frozen, not learned by us; it is allowed by the project owner's choice. The list of hand-written pieces still to replace belongs to a later part."
        },
        {
          "id": "s06",
          "duration": 35,
          "heading": "Rules so the practice stays honest",
          "caption": [
            {
              "at": 0.02,
              "text": "No practice answer is ever cut short."
            },
            {
              "at": 0.134,
              "text": "Pass marks are written down before a run."
            },
            {
              "at": 0.259,
              "text": "Questions kept aside for the exam are never practised on."
            },
            {
              "at": 0.404,
              "text": "No new teacher: only the 171,940 teaching rows we have, plus human-written web text."
            },
            {
              "at": 0.589,
              "text": "A win claim needs 6 or more paired copies. A 2-copy screen only decides whether to try."
            }
          ],
          "labels": {
            "r1": "No cut-off answers",
            "r2": "Marks first",
            "r3": "Exam kept aside",
            "r4": "No new teacher",
            "r5": "6 paired copies",
            "t4": "teaching rows",
            "pic": "picture only"
          },
          "src": [
            "no-hardcoding/PLAN-AND-MARKS-2026-10-07.md line 68 (nothing is cut off: standing rule)",
            "whole-model-roadmap/whole-model-roadmap-2026-10-06.md lines 431-432 (marks before the run; 6 or more paired seeds, 2-seed screens only decide whether to confirm)",
            "whole-model-roadmap/whole-model-roadmap-2026-10-06.md lines 442-448 (no new teacher; 171,940 TEACH rows; never score on or touch the protected panels)",
            "architecture/FINISHED-MODEL-2026-10-09.md line 147 (web pool gated by protected-panel hash checks)"
          ],
          "notes": "These are the team's own rules, not outside standards. 'Paired' means each copy is compared with a plain-model copy.",
          "nums": {
            "teach": 171940
          }
        },
        {
          "id": "s07",
          "duration": 40,
          "heading": "Where the rules slipped, said plainly",
          "caption": [
            {
              "at": 0.017,
              "text": "Earlier runs cut some practice answers to 8 letters: a bug."
            },
            {
              "at": 0.187,
              "text": "The fix run reported 0 rows cut, on both copies."
            },
            {
              "at": 0.347,
              "text": "A calculator-test leak mark was missed as written. The project owner cleared it on Oct 9."
            },
            {
              "at": 0.552,
              "text": "One copy's saved model was lost, so that copy is unscored."
            }
          ],
          "labels": {
            "a": "Cut-off answers",
            "a1": "rows with longer answers",
            "a2": "rows in the practice pool",
            "b": "Leak check",
            "b1": "leak, lowest",
            "b2": "leak, highest",
            "b3": "limit",
            "c": "Lost copy",
            "c1": "calculator-test copies",
            "c2": "saved model lost",
            "tag": "said plainly",
            "a3": "0 rows cut now, as reported"
          },
          "nums": {
            "long": 191172,
            "pool": 1655902,
            "lo": 5,
            "hi": 5.6,
            "lim": 5,
            "copies": 6,
            "lost": 1
          },
          "src": [
            "big-run/PLAN.md line 75 (row 6: register bug cut answers to 8 letters; 191,172 of 1,655,902 pool rows have longer answers; G1 seeds 400 and 401 pass the audit with 0 rows over caps)",
            "no-hardcoding/PLAN-AND-MARKS-2026-10-07.md line 95 (donor leak 5.0-5.6 against <= 5; cleared by the project owner 8:21 AM ET 10-09; not a pass by the sealed marks alone)",
            "architecture/FINISHED-MODEL-2026-10-09.md lines 107-108 (seed 205 unscored because its checkpoint was lost)"
          ],
          "notes": "Leak = answers right with the thinking turned off. 5.0 to 5.6 is the range over copies in the calculator test (T1SDR). Not the same leak test as in other parts."
        },
        {
          "id": "s08",
          "duration": 36,
          "heading": "The spend rule: one big proven run",
          "caption": [
            {
              "at": 0.019,
              "text": "The team's rule: spend big only on a run that demonstrably works, not on many small tests."
            },
            {
              "at": 0.23,
              "text": "So it climbs a size ladder on the project's own PC and Macs. No rented machines now."
            },
            {
              "at": 0.44,
              "text": "The 100 million run waits for the Oct 31 readout, planned."
            },
            {
              "at": 0.591,
              "text": "Estimate for that run: 3 to 6 weeks on the PC alone."
            }
          ],
          "labels": {
            "k1": "3M",
            "k2": "10M",
            "k3": "30M",
            "k4": "readout",
            "k5": "100M run",
            "c1": "planned",
            "c2": "planned",
            "mach": "project PC (16 GB) and Mac laptops",
            "wk": "3 to 6 weeks, estimate"
          },
          "src": [
            "big-run/PLAN.md lines 3-4 (one big proven run, not a bunch of little tests)",
            "big-run/PLAN.md lines 26, 43-44 (ladder 3M, 10M, 30M then 100M; Oct 31 readout; 100M run 3 to 6 weeks on the PC alone, suggested)",
            "memory/MEMORY.md lines 10-11 (no rentals; Mac and 5070 Ti PC only)"
          ],
          "notes": "Dates are suggested in the source, so the video says planned. No money amount is shown on purpose."
        },
        {
          "id": "s09",
          "duration": 34,
          "heading": "How sure is the team? Not 90% yet",
          "caption": [
            {
              "at": 0.021,
              "text": "The 90% bar: no weeks-long step starts until the team can truthfully say it is 90% sure the run does what its marks say."
            },
            {
              "at": 0.324,
              "text": "The plan's own judgement, not measured: about 1 in 3 that the design out-scales a plain model."
            },
            {
              "at": 0.553,
              "text": "For the Minecraft goal: well under 1 in 10."
            }
          ],
          "labels": {
            "b1": "out-scales a plain model",
            "b2": "Minecraft goal",
            "bar": "90% bar",
            "v1": "about 1 in 3",
            "v2": "under 1 in 10",
            "judge": "judgement, not measured"
          },
          "src": [
            "big-run/PLAN.md line 51 (the 90% bar; about 1 in 3 out-scales; well under 1 in 10 for Minecraft; judgement, not measured)"
          ],
          "notes": "Bar for 'about 1 in 3' is drawn at one third of the scale only as a picture of 1 in 3; the source gives no exact percent. 'Under 1 in 10' is drawn as a short bar under a tenth of the scale. Both bars are the plan's own judgement, not measured."
        },
        {
          "id": "s10",
          "duration": 45,
          "heading": "The scorecard: nine goals, none green yet",
          "caption": [
            {
              "at": 0.016,
              "text": "The plan keeps a scorecard of nine goals, each with a pass mark written in advance."
            },
            {
              "at": 0.198,
              "text": "Part-way shown: skills, its own thinking, running itself, honest practice, creativity, new domains."
            },
            {
              "at": 0.354,
              "text": "Red: hand-written parts still sit on the answer path. Untested: bigger helps more, and beating its whole size."
            },
            {
              "at": 0.552,
              "text": "Today, none of the nine is fully green."
            }
          ],
          "src": [
            "big-run/PLAN.md lines 62-88 (scorecard table, nine rows, status column)",
            "big-run/PLAN.md line 80 (Today: 0 of 9 fully green; part-green 1, 2, 5, 6, 7 and row 9 partly; red 4)",
            "big-run/PLAN.md lines 70-78 (rows 3 and 8 untested)"
          ],
          "notes": "Row names are our short plain-word versions of the nine principles in the PLAN scorecard (1 think first / few examples; 2 its own brain thinks; 3 bigger helps more; 4 nothing hand-coded inside; 5 runs itself; 6 no shortcuts in training; 7 creative when stuck; 8 beat models of its whole size / Minecraft; 9 learns a new domain by itself). Colours follow the 'Status today' column: part-green rows 1, 2, 5, 6, 7 and 9 (row 9 'partly'), red row 4, untested rows 3 and 8. Half-filled squares are a picture of 'partly', not a measurement.",
          "rows": [
            {
              "name": "Think first",
              "st": "part"
            },
            {
              "name": "Own thinking",
              "st": "part"
            },
            {
              "name": "Bigger helps",
              "st": "none"
            },
            {
              "name": "No hand code",
              "st": "red"
            },
            {
              "name": "Runs itself",
              "st": "part"
            },
            {
              "name": "Honest practice",
              "st": "part"
            },
            {
              "name": "Creative",
              "st": "part"
            },
            {
              "name": "Beat its size",
              "st": "none"
            },
            {
              "name": "New domains",
              "st": "part"
            }
          ],
          "labels": {
            "l1": "partly shown",
            "l2": "hand code left",
            "l3": "not shown yet",
            "pic": "status colours, not a score",
            "score": "0 of 9 fully green"
          }
        },
        {
          "id": "s11",
          "duration": 29,
          "heading": "Outside opinions on hard questions",
          "caption": [
            {
              "at": 0.024,
              "text": "When a hard question has several plausible answers, the team asks other AI reviewers."
            },
            {
              "at": 0.307,
              "text": "Each prompt asks them to label claims shown, suggested or untested."
            },
            {
              "at": 0.553,
              "text": "Every reply is checked against the code before anyone acts on it."
            }
          ],
          "labels": {
            "q": "hard question",
            "a": "lead AI agent, sees the repo",
            "b": "web AI model, no repo",
            "chk": "checked against the code",
            "c1": "the team's process",
            "t1": "shown",
            "t2": "suggested",
            "t3": "untested"
          },
          "src": [
            "CLAUDE.md lines 3-17 (Outside opinions on hard problems: Astra and GPT web; label claims shown, suggested, untested; one change at a time; check factual claims against the code)"
          ],
          "notes": "Process only; no result is claimed."
        },
        {
          "id": "s12",
          "duration": 28,
          "heading": "What to remember",
          "caption": [
            {
              "at": 0.025,
              "text": "The goal: think first, learn from few examples, beat models of its whole size."
            },
            {
              "at": 0.308,
              "text": "The rules: size counts everything, learned inside, honest practice, marks first."
            },
            {
              "at": 0.554,
              "text": "Today: none of the nine goals is fully shown yet."
            }
          ],
          "labels": {
            "n1": "1",
            "n2": "2",
            "n3": "3",
            "w1": "goal",
            "w2": "rules",
            "w3": "today",
            "p1": "think first, few examples, whole size",
            "p2": "size counts all, learned inside, honest practice, marks first",
            "p3": "0 of 9 goals fully green"
          },
          "src": [
            "big-run/PLAN.md lines 70-80",
            "architecture/FINISHED-MODEL-2026-10-09.md lines 71-77, 125-131"
          ],
          "notes": "Recap of scenes s01 to s10."
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
          "heading": "Measured: 3 to 4 letters per token",
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
          "duration": 28,
          "heading": "Recap: what to remember",
          "cards": [
            {
              "label": "Reader",
              "sub": "borrowed, frozen"
            },
            {
              "label": "Window",
              "sub": "4 letters each side"
            },
            {
              "label": "No window",
              "sub": "5.0 and 2.5 out of 100"
            }
          ],
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
          "question": "Tom has 12 apples. (made-up example)",
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
            "o": "1",
            "end": "end"
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
          "duration": 42,
          "heading": "How it will be judged: marks set in advance",
          "caption": [
            "These marks were written before any run. They are targets, not results.",
            "Easy questions must use at most half the rounds of the longest ones (11 steps in the code; the plan says 12).",
            "Always-32 means the same model forced to think all 32 rounds. Practised questions: within 1 of it. Longer chains: within 2.",
            "It fails if it never stops early, or if longer chains fall more than 5 below always-32."
          ],
          "barA": "1-step questions: rounds (target)",
          "barB": "longest questions: rounds (target)",
          "ruleA": "at most half of the longest",
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
    "ch07": {
      "kicker": "Part 7 of 14",
      "title": "Writing down the answer",
      "blurb": "The talker writes only the final answer, copying where the thinker points. Today it is a small stand-in. The talker that writes English is a placeholder.",
      "accent": "talker",
      "scenes": [
        {
          "id": "s01",
          "duration": 34,
          "heading": "Where we are: the talker writes the answer",
          "caption": [
            {
              "at": 0.02,
              "text": "This is the last stop on the map: the talker."
            },
            {
              "at": 0.2,
              "text": "Its only job is to write the final answer. It adds no thinking."
            },
            {
              "at": 0.38,
              "text": "It reads the thinker's final state, and may copy from the question and the calculator's replies."
            },
            {
              "at": 0.6,
              "text": "But only where the thinker points. Today's talker is a small stand-in."
            }
          ],
          "labels": {
            "question": "the question",
            "replies": "the calculator's replies",
            "state": "thinker's final state",
            "points": "points",
            "talker": "Talker",
            "talkerSub": "adds no thinking",
            "answer": "answer",
            "ten": "10",
            "tag": "made-up example",
            "chip": "small stand-in today"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 Talker row (line 38): writes only the final answer from the thinker's final state; today a small stand-in",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 (lines 19-20): talker copies exact names and digits where the thinker points, adds no thinking of its own",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 4 (line 115): may copy from the question and the calculator replies, only where the thinker points",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 6 (line 57): the 10 copied from the last reply (made-up Tom example)"
          ],
          "notes": "The talker's input is the thinker's final state, NOT 'notes' (ch09 s07 labelled the talker box 'notes'; FINISHED sec. 5 item 4 says the notebook memory is not read by the talker). BUILDER PLAN: modelMap highlight talker at y 215 h 150. Below: left two small cards (question, replies) at x 100; thinker-state S.vec top middle (x ~620,y 470); Talker box pink x 900 y 540 w 380 h 150; answer box x 1440 w 300 with big pink 10; soft arrows question->talker, replies->talker; a thinker-coloured arrow state->talker labelled points; chip 'made-up example' near answer; placeholder chip label 'small stand-in today' under the talker at the last caption."
        },
        {
          "id": "s02",
          "duration": 39,
          "heading": "Three ways the talker writes, today",
          "caption": [
            {
              "at": 0.02,
              "text": "Today's talker is a small stand-in with three ways to write an answer."
            },
            {
              "at": 0.25,
              "text": "Span copy takes a stretch of letters from the question or a reply."
            },
            {
              "at": 0.45,
              "text": "A word pointer takes one whole word from the question."
            },
            {
              "at": 0.62,
              "text": "Letter slots spell the answer when it is not in the text."
            }
          ],
          "labels": {
            "titles": [
              "Span copy",
              "Word pointer",
              "Letter slots"
            ],
            "from": [
              "add 7 3 = 10",
              "Tom has 12 apples.",
              "not in the text"
            ],
            "to": [
              "10",
              "Tom",
              "yes"
            ],
            "tag": "made-up examples",
            "gone": "An older mode, where plain code typed the number, is gone."
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 Talker row (line 38): a span copy (its own pointer and stop head), a word pointer, or letter slots; the old number-copy mode is gone",
            "custom_io/models/tool.py @17a356e62 docstring lines 19-20 (B2's NUM mode, str of a slot value, is gone) and lines 406-417 (answers(): mode 0 span, mode 1 word of the prompt, else GEN letters)"
          ],
          "notes": "All three examples are made up (picture only). Word pointer: tool.py answers() copies word w of the row's prompt, found by a hand-written word splitter (FINISHED sec. 4 table, tool.py:411). BUILDER PLAN: three cards x 100/686/1272, y 230, w 546, h 400 (title pink 48px bold; below it from-text mono 36px, an arrow drawn after the cards, and the result in a pink-edged box). Cards appear on captions 1-3; the 'gone' S.note at y 690 w 1720 appears about 0.72; tag chip placeholder 'made-up examples' at x 100 y 770."
        },
        {
          "id": "s03",
          "duration": 40,
          "heading": "Span copy: a pointer, a step left, a stop",
          "caption": [
            {
              "at": 0.02,
              "text": "The thinker's final state sets a pointer on the last digit of the last reply: the 0."
            },
            {
              "at": 0.23,
              "text": "The copy steps one letter left and takes the 1."
            },
            {
              "at": 0.4,
              "text": "Next to the left is a space. A learned stop head says stop."
            },
            {
              "at": 0.57,
              "text": "The digits came out last first, 0 then 1. Plain code flips them to read 10."
            }
          ],
          "labels": {
            "reply1": "sub 12 5 = 7",
            "reply2": "add 7 3 = 10",
            "ptr": "pointer",
            "stop": "stop head",
            "out": [
              "0",
              "1"
            ],
            "final": "10",
            "learnedChip": "pointer and stop head: learned",
            "handChip": "step left and flip: hand-written",
            "tag": "made-up example"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 table 'Span copy rules' (line 96): start at the pointer's letter, step one letter left, stop at the learned stop head; 'Last letter first' (line 98): the code flips the text",
            "custom_io/models/tool.py @17a356e62 docstring lines 33-41: a pointer picks the units digit, the copy advances one char left, a learned stop head ends it",
            "animations/model-explainer-build/chapters-out/ch05/ch05.json s05: same trick for the call writer (made-up Tom example)"
          ],
          "notes": "The strings are made-up example replies (picture only). In the T1S docstring the answer pointer reads control vector 1 while the call writer reads vector 0 (tool.py line 41); the video only says 'the thinker's final state'. BUILDER PLAN (copy ch05 s05): two letter rows from S.letters at x 170: reply1 at y 215 size 60 (dim, soft colour), reply2 at y 330 size 80. Pointer box (thinker colour) under index 11 (the 0); tint cells pale pink (#F9C5DA). Output boxes at x 1250 and 1370, y 330 for 0 then 1; stop head box (stop purple) pulses; last caption: final big 10 pops, then the two chips (learned = blue, hand = brown) at y 600/670."
        },
        {
          "id": "s04",
          "duration": 44,
          "heading": "Span copy: how often, and what is hand code",
          "caption": [
            {
              "at": 0.02,
              "text": "On every trained copy of the T1SDR model at 3M, span copy wrote 91.5% of the answers."
            },
            {
              "at": 0.22,
              "text": "That counts how often it was used, not how often it was right."
            },
            {
              "at": 0.42,
              "text": "The pointer and the stop head are learned. Three small pieces are still hand-written code."
            },
            {
              "at": 0.62,
              "text": "The plan: one learned writer replaces them. That build has not been run."
            }
          ],
          "labels": {
            "bars": [
              {
                "label": "answers",
                "value": 91.5
              },
              {
                "label": "numbers in calls",
                "value": 98
              }
            ],
            "chip": "tested at 3M: how often used",
            "barNote": "share of uses, not accuracy",
            "hand": [
              "step one letter left",
              "split text into words",
              "flip last-first text"
            ],
            "handChip": "hand-written",
            "plan": "one learned writer",
            "planChip": "plan only, not run"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 table 'Span copy rules' (line 96): used for 98% of written operands and 91.5% of answers on every T1SDR seed; replaced by O1, the one learned writer",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 table 'Word splitter' (line 90) and 'Last letter first' (line 98)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (lines 84-86): B3 group 2 build started 12:15 PM ET 10-09, code only, its 3M run waits for G1",
            "animations/model-explainer-build/chapters-out/ch05/ch05.json s05 notes: shares of uses, not accuracy"
          ],
          "notes": "Shares of uses, not scores. FINISHED sec. 4 is the only source found; the raw per-seed file was not located (same as ch05). No talker-only test exists; the T1SDR runs are the 3M runs where the calculator outside matched B2 over 6 copies (sec. 5 item 1). BUILDER PLAN: left, S.hbars (two rows, suf %, dec 1/0, x 100 y 250 w 600) + chip tested at y 480; right, three brown S.box (hand code) stacked at x 1000..1800, y 230/330/430, arrow to a grey box 'one learned writer' (placeholder colour) at y 570 with chip 'plan only, not run'."
        },
        {
          "id": "s05",
          "duration": 34,
          "heading": "Letter slots: spelling an answer",
          "caption": [
            {
              "at": 0.02,
              "text": "When the answer is not in the text, the talker spells it in letter slots."
            },
            {
              "at": 0.22,
              "text": "There are 9 places: room for 8 letters and an end mark. Each place picks a letter, or copies one."
            },
            {
              "at": 0.48,
              "text": "They fill last letter first, so yes comes out as s, e, y. The code flips it."
            }
          ],
          "labels": {
            "slots": [
              "s",
              "e",
              "y",
              "end"
            ],
            "word": "yes",
            "tag": "made-up answer",
            "order": "written last letter first",
            "flip": "the code flips it"
          },
          "src": [
            "custom_io/models/ledger.py:70-72 (N_REG = 9 registers; GEN_MAX = 8 chars + EOS)",
            "custom_io/models/tool.py @17a356e62 line 417 (letter answer decoded then reversed: out.append(self.vocab.decode(gen_ids[i])[::-1])) and docstring lines 19-20 (GEN pointer-generator copies from the prompt and the entries)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 table 'Last letter first' (line 98)"
          ],
          "notes": "'yes' is a made-up answer. Each slot is a pointer-generator: vocabulary readout or copy attention over the context letters. BUILDER PLAN: nine slot boxes (x 160 + i*104, y 330, 90x110, label empty), 8 plain + the 9th labelled 'end' tinted purple-ish soft; fill slots 0..2 with s, e, y then the end mark in slot 3 on captions 2-3 (pop). Then flip: a new mono word 'yes' types out in a pink box below with the flip note. Tag chip placeholder 'made-up answer'. Empty slots 4-7 stay empty/pale."
        },
        {
          "id": "s06",
          "duration": 44,
          "heading": "The 8-letter limit, and the 35-letter path",
          "caption": [
            {
              "at": 0.02,
              "text": "Today's answer slots hold 8 letters. A longer training answer would be cut to 8."
            },
            {
              "at": 0.19,
              "text": "That never happened: 0 of 200,000 training answers were longer than 8."
            },
            {
              "at": 0.33,
              "text": "But a fill-in blank of 9 to 12 letters would hit it."
            },
            {
              "at": 0.46,
              "text": "The new build, B3, writes up to 35 letters and counts longer answers, never cutting them."
            },
            {
              "at": 0.63,
              "text": "A count above 0 fails its sealed mark. Blanks of 9 to 12 letters are safe only here."
            }
          ],
          "labels": {
            "word": "umbrellas",
            "cutLabel": "cut off",
            "tag": "made-up word",
            "zero": "0 of 200,000",
            "zeroLabel": "training answers over 8",
            "bars": [
              {
                "label": "today",
                "value": 8
              },
              {
                "label": "B3 path",
                "value": 35
              }
            ],
            "unit": "letters",
            "chipToday": "in the code",
            "chipB3": "built, never run",
            "end": "end"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (lines 79-83): T1SDR and H1 hold 8 answer letters; tool.py:510 cuts a longer non-drill training answer to 8; 0 of 200,000 training answers over 8; data.py:109 refuses longer ones; B3 under caps_b3 writes up to 35 letters and counts a longer answer (gen_answer_over); a run with any count above 0 fails its sealed mark; blanks of 9-12 letters safe only on the caps path",
            "custom_io/models/tool.py @17a356e62 line 510 (ans[:GEN_MAX][::-1]) and custom_io/data.py @17a356e62 line 109 (assert answer length <= MAX_ANS)",
            "custom_io/g8a/caps_b3.json (max_ans 35) and custom_io/capcount.py:17 (gen_answer_over)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 11 (lines 140-145): blanks of 3-12 letters; 9-12 need the 35-letter path"
          ],
          "notes": "'umbrellas' (9 letters) is a made-up word that shows what a cut would do (the last letter is lost); picture only. The 0-of-200,000 count is for T1SDR runs. B3 group 1 is built, never run. BUILDER PLAN: top, nine boxes: first 8 hold u,m,b,r,e,l,l,a and a 9th red-outlined box 's' that gets a 'cut off' tag and fades to dim; middle, big counting '0 of 200,000' text (S.count to 200000 with comma, then fixed '0 of'); bottom, two bars 8 vs 35 letters (S.bar scaled to 35, labels), chips tested/untested: 'shown in the code' (use hand-neutral chip), 'built, never run' amber. Caption 5 text note: sealed mark rule shown as S.note."
        },
        {
          "id": "s07",
          "duration": 38,
          "heading": "The planned English talker is not built",
          "caption": [
            {
              "at": 0.02,
              "text": "The finished plan has a real talker, about 25M numbers, that writes English."
            },
            {
              "at": 0.25,
              "text": "It is not built. As built, the whole model is 373.1M: 271.0M of borrowed, frozen Gemma plus 102.1M trained."
            },
            {
              "at": 0.5,
              "text": "How it would learn to write English is not in the plan. A separate team session owns that."
            }
          ],
          "labels": {
            "bars": [
              {
                "label": "borrowed, frozen Gemma",
                "value": 271
              },
              {
                "label": "trained thinker and heads",
                "value": 102.1
              },
              {
                "label": "English talker, planned",
                "value": 25
              }
            ],
            "total": "373.1M as built",
            "chip": "placeholder",
            "note": "Today: short answers only. A number, a copied word, up to 8 letters. No sentences."
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 (lines 19-23): talker about 25M planned; 373.1M whole as built (102.1M trained + 271.0M frozen Gemma) because the 25M English talker is not built",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 11 (line 145): how the 25M talker learns to write English is not in the plan; a separate 'talking from scratch' session owns it",
            "architecture/redesign-ideas-2026-10-07.md sec. 6 (line 91): today the talker writes short answers, a number, a copied word, or up to 8 letters; it does not produce sentences",
            "big-run/PLAN.md line 148: about 373M as built, about 398M once a 25M talker is added"
          ],
          "notes": "The 25M talker is a plan; its bar is drawn grey and outlined only. The 373.1M total does not include it. The planned total is quoted as 397M in FINISHED sec. 1 and 398M in PLAN line 148 (different thinker sizes); the video avoids the planned total. BUILDER PLAN: stacked horizontal strip, widths proportional to 271.0 : 102.1 : 25 across 1500 px (x 160, y 330, h 110): teal, indigo, grey (placeholder fill, outline). Counting labels under each (S.count dec 1, suffix M). Bracket/arrow over the first two parts counting to 373.1M; placeholder chip over the grey part. Note at y 640 appears with caption 3."
        },
        {
          "id": "s08",
          "duration": 44,
          "heading": "Older tests of talking English",
          "caption": [
            {
              "at": 0.02,
              "text": "These tests are older, from a design built on borrowed language models. Not today's talker."
            },
            {
              "at": 0.25,
              "text": "A 350M model as reader and talker scored 66.1. The 1.2B system scored 92.6."
            },
            {
              "at": 0.5,
              "text": "A small copy talker scored 13.6 on question kinds it never practised. The language-model talker scored 78.2."
            }
          ],
          "labels": {
            "head": "older English design, not today's talker",
            "unit": "points out of 100",
            "panelA": "350M model as reader and talker",
            "rowsA": [
              {
                "label": "350M model",
                "value": 66.1
              },
              {
                "label": "1.2B system",
                "value": 92.6
              }
            ],
            "subA": "192 fresh questions, 6 runs",
            "panelB": "small copy talker, about 2M numbers",
            "rowsB": [
              {
                "label": "copy talker",
                "value": 13.6
              },
              {
                "label": "language-model talker",
                "value": 78.2
              }
            ],
            "subB": "384 questions of unpractised kinds, 6 runs",
            "chip": "tested, older design",
            "risk": "Talking English from scratch: not shown"
          },
          "src": [
            "notes/hearer-talker/RESULTS-SMALL-LM.md lines 8-16 (verdict table lines 10-11): 1.2B system 92.6% vs 350M system 66.1% (60.9-72.0) on the fresh in-family set FRESH-EN-R3 (192 questions), 6 paired seeds; both marks fail",
            "reader-talker-compare/RESULTS-CT.md lines 8-15: copy talker 13.6 vs allptr 78.2 on 384 unseen-kind questions (mean of 6 paired seeds); verdict FAILS",
            "architecture/redesign-ideas-2026-10-07.md sec. 6 (line 92): the same two pairs, quoted as earlier results",
            "big-run/PLAN.md line 139: 'Talking English from scratch: Not shown, the second big risk'",
            "idea-swarm/raw/areas/talker.json lines 88, 93, 570, 1350: marks the copy talker as the old 1.2B line"
          ],
          "notes": "Two different pairs, two different tests. A: 350M language model used as both reader and talker vs the 1.2B system, exact-match % on 192 fresh questions in the same family. B: the roughly 2M-number copy-and-gate talker (span start/end pointers, a word head, a copy/word gate) vs the language-model talker ('allptr') on 384 questions of question kinds never practised. Both are the older 1.2B-reader line (separate from today's B2/T1SDR talker); the superseded banner on reader-talker-compare/verdict.md says do not act on its recommendation. Copy talker on practised kinds with generated wording scored 97.4 vs 99.7 (RESULTS-CT.md line 18); not shown on screen. PR #54 numbers are NOT used (only in the memory index). BUILDER PLAN: two hbars blocks (x 160/y 300 and y 560, w 640 labelW 360) revealed with captions 2 and 3; panel titles 36px; sub lines 32px soft; header chip tested label 'tested, older design' top right; risk text appears at about 0.62 in an amber/grey S.note."
        },
        {
          "id": "s09",
          "duration": 42,
          "heading": "Could the talker answer alone?",
          "caption": [
            {
              "at": 0.02,
              "text": "One check turned the thinking off on one trained copy at 3M. This is the older design: calculator inside, 12 rounds."
            },
            {
              "at": 0.26,
              "text": "Thinking on scored 73.01. Thinking off scored 0.66, on 6,040 questions kept aside."
            },
            {
              "at": 0.44,
              "text": "That hints the talker cannot answer alone. One copy is only a hint."
            },
            {
              "at": 0.6,
              "text": "An earlier Gemma-reader copy scored 18.09 on familiar questions with zero rounds, so 'cannot' is not shown."
            }
          ],
          "labels": {
            "bars": [
              {
                "label": "thinking on",
                "value": 73.01
              },
              {
                "label": "thinking off",
                "value": 0.66
              }
            ],
            "unit": "points out of 100",
            "chip": "suggested, one copy",
            "earlier": "18.09",
            "earlierLabel": "an earlier Gemma-reader copy, zero rounds, familiar questions only",
            "note": "Gemma's meaning also reaches the talker's copy keys. Allowed."
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 2 (lines 109-112): G1 3M seed 400: 73.01 thinker on, 0.66 thinker off; Gemma-reader arms do answer some questions with zero rounds (EGE 18.09 in-distribution on seed 200)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 items 3-4 (lines 113-119): Gemma also reaches the talker's copy keys, allowed; 'cannot' is not shown (suggested)",
            "animations/source-g1-3m-s400.json (as cited in ch06 s03): by_thinking_rounds loops:0 0.66, trained rounds 12, 6,040 questions",
            "memory/gemma-reader-results.md line 14: EGE loops:0 18.09 on seed 200 (4.49 on seed 201)"
          ],
          "notes": "Label this whole scene 'suggested', not shown. 73.01 and 0.66 are the older design (calculator inside, 12 fixed rounds), as ch06 s03 says. The 18.09 comes from a different earlier model (EGE, Gemma added before the letter window) on a familiar-question set, so it must NOT share a bar chart with the 6,040-question scores. No leak limit is quoted (4.62 vs 5 conflict between ch03 and ch05). BUILDER PLAN: left, two S.hbars (x 100, y 300, w 600) with unit text; chip 'suggested, one copy'; right, a card (x 1000 y 280 w 780 h 260) with big counting 18.09 (amber) and the small label; S.note for the Gemma copy-keys line at y 620."
        },
        {
          "id": "s10",
          "duration": 39,
          "heading": "Web text teaches reading, not writing",
          "caption": [
            {
              "at": 0.02,
              "text": "Free web text, called FineWeb-Edu, enters practice as fill-in-the-blank rows."
            },
            {
              "at": 0.22,
              "text": "One word of 3 to 12 letters is hidden, and the model must name it."
            },
            {
              "at": 0.44,
              "text": "So the run teaches reading English, not writing it."
            },
            {
              "at": 0.6,
              "text": "By plan, 84% of the big run's practice text is web text."
            }
          ],
          "labels": {
            "sentence": "The cat sat on the",
            "blank": "____",
            "fill": "mat",
            "tag": "made-up sentence",
            "range": "3 to 12 letters hidden",
            "chunk": "Chunk shown: up to 280 letters in G1, up to 2,000 in the B3 plan",
            "web": "web text 84%",
            "own": "our own rows 16%",
            "chip": "plan only"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 11 (lines 140-145): FineWeb-Edu enters as fill-in-the-blank rows, one word of 3-12 letters blanked (custom_io/g8a/cloze.py:1-25), at most 280 letters in G1, up to 2,000 in B3's long-chunk pool; so the run teaches reading English, not writing it",
            "big-run/PLAN.md line 149: about 2.5B word pieces seen, 16% our text and 84% FineWeb-Edu (roadmap sec. 1.2)",
            "architecture/redesign-ideas-2026-10-07.md sec. 6 (line 94): free human-written web text (FineWeb-Edu) approved for the bigger rungs"
          ],
          "notes": "The cat sentence is made up (picture only); the real rows use FineWeb-Edu chunks. The 84/16 split is a plan figure from PLAN line 149, measured in word pieces; 'our own rows' = rows made by our code generators plus the 171,940 TEACH rows (PLAN line 149). The web pool has a gate: it must not be used for training until protected-panel hashes are merged and checked (FINISHED sec. 5 item 12). BUILDER PLAN: left, big mono sentence 'The cat sat on the ____' (S.type) then 'mat' pops in the blank in pink; range tag below; right, chunk note and a two-part stacked bar 84/16 (S.card widths 84% and 16% of 700 px) with chip 'plan only' appearing with caption 4."
        },
        {
          "id": "s11",
          "duration": 43,
          "heading": "What would have to be true to win the race",
          "caption": [
            {
              "at": 0.02,
              "text": "The plan's final proof is a race against small public models, such as SmolLM2-360M."
            },
            {
              "at": 0.24,
              "text": "To win, it must be ahead by at least 3 points on our sealed tests, and ahead on a question set called bAbI."
            },
            {
              "at": 0.5,
              "text": "The whole size is counted, borrowed numbers too. The race needs the English talker, which does not exist yet."
            }
          ],
          "labels": {
            "steps": [
              "English talker built",
              "Race a same-size model",
              "Ahead by 3 points, and on bAbI"
            ],
            "chips": [
              "placeholder",
              "never run",
              "plan only"
            ],
            "chipLabels": [
              "not built",
              "never run",
              "plan only"
            ],
            "note": "Plan: not finished by the Oct 31 readout"
          },
          "src": [
            "big-run/PLAN.md line 77 (scorecard row 8): race ahead of SmolLM2-360M by >= +3 on our sealed sets and ahead on bAbI, whole size counted; untested; the race needs the open-English talker",
            "big-run/PLAN.md lines 284-285 (R4, the race): rivals SmolLM2-360M, LFM2-350M, Qwen3-0.6B; the bAbI part cannot pass until the open-English talker works",
            "big-run/PLAN.md line 87: not closable by the Oct 31 readout: talker (1c) and the race (8)"
          ],
          "notes": "Plan only, nothing run. The video does not say which size model races: PLAN row 8 races the 30M thinker model (about 301M whole as built) while FINISHED keeps the 100M thinker (373.1M whole as built). The Oct 31 date is a plan, stated as 'plan'. BUILDER PLAN: three step boxes left to right (x 160/700/1240, y 300, w 480, h 190) with arrows drawn between; chip under each; the first box pulses at caption 3; S.note with the Oct 31 line at y 620 appears about 0.7."
        },
        {
          "id": "s12",
          "duration": 32,
          "heading": "What to remember about the talker",
          "caption": [
            {
              "at": 0.02,
              "text": "It writes only the final answer, copying where the thinker points."
            },
            {
              "at": 0.28,
              "text": "Today it is a small stand-in, tested only inside the 3M runs."
            },
            {
              "at": 0.5,
              "text": "The English talker is a placeholder. The model cannot chat."
            }
          ],
          "labels": {
            "cards": [
              "Writes only the answer",
              "Today: a small stand-in",
              "English talker: not built"
            ],
            "chips": [
              {
                "kind": "learned",
                "label": "pointer and stop head: learned"
              },
              {
                "kind": "tested",
                "label": "ran in 3M tests, never alone"
              },
              {
                "kind": "untested",
                "label": "35-letter path: never run"
              },
              {
                "kind": "placeholder",
                "label": "English talker: placeholder"
              }
            ]
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 Talker row (line 38) and sec. 5 item 4 (line 115)",
            "architecture/redesign-ideas-2026-10-07.md sec. 6 (line 91): today the talker writes short answers and does not produce sentences",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (lines 79-83): the 35-letter path is built, not run"
          ],
          "notes": "The brief's recap said 'copy talker tested at small size'. No talker-only test exists; the stand-in ran inside T1SDR 3M runs, so the chip says 'ran in 3M tests, never alone'. BUILDER PLAN: three cards (x 100/686/1272, y 260, w 546, h 170, label 44px) appear one per caption; the four chips sit below in two rows (y 520 and 600) and appear with their card's caption (learned with card 1, tested and untested with card 2, placeholder with card 3)."
        }
      ]
    },
    "ch08": {
      "kicker": "Part 8 of 14",
      "title": "Practice, one small nudge at a time",
      "blurb": "How the model learns: it tries a question, is shown the right answer, and every setting moves a tiny bit. This part covers the practice loop, the data, the fairness rules and the cost.",
      "accent": "learned",
      "scenes": [
        {
          "id": "s01",
          "duration": 22,
          "heading": "Where we are: practice sets the numbers",
          "caption": [
            "Practice sets the numbers inside the thinker, the call writer, the stop switch and the talker.",
            "The borrowed reader stays frozen. The calculator is plain code, so it needs no practice."
          ],
          "labels": {
            "reader": "frozen",
            "thinker": "learned",
            "calc": "hand-written",
            "stop": "learned",
            "talker": "learned"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 table (lines 29-38: reader borrowed and frozen; thinker, stop, talker learned; calculator hand code, allowed as a tool)",
            "kit/GLOSSARY.md (frozen, hand-written, learned)"
          ],
          "notes": "The stop switch (H1) is built but never run; the chip says what the part is meant to be (learned). Statuses per part are shown in earlier chapters."
        },
        {
          "id": "s02",
          "duration": 26,
          "heading": "The loop: try, check, nudge",
          "caption": [
            "The model tries a question.",
            "It is shown the right answer.",
            "Then every setting moves a tiny bit. One nudge is one update."
          ],
          "labels": {
            "q": "12 minus 5 = ?",
            "try": "its try: 6",
            "key": "right answer: 7",
            "settings": "settings",
            "nudge": "nudge",
            "pic": "picture only: made-up question",
            "model": "the model"
          },
          "src": [
            "kit/GLOSSARY.md (practice = try, told the right answer, every setting nudged; one nudge = one update)",
            "architecture/model-deep-dive.html line 156-165 (How it learns: question, model tries, compare to the key, nudge the weights, repeat)"
          ],
          "notes": "The question, the wrong try and the needle angles are all made up to show the idea."
        },
        {
          "id": "s03",
          "duration": 30,
          "heading": "24,000 updates of 256 rows each",
          "caption": [
            "Each update looks at 256 practice rows, then nudges every setting once. The 3M test copy did 24,000 updates.",
            "Our multiplication: 24,000 × 256 = 6,144,000 row draws. The pool has 1,418,702 rows, so rows come round again."
          ],
          "labels": {
            "updates": "updates",
            "rows": "rows per update",
            "draws": "row draws",
            "mult": "our multiplication",
            "div": "÷ 1,418,702 pool rows = about 4.3 draws each",
            "chip": "3M, seed 400"
          },
          "src": [
            "animations/source-g1-3m-s400.json G-B2 updates 24000",
            "architecture/EXPERTS-TEST-2026-10-09.md lines 36-38 (24,000 updates of 256 rows)",
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md line 166 (pool train file 1,418,702 rows)",
            "whole-model-roadmap/8A-SPEC-2026-10-07.md line 253 (B1: about 3.9 passes, an estimate before the run)"
          ],
          "notes": "Computed by us: 24,000 x 256 = 6,144,000; 6,144,000 / 1,418,702 = 4.33. The spec's earlier estimate was about 3.9 passes; we show our own division, labelled. Not 6.1 million different questions.",
          "nums": {
            "updates": 24000,
            "rows": 256,
            "draws": 6144000
          }
        },
        {
          "id": "s04",
          "duration": 30,
          "heading": "The recipe: how each nudge is made",
          "caption": [
            "AdamW is the nudging rule. The learning rate is how big a nudge may be.",
            "It peaks at 1e-3 after a warm-up, then falls to 10% of the peak.",
            "Numbers are stored short (bf16), rows come shuffled, and the start is random."
          ],
          "labels": {
            "adamw": "AdamW",
            "bf16": "bf16",
            "shuf": "shuffled",
            "rand": "random start",
            "clip": "nudge cap 1.0",
            "y": "size of nudge",
            "x1": "24,000 updates",
            "warm": "warm-up",
            "peak": "1e-3",
            "tenth": "10% of peak",
            "pic": "picture only"
          },
          "src": [
            "architecture/EXPERTS-TEST-2026-10-09.md lines 36-38 (AdamW, lr 1e-3, grad clip 1.0, bf16, 24,000 updates of 256 rows)",
            "architecture/model-deep-dive.html line 165 (older recipe: AdamW, lr 1e-3 with warm-up then cosine fall to 10%, batch 256, bf16, shuffled order, from random start)",
            "whole-model-roadmap/8A-SPEC-2026-10-07.md line 93 (as q33: AdamW, bf16, batch 256)"
          ],
          "notes": "Warm-up and the fall to 10% come from the older recipe page, which G1 inherits 'as q33'; the warm-up length is not in the sources so the curve is a picture only."
        },
        {
          "id": "s05",
          "duration": 31,
          "heading": "What it practises on",
          "caption": [
            "The 3M test copy practised on a pool of 60 million pieces of text (GPT-2 word pieces).",
            "38% is our own text: practice questions and teaching rows. 62% is web text.",
            "The TEACH rows were written earlier by a 1.2-billion-number teacher model."
          ],
          "labels": {
            "own": "our own text",
            "web": "web fill-in rows",
            "skills": "skills set: made by our code",
            "skillsN": "200,000 questions",
            "teach": "TEACH set",
            "teachN": "171,940 rows",
            "pool": "60 million pieces",
            "chip": "tested: 3M copy"
          },
          "src": [
            "whole-model-roadmap/8A-10M-RESULT-2026-10-08.md line 5 (60M-piece pool: 38% our questions, 62% web fill-in rows)",
            "whole-model-roadmap/8A-SPEC-2026-10-07.md lines 71-74 (20M/60M/190M word pieces, GPT-2 count; 38% own text = generator rows plus TEACH; 62% web)",
            "no-hardcoding/LIMIT-COUNTS-2026-10-07.json train rows 200000",
            "whole-model-roadmap/whole-model-roadmap-2026-10-06.md lines 250, 265, 393 (TEACH 171,940 kept rows, PR #46; written by the 1.2B teacher; no new teacher rows)"
          ],
          "notes": "Shares are of pieces, not of rows. 200,000 is the skills practice set only. TEACHING_TO_TEST_CONTRACT.md is an older design memo, unrelated to these TEACH rows, and was not used.",
          "nums": {
            "own": 38,
            "web": 62
          }
        },
        {
          "id": "s06",
          "duration": 38.5,
          "heading": "Web text: fill in the missing word",
          "caption": [
            "FineWeb-Edu web text: a script blanks one word of 3 to 12 letters, and the model must name it.",
            "Each prompt holds at most 280 letters, blank included, in the 3M runs; the finished design's long pool goes up to 2,000.",
            "It learns to read English, not write it. Rows without steps add a faint no-call label, weight 0.1."
          ],
          "labels": {
            "pre": "Plants make food from",
            "post": ", water and air.",
            "word": "sunlight",
            "ex": "made-up example",
            "b1": "280 letters",
            "b2": "2,000 letters",
            "b1chip": "tested",
            "b2chip": "never run",
            "w": "no-call weight"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 11 (lines 140-146)",
            "custom_io/g8a/cloze.py lines 12, 21-22 (prompt <= 280 chars with blank; chunk text itself capped at 279; blanked word 3..12 letters; rows made by a script)",
            "custom_io/models/ledger.py line 140 and tool.py line 125 (w_noop=0.1)"
          ],
          "notes": "FineWeb-Edu = free human-written web text. The example sentence is made up; real rows come from FineWeb-Edu. The 2,000-letter pool (cloze_long, --cloze-long) is built but never run.",
          "nums": {
            "b1": 280,
            "b2": 2000,
            "w": 0.1,
            "lo": 3,
            "hi": 12
          }
        },
        {
          "id": "s07",
          "duration": 35,
          "heading": "Worked steps: practising each call",
          "caption": [
            "Where a row has worked steps, the answer key gives the right call each round.",
            "Call loss: was the call slip right? After the last call, the right slip is no call.",
            "Answer loss: is the final answer right? Counted from the last call round on."
          ],
          "labels": {
            "round": "round",
            "r1": "1",
            "r2": "2",
            "r3": "3",
            "key": "answer key",
            "cw": "call writer",
            "c1": "sub 12 5 = 7",
            "c2": "add 7 3 = 10",
            "c3": "no call",
            "ans": "answer 10",
            "callLoss": "call loss",
            "ansLoss": "answer loss",
            "ex": "made-up example",
            "chip": "built, never run"
          },
          "src": [
            "architecture/B3-GROUP1-BUILD-2026-10-09.md lines 53-60 (teacher forcing: op loss on the gold call each call round and no-call after the last; answer loss from the last call round on)",
            "architecture/model-deep-dive.html line 165 (older write-up: losses for operation, pointers, answer, spelling)"
          ],
          "notes": "This is the finished design's loss schedule (B3 group 1): built, never run. The 3M test copy was an older design with its own losses."
        },
        {
          "id": "s08",
          "duration": 31.5,
          "heading": "Teacher forcing: practice follows the key",
          "caption": [
            "Teacher forcing: in practice the next round sees the key's call and reply, even after a wrong guess.",
            "At test time there is no key. The model writes its own calls.",
            "Not every row has steps: 62.5% of the skills rows have none (an older page said only 11 families had them)."
          ],
          "labels": {
            "lane1": "practice",
            "lane2": "test",
            "k": "key's call",
            "r": "reply",
            "n": "next round",
            "g": "own guess: graded",
            "o": "own call",
            "none": "no steps"
          },
          "src": [
            "architecture/B3-GROUP1-BUILD-2026-10-09.md lines 49-53, 67-71 (running with no teacher vs teacher forcing; gold calls fed in a free run give the same thinker states)",
            "architecture/FINISHED-MODEL-2026-10-09.md line 143 (62.5% of the skills rows the 3M models trained on have no worked steps)",
            "architecture/model-deep-dive.html line 165 (only 11 arithmetic families have teacher steps; older B2)"
          ],
          "notes": "Finished-design behaviour (built, never run). The 62.5% is a share of skills rows and comes from FINISHED; the older page speaks of 11 families.",
          "nums": {
            "share": 62.5
          }
        },
        {
          "id": "s09",
          "duration": 34.5,
          "heading": "Fair practice: three rules",
          "caption": [
            "Rule 1: no answer is cut short. A longer answer is counted, and any count above 0 fails.",
            "Rule 2: exam questions are kept apart: 6,040 questions are never used in practice.",
            "Rule 3: web text is scanned against exam sets. The 3M runs started before the last check, still pending."
          ],
          "labels": {
            "c1": "No answer cut short",
            "c1a": "T1SDR runs: 0 of 200,000 over 8 letters",
            "c1b": "B3 cap: 35 letters",
            "c1chip": "built, never run",
            "c2": "Kept aside",
            "c3": "Web gate",
            "c3chip": "check pending"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 lines 79-82 (0 of 200,000 over 8 letters in T1SDR runs; B3 caps_b3 writes up to 35 letters, counts longer ones; any count above 0 fails its sealed mark)",
            "no-hardcoding/PLAN-AND-MARKS-2026-10-07.md sec. 2 (nothing is cut off; every limit listed with rows touched) and no-hardcoding/LIMIT-COUNTS-2026-10-07.json",
            "whole-model-roadmap/8A-SPEC-2026-10-07.md line 115 (pooled-5 = 6,040 dev rows), lines 84-90 and A1 lines 179-184 (overlap scan; never trained on the dev splits; 3M runs may start before the protected-panel check)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 12 (web pool gate; hash file waits on a Mac job). DATA-POOL-PLAN sec. 6 and 10 is not in the project snapshot and was not read."
          ],
          "notes": "Present as a rule plus a check, not a guarantee. 8a's B2 had answers cut to 8 letters by a settings bug (8A-10M-RESULT correction); G1 is the fixed re-run. 6,040 = 1360+1200+1360+800+1320 (LIMIT-COUNTS dev splits).",
          "nums": {
            "kept": 6040
          }
        },
        {
          "id": "s10",
          "duration": 37.5,
          "heading": "Time: our model versus the plain model",
          "caption": [
            "Ours did 24,000 updates on the project's PC: 1.02 updates a second, 6.51 hours.",
            "Plain: 2.8 a second, 2.38 hours (its update count was not logged; the plan's floor is 24,000). Our division: 6.51 ÷ 2.38, about 2.7 times longer.",
            "A plan, not a result: the 100M run is estimated at 3 to 5 weeks on this PC."
          ],
          "labels": {
            "ours": "our model",
            "plain": "plain model",
            "hrs": "hours",
            "chip": "tested: 3M, one copy",
            "plan": "plan only",
            "weeks": "100M: 3 to 5 weeks",
            "ratio": "times longer (our division)"
          },
          "src": [
            "animations/source-g1-3m-s400.json G-B2 updates_per_s 1.02, train_hours 6.51; G-PT updates_per_s 2.8, train_hours 2.38",
            "whole-model-roadmap/8A-SPEC-2026-10-07.md lines 250-251 (every arm trains at least 24,000 updates of 256 rows)",
            "big-run/PLAN.md sec. 6 (lines 274-275: about 23 to 32 days, so 3 to 5 weeks on the PC, suggested; not run)"
          ],
          "notes": "Only ours has updates=24000 in the run JSON; the plain model's update count is NOT logged. The spec sets 24,000 as the least for every arm, and 2.8 x 3600 x 2.38 = 23,990 is consistent with it (our inference, not a logged count), so the caption says floor, not \"both did\". Our division 6.51 / 2.38 = 2.74. Older design (calculator inside, 12 rounds).",
          "nums": {
            "oursH": 6.51,
            "plainH": 2.38,
            "ratio": 2.7
          }
        },
        {
          "id": "s11",
          "duration": 36,
          "heading": "Why the thinker is harder to train",
          "caption": [
            "The same blocks run every round, so the lesson from a wrong answer must travel back through all of them.",
            "To save memory, training redoes some work instead of storing it: about a third more compute (plan estimate).",
            "Depth has a known cost: on one old probe, 16 rounds cost 1.2 to 1.9 points. At 100M it is an open risk."
          ],
          "labels": {
            "rounds": "rounds",
            "fwd": "answer goes forward",
            "back": "the lesson goes back",
            "chip": "never run",
            "pic": "picture only",
            "r1": "1",
            "r2": "2",
            "r3": "3",
            "dots": "...",
            "r32": "32"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 13 (line 149: 16 rounds cost 1.2-1.9 points on one B2 probe; open risk for 100M) and line 186 (H1 back-propagates through every round with checkpointing)",
            "custom_io/models/tool_h1.py lines 22-24 (rounds 9..32 gradient-checkpointed: same values, less memory)",
            "big-run/PLAN.md sec. 6 line 274 (checkpointing recomputes about a third more)",
            "no-hardcoding/INPUT-UNITS-2026-10-07.md line 39 (16 rounds cost 1.2-1.9 points, one seed; FINISHED cites line 31)"
          ],
          "notes": "The 'third more' is a suggested plan estimate. The 100M fit in 16 GB with 32 rounds is untested."
        },
        {
          "id": "s12",
          "duration": 20,
          "heading": "What changes after practice",
          "caption": [
            "The model's size stays the same. Only the values of its settings change, by many tiny nudges.",
            "Real before-and-after values are not shown here. This is an idea, drawn as a picture."
          ],
          "labels": {
            "before": "before: random start",
            "after": "after: 24,000 updates",
            "pic": "picture only"
          },
          "src": [
            "architecture/model-deep-dive.html line 165 (from random start; nudge the weights, repeat 24,000 times)",
            "No source lists real before and after setting values, so none are shown."
          ],
          "notes": "All needle positions are decoration."
        },
        {
          "id": "s13",
          "duration": 26.5,
          "heading": "Recap: what to remember",
          "caption": [
            "Practice is try, check against the key, nudge: 24,000 updates of 256 rows.",
            "Rows are our questions, teaching rows and web blanks, with exam questions kept apart.",
            "At 3M ours took about 2.7 times longer than the plain model; the finished design is not trained yet."
          ],
          "labels": {
            "t1": "the loop",
            "t2": "the rows",
            "t3": "the cost"
          },
          "src": [
            "see scenes s02, s03, s05, s06, s09, s10 of this chapter",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 6 (B3 group 1's first run comes after G1)"
          ],
          "notes": "Recap only; every number is shown earlier.",
          "nums": {
            "updates": 24000,
            "rows": 256,
            "kept": 6040,
            "ratio": 2.7
          }
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
    },
    "ch10": {
      "kicker": "Part 10 of 14",
      "title": "Tests that cannot be gamed",
      "blurb": "How we test fairly: exams the model never practised, marks written before the run, paired copies, a range of likely error, and honest limits.",
      "accent": "tested",
      "scenes": [
        {
          "id": "s01",
          "duration": 28,
          "heading": "Why a score alone means little",
          "caption": [
            "A score means little if the model has seen the questions before.",
            "So two models of the same size practise on the same rows, in the same order.",
            "The exam questions are kept aside. Some sets stay sealed and are never touched while we build."
          ],
          "labels": {
            "practice": "practice rows",
            "model": "model",
            "exam": "exam: kept aside",
            "lock": "sealed sets, never touched"
          },
          "locks": [
            "GOLD-PRIVATE",
            "reserved",
            "blind"
          ],
          "illustration": "picture only",
          "src": [
            "custom-io/gpt-b2-leak-and-credit-2026-10-05.md lines 37-39 (same size, same practice rows, same order)",
            "whole-model-roadmap/whole-model-roadmap-2026-10-06.md line 448 (never score on GOLD-PRIVATE, never touch reserved/blind panels)",
            "whole-model-roadmap/8A-SPEC-2026-10-07.md lines 88-89 (never trained on dev splits behind protected panels)"
          ],
          "notes": "The stacks and locks are a picture only. The three lock names are the sealed panels named in the sources; we never read them."
        },
        {
          "id": "s02",
          "duration": 29,
          "heading": "Two exams: pooled-5 and chain-5",
          "caption": [
            "Exam one, pooled-5, is 6,040 questions kept aside, in five kinds from familiar to new.",
            "Exam two, chain-5, is 1,000 multi-step questions.",
            "Our own programs write every question, from 34 made-up families, in short English with short answers."
          ],
          "names": {
            "p": "pooled-5",
            "c": "chain-5"
          },
          "total": 6040,
          "totalLabel": "questions",
          "kinds": [
            {
              "label": "Familiar",
              "value": 1360
            },
            {
              "label": "New answers",
              "value": 1200
            },
            {
              "label": "New sentence frames",
              "value": 1360
            },
            {
              "label": "New words",
              "value": 800
            },
            {
              "label": "New wording",
              "value": 1320
            }
          ],
          "chain": {
            "value": 1000,
            "label": "multi-step"
          },
          "src": [
            "architecture/model-deep-dive.html line 166 (How we score it: pooled-5 = 6,040 held-out questions across 5 splits; chain-5 = 1,000 multi-step questions)",
            "custom-io/gpt-b2-leak-and-credit-2026-10-05.md lines 25-36 (34 synthetic families; short English prompts, short answers; the five dev splits named)",
            "chapters-out/ch09/g1-3m-s400-extract.json splits (in_dist 1,360; answer 1,200; frame 1,360; vocab 800; variant 1,320; sum 6,040)"
          ],
          "notes": "Split sizes sum to 6,040. Plain names match ch09 s03 (in_dist, answer, frame, vocab, variant).",
          "families": {
            "n": 34,
            "label": "made-up families"
          }
        },
        {
          "id": "s03",
          "duration": 29,
          "heading": "Marks written before the run",
          "caption": [
            "Before a test, we write down a pass mark, a proved-wrong line, and a prediction.",
            "Then we run the test, and only then read the result.",
            "A mark may be tightened before the first run. It is never loosened after a result is seen."
          ],
          "steps": [
            "1. Write the marks",
            "2. Run the test",
            "3. Read the result"
          ],
          "env": [
            "pass mark",
            "proved-wrong line",
            "prediction"
          ],
          "illustration": "picture only",
          "src": [
            "whole-model-roadmap/whole-model-roadmap-2026-10-06.md line 431 (pass mark, proved-wrong result and a prediction are written before the run)",
            "architecture/MARKS-D0-T1-2026-10-07.md line 34 (may tighten before the first run, never loosen after seeing a result)"
          ],
          "notes": "The envelope is a picture only; real marks follow in the next scene."
        },
        {
          "id": "s04",
          "duration": 35,
          "heading": "A real mark, sealed before the run",
          "caption": [
            "Sealed Oct 9, 12:10 PM, before any run: B3 group 1 must beat its plain partner by 3.0 points.",
            "Below 1.0 it is proved wrong. From 1.0 to 3.0 it is not shown.",
            "Each test runs copy 400 first and stops there if it is proved wrong."
          ],
          "zones": [
            {
              "name": "proved wrong",
              "range": "below 1.0"
            },
            {
              "name": "not shown",
              "range": "1.0 to 3.0"
            },
            {
              "name": "pass",
              "range": "3.0 or more"
            }
          ],
          "prediction": "prediction: 3 to 6",
          "axis": "points over plain partner (copy 400)",
          "chip": "B3: never run",
          "src": [
            "big-run/PLAN.md lines 220-229 (G2 step 2 marks, B3-1: pass at least +3.0 on seed 400, proved wrong below +1.0; sealed 12:10 PM ET 10-09 before any B3 run; prediction +3 to +6)",
            "big-run/PLAN.md line 25 (kill-first: seed 400 first, seed 401 only otherwise)",
            "architecture/MARKS-D0-T1-2026-10-07.md Verdicts line (a mark missed but not proved wrong = not shown)"
          ],
          "notes": "B3 group 1 is built (PR #56) but has never been run, so no result is shown. The zone bar is to scale on the axis (units are points). Seed is shown as copy."
        },
        {
          "id": "s05",
          "duration": 28,
          "heading": "One run is not enough: paired copies",
          "caption": [
            "A copy is one model trained from its own random start. Copy 200 of ours is paired with copy 200 of the plain model.",
            "A quick screen uses 2 copies and only decides whether to confirm. A claim needs 6 or more paired copies."
          ],
          "labels": {
            "ours": "ours",
            "plain": "plain",
            "copies": "copy 200 to 205",
            "screen": "screen: 2 copies",
            "claim": "claim: 6 or more"
          },
          "illustration": "picture only",
          "src": [
            "whole-model-roadmap/whole-model-roadmap-2026-10-06.md lines 431-432 (6 or more paired seeds before any claim; 2-seed screens only decide whether to confirm; noise rule PR #29)"
          ],
          "notes": "The pairs are a picture of the rule, not data. Seed shown as copy."
        },
        {
          "id": "s06",
          "duration": 37,
          "heading": "A real result: six paired copies",
          "caption": [
            "Oct 7, older design (B2), 3M, copies 200 to 205: pooled-5 means 74.0, 67.1 and 53.7.",
            "Ours led by 6.9 over the plain model that writes steps, and by 20.3 over the one that answers directly.",
            "The earlier 2-copy screen gave 73.7, 67.7 and 54.4."
          ],
          "bars": [
            {
              "label": "Our design (B2)",
              "value": 74
            },
            {
              "label": "Plain, writes steps",
              "value": 67.1
            },
            {
              "label": "Plain, answers directly",
              "value": 53.7
            }
          ],
          "gains": [
            "+6.9",
            "+20.3"
          ],
          "ahead": "ahead on 6 of 6 copies",
          "chip": "tested: 6 copies, 3M",
          "caveat": "Caveat: the thinking-off leak check was over 5% on copies 201 and 203.",
          "src": [
            "whole-model-roadmap/8A-SPEC-2026-10-07.md lines 185-188 (B2 confirm, seeds 200-205: pooled-5 mean 74.0; plain_tf_steps 67.1; plain_tf 53.7)",
            "whole-model-roadmap/whole-model-roadmap-2026-10-06.md lines 365-369 (+20.3 vs plain_tf, CI 19.4 to 21.3; +6.9 vs plain_tf_steps; ahead on 6 of 6; leak check over 5% on seeds 201 and 203)",
            "architecture/model-deep-dive.html line 166 (2-seed screen: 73.7, 67.7, 54.4)"
          ],
          "notes": "Design: older B2 (calculator inside, 3M), not the finished design. No per-copy numbers exist in the sources, so no per-copy bars are drawn. +6.9 and +20.3 are as written in the sources (74.0 minus 67.1 = 6.9 and 74.0 minus 53.7 = 20.3 agree)."
        },
        {
          "id": "s07",
          "duration": 37,
          "heading": "A range of likely error",
          "caption": [
            "Even paired copies disagree a little, so we give a range of likely error, not one number.",
            "Calculator outside (T1SDR) minus the older design (B2), over 6 paired copies: plus 0.62, range minus 0.23 to plus 1.46.",
            "Marks: average at least minus 1.0, low end at least minus 2.0, and 5 of 6 copies within 1.0. All held."
          ],
          "axis": "T1SDR minus B2, pooled-5 points",
          "ticks": [
            "0",
            "1"
          ],
          "lines": {
            "m1": "mean mark -1.0",
            "m2": "low-end mark -2.0"
          },
          "mean": {
            "text": "+0.62",
            "value": 0.62
          },
          "lo": {
            "text": "-0.23",
            "value": -0.23
          },
          "hi": {
            "text": "+1.46",
            "value": 1.46
          },
          "chip": "tested: 6 paired copies",
          "src": [
            "architecture/MARKS-D0-T1-2026-10-07.md Record 13 (line ~200: pooled-5 T1SDR minus B2 mean +0.62, 95% CI -0.23 to +1.46, 6/6 seeds within 1.0)",
            "architecture/MARKS-D0-T1-2026-10-07.md Amendment 2 lines 49-58 (marks 1a mean >= -1.0, 1b CI low end >= -2.0, 1c at least 5 of 6 within 1.0)"
          ],
          "notes": "Marks 1a, 1b and 1c all held per Record 13 (relayed by another thread, not rechecked). Design: T1SDR vs B2 at 3M. The number line is to scale."
        },
        {
          "id": "s08",
          "duration": 35,
          "heading": "Switch a part off and watch",
          "caption": [
            "A lesion test switches one part off. If the answers break, that part was doing the work.",
            "Scores before and after: all three collapse.",
            "For B3, sealed first: thinking off must score at most half the full score, and above 60% of it is proved wrong."
          ],
          "cards": [
            {
              "title": "Thinking off",
              "sub": "6,040 questions",
              "from": 73.01,
              "to": 0.66,
              "dec": 2
            },
            {
              "title": "Another question's notes",
              "sub": "1,360 questions",
              "from": 86.03,
              "to": 4.19,
              "dec": 2
            },
            {
              "title": "Calculator off",
              "sub": "2,085 questions",
              "from": 100,
              "to": 0,
              "dec": 1
            }
          ],
          "chipTested": "tested: 1 copy, 3M",
          "chipB3": "B3 marks: never run",
          "src": [
            "chapters-out/ch09/g1-3m-s400-extract.json (thinking off 73.01 to 0.66; other question's notes 86.03 to 4.19 on 1,360 questions; calculator off 100.0 to 0.0 on 2,085 questions)",
            "big-run/PLAN.md lines 220-229 (B3-2 thinking-off at most half the full score; proved wrong above 60% of the full score)"
          ],
          "notes": "Reused from ch09 (G1 3M, copy 400, one copy). The B3-2 mark is a sealed mark for a design that has not run, so it is shown with the amber chip."
        },
        {
          "id": "s09",
          "duration": 35,
          "heading": "The leak light: two different checks",
          "caption": [
            "A leak means getting answers right when it should not. A small leak is a warning light.",
            "Check one, thinking off: the reader version averaged 6.59 against a limit of 4.62. Missed.",
            "Check two, another question's notes: 5.00 to 5.59 on 6 copies against a limit of 5. The project owner cleared it on Oct 9."
          ],
          "check1": {
            "title": "Thinking off",
            "limit": 4.62,
            "got": 6.59
          },
          "check2": {
            "title": "Another question's notes",
            "limit": 5,
            "got": 5.59
          },
          "labels": {
            "limit": "limit",
            "got": "measured",
            "high": "highest copy"
          },
          "chipMissed": "mark missed",
          "chipCleared": "cleared by owner, disclosed",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md line 31 (EGE confirm: zero-round leak mean 6.59 vs limit 4.62)",
            "architecture/MARKS-D0-T1-2026-10-07.md Record 13 lines 198-204 (T1SDR donor leak 5.59/5.15/5.59/5.07/5.00/5.59 vs flat limit 5; owner cleared mark 4 on Oct 9)"
          ],
          "notes": "Two different measures: check one is the zero-round (thinking off) leak of the reader version EGE; check two is the donor leak of T1SDR (right answers from another question's notes). The clearing was reported by another thread and not rechecked. The bar for check two shows the highest of the six copies."
        },
        {
          "id": "s10",
          "duration": 34,
          "heading": "Near-misses: a rule for screens only",
          "caption": [
            "On a 2-copy screen, missing a mark by at most 0.5 point still counts, if all else passes and the miss is reported.",
            "Examples: 98.96 against a mark of 99, and 97.89 against 98.0. The project owner called the first one close enough.",
            "Proved-wrong lines do not move. A 6-copy confirm gets no such tolerance."
          ],
          "rows": [
            {
              "mark": "mark 99",
              "got": "got 98.96"
            },
            {
              "mark": "mark 98.0",
              "got": "got 97.89"
            }
          ],
          "met": "counts as met on a screen",
          "confirm": "6-copy confirm: no tolerance",
          "src": [
            "architecture/MARKS-D0-T1-2026-10-07.md Amendment 10 item 1, lines 160-166 (hair tolerance: screens only, at most 0.5 point; 98.96 vs 99 and 97.89 vs 98.0 pass; 6-seed confirm gets no tolerance)",
            "big-run/PLAN.md line 229 (hair-miss rule applies on a screen; a confirm still needs the owner's call)"
          ],
          "notes": "The 97.89 case was one call over, a count-based mark. Numbers as written in the source."
        },
        {
          "id": "s11",
          "duration": 40,
          "heading": "Sleep must not hurt any family",
          "caption": [
            "An average can hide a weak spot: new wording scored 36.67 while the average was 73.01.",
            "So sleep, a night of study, is judged on every family. Harm: familiar down over 1.5, or a family down over 5, range below zero.",
            "A self-picking sleep trial was proved wrong on harm: 2 to 3 families lost 7 to 11 points."
          ],
          "kinds": [
            {
              "label": "Familiar",
              "value": 86.03
            },
            {
              "label": "New answers",
              "value": 71.92
            },
            {
              "label": "New sentence frames",
              "value": 86.62
            },
            {
              "label": "New words",
              "value": 89.38
            },
            {
              "label": "New wording",
              "value": 36.67
            }
          ],
          "avg": "average 73.01",
          "rule": {
            "a": "1.5",
            "aLabel": "familiar drop",
            "b": "5",
            "bLabel": "any family drop"
          },
          "result": {
            "big": "7 to 11",
            "chip": "proved wrong on harm"
          },
          "src": [
            "chapters-out/ch09/g1-3m-s400-extract.json (per-kind scores 86.03 / 71.92 / 86.62 / 89.38 / 36.67; pooled 73.01 = 4,410 of 6,040)",
            "big-run/PLAN.md line 74 (row 5: harm if in_dist drops more than 1.5 or any family drops more than 5 with its range below 0; SC proved wrong on harm, 2 to 3 families fell 7 to 11 points per parent)",
            "memory/MEMORY.md line 13 (same harm rule)"
          ],
          "notes": "The sleep trial was reported by the creative thread and not rechecked; it ran on older parent models, not the finished design. The five scores are one copy, 3M, copy 400."
        },
        {
          "id": "s12",
          "duration": 29,
          "heading": "Size counts every part",
          "caption": [
            "Size counts every number that runs, borrowed ones included.",
            "Drawn to scale: our learned part is a thin sliver beside the borrowed reader.",
            "So the 73.01 against 67.12 gap compares learned numbers only, on one copy. A whole-size race is planned, not run."
          ],
          "bars": [
            {
              "label": "Ours (3M)",
              "learned": 3544913,
              "borrowed": 271002624,
              "total": 274547537
            },
            {
              "label": "Plain model",
              "learned": 3495936
            }
          ],
          "labels": {
            "learned": "learned",
            "borrowed": "borrowed reader",
            "total": "in all"
          },
          "chip": "whole-size race: plan only",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md line 130 (size counts every weight that runs, borrowed ones included)",
            "chapters-out/ch09/g1-3m-s400-extract.json (our learned 3,544,913; whole size with frozen Gemma 274,547,537; plain model 3,495,936; 73.01 vs 67.12)",
            "architecture/FINISHED-MODEL-2026-10-09.md line 31 (reader: EmbeddingGemma 2 text part, 271,002,624, borrowed, frozen; 3,544,913 + 271,002,624 = 274,547,537)",
            "big-run/PLAN.md lines 33, 46, 77 (planned whole-size race, untested)"
          ],
          "notes": "Bar widths are to scale (learned part is 1.3% of the whole, our division of 3,544,913 by 274,547,537). The gap is a comparison of learned numbers only; 73.01 minus 67.12 = 5.89 is our subtraction, not drawn.",
          "scores": {
            "ours": "73.01",
            "plain": "67.12"
          }
        },
        {
          "id": "s13",
          "duration": 40,
          "heading": "Checked by reviewers, and still limited",
          "caption": [
            "On Oct 9, 20 AI helpers checked every note and code file against the source of truth. A second helper rechecked each finding.",
            "220 findings survived. The source of truth itself was wrong in 17 small places, and is now fixed.",
            "A test only fixes what it measures: one clean size, made-up families, and nothing yet on the game goal."
          ],
          "audit": {
            "title": "Oct 9 audit",
            "found": 220,
            "rows": [
              {
                "label": "high",
                "value": 14
              },
              {
                "label": "medium",
                "value": 140
              },
              {
                "label": "low",
                "value": 66
              }
            ]
          },
          "limits": [
            {
              "kind": "untested",
              "text": "learned stop: never run"
            },
            {
              "kind": "untested",
              "text": "finished design B3: never run"
            },
            {
              "kind": "placeholder",
              "text": "game goal: not touched"
            }
          ],
          "limitsTitle": "Not shown yet",
          "src": [
            "architecture/AUDIT-2026-10-09.md lines 5-8 (20 helpers, second helper checks each, 220 findings: 14 high, 140 medium, 66 low; source of truth wrong in 17 small places, fixed; learned stop never run)",
            "big-run/PLAN.md row 8 (eyes, hands and a game loop are not built)"
          ],
          "notes": "The audit file says Haiku helpers; shown as AI helpers. B3 never run is from big-run/PLAN.md lines 220-229."
        },
        {
          "id": "s14",
          "duration": 22,
          "heading": "What to remember",
          "caption": [
            "Marks are written first, with a line that would prove the idea wrong.",
            "Six paired copies and a range of likely error come before any claim.",
            "Every part is counted, and every miss is reported."
          ],
          "badges": [
            "marks first",
            "6 paired copies",
            "count every part"
          ],
          "src": [
            "Recap of scenes s03, s05 to s07, s09 to s12 of this chapter"
          ]
        }
      ]
    },
    "ch11": {
      "kicker": "Part 11 of 14",
      "title": "Learning while it sleeps",
      "blurb": "After a day of practice, the model studies what it found and settles it in. Here is how a night of sleep works, what it scored, and what is not shown.",
      "accent": "learned",
      "scenes": [
        {
          "id": "s01",
          "duration": 30,
          "heading": "Where we are: outside the five parts",
          "caption": [
            {
              "at": 0.023,
              "text": "Sleep is not a sixth part. It is a way of learning, tested so far only in research."
            },
            {
              "at": 0.333,
              "text": "After a day of practice, the model studies what it found and settles it in."
            },
            {
              "at": 0.6,
              "text": "The model runs its own night. The tests used six starting copies from an earlier design."
            }
          ],
          "L": {
            "day": "Day: practice",
            "night": "Night: sleep",
            "chip": "research result",
            "note": "Earlier design, not the finished model"
          },
          "src": [
            "animations/model-explainer-build/kit/GLOSSARY.md:37 (sleep definition)",
            "animations/model-explainer-build/sources/pr-53-consolidation-sleep.md:4 (the model must run its sleep itself), :23 (parent build, B2 -> N)",
            "big-run/PLAN.md:184 (shipped model needs sleep; sleep tested on the parents), :191"
          ],
          "notes": "Five-part map is the shared kit picture of the finished design; sleep is drawn outside it so it does not read as a sixth part. 'Earlier design' rests on PR #53 line 23 ('B2 -> N' parent build); PLAN line 184 says B3 3M tests are in parallel, so no sleep result on the finished design exists in the sources.",
          "illustration": "day and night boxes with a moon are a picture only"
        },
        {
          "id": "s02",
          "duration": 35,
          "heading": "A puzzle with a hidden rule",
          "caption": [
            {
              "at": 0.02,
              "text": "A few examples hide a rule: 2 gives 5, 4 gives 9, 7 gives 15."
            },
            {
              "at": 0.282,
              "text": "The model tries rules. A try counts only if it fits every example, so no answer key is needed."
            },
            {
              "at": 0.6,
              "text": "Only x times 2 plus 1 fits all three. So 10 gives 21 (our arithmetic: 10 times 2, plus 1)."
            }
          ],
          "L": {
            "exHead": "examples",
            "ex": [
              "2→5",
              "4→9",
              "7→15"
            ],
            "query": "10→?",
            "rules": [
              "x+3",
              "x×2+1",
              "x×3−1"
            ],
            "fits": [
              1,
              3,
              1
            ],
            "fitSuf": " of 3",
            "answer": "10→21",
            "tag": "made-up example in the style of the test"
          },
          "src": [
            "creative-roadmap/creative-roadmap-page.html:248-264 (puzzle 2->5, 4->9, 7->15, 10->?; tries x+3, x*2+1, x*3-1; fit counts 1 of 3, 3 of 3, 1 of 3), :251 ('No answer key needed: a try counts only if it fits every example')",
            "animations/storyboards-2026-10-09.md idea 3 table row 1 (tag 'example in the style of the test')"
          ],
          "notes": "The answer 21 is our arithmetic: 10 x 2 + 1. Fit counts checked by hand: x+3 fits 2->5 only; 3x-1 fits 2->5 only; 2x+1 fits 5, 9, 15. The page tags this puzzle 'easy rules only so far'.",
          "illustration": "the whole puzzle is a picture in the style of the test, not a test question"
        },
        {
          "id": "s03",
          "duration": 41,
          "heading": "What the test really is",
          "caption": [
            {
              "at": 0.017,
              "text": "The test has five kinds of rules, 65 rules in all, as the project's notes describe it."
            },
            {
              "at": 0.218,
              "text": "The model reads which rule a few new examples show, then answers a new question of that kind on the first try."
            },
            {
              "at": 0.466,
              "text": "It is not inventing a rule it has never met."
            },
            {
              "at": 0.6,
              "text": "The notes do not agree on whether these rules were practised before. That is not settled."
            }
          ],
          "L": {
            "kinds": [
              "a×x+b",
              "x²",
              "x²+k",
              "last digit of x",
              "2×(x+k)"
            ],
            "n": 65,
            "nLabel": "rules in all",
            "ex": "a few new examples",
            "which": "which rule?",
            "ans": "first-try answer",
            "tag": "notes only, report not seen",
            "pic": "picture only"
          },
          "src": [
            "animations/storyboards-2026-10-09.md:95 (five kinds of rules, 65 rules in all, all seen in practice; reading which rule, not inventing one; quotes the report's caveat; the report itself is not in the snapshot)",
            "idea-swarm/raw/areas/minecraft.json:1021 (holdout uses the same 65 rules as practice; board claim)",
            "memory/fast-sleep.md:20 (kinds a*x+b, x^2, x^2+k, x mod 10, 2(x+k))",
            "creative-roadmap/creative-roadmap-2026-10-06.md:498-499 and creative-roadmap-page.html:528 (early test used 5 never-practised kinds)"
          ],
          "notes": "UNSUPPORTED in primary sources: the report fast-sleep/RESEARCH-LOOP-2026-10-07-report.md is not in our copy, so 65 rules, 'seen in practice' and the 'not inventing' caveat come only from the storyboard (and one board claim). The roadmap says the early version of this test used 5 never-practised kinds, so the notes disagree; shown on screen as 'not settled'. Kind names follow memory/fast-sleep.md:20 (x mod 10 shown as 'last digit of x').",
          "illustration": "the three example cards and the flow are a picture only"
        },
        {
          "id": "s04",
          "duration": 43,
          "heading": "Where it started, and the old sleep",
          "caption": [
            {
              "at": 0.016,
              "text": "At the start, the model scored 41.6 out of 100 on this test, as the project's notes say."
            },
            {
              "at": 0.22,
              "text": "The old sleep lifted that to 71.3, give or take 2.5, averaged over six copies."
            },
            {
              "at": 0.396,
              "text": "It needed 558 to 610 updates, by its formula. One update is one small nudge to every setting."
            },
            {
              "at": 0.6,
              "text": "By kind, a×x+b was hardest at 15.5, and x squared easiest at 98.7."
            }
          ],
          "L": {
            "start": "Start",
            "old": "Old sleep",
            "startVal": 41.6,
            "oldVal": 71.3,
            "range": "±2.5",
            "steps": 558,
            "stepsTo": "to 610",
            "stepsLabel": "updates, by its formula",
            "kindHead": "Old sleep, score by kind",
            "kinds": [
              "a×x+b",
              "x²",
              "x²+k",
              "last digit of x",
              "2×(x+k)"
            ],
            "kindVals": [
              15.5,
              98.7,
              76.6,
              93.1,
              72.5
            ]
          },
          "src": [
            "memory/fast-sleep.md:20 (old sleep 71.3 +/- 2.5 on s200-s205: 71.1 72.5 73.8 69.5 67.2 73.4; per kind a*x+b 15.5, x^2 98.7, x^2+k 76.6, x mod 10 93.1, 2(x+k) 72.5)",
            "idea-swarm/raw/areas/minecraft.json:2351 and fastsleep.json:148 (41.6% start; board claims)",
            "animations/model-explainer-build/sources/pr-53-consolidation-sleep.md:9 (558-610 by its formula)",
            "animations/storyboards-2026-10-09.md idea 3 (41.6, 558 to 610)"
          ],
          "notes": "Computed: the six old values 71.1 72.5 73.8 69.5 67.2 73.4 average 71.25, written 71.3; the five kind scores average 71.28 (our addition, matches 71.3). 41.6 appears only in board notes and the storyboard, no primary result file in our copy; the formula for 558-610 is not in our copy, only stated by PR #53 and the storyboard.",
          "illustration": "none; bars and counters are measurements as stated"
        },
        {
          "id": "s05",
          "duration": 43,
          "heading": "One night of the new sleep",
          "caption": [
            {
              "at": 0.016,
              "text": "The model runs its own night: its own tries, at a temperature it picks, plus chain search."
            },
            {
              "at": 0.197,
              "text": "Then it sleeps for 256 updates, each of 1,024 rows. A row is one practice question."
            },
            {
              "at": 0.368,
              "text": "Half the rows are fresh dreams, new questions written from a found program, so none is read twice. Half are fresh skills rows."
            },
            {
              "at": 0.6,
              "text": "Every 32 updates it checks its fit rate on 128 held questions and keeps its best saved model."
            }
          ],
          "L": {
            "tries": "Its own tries",
            "search": "Chain search",
            "rows": "1,024 rows",
            "dreams": "Fresh dreams",
            "skills": "Fresh skills rows",
            "updates": "updates",
            "total": 256,
            "check": "check",
            "keep": "keep best saved model",
            "pic": "picture only"
          },
          "src": [
            "animations/model-explainer-build/sources/pr-53-consolidation-sleep.md:15-18 (recipe)",
            "creative/consol.py (code named by PR #53 line 31; not read)"
          ],
          "notes": "256 / 32 = 8 checks (our division). 'A row is one practice question' and 'fit rate' are plain-words readings of PR #53 wording; 'fit' = how often its tries fit the examples (creative-roadmap-page.html:251). Chain search is named in PR #53 and memory/fast-sleep.md:20 with no further definition in our copy. The 32 here is updates between checks, not the 32-round cap of the thinker.",
          "illustration": "the row strips and the dream cards are a picture only; the numbers 256, 1,024, 32 and 128 are from the pull request"
        },
        {
          "id": "s06",
          "duration": 34,
          "heading": "Six copies, one score",
          "caption": [
            {
              "at": 0.021,
              "text": "Six separate copies each went through the new sleep. Each score is out of 100."
            },
            {
              "at": 0.31,
              "text": "Averaged, that is 76.1. Our addition: the six add to 456.7, then divide by 6."
            },
            {
              "at": 0.6,
              "text": "Copy C scored 71.3. That is its own new score, not the old sleep's average."
            }
          ],
          "L": {
            "labels": [
              "copy A",
              "copy B",
              "copy C",
              "copy D",
              "copy E",
              "copy F"
            ],
            "values": [
              78.3,
              77.9,
              71.3,
              75.8,
              76.4,
              77
            ],
            "avg": "average",
            "avgVal": 76.1,
            "chip": "six copies, one run each",
            "note": "Not the old sleep's 71.3"
          },
          "src": [
            "animations/model-explainer-build/sources/pr-53-consolidation-sleep.md:8 (76.1% = 78.3, 77.9, 71.3, 75.8, 76.4, 77.0), :28 (one training run per parent)"
          ],
          "notes": "Computed: 78.3 + 77.9 + 71.3 + 75.8 + 76.4 + 77.0 = 456.7; 456.7 / 6 = 76.12, written 76.1. Copy letters follow the order listed in the pull request (parents s200-s205).",
          "illustration": "none; bars are measurements"
        },
        {
          "id": "s07",
          "duration": 36,
          "heading": "New sleep next to old sleep",
          "caption": [
            {
              "at": 0.019,
              "text": "On paper, the new sleep scores 76.1 and the old sleep 71.3."
            },
            {
              "at": 0.241,
              "text": "It used 256 updates; the old one 558 to 610. Half of 558 is 279 (our arithmetic), and 256 is under it."
            },
            {
              "at": 0.6,
              "text": "But this is not a paired comparison. 71.3 is the old sleep's stored number, from its own near-copy starting copies."
            }
          ],
          "L": {
            "scoreHead": "first-try score, out of 100",
            "old": "Old sleep",
            "new": "New sleep",
            "oldVal": 71.3,
            "newVal": 76.1,
            "range": "±2.5",
            "stepsHead": "updates used",
            "oldSteps": "to 610",
            "oldStepsVal": 558,
            "newSteps": 256,
            "half": "half: 279",
            "stamp": "not a paired comparison"
          },
          "src": [
            "animations/model-explainer-build/sources/pr-53-consolidation-sleep.md:8-9 (76.1, 256 updates, 558-610 by its formula), :27 (Not a paired comparison: 71.3% is the research loop's stored number on its own near-copy parents)",
            "memory/fast-sleep.md:20 (71.3 +/- 2.5)"
          ],
          "notes": "Computed: 558 / 2 = 279. The bar for the old sleep's updates ends at 558 with a light extension to 610.",
          "illustration": "none; the stamp is a warning label"
        },
        {
          "id": "s08",
          "duration": 39,
          "heading": "The pass marks: four met, one not shown",
          "caption": [
            {
              "at": 0.018,
              "text": "Every pass mark was fixed before the run. Score: 76.1, where 71.3 was needed."
            },
            {
              "at": 0.212,
              "text": "Updates: 256 each night, under half of the old sleep's."
            },
            {
              "at": 0.363,
              "text": "Harm measure: did old skills drop? No. Old skills also went up, with a likely range above zero."
            },
            {
              "at": 0.6,
              "text": "Last: does sleep beat plain practice? That was not shown."
            }
          ],
          "L": {
            "rows": [
              {
                "name": "First-try score",
                "res": "76.1, needed 71.3",
                "v": "pass"
              },
              {
                "name": "Updates",
                "res": "256 each night",
                "v": "pass"
              },
              {
                "name": "No harm",
                "res": "+0.12 to +0.82",
                "v": "pass"
              },
              {
                "name": "Old skills up",
                "res": "+0.52 [0.31, 0.74]",
                "v": "pass"
              },
              {
                "name": "Through transfer",
                "res": "−1.58 [−1.79, −1.37]",
                "v": "not shown"
              }
            ]
          },
          "src": [
            "animations/model-explainer-build/sources/pr-53-consolidation-sleep.md:4 (every pass mark fixed before its run), :7-12 (verdict table)"
          ],
          "notes": "Numbers in square brackets are likely ranges. Mark 3 'no harm vs the pre-sleep model (harm_measure)': in_dist +0.12 to +0.82, no family fires on any parent. 'Through transfer' = sleep minus replay-only control, must be above 0.",
          "illustration": "none"
        },
        {
          "id": "s09",
          "duration": 43,
          "heading": "Old skills: no harm, but who gets the credit?",
          "caption": [
            {
              "at": 0.016,
              "text": "Harm measure: did old skills get worse? On every copy they moved +0.12 to +0.82 points."
            },
            {
              "at": 0.218,
              "text": "Pooled over the six copies, they rose by 0.52, likely range 0.31 to 0.74."
            },
            {
              "at": 0.399,
              "text": "A replay-only control, practising the same skills rows, raised them by 2.11, range 1.88 to 2.32."
            },
            {
              "at": 0.6,
              "text": "So the gain is not shown to come from the sleep. Sleep minus control: −1.58."
            }
          ],
          "L": {
            "axisHead": "change in old-skill score, in points",
            "ticks": [
              -2,
              0,
              2
            ],
            "copyRow": {
              "label": "Each copy",
              "lo": 0.12,
              "hi": 0.82
            },
            "rows": [
              {
                "label": "Sleep",
                "v": 0.52,
                "lo": 0.31,
                "hi": 0.74
              },
              {
                "label": "Replay-only control",
                "v": 2.11,
                "lo": 1.88,
                "hi": 2.32
              },
              {
                "label": "Sleep minus control",
                "v": -1.58,
                "lo": -1.79,
                "hi": -1.37
              }
            ],
            "chip": "pooled, six copies"
          },
          "src": [
            "animations/model-explainer-build/sources/pr-53-consolidation-sleep.md:10 (in_dist +0.12 to +0.82, no family fires), :11 (+0.52 [0.31, 0.74]), :12 (-1.58 [-1.79, -1.37]), :22 (replay-only control +2.11 [1.88, 2.32]; the +0.52 is not shown to come from the new skill)"
          ],
          "notes": "The score change is the 'in_dist' measure of PR #53 (questions like the practice ones). The control is the pull request's 'replay-only control with the same skills rows'. Square brackets and 'range' mean likely range.",
          "illustration": "none; the number line is a measurement plot"
        },
        {
          "id": "s10",
          "duration": 43,
          "heading": "Fresh dreams or re-read rows?",
          "caption": [
            {
              "at": 0.016,
              "text": "The old sleep re-reads the day's rows. The new one writes a fresh dream each time, so no row is read twice."
            },
            {
              "at": 0.32,
              "text": "At equal updates, fresh dreams beat re-read rows by 7.4 (range 3.5 to 11.3) and 5.5 (range 0.8 to 10.2)."
            },
            {
              "at": 0.6,
              "text": "Two copies, development questions only. Whether fresh dreams cut harm could not be tested: re-read rows did no harm either."
            }
          ],
          "L": {
            "reread": "Re-read rows",
            "fresh": "Fresh dreams",
            "pic": "picture only",
            "same": "2→5",
            "diff": [
              "2→5",
              "4→9",
              "7→15",
              "10→21"
            ],
            "head": "fresh dreams minus re-read rows, in points",
            "ticks": [
              0,
              4,
              8,
              12
            ],
            "rows": [
              {
                "label": "Copy 1",
                "v": 7.4,
                "lo": 3.5,
                "hi": 11.3
              },
              {
                "label": "Copy 2",
                "v": 5.5,
                "lo": 0.8,
                "hi": 10.2
              }
            ],
            "chip": "first screen, 2 copies"
          },
          "src": [
            "animations/model-explainer-build/sources/pr-53-consolidation-sleep.md:21 (Screen A, 2 parents, DEV: +7.4 [3.5, 11.3] and +5.5 [0.8, 10.2]; A1 could not be tested)",
            "big-run/PLAN.md:191 (consolidation Screen A is on hold)"
          ],
          "notes": "'Development questions' = DEV. The two copies are the two parents of Screen A, not necessarily two of the six.",
          "illustration": "the stacks of cards are a picture only"
        },
        {
          "id": "s11",
          "duration": 45,
          "heading": "What is not shown",
          "caption": [
            {
              "at": 0.016,
              "text": "71.3 is the old sleep's stored number, from its own near-copy starting copies. It is not side by side with 76.1."
            },
            {
              "at": 0.214,
              "text": "Each copy slept once, so a repeat might score differently."
            },
            {
              "at": 0.326,
              "text": "The stop rule never ended a night early. Only keeping the best saved model acted."
            },
            {
              "at": 0.477,
              "text": "Building the copies cost rule-from-examples skills 2.3 points. Sleep won back about 0.5; the control, most."
            },
            {
              "at": 0.637,
              "text": "Against the earlier model, the harm check still fails on all six copies. Report only."
            }
          ],
          "L": {
            "tag": "careful",
            "cards": [
              "Not a paired comparison",
              "One training run per copy",
              "Stop rule never ended a night",
              "Copies lost 2.3 points before sleep"
            ],
            "sub4": "harm check still fails"
          },
          "src": [
            "animations/model-explainer-build/sources/pr-53-consolidation-sleep.md:27-28 (not paired; one run per parent), :24 (stop rule never ended a night early; only keep best checkpoint acted), :23 (B2 -> N costs 2.3 in_dist points; sleep wins back about 0.5; control most; harm_measure against B2 fails on all six; report only)",
            "memory/fast-sleep.md:20 (in_dist harm of the 71.3 run UNMEASURED)"
          ],
          "notes": "Caveat cards use the warning orange, not the amber 'built, never tested' colour. 'saved model' is the plain word for the pull request's 'checkpoint'. 'The model deciding when to stop' is not tested (PR #53 line 24).",
          "illustration": "none"
        },
        {
          "id": "s12",
          "duration": 39,
          "heading": "Follow-ups, all on hold",
          "caption": [
            {
              "at": 0.018,
              "text": "Next, sleeps where the model picks its own replay rows. SC kept its gain but failed the harm mark."
            },
            {
              "at": 0.286,
              "text": "On SC, 2 to 3 skill groups fell 6.5 to 11.0 points per copy. SCL, with a slower learning rate, passed its marks."
            },
            {
              "at": 0.6,
              "text": "Both ran on two other copies, not the six. All of this is on hold; none feeds the first big training run."
            }
          ],
          "L": {
            "sc": "SC",
            "scRes": "failed the harm mark",
            "scl": "SCL",
            "sclRes": "passed its marks, reported not rechecked",
            "holdHead": "On hold",
            "hold": [
              "SC",
              "3e-4 learning rate",
              "fresh-dream screen",
              "71.3 re-check"
            ],
            "chip": "plan only"
          },
          "src": [
            "creative-roadmap/creative-roadmap-2026-10-06.md:1515-1521 (SC result: harm fails on both parents; s100 rule_apply -11.0, seq_next -10.5, list_stats -6.5; s101 order_chain -7.5, seq_next -8.0; first-try gain ratio 1.08 / 1.08 met)",
            "creative-roadmap/creative-roadmap-2026-10-06.md:1541-1545 (SCL passes on both parents; no family fires; lr 1e-4)",
            "big-run/PLAN.md:74 (sleep partly failed, SC proved wrong, SCL reported not rechecked), :191 (SC, AP, lr 3e-4, consolidation Screen A, the 71.3% re-check on hold; none feeds the pretraining run)"
          ],
          "notes": "Range 6.5 to 11.0 taken from the raw SC result lines (the dossier's '7 to 11' was rounded). Both follow-ups ran on development copies s100 and s101, not the six s200-s205 copies. PLAN line 74 says the SCL pass was reported, not rechecked. 'AP' is not explained anywhere in our copy of the sources.",
          "illustration": "none"
        },
        {
          "id": "s13",
          "duration": 45,
          "heading": "Another test: sleeping on its own tries",
          "caption": [
            {
              "at": 0.016,
              "text": "A different test, from Oct 7: first answer right out of 100, on 5 new rules and 256 development questions."
            },
            {
              "at": 0.216,
              "text": "Before sleeping: 0.4 for copy A, 1.2 for copy B. Sleeping on tries that failed the check did nothing."
            },
            {
              "at": 0.408,
              "text": "Sleeping on tries that passed the check: 27.3 and 35.9. The line, set first, was 15 more than before."
            },
            {
              "at": 0.6,
              "text": "Two copies, one short sleep each. Not comparable with 76.1 or 71.3."
            }
          ],
          "L": {
            "rows": [
              {
                "label": "A, before",
                "value": 0.4
              },
              {
                "label": "A, failed tries",
                "value": 0.4
              },
              {
                "label": "A, passed tries",
                "value": 27.3
              },
              {
                "label": "B, before",
                "value": 1.2
              },
              {
                "label": "B, failed tries",
                "value": 1.2
              },
              {
                "label": "B, passed tries",
                "value": 35.9
              }
            ],
            "line": "needed: 15 more than before",
            "box": "Different test",
            "chip": "2 copies"
          },
          "src": [
            "creative-roadmap/creative-roadmap-page.html:414-429 (bars 0.4 / 0.4 / 27.3 and 1.2 / 1.2 / 35.9; 'dashed line = 15 more than before, fixed before the run'), :528 (256 DEV questions; one sleep; first answer = greedy)",
            "creative-roadmap/creative-roadmap-page.html:524 (C2 first look: 256 questions on 5 never-practised rule kinds)"
          ],
          "notes": "The pass lines sit at 0.4 + 15 = 15.4 and 1.2 + 15 = 16.2 (our addition). The page marks this card 'passed'. Different test from the 71.3 / 76.1 scores: 5 new rules, 2 copies, 256 development questions.",
          "illustration": "none; bars are measurements"
        },
        {
          "id": "s14",
          "duration": 43,
          "heading": "What to remember",
          "caption": [
            {
              "at": 0.016,
              "text": "Sleep is a night of study after a day of practice. The new sleep scored 76.1 in 256 updates, not in a paired test."
            },
            {
              "at": 0.35,
              "text": "Old skills were not harmed, but sleep is not shown to help them more than plain practice."
            },
            {
              "at": 0.6,
              "text": "A research result, not yet part of the model. The first big run does not wait for it; a finished model needs it."
            }
          ],
          "L": {
            "cards": [
              "76.1 in 256 updates",
              "No harm found; credit not shown",
              "Research result, not a part yet"
            ],
            "chips": [
              "tested",
              "tested",
              "plan only"
            ],
            "compute": "Compute: new sleep, cloud CPU, no money. Old sleep's search: rented card, about $2.9."
          },
          "src": [
            "animations/model-explainer-build/sources/pr-53-consolidation-sleep.md:8, :22, :27, :29 (cloud CPU, no money)",
            "memory/fast-sleep.md:20 (old sleep's research loop: Vast 5090, ~$2.9 of $4 cap)",
            "big-run/PLAN.md:184 (does not block the pretraining launch, a shipped model needs it), :191",
            "animations/storyboards-2026-10-09.md idea 3 closing line (a research result, not a part of the model yet)"
          ],
          "notes": "Compute is stated per run: the pull request says the new sleep ran on the cloud CPU and cost nothing; the memory note says the research loop that gave the old sleep's 71.3 used a rented graphics card for about $2.9 of a $4 limit. These are different runs, so they do not contradict each other. Glossary: no rented machines are being used now.",
          "illustration": "none"
        }
      ]
    },
    "ch12": {
      "kicker": "Part 12 of 14",
      "title": "Built or planned, not yet proven",
      "blurb": "Ideas the team has built or planned but not proven. For each one: the question it answers, what exists today, and what result would count as a pass.",
      "accent": "untested",
      "scenes": [
        {
          "id": "s01",
          "duration": 26,
          "heading": "Where each idea touches the model",
          "caption": [
            "These are the ideas on the way to the finished model.",
            "Almost none has been run. Amber means built, never tested. Grey means a plan only."
          ],
          "labels": {
            "reader": "2,000 letters, tokens",
            "thinker": "experts",
            "calc": "calls in any round",
            "stop": "learned stop",
            "talker": "one learned writer",
            "domain": "domain mode",
            "later": "later plans"
          },
          "chips": {
            "built": "built, never tested",
            "plan": "plan only",
            "ran": "run once, not passed"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (B3 groups), sec. 6 (Being tested, Not in run-1)",
            "sources/pr-56-b3-group1-and-token-test.md (Runs: none yet)",
            "domain-mode/DESIGN-AND-MARKS-2026-10-09.md addendum A10 (one run, did not pass)"
          ],
          "notes": "BUILD: S.modelMap, no highlight, all five parts + arrows. Under each part a small tag text from labels and an amber S.chip('untested',{label:chips.built}). Below the map two wide cards: 'domain mode' with S.chip('tested',{label:chips.ran}) (the only result in the chapter; a failed run is still a result) and 'later plans' with S.chip('placeholder',{label:chips.plan}). Long-text reading and the other later ideas are grey. Group 1 touches reader (2,000 letters), calc (calls in any round), stop; group 2 touches the writer; tokens touch the reader; experts touch the thinker. Mapping is ours, for orientation."
        },
        {
          "id": "s02",
          "duration": 31,
          "heading": "Group 1: four changes in one model",
          "caption": [
            "Group 1 puts four changes in one model. A switch is an on/off setting in the code.",
            "Only two are real switches, both off at the start.",
            "If the first test fails, turning each switch off, one at a time, shows the cause."
          ],
          "labels": {
            "a": "Gemma, outside calculator",
            "a_tag": "switch",
            "b": "calls in any round",
            "b_tag": "switch",
            "c": "2,000-letter inputs",
            "c_tag": "settings file",
            "d": "learned stop",
            "d_tag": "always on",
            "off": "off"
          },
          "chip": "built, never tested",
          "src": [
            "sources/pr-56-b3-group1-and-token-test.md (After: two real switches eg_embed and any_round, both off by default; caps_b3.json; stop always on; bisect)",
            "architecture/B3-GROUP1-BUILD-2026-10-09.md sec. 0, sec. 9"
          ],
          "notes": "TRAP: PR #56's first paragraph and the spec sec. 0 say 'each of the four is a switch'; the code has TWO (eg_embed, any_round). Show two real switch toggles (shown OFF, small code names as tags eg_embed / any_round next to the plain words) and two boxes with a 'not a switch' tag. Newer wording (PR After paragraph) wins. BUILD: four boxes in a row; a small toggle graphic (card + knob) on the two switch boxes, knob slides to off then both pulse; at the third caption a coral arrow turns one toggle at a time (illustration of the bisect plan). Colours: reader/calc/stop part colours for the three part-related boxes."
        },
        {
          "id": "s03",
          "duration": 38,
          "heading": "Calls in any round, on a tape of 16",
          "caption": [
            "Tested so far: calls only after rounds 2 to 8. The new build allows any round.",
            "Each call goes in the next free place on a tape of 16: calls after rounds 2 and 5 fill places 1 and 2.",
            "In practice, 1 row in 4 gets 0 to 2 extra thinking rounds before each call."
          ],
          "labels": {
            "rounds": "rounds",
            "tape": "tape of 16",
            "c1": "call",
            "c2": "call",
            "full": "17th: not run, counted",
            "pic": "picture only",
            "rnums": [
              "1",
              "2",
              "3",
              "4",
              "5",
              "6"
            ],
            "pl": [
              "1",
              "2"
            ]
          },
          "illustration": "picture only: a made-up row of rounds, taken from the build's own test plan",
          "chip": "built, never tested",
          "src": [
            "architecture/B3-GROUP1-BUILD-2026-10-09.md sec. 3 (Tape, Running, Training with gap_p 0.25 and g from 0,1,2; test (b) rounds 2 and 5 give entries 0 and 1 visible from rounds 3 and 6; test (c) the 17th call)",
            "chapters-out/ch01 s12 (tested model: calls after rounds 2 to 8 only)",
            "chapters-out/ch05 s10 (tape holds 16 calls, 1 row in 4 gets 0 to 2 extra rounds)"
          ],
          "notes": "Max 32 rounds, so the picture shows only some rounds; draw 12 round boxes and an ellipsis, not 32. The 17th-call text: spec says a call when the tape is full is not run and is counted. BUILD: row of round boxes (thinker colour) left to right; a call box (coral) drops from round 2 into tape place 1, later from round 5 into place 2; the reply appears one round later with a thin arrow; then tape of 16 small cells fills; last a grey box for the 17th. Everything finished by 80%."
        },
        {
          "id": "s04",
          "duration": 38,
          "heading": "Group 1: the pass marks",
          "caption": [
            "Pass marks are fixed before any run, never moved.",
            "Mark 1: beat the plain model by 3.0 or more points out of 100, on 6,040 kept-aside questions.",
            "Proved wrong if the lead is under 1.0. Mark 5: no length group may fall over 10 points below the short one."
          ],
          "labels": {
            "axis": "lead over plain model",
            "wrong": "proved wrong: under 1.0",
            "mid": "undecided",
            "pass": "pass: 3.0 or more",
            "guess": "guess: +3 to +6",
            "pic": "picture only",
            "groups": [
              "280-700",
              "700-1,300",
              "1,300-2,000"
            ],
            "gt": "length groups, in letters"
          },
          "illustration": "picture only: the bar shows the marks, not a result",
          "chip": "marks B3-1, B3-5: first run after the size test (G1)",
          "src": [
            "big-run/PLAN.md sec. 5, 'G2 step 2 marks: B3 group 1 at 3M' table, rows B3-1 and B3-5 (lines 219-229)",
            "big-run/PLAN.md line 229 (prediction between +3 and +6, suggested)",
            "big-run/PLAN.md line 39 (first run after the G1 verdict)"
          ],
          "notes": "B3-1 compares B3 group 1 (3M, seed 400) with g2c3, the plain 3M control at the same caps and pool, on pooled-5 (6,040 dev rows). Pass +3.0, proved wrong below +1.0; anything between is not decided in the sources. B3-5 length groups 280-700, 700-1,300, 1,300-2,000 letters: pass no group more than 10 under the short one; proved wrong more than 20. The guess (+3 to +6) is labelled as a guess written before the run. Other marks B3-2..B3-4, B3-6 exist; not shown here. BUILD: a horizontal number line 0..6 drawn with three coloured zones (warn orange for below 1.0, grey for between, plain ink for 3.0 or more; no green), a marker labelled 'guess' spans 3 to 6; below, three small length boxes with a '10' bracket. G1 = growth size test (glossary)."
        },
        {
          "id": "s05",
          "duration": 33,
          "heading": "Group 2: counting hand-written pieces",
          "caption": [
            "Hand-written code is ordinary code a person wrote. The team counted what is left on group 1's answer path.",
            "Every count must reach 0. Reading and new kinds have the most left."
          ],
          "labels": {
            "stop": "stopping",
            "arith": "arithmetic",
            "read": "reading",
            "write": "writing",
            "kinds": "new kinds",
            "mark": "pass mark: 0",
            "r_stop": "learned stop",
            "r_arith": "one learned writer",
            "r_read": "number finder, no place code, raw bytes",
            "r_write": "one learned writer",
            "r_kinds": "steps as written, checked tries"
          },
          "values": {
            "stop": 0,
            "arith": 2,
            "read": 6,
            "write": 4,
            "kinds": 6
          },
          "chip": "counted in code, not a run",
          "src": [
            "no-hardcoding/INVENTORY-B3-2026-10-09.md 'Summary (scorecard counts)' lines 11-19",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (counts stop 0, arithmetic 2, reading 6, writing 4, new kinds 6; table of N1, O1, P1, V1, L1, ST1)",
            "architecture/B3-GROUP2-BUILD-2026-10-09.md sec. 1 (parts table)"
          ],
          "notes": "Counts are an inventory read in code, group 1 build; not a model result. 'Reading' lists A1,A3,A9,A10,A11,A16 = number finder N1, no place code P1, raw bytes V1; 'writing' lists A12,A14,A15,X1 and arithmetic X1,X2 = one learned writer O1; 'new kinds' B1..B6 = L1 and ST1. Group 2 is code only: its 3M run waits for the G1 test. BUILD: S.hbars with five rows, values count up, a thin dashed line at 0 labelled mark; right of each row an arrow to the replacement text (labels r_*). Amber chip."
        },
        {
          "id": "s06",
          "duration": 43,
          "heading": "Group 2: one writer spells the whole call",
          "caption": [
            "Today a small head picks one of 8 operations, and code types its name.",
            "Group 2 replaces both with one learned writer. It spells the call letter by letter, copying numbers from the question.",
            "A tool added later could then be called too."
          ],
          "labels": {
            "today": "today: 8 fixed names",
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
            "thinker": "thinker's notes",
            "writer": "writer",
            "q": "Tom has 12 apples and gives away 5.",
            "call": "sub 12 5",
            "toy": "Toy check, 500 questions, out of 100: copy a number 100.0; operation and numbers 99.0; thinker-only number 99.8",
            "pic": "made-up example"
          },
          "illustration": "made-up example: Tom's apples are not from a test",
          "chip": "code only, never run",
          "src": [
            "architecture/B3-GROUP2-BUILD-2026-10-09.md sec. 0 and sec. 2 (the writer)",
            "architecture/B3-GROUP1-BUILD-2026-10-09.md sec. 8 (the call writer must write the WHOLE call as letters so a tool added later can be called)",
            "big-run/PLAN.md addendum 2:10 PM ET item 5 (toy checks: copy a number 100.0%, op plus two copied numbers 99.0%, a number given only through the thinker 99.8%, 500 held-out rows; their numbers, not rerun)"
          ],
          "notes": "The toy numbers are the build thread's own small code check on made-up toy rows, quoted in PLAN.md; nothing here was rerun by us and it is not a result of the model on real questions. The example question is the video's made-up Tom's apples (ch01, ch04); the call sub 12 5 is the same as ch01. BUILD: left a faded card with the 8 op boxes (brown 'hand-written' tint, strike line), right the thinker vectors (S.vec indigo) -> writer box (call colour) -> S.type typing 'sub 12 5' letter by letter, with curves from the 12 and 5 in the question text to the typed digits. Toy line is a small note at the bottom (S.note). Amber chip."
        },
        {
          "id": "s07",
          "duration": 40,
          "heading": "Group 2: learning steps as written",
          "caption": [
            "A step like 7 + 5 = 12 was rewritten by a hand rule as sub 12 5.",
            "Now it is taught as written: add 7 5. The model finds the 7 itself; the calculator checks.",
            "Then it practises alone: 4 tries per question, checked by the calculator; only right tries are kept.",
            "Pass mark: up by at least 20 points on both copies. Never run."
          ],
          "labels": {
            "old": "hand rule",
            "old_to": "sub 12 5",
            "new": "as written",
            "new_call": "add 7 5",
            "reply": "calculator: 12",
            "tries": "4 tries",
            "kept": "kept for study",
            "pic": "picture only",
            "q": "question"
          },
          "illustration": "picture only: which tries are kept is made up",
          "chip": "built, never run",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 table (Worked steps rewritten by hand rules, e.g. '? + 5 = 12' becomes a subtraction; L1, ST1)",
            "architecture/B3-GROUP2-BUILD-2026-10-09.md sec. 4 (L1: '7 + 5 = 12' taught as add 7 5) and sec. 5 (ST1: sample 4 traces, keep matching answers, up to 3 rounds)",
            "big-run/PLAN.md line 262 (ST1 marks: up at least +20 on both seeds, pooled-5 not down more than 1.0; proved wrong below +5 on both)"
          ],
          "notes": "L1 and ST1 are two parts of group 2; ST1 is a separate stage run on a trained group 2 checkpoint. 'Both copies' = seeds 400 and 401 (glossary: copy). ST1 detail not shown: temperature 1.0, 500 updates per round at 1e-4; also pooled-5 must not drop more than 1.0 (not on screen). Proved wrong: below +5 on both. BUILD: top half L1: old box -> sub 12 5 (struck), new box -> add 7 5 where '?' turns into 7 and the calculator slip returns 12 with a tick; bottom half ST1: one question box -> 4 try boxes -> calculator -> two ticked tries slide into a 'kept for study' box. Which tries pass is made up (illustration)."
        },
        {
          "id": "s08",
          "duration": 44,
          "heading": "Experts: many small layers, a few used",
          "caption": [
            "Each thinker block's feed-forward layer is a small network of 1,228 units, at the 3 million size.",
            "The test cuts it into 52 experts of 154 units. A router picks 8 per input, as big public models do.",
            "The 8 picked hold 8 × 154 = 1,232 units: about the same work.",
            "On the Mac one update takes 25.0 s (about 6.9 days in all), so it runs on the PC."
          ],
          "labels": {
            "old": "today's layer",
            "new": "52 experts",
            "router": "router",
            "picked": "picked",
            "stored": "stored",
            "used": "used",
            "plain": "plain 3M thinker",
            "pic": "picture only",
            "sum": "8 × 154 =",
            "unit": "154 units each"
          },
          "values": {
            "stored": 10553929,
            "used": 3579225,
            "plain": 3544913,
            "units": 1232
          },
          "illustration": "picture only: which 8 experts are picked is made up",
          "chip": "built, never tested",
          "src": [
            "architecture/EXPERTS-TEST-2026-10-09.md sec. 2 (52 experts, 8 used, each Linear d to 154 to d, 1,232 vs 1,228 at d = 256)",
            "architecture/EXPERTS-TEST-2026-10-09.md sec. 3 (sizes table: G-B2 3M 3,544,913; GX-3M 10,553,929 total, 3,579,225 active)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 6 item 10 (finished model dense by default)"
          ],
          "notes": "OUR MULTIPLICATION: 8 x 154 = 1,232 (source says 1,232). 1,228 is 4.8 x width 256 (the 3M thinker); the 100M thinker is width 512 (ch04). Sizes are counted by formula in the spec, checked by the build's tests; not a run. Source says 8 active is what DeepSeek-V3, Qwen3 and Kimi K2 use; may be said in half a sentence if room. BUILD: left a wide box (old layer); right a grid of 52 small squares (4 rows x 13), router box with curves to 8 lit squares (expert colour: use thinker indigo tint); count '8 × 154' to 1,232 beside; beneath, three S.hbars rows (stored, used, plain) counting up. Source: experts built, nothing has run (Addendum C: after the build, before any run)."
        },
        {
          "id": "s09",
          "duration": 41,
          "heading": "Experts: keeping every expert in use",
          "caption": [
            "In an older design the experts were dead: its routers started at exactly 0.",
            "So experts 0 and 1 were exact copies and never split apart.",
            "Now the router starts random, and a small balance loss keeps picks about even.",
            "Pass mark: beat the plain 3M thinker by at least 1.0 point on each copy. The team's guess: no clear gain."
          ],
          "labels": {
            "old": "older design",
            "same": "exact copies",
            "new": "now",
            "band": "half to double an even share",
            "even": "even share: about 1.9 percent",
            "why": "why: 3 times more stored numbers gained only 0.49 before",
            "pic": "picture only"
          },
          "illustration": "picture only: the bars are not measured picks",
          "chip": "built, never tested",
          "src": [
            "architecture/EXPERTS-TEST-2026-10-09.md sec. 1 (dead experts: routers at exactly 0, experts 0 and 1 exact copies)",
            "architecture/EXPERTS-TEST-2026-10-09.md sec. 2 (router random, balance loss weight 0.01) and sec. 8 addendum A (mark X4: between half and double an even share, 1/52, about 1.9 percent)",
            "architecture/EXPERTS-TEST-2026-10-09.md sec. 4 (mark X1: plus 1.0 on each seed; prediction UNCLEAR or STOP; +0.49 over 6 seeds, with the 8-letter bug)"
          ],
          "notes": "The older experts audit is 10-05 (model audit). X1 compares GX-3M with G1's plain-thinker 3M (G-B2) per seed, pooled-5. Prediction in source: UNCLEAR or STOP, reason: in the 8a size test the thinker gained +0.49 over 6 seeds from 3x more dense weights (with the 8-letter bug), so stored weights do not look like the limit. The balancing-nudge detail (0.001 per pass) and the balance loss weight 0.01 are not on screen. Stage 2 (more layers) runs only if stage 1 passes; finished model stays dense unless both stages pass (said in s16). BUILD: left two identical S.vec strips 'expert 0' 'expert 1' with an equals sign and a cross; right 52 thin bars (heights random from K.rng, picture only) with a shaded band for half to double the even share; at the last caption the guess note."
        },
        {
          "id": "s10",
          "duration": 35,
          "heading": "Tokens: one spot per word piece",
          "caption": [
            "Today the thinker has one spot for every letter of the question.",
            "Gemma already cuts text into tokens, or word pieces. One token covers 3.08 letters on skill questions and 4.27 on web text.",
            "With one spot per token, the thinker's reading gets about 3 to 4 times cheaper. The rest still reads letters."
          ],
          "labels": {
            "letters": "Tom has 12 apples.",
            "today": "per letter",
            "tok": "per token",
            "skills": "skill questions",
            "web": "web text",
            "pic": "picture only",
            "unit": "letters per token"
          },
          "values": {
            "skills": 3.08,
            "web": 4.27
          },
          "illustration": "picture only: the real word pieces differ",
          "chip": "built, never tested",
          "src": [
            "architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 1 (3-4 times cheaper for the thinker's reading) and sec. 2 table (3.08 skill questions; 4.27 web text in 279-letter chunks; 4.36 at 2,000 letters)",
            "chapters-out/ch03 s03 (3.08 and 4.27) and s15 (promise: Chapter 12 covers tokens)"
          ],
          "notes": "The 3.08 and 4.27 are measured letters per token (counts of Gemma's tokenizer, spec sec. 2). '3 to 4 times cheaper' is the spec's own wording for the thinker's part, from letters per token; the whole model gets cheaper by less. Test name TK (and TKN, next scene). The grouping of letters in the picture is invented. BUILD: top the 18-letter row (S.letters), below a shorter row of grouped boxes with brackets joining about 3 letters each (picture only), two counting number cards 3.08 and 4.27 with their meanings."
        },
        {
          "id": "s11",
          "duration": 42,
          "heading": "Tokens: the risk is spelling",
          "caption": [
            "The risk is spelling: each token's spot is built from its letters, so single letters stay visible.",
            "An older test used word pieces instead of letters and lost 3.1 and 5.4 points out of 100. Here the letters stay.",
            "Pass mark: lose no more than 1.0 point. A second version drops the letter window, to test whether it can go."
          ],
          "labels": {
            "tk": "tokens, window kept (TK)",
            "tkn": "tokens, no window (TKN)",
            "old": "older test: pieces instead of letters",
            "runs": "4 runs, about 26 hours on the PC",
            "l": "letters",
            "w": "window",
            "t": "token spot"
          },
          "values": {
            "lost1": 3.1,
            "lost2": 5.4
          },
          "chip": "no run yet; decided before 30M",
          "src": [
            "architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 1 (risk: spelling) and sec. 2 first bullet (U0: lost 3.1 and 5.4 points pooled-5) and sec. 3, 3b",
            "architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 5 (M1: pooled-5 TK minus plain thinker, 2-seed mean, at least minus 1.0)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 6 (decided before the 30M freeze; seed 400 first)",
            "big-run/PLAN.md line 39 / REPLAN (token test 4 runs, about 26 PC-hours)"
          ],
          "notes": "Mark M1 is a two-copy mean (copies 400 and 401), no tolerance; other marks (M2 frame/vocab, M3 spelling puzzles, M4 chains, M5 thinker drives) not shown. 'Window' = the letter window (ch03). '30M' = the 30 million size rung of the ladder. The 3.1 and 5.4 are from the earlier U0 test, which removed letters; do not call them two copies (source does not say). 4 runs = TK and TKN x seeds 400, 401. BUILD: two rows of boxes (letters -> window -> token spot) for TK and TKN with the window box struck out in TKN; at the second caption two red-orange loss cards -3.1 and -5.4 counting down from 0 labelled 'older test'. Amber chip."
        },
        {
          "id": "s12",
          "duration": 32,
          "heading": "Long text: carry the notes forward",
          "caption": [
            "Plan only, no test proposed. The thinker now sees the question at once and forgets it afterwards.",
            "Idea: read long text in pieces and carry the thinker's notes from one piece to the next.",
            "It could also learn which older pieces to look back at, a pattern from DeepSeek's Native Sparse Attention."
          ],
          "labels": {
            "limit": "today's limit: 2,000 letters",
            "p1": "piece 1",
            "p2": "piece 2",
            "p3": "piece 3",
            "notes": "notes carried",
            "look": "learned look-back",
            "pic": "picture only"
          },
          "illustration": "picture only: pieces and notes are drawn, not measured",
          "chip": "plan only",
          "src": [
            "architecture/running-summary-2026-10-08.md sec. 1 and sec. 6 (carry vectors piece to piece, keep a glance back)",
            "architecture/important-links-2026-10-09.md sec. 3 (Native Sparse Attention, 2502.11089) and sec. 5 (add learned picking at the long-input stage; no test proposed)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 6 (Not in run-1: reading text longer than 2,000 letters)"
          ],
          "notes": "Both source notes are labelled suggested/untested; nothing was run for them. The look-back must be learned, never a hand list (important-links sec. 4). BUILD: three piece boxes in a row (reader teal), a strip of S.vec (thinker indigo) carried by arrows from piece 1 to 2 to 3, a curved arrow from piece 3 back to piece 1 appearing at the third caption, grey 'plan only' chip (S.chip('placeholder',{label:chips})). All motion by 80%."
        },
        {
          "id": "s13",
          "duration": 35,
          "heading": "Domain mode: the model teaches itself",
          "caption": [
            "The idea: type one line, like learn how to do spreadsheets, and the model studies the subject by itself.",
            "It makes practice by changing worked examples, checks each with a tool, and keeps what matched.",
            "Then it sleeps on it, checks it has not forgotten old skills, and stops when its own quiz stalls."
          ],
          "labels": {
            "s1": "open the tool",
            "s2": "make practice",
            "s3": "try it",
            "s4": "choose what to practise",
            "s5": "sleep",
            "s6": "check old skills",
            "s7": "stop",
            "pic": "picture only"
          },
          "illustration": "picture only: the loop is a plan; most steps are not built",
          "chip": "partly built, one run",
          "src": [
            "domain-mode/DESIGN-AND-MARKS-2026-10-09.md sec. 1 and sec. 2 (the seven steps table: what exists today)",
            "sources/pr-58-domain-mode.md (After: python -m domain.mode, nightly lr 1e-4, half self-replay, undo a night)"
          ],
          "notes": "Per sec. 2 'Exists today': open = not built (tool and help page are handed over in the small test); make practice = not built in the full sense; choose, check, stop = built into the small test loop but never run before this one run; sleep = partly. In the test, the loop calls the tool at fixed points on the model's behalf (disclosed, 'Level 1'); the full version needs group 2's whole-call writer. Fixed numbers (not on screen unless wanted): 1,024 made problems a day, quiz of 256 day-1 problems, 512 old questions for the forgetting check, undo if drift more than 3 points, at most 12 nights. BUILD: seven boxes on a ring or two rows with arrows between, a small marker token moves along them in step with the captions; spreadsheet example text in a note: 'A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A3)' -> 13 (this is the design's own help example, label it example)."
        },
        {
          "id": "s14",
          "duration": 41,
          "heading": "Domain mode: the first run did not pass",
          "caption": [
            "First real run: spreadsheets, one copy, 7 nights. Its own quiz rose from 11.7 to about 74.",
            "But on kept-aside sheet questions it went from 3.33 to 2.86. The pass mark was a gain of 30 points.",
            "Cause: its practice used one narrow grid shape, so it learned shortcuts, not what a cell reference means.",
            "Next: a wider practice maker, still hand-written code run at fixed points."
          ],
          "labels": {
            "quiz": "its own quiz",
            "near": "kept-aside, near",
            "far": "kept-aside, far",
            "before": "before",
            "after": "after",
            "need": "needed: +30"
          },
          "values": {
            "quiz0": 11.7,
            "quiz1": 74,
            "near0": 3.33,
            "near1": 2.86,
            "far0": 1.07,
            "far1": 0.36
          },
          "chip": "run once, not passed",
          "src": [
            "domain-mode/DESIGN-AND-MARKS-2026-10-09.md addendum A10 (run 1:02-1:52 PM ET 10-09, sheet, seed 200: 7 nights; quiz 11.7 to about 74; near 3.33 to 2.86; far 1.07 to 0.36; old skills in_dist 90.22 to 88.16; cause; ruling v2 wider practice maker)",
            "domain-mode/DESIGN-AND-MARKS-2026-10-09.md addendum A11 (practice maker is hand-written code called at fixed points; Level 1)",
            "domain-mode/DESIGN-AND-MARKS-2026-10-09.md marks DM1 (near plus 30; proved wrong below plus 10) and DM2"
          ],
          "notes": "NEWER THAN PR #58 and the brief: the PR body (and brief) say the first run is 'running'; addendum A10 (2:05 PM ET) records that it ran and DM1 was proved wrong on seed 200, so seed 201 did not run. Scores are on the 7 trainable kinds (ruling A2), not the 4.67 / 2.50 of the PR body (all 10 kinds, before practice). The 'quiz rose to about 74' is the source's pooled own-quiz value (74.22, 75.78, 73.83 in the last nights). Far score 1.07 to 0.36 (DM2 needed plus 10). Also reported: old-skills score dropped from 90.22 to 88.16 and two families fired (not on screen). Use S.chip('tested',{label:chips}) only because a result file exists; say in notes it is a failed result. BUILD: S.hbars before/after pairs (quiz, near, far) counting; a dashed marker at 'needed' on the near row; scene stays still last 20%."
        },
        {
          "id": "s15",
          "duration": 33,
          "heading": "Plans with no design or test yet",
          "caption": [
            "The model would call creative mode only when stuck. It would use a use-once puzzle tool and an example checker.",
            "The notebook would be a tool it can call. Saying I don't know has no design yet. Eyes, ears and hands for games are paused."
          ],
          "labels": {
            "c1": "creative mode, only when stuck",
            "c2": "use-once puzzle tool",
            "c3": "example checker",
            "c4": "notebook as a tool",
            "c5": "saying I don't know",
            "c6": "eyes, ears, hands: paused"
          },
          "chip": "plan only",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 6 'Not in run-1' (puzzle tool, example checker `check <program>`, notebook as a recall tool, I don't know has no design, eyes ears hands paused)",
            "creative-roadmap/creative-roadmap-2026-10-06.md lines 26, 43, 266 (creative mode used when the worker is stuck)"
          ],
          "notes": "All six are grey plans, none built into the finished model's run-1. The first caption's items are 'planned for the tool loop' (creative roadmap 7b); the creative mode when stuck has its own earlier small tests in the creative roadmap which are NOT claimed here. BUILD: six grey cards in a 3 x 2 grid appearing one per beat, each with S.chip('placeholder',{label:'plan only'}) only once for the group, not six times (word budget)."
        },
        {
          "id": "s16",
          "duration": 39,
          "heading": "What each idea would change, and the order",
          "caption": [
            "If it works, group 1 gives the 3M model calls anywhere, 2,000 letters and its own stop; group 2 removes hand-written pieces.",
            "Experts and tokens are side tests: they change the finished model only if their marks pass.",
            "The plan runs left to right, with no dates promised.",
            "Remember: almost none of this has been run."
          ],
          "labels": {
            "g1": "size test (G1)",
            "ex": "experts",
            "b1": "group 1, 3M",
            "b2": "group 2, 3M",
            "m10": "10M",
            "m30": "30M",
            "m100": "100M",
            "side": "tokens: fills a free PC slot",
            "dom": "domain mode: free cloud CPU"
          },
          "chip": "plan, no dates",
          "src": [
            "big-run/PLAN.md lines 39 and 41-46 (REPLAN path: after G1, GX stage 1 seed 400, fc100 fit check, plain control g2c3, B3 group 1 at 3M seed 400, then group 2 at 3M, then B3 10M, 30M, 100M)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 6 (tokens decided before the 30M freeze; experts join only if both stages pass)",
            "domain-mode/DESIGN-AND-MARKS-2026-10-09.md sec. 5 (cloud CPU)"
          ],
          "notes": "ORDER (plan, from PLAN.md REPLAN 'Path and dates', dates removed): G1 verdict -> experts stage 1 (seed 400 first) -> a free fit check of the 100M thinker in 16 GB -> plain 3M control -> B3 group 1 at 3M -> B3 group 2 at 3M (then ST1) -> 10M -> 30M -> 100M. Skipped for space: GX stage 2, seed 401 runs, c30 and g2c10 controls, six-seed confirm. The plan gives dates; none are shown (never state a future date as certain). Tokens: PLAN says it fills a gap on the PC and must never delay the B3 ladder. BUILD: a lane of 8 boxes with a marker that moves along to the 100M box by 70% of the scene; two side boxes (tokens, domain mode) below on dashed arrows; recap as last caption, three short lines would also be fine."
        }
      ]
    },
    "ch13": {
      "kicker": "Part 13 of 14",
      "title": "Size, and whether it pays off",
      "blurb": "The project does not ask whether bigger models are good. It asks whether our design gains more from extra size than a plain model does. Here is the ladder of sizes, what the first tests showed, and what is still unknown.",
      "accent": "thinker",
      "scenes": [
        {
          "id": "s01",
          "duration": 30,
          "heading": "Does a bigger model pay off?",
          "caption": [
            "A model is a list of learned numbers. More numbers means a bigger model.",
            "The project asks: does our design gain more from extra size than a plain model does?",
            "That is the bar. When both grow, our line must climb steeper than the plain line."
          ],
          "tag": "picture only: not a measurement",
          "labels": {
            "ours": "ours: the bar",
            "plain": "plain model",
            "more": "more gain",
            "xs": "smaller",
            "xe": "bigger",
            "y": "score"
          },
          "src": [
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md sec. 0 lines 8-13 (the project owner's bar: the benefit from more parameters should be more than the plain model's)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 7 line 125 ('must pass Ben's size bar itself')",
            "glossary: plain model = standard transformer of the same size on the same practice"
          ],
          "notes": "The two lines are an illustration only; no number is drawn from data."
        },
        {
          "id": "s02",
          "duration": 38,
          "heading": "The size ladder: 3M, 10M, 30M, 100M",
          "caption": [
            "The thinker comes in four sizes, named for their rough count of learned numbers. M means million.",
            "These counts come from the build. No run of the new build at these sizes has happened yet.",
            "At 100M the thinker is 21 blocks at width 512. The blocks alone are 97.1 million; with the adapter, window and heads, 102.1 million."
          ],
          "chip": "counted, never run",
          "rungs": [
            {
              "label": "3M",
              "value": 4039957
            },
            {
              "label": "10M",
              "value": 9832977
            },
            {
              "label": "30M",
              "value": 29789693
            },
            {
              "label": "100M",
              "value": 102116618
            }
          ],
          "src": [
            "animations/model-explainer-build/sources/pr-56-b3-group1-and-token-test.md line 15 (sizes at caps_b3: 4,039,957; 9,832,977; 29,789,693; 102,116,618) and line 17 ('Runs: none yet')",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 lines 21-25 (21 blocks at width 512 = 97.1M; 102.1M trained incl. Gemma adapter and letter window; ladder 3M, 10M, 30M, then 100M) and sec. 5 item 9 lines 132-135",
            "big-run/PLAN.md line 270 (102.1M trained thinker and heads, 21 blocks x 512)"
          ],
          "notes": "Counts are the B3 group-1 thinker at caps_b3. G1's older 3M thinker was 3,544,913 (ch09); the number name '3M' differs by build.",
          "labels": {
            "unit": "learned numbers in the thinker alone",
            "big": "100M: 21 blocks at width 512"
          }
        },
        {
          "id": "s03",
          "duration": 33,
          "heading": "Whole size counts the borrowed reader",
          "caption": [
            "The rule: size counts every number that runs, including the borrowed reader.",
            "As built at the 100M step: reader 271.0 million, frozen, plus the trained part 102.1 million makes 373.1 million.",
            "The plan adds an English talker of about 25 million. It is not built, so about 398 million is a plan."
          ],
          "labels": {
            "reader": "reader: borrowed, frozen",
            "ours": "ours: trained",
            "talker": "talker: planned",
            "built": "million, as built",
            "plan": "about 398 million: plan only"
          },
          "values": {
            "reader": 271,
            "ours": 102.1,
            "talker": 25,
            "total": 373.1
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 lines 21-23 (373.1M as built = 102.1M trained + 271.0M frozen Gemma; the 25M talker is not built) and sec. 5 item 8 lines 130-131 (size counts every weight that runs, borrowed ones included); the same lines give about 397M planned, counting the thinker as about 100M, which is why the sum on screen (373.1 + 25 = 398.1) is shown as about 398M",
            "big-run/PLAN.md line 270 and line 47 (about 373M whole as built; about 398M once a 25M talker is added)"
          ],
          "notes": "Bar segment widths are drawn to scale from the three source numbers. FINISHED line 21 says about 397M (thinker counted as about 100M); PLAN.md lines 47 and 270 say about 398M (373.1 + 25 = 398.1). The video shows about 398M so the sum on screen matches its own parts."
        },
        {
          "id": "s04",
          "duration": 44,
          "heading": "First size test: 3M to 10M (8a)",
          "caption": [
            "In the first size test, tag 8a, our model was grown from 3M to 10M. Its score moved from 72.34 to 72.83 points out of 100.",
            "That is a gain of 0.49. We needed about 3.0 per step. This is the older design, as it actually ran.",
            "On the same practice, the plain step-writing model gained 3.77 and the plain language model 15.77."
          ],
          "chip": "tested: 6 copies ours, 5 plain",
          "rows": [
            {
              "label": "ours",
              "value": 0.49,
              "from": 72.34,
              "to": 72.83
            },
            {
              "label": "plain step model",
              "value": 3.77
            },
            {
              "label": "plain language model",
              "value": 15.77
            }
          ],
          "needed": 3,
          "labels": {
            "head": "gain, 3M to 10M",
            "need": "needed: 3.0",
            "range": "5 of 6 copies gained; likely range -0.74 to +1.72"
          },
          "src": [
            "whole-model-roadmap/8A-10M-RESULT-2026-10-08.md line 49 (mark 1: +0.49, CI -0.74 to +1.72, 5 of 6 seeds positive, needed +3.0) and line 68 (means: B2 72.34 to 72.83 = +0.49; PT +3.77 (5 seeds); LLM +15.77 (5 seeds))",
            "same file lines 27-31 (plain summary says about 3.7 and about 15.6; the table values are used here)"
          ],
          "notes": "The summary text rounds to 3.7 and 15.6; the table says 3.77 and 15.77 (5 seeds each). The video uses the table. 'Ours' is B2 as it ran, with the settings bug of the next scene."
        },
        {
          "id": "s05",
          "duration": 37,
          "heading": "Where our model stayed flat",
          "caption": [
            "Split by question type, our model was already near the top on arithmetic stories.",
            "But on rule questions, like finding a rule from examples, ours stayed flat while the plain model kept growing.",
            "Continuing a pattern showed the same. Numbers are averages over 5 copies, about 120 to 200 questions per type."
          ],
          "heads": {
            "ours": "ours",
            "plain": "plain step model",
            "from": "3M",
            "to": "10M"
          },
          "rows": [
            {
              "label": "arithmetic stories",
              "o3": 100,
              "o10": 99.9,
              "p3": 94.2,
              "p10": 97.9
            },
            {
              "label": "find the rule",
              "o3": 19.1,
              "o10": 18.9,
              "p3": 31.8,
              "p10": 44.2
            },
            {
              "label": "continue the pattern",
              "o3": 36.2,
              "o10": 37.8,
              "p3": 41.5,
              "p10": 51.1
            }
          ],
          "chip": "tested, older design",
          "src": [
            "whole-model-roadmap/8A-10M-RESULT-2026-10-08.md lines 78-97 (per question type, mean of the 5 seeds with all arms; about 120-200 rows per type per seed): chain_ops line 84 (B2 100.0 to 99.9; PT 94.2 to 97.9), fewshot_number_rule line 94 (19.1 to 18.9; 31.8 to 44.2), seq_next line 95 (36.2 to 37.8; 41.5 to 51.1)"
          ],
          "notes": "Scores are points out of 100 per question type. 'Arithmetic stories' = chain_ops; 'find the rule' = fewshot_number_rule; 'continue the pattern' = seq_next."
        },
        {
          "id": "s06",
          "duration": 39,
          "heading": "The correction: a settings bug",
          "caption": [
            "Later, a settings bug was found. Our model had run with 9 note vectors, not the 36 the settings said.",
            "Its answer targets were also cut to 8 letters. The plain models were not affected.",
            "So the result is real for the model that ran, but untested for the model as designed."
          ],
          "tag": "picture only: cell shading means nothing",
          "labels": {
            "said": "settings said: 36 note vectors",
            "ran": "it ran with: 9 note vectors",
            "cut": "answer targets cut to 8 letters",
            "real": "real for the model that ran",
            "untested": "untested as designed"
          },
          "counts": {
            "said": 36,
            "ran": 9
          },
          "src": [
            "whole-model-roadmap/8A-10M-RESULT-2026-10-08.md lines 7-11 (Correction, 3:40 PM ET 10-08: 9 register tokens instead of 36, GEN targets cut to 8 letters, plain arms not affected; real for the B2 that ran, untested for B2 as designed)",
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md sec. 9 (addendum D) lines 129-136 (N_REG 9 and GEN_MAX 8 versus 36 and 35)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 line 34 (8 control + 36 memory vectors under the caps)"
          ],
          "notes": "'Register tokens' in the sources are the memory ('note') vectors of ch04. The fix is the re-run called G1."
        },
        {
          "id": "s07",
          "duration": 42,
          "heading": "The fixed re-run (G1): first result",
          "caption": [
            "The fixed re-run is called G1. So far only one rung is finished: 3M, copy 400, on the project's own PC.",
            "Ours scored 73.01 points out of 100, which is 4,410 right of 6,040. The plain model scored 67.12, which is 4,054 of 6,040.",
            "The difference is 5.89 points (our subtraction: 73.01 minus 67.12). One copy at one size is a first result, not proof."
          ],
          "chip": "tested once: 3M, one copy",
          "rows": [
            {
              "label": "ours",
              "value": 73.01
            },
            {
              "label": "plain model",
              "value": 67.12
            }
          ],
          "src": [
            "animations/source-g1-3m-s400.json (G-B2 pooled5 73.01 = 4410 of 6040; G-PT 67.12 = 4054 of 6040)",
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md sec. 12 (addendum G) lines 187-189 (3M s400 done; one rung of one seed: no readout yet)",
            "big-run/PLAN.md line 51 ('one clean 3M rung, 73.01 vs 67.12')"
          ],
          "notes": "5.89 = 73.01 - 67.12 (our subtraction; ch09 rounds it to 5.9). Design: calculator inside, 12 fixed rounds.",
          "labels": {
            "rung": "G1 re-run: 3M, copy 400",
            "of": "of 6,040 right",
            "diff": "points more (our subtraction: 73.01 minus 67.12)"
          },
          "counts": {
            "ours": 4410,
            "plain": 4054
          },
          "diff": 5.89
        },
        {
          "id": "s08",
          "duration": 44,
          "heading": "As of Oct 9: what G1 still has to show",
          "caption": [
            "G1 has more to run: copy 401 at 3M, and both copies at 10M. Results are not in yet.",
            "A copy's gain is its 10M score minus its 3M score. To go on, ours must gain at least 1.0 more than plain, on both copies.",
            "Stop if ours gains no more than plain on both. Between is unclear. The team's guess, written first: stop or unclear."
          ],
          "labels": {
            "axis": "ours gain minus plain gain",
            "stop": "Stop",
            "unclear": "Unclear",
            "go": "Go",
            "q": "?",
            "t0": "0",
            "t1": "1.0"
          },
          "status": {
            "a": "3M copy 400: done",
            "b": "3M copy 401: running",
            "c": "10M: queued"
          },
          "src": [
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md sec. 4 lines 63-72 (screen readout: go on if d(G-B2)-d(G-PT) >= +1.0 on both seeds and d(G-B2) > 0 on both; stop if <= 0 on both; otherwise unclear; prediction: the screen stops) and sec. 13 (addendum H) lines 203-214 (3M s401 keeps running; 10M jobs queued)",
            "big-run/PLAN.md line 204 (readout: GO at >= +1.0, STOP at <= 0) and line 206 (prediction: G-B2 gains +0 to +2, G-PT +3 to +4, likely UNCLEAR or STOP)"
          ],
          "notes": "No time is given for seed 401 or the 10M readout: both are estimates in the sources. The zone picture is an illustration of the written rule; no marker is a result.",
          "tag": "picture only: shows the written rule, not a result"
        },
        {
          "id": "s09",
          "duration": 41,
          "heading": "The finished design climbs its own ladder",
          "caption": [
            "G1 tests the older design. The finished design, called B3, must pass the same size test itself.",
            "It climbs 3M, then 10M, then 30M, each paired with a plain model trained at the same settings.",
            "The 100M run is the last rung. It starts only after the planned Oct 31 readout and the team's 90 percent bar."
          ],
          "rungs": [
            {
              "label": "3M",
              "chip": "built, never run"
            },
            {
              "label": "10M",
              "chip": "plan only"
            },
            {
              "label": "30M",
              "chip": "plan only"
            },
            {
              "label": "100M",
              "chip": "plan only"
            }
          ],
          "labels": {
            "pair": "plain model at the same settings",
            "ours": "finished design (B3)"
          },
          "tag": "picture only: steps drawn in order, not to size",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 7 lines 125-129 (B3 climbs its own ladder on the PC: 3M, then 10M with both groups as the G2 screen, then 30M, each paired with a plain model at the same caps; B3 group 1 built, never run)",
            "big-run/PLAN.md lines 38-44 (path: 10-31 ladder readout; 100M launches after it) and line 51 (the 90% bar)"
          ],
          "notes": "The 30M step of the OLDER design (B2) is on hold by the team's rule 'one big proven run, no more little tests' (8A-10M-RESULT line 15-16 and the audit note lines 13-17); B3's 30M rung is a plan. Dates are planned, never certain. The staircase is an illustration of order only: rung boxes are placed by position, not by size or date."
        },
        {
          "id": "s10",
          "duration": 42,
          "heading": "How sure is the team?",
          "caption": [
            "The team's rule, as the plan reads it: no weeks-long or money-costing step starts until it can truthfully say 90 percent sure.",
            "Its own honest odds today: about 1 in 3 that our design out-scales a plain model.",
            "For the long-term Minecraft goal, well under 1 in 10, because eyes, hands and a game loop are not built."
          ],
          "chip": "judgment, not measured",
          "tag": "picture only: boxes not to scale; under 1 in 10 is not zero",
          "labels": {
            "a": "our design out-scales a plain model",
            "b": "the Minecraft goal",
            "aOdds": "about 1 in 3",
            "bOdds": "well under 1 in 10"
          },
          "src": [
            "big-run/PLAN.md line 51 (the 90% bar; 'judgment, not measured': about 1 in 3 that our design out-scales a plain model, well under 1 in 10 for the Minecraft goal itself; eyes, hands and a game loop not built)"
          ],
          "notes": "Boxes are an illustration of the odds only (tagged on screen): 1 of 3 filled; none of 10 filled to show 'under 1' (not 'zero'; the source says well under 1 in 10). Not to scale."
        },
        {
          "id": "s11",
          "duration": 45,
          "heading": "Where it will run, and how long",
          "caption": [
            "Everything that trains runs on the project's own PC, with a 16 GB graphics card. Whether the 100M thinker fits is untested.",
            "The Mac laptops are too slow: a 3M test run measured 25.0 seconds per update, about 6.9 days for 24,000 updates.",
            "On the PC alone the 100M run is estimated at 3 to 5 weeks. Renting, about $80 with a $120 cap, is not used now."
          ],
          "cards": {
            "pc": {
              "name": "Project PC",
              "chip": "100M fit: untested",
              "big": "3 to 5",
              "unit": "weeks, estimate"
            },
            "mac": {
              "name": "Mac laptop",
              "chip": "measured",
              "big": 25,
              "unit": "seconds per update",
              "days": "6.9 days for 24,000 updates"
            },
            "rent": {
              "name": "Rented machine",
              "chip": "plan only",
              "big": "$80",
              "unit": "expected, cap $120"
            }
          },
          "src": [
            "big-run/PLAN.md line 17 (5070 Ti PC 16 GB: fits everything up to 30M; 100M fit untested, free fit check first) and line 18 (M1 Pro: GX-3M on MPS fp32 = 25.0 s per update, 100-update check; one 24,000-update run = about 6.9 days)",
            "big-run/PLAN.md lines 273-275 (hardware: PC alone; time on the PC about 23 to 32 days, so 3 to 5 weeks, suggested; if rented about 150 h, about $80 expected, range $55-$150, hard cap $120, one seed)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 lines 24-25 (plan on the PC and Macs only)"
          ],
          "notes": "6.9 days is as written in PLAN.md line 18 (25.0 s x 24,000 = 600,000 s, which is 6.9 days). The Mac test model was the experts test at 3M, not the finished design."
        },
        {
          "id": "s12",
          "duration": 35,
          "heading": "The race: the real proof (a plan)",
          "caption": [
            "After the model exists, the plan races it against the closest-size public model, SmolLM2-360M, on the team's own sealed question sets.",
            "The pass mark, written first: ahead by at least 3 points on those sets, and ahead on bAbI, with whole size counted.",
            "The race needs an English talker, a placeholder today. So no race has been run."
          ],
          "tag": "picture only: no race has been run",
          "labels": {
            "ours": "our model",
            "rival": "SmolLM2-360M",
            "start": "start",
            "finish": "?",
            "talker": "English talker: not built"
          },
          "src": [
            "big-run/PLAN.md line 77 (scorecard row 8: race ahead of SmolLM2-360M by >= +3 on our sealed sets and ahead on bAbI, whole size counted; untested; the race needs the open-English talker) and line 284 (R4: cannot pass until the English talker works)",
            "big-run/PLAN.md line 33 (race one rival first, SmolLM2-360M, on the 30M model; the 100M model raced again when it exists)"
          ],
          "notes": "PLAN.md line 33 races the 30M model first; the brief and R4 race the finished model. Both are plans; the caption keeps to 'after the model exists'."
        },
        {
          "id": "s13",
          "duration": 33,
          "heading": "Recap: what is shown, what is not",
          "caption": [
            "Shown: one clean rung. At 3M, one copy, ours scored 73.01 and the plain model 67.12.",
            "Not shown: the 10M answer, the 30M rung, the 100M run, or the finished design at any size.",
            "So there is no size claim yet. The test is whether our line climbs steeper than the plain line."
          ],
          "rungs": [
            {
              "label": "3M",
              "chip": "tested once",
              "sub": "73.01 vs 67.12"
            },
            {
              "label": "10M",
              "chip": "result not in"
            },
            {
              "label": "30M",
              "chip": "plan only"
            },
            {
              "label": "100M",
              "chip": "plan only"
            }
          ],
          "src": [
            "big-run/PLAN.md line 51 (one clean 3M rung, 73.01 vs 67.12, a 10M answer still to come)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 items 2, 6, 7 lines 109-129 (shown on one seed; the finished design must pass the size bar itself)"
          ],
          "notes": "Recap of the chapter. Nothing new is introduced."
        }
      ]
    },
    "ch14": {
      "kicker": "Part 14 of 14",
      "title": "What is proven, what is not, what comes next",
      "blurb": "An honest ledger as of Oct 9: which parts have a result, which are only built or planned, and what would prove the idea wrong.",
      "accent": "tested",
      "scenes": [
        {
          "id": "s01",
          "duration": 43,
          "heading": "Where we stand on Oct 9",
          "caption": [
            {
              "at": 0.02,
              "text": "The honest ledger, as of Oct 9: what has a result, and what does not."
            },
            {
              "at": 0.33,
              "text": "Reader, thinker and calculator have results at the smallest size, 3M: about three million learned numbers."
            },
            {
              "at": 0.66,
              "text": "The stop switch has never run. The English talker is not built."
            }
          ],
          "legend": [
            {
              "kind": "tested",
              "label": "result exists"
            },
            {
              "kind": "untested",
              "label": "built, never run"
            },
            {
              "kind": "placeholder",
              "label": "not built"
            }
          ],
          "parts": [
            {
              "chips": [
                {
                  "kind": "tested",
                  "label": "tested at 3M"
                }
              ],
              "text": "+2.67 points on 6 of 6 copies. One safety mark missed."
            },
            {
              "chips": [
                {
                  "kind": "tested",
                  "label": "tested at 3M"
                },
                {
                  "kind": "untested",
                  "label": "100M: untested"
                }
              ],
              "text": ""
            },
            {
              "chips": [
                {
                  "kind": "tested",
                  "label": "tested, 6 copies"
                },
                {
                  "kind": "untested",
                  "label": "any round: never run"
                }
              ],
              "text": "Plain code, outside the model."
            },
            {
              "chips": [
                {
                  "kind": "untested",
                  "label": "built, never run"
                }
              ],
              "text": ""
            },
            {
              "chips": [
                {
                  "kind": "placeholder",
                  "label": "stand-in only"
                }
              ],
              "text": ""
            }
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:29-38 (parts table: reader row 31, thinker 34, calculator 37, stop 36, talker 38)",
            "big-run/PLAN.md:80 (the learned stop has never run)"
          ],
          "notes": "Reader +2.67, 6 of 6 seeds, but the 6-seed confirm missed its zero-round leak mark (6.59 vs 4.62), FINISHED:31. Calculator column covers the call writer (tested in T1SDR, 6 seeds) and the any-round change (B3 group 1, built, never run, FINISHED:62-64). Talker: FINISHED:38 says 'today a small stand-in; the English talker is unbuilt'; the brief's 'stand-in works' is not a stated test result, so the chip only says 'stand-in only'."
        },
        {
          "id": "s02",
          "duration": 44,
          "heading": "Smaller pieces, tests and plans",
          "caption": [
            "Two small learned pieces sit between reader and thinker. Both count toward size.",
            "The rest are tests or plans. Sleep and domain mode wait until after the first big run."
          ],
          "rows": [
            {
              "name": "Plug and letter window",
              "text": "Learned. Without the window, a letter puzzle fell from 100% to 2.5-10%.",
              "chips": [
                {
                  "kind": "tested",
                  "label": "tested together"
                }
              ]
            },
            {
              "name": "Sleep",
              "text": "Reached 76.1. Not in run one.",
              "chips": [
                {
                  "kind": "placeholder",
                  "label": "research only"
                }
              ]
            },
            {
              "name": "Experts, word pieces",
              "text": "Experts join only if both stages pass.",
              "chips": [
                {
                  "kind": "placeholder",
                  "label": "plan only"
                }
              ]
            },
            {
              "name": "Group 2",
              "text": "Learned parts replace hand-written ones.",
              "chips": [
                {
                  "kind": "placeholder",
                  "label": "being built, no run"
                }
              ]
            },
            {
              "name": "Domain mode",
              "text": "Teaches itself a new field. First try failed.",
              "chips": [
                {
                  "kind": "untested",
                  "label": "v1 failed",
                  "color": "warn"
                }
              ]
            }
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:32-33 (adapter 196,864 / 393,728; window ~0.7M / ~2.6M; kept), 177-178 (cipher_map 100% to 2.5-10%), 130-131 (size counts borrowed and adapter and window)",
            "architecture/FINISHED-MODEL-2026-10-09.md:136-139 (experts), 155-157 (tokens), 85-86 (group 2 build started 12:15 PM ET), 160-162 (sleep and domain mode not in run-1)",
            "domain-mode/DESIGN-AND-MARKS-2026-10-09.md:171 (DM-S v1 proved wrong on seed 200)",
            "sources/pr-53-consolidation-sleep.md:2,8"
          ],
          "notes": "Group 2: the dossier said 'code built, no run'; FINISHED:85-86 and PLAN:41 say its BUILD STARTED Oct 9 (code only), so the chip says 'being built, no run'. Domain mode: the brief says 'untested' and FINISHED:160-162 says 'later, planned', but the DM design file records a v1 run that failed its mark on seed 200; the chip says v1 failed. Plug and window sizes (393,728 and about 2.6M at width 512) are left out to save words; the window figure cites RESULTS-EG2, which is not in the project snapshot."
        },
        {
          "id": "s03",
          "duration": 40,
          "heading": "Result one: the thinking does the work",
          "caption": [
            "Result one. On 6,040 questions kept aside, the model scored 73.01 out of 100 with its thinking on.",
            "With thinking switched off it scored 0.66. A plain model of the same size scored 67.12.",
            "So the thinking does the work, on one copy at the smallest size. Bigger sizes are untested."
          ],
          "bars": [
            {
              "label": "Thinking on",
              "value": 73.01,
              "color": "thinker"
            },
            {
              "label": "Thinking off",
              "value": 0.66,
              "color": "warn"
            },
            {
              "label": "Plain model",
              "value": 67.12,
              "color": "placeholder"
            }
          ],
          "labels": {
            "chip": "tested: one copy, 3M",
            "gap": "Gap over the plain model: +5.9",
            "caveat": "Older design: calculator inside, 12 fixed rounds. Second copy and 10M not in yet."
          },
          "src": [
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md:187-189 (G-B2 73.01 = 4,410/6,040, thinker-off 0.66; G-PT 67.12 = 4,054/6,040; one rung of one seed)",
            "architecture/FINISHED-MODEL-2026-10-09.md:109-110",
            "big-run/PLAN.md:223 (G1's 3M lead for G-B2 over G-PT was +5.9 on one seed); architecture/FINISHED-MODEL-2026-10-09.md:125-126 (G1 tests the calculator-inside, 12-round model)"
          ],
          "notes": "Same numbers as ch04 s14, ch06 s03, ch09 s04. 73.01 belongs to the older design with the calculator inside and 12 fixed rounds (the Gemma-fronted G-B2 arm, 3M, seed 400); the finished design has not produced a number yet. The +5.9 gap is quoted from PLAN:223, not computed here (73.01 - 67.12 = 5.89)."
        },
        {
          "id": "s04",
          "duration": 44,
          "heading": "Result two: the calculator can sit outside",
          "caption": [
            {
              "at": 0.02,
              "text": "Result two. The calculator is plain code outside the model: it gets a slip, sends a reply."
            },
            {
              "at": 0.26,
              "text": "Over 6 copies it scored 0.62 points above the inside design. The likely range includes zero."
            },
            {
              "at": 0.5,
              "text": "With the calculator switched off, program questions score 0.0, so the model really uses it."
            },
            {
              "at": 0.68,
              "text": "One check is incomplete: the swapped-reply test passed on 5 of 6 copies; one file was lost."
            }
          ],
          "labels": {
            "slip": "sub 12 5",
            "calc": "Calculator",
            "reply": "7",
            "tag": "made-up example",
            "chip": "tested: 6 copies",
            "ticks": [
              "-1",
              "0",
              "+1",
              "+2"
            ],
            "dot": "+0.62",
            "range": "likely range: -0.23 to +1.46",
            "off": "Calculator off: 0.0",
            "swap": "Swap check: 5 of 6 copies"
          },
          "values": {
            "lo": -0.23,
            "mid": 0.62,
            "hi": 1.46
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:106-108 (T1SDR matched B2 over 6 seeds: pooled-5 +0.62, CI -0.23 to +1.46; calculator off scores 0.0; mark 5 holds on 5 of 6 seeds, seed 205 unscored, checkpoint lost)",
            "architecture/FINISHED-MODEL-2026-10-09.md:42-57 (the sub 12 5 = 7 example)"
          ],
          "notes": "The slip 'sub 12 5' and reply '7' are the project's made-up example (Tom's apples), a picture, not a result. The number-line is drawn to scale for the three numbers only. Chain-5 99.6-99.8 (FINISHED:106) is left out to save words; ch05 s12 already shows it. Brief says 'matched'; the source says matched with +0.62 and a range that includes 0, so the caption says so."
        },
        {
          "id": "s05",
          "duration": 40,
          "heading": "Result three: a sleep that reached 76.1",
          "caption": [
            "Result three, research only. Six starting models slept, then took a kept-aside test and averaged 76.1 out of 100.",
            "Each night took 256 updates. The research loop's own sleep needs 558 to 610.",
            "The 71.3 line is that loop's stored number, not a side-by-side test. Each starting model ran once."
          ],
          "chip": "research only",
          "dots": [
            {
              "name": "A",
              "value": 78.3
            },
            {
              "name": "B",
              "value": 77.9
            },
            {
              "name": "C",
              "value": 71.3
            },
            {
              "name": "D",
              "value": 75.8
            },
            {
              "name": "E",
              "value": 76.4
            },
            {
              "name": "F",
              "value": 77
            }
          ],
          "ticks": [
            "70",
            "75",
            "80"
          ],
          "labels": {
            "mean": 76.1,
            "meanSub": "average of the six",
            "upd": "256 updates a night",
            "loop": "research loop: 558 to 610",
            "line": "dashed: 71.3, the research loop's stored number"
          },
          "src": [
            "sources/pr-53-consolidation-sleep.md:2,8,9 (76.1% = 78.3, 77.9, 71.3, 75.8, 76.4, 77.0; 256 updates against 558-610)",
            "sources/pr-53-consolidation-sleep.md:27 (71.3 is the research loop's stored number, not a paired baseline; one training run per parent)"
          ],
          "notes": "Dots A-F are the six parents s200-s205 in order. 'The test kept aside' is the C2 holdout, first try. 76.1 is the source's own mean (the six values average to 76.1). PR #53 is open, not merged. This is NOT the 30M forecast of 76.1 in scale.json (a different number)."
        },
        {
          "id": "s06",
          "duration": 42,
          "heading": "Sleep: what the result does not show",
          "caption": [
            {
              "at": 0.02,
              "text": "Transfer is not shown. Plain practice alone raised old skills by 2.11; the sleep added only 0.52."
            },
            {
              "at": 0.36,
              "text": "Harm is disputed. The write-up says none against the model just before sleep, but the check against the original model fails on all six."
            },
            {
              "at": 0.66,
              "text": "An earlier, different sleep did hurt old skills, then a lower learning rate fixed it. The stop rule never ended a night early."
            }
          ],
          "labels": {
            "axis": "Old-skill gain (points)",
            "sleep": "Sleep",
            "practice": "Practice only",
            "transfer": "Transfer: not shown",
            "diff": "sleep minus practice-only",
            "harm": "Harm: sources disagree",
            "earlier": "an earlier, different sleep: one old skill"
          },
          "values": {
            "sleep": 0.52,
            "practice": 2.11,
            "diff": -1.58,
            "from": 85,
            "to": 30
          },
          "src": [
            "sources/pr-53-consolidation-sleep.md:7,12,16,22,24 (sleep minus replay-only -1.58 [-1.79, -1.37]; replay-only control +2.11; harm vs original model fails on all six parents; stop rule never ended a night early)",
            "progress-board/data.json key blockers[0] (earlier fast-sleep: seq_next 85 -> 30; claim of no harm withdrawn; lower learning rate removes the loss on both parents)",
            "big-run/PLAN.md:80 (SC proved wrong on harm 12:14 PM ET, SCL passed on two parents 1:18 PM ET)"
          ],
          "notes": "Conflict on harm: PR #53 marks 'no harm' as pass (against the pre-sleep model) but says the check against raw B2 still fails on all six parents; the progress board withdraws the earlier 'no harm' claim for the 71.3 fast-sleep win. The 85 to 30 drop belongs to that earlier, different sleep, not to the 76.1 recipe, and the caption says so. The +0.52 and +2.11 are in_dist changes in points; -1.58 is quoted from the PR, not subtracted here."
        },
        {
          "id": "s07",
          "duration": 43,
          "heading": "What has never been done",
          "caption": [
            {
              "at": 0.02,
              "text": "All parts together has never run: the Gemma reader, outside calculator, any-round calls and learned stop."
            },
            {
              "at": 0.22,
              "text": "The first run is planned at 3M, after the size test finishes."
            },
            {
              "at": 0.4,
              "text": "Bigger sizes are unproven: an earlier 10M test gave ours +0.49 and plain +3.77, but it had a setting bug."
            },
            {
              "at": 0.7,
              "text": "The talker, the race and games come later."
            }
          ],
          "pieces": [
            "Gemma reader",
            "Outside calculator",
            "Calls in any round",
            "Learned stop"
          ],
          "frame": "never run together",
          "tag": "picture only",
          "cards": [
            {
              "text": "Bigger sizes, fixed settings",
              "chip": {
                "kind": "untested",
                "label": "not done",
                "color": "warn"
              }
            },
            {
              "text": "English talker",
              "chip": {
                "kind": "placeholder",
                "label": "not built"
              }
            },
            {
              "text": "Race vs a 360M-number model",
              "chip": {
                "kind": "placeholder",
                "label": "planned"
              }
            },
            {
              "text": "Anything with a game",
              "chip": {
                "kind": "placeholder",
                "label": "paused"
              }
            }
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:123-124 (outside calculator and Gemma never run together; first run B3 group 1 at 3M seed 400 after G1)",
            "big-run/PLAN.md:114-116 (B2 +0.49 from 3M to 10M, plain step model +3.77; B2 ran with 9 letter slots instead of 36)",
            "architecture/FINISHED-MODEL-2026-10-09.md:38 (English talker unbuilt), 167 (games paused); big-run/PLAN.md:77,33 (SmolLM2-360M race, planned)"
          ],
          "notes": "The pieces sliding together is a picture of the plan, not a measurement. FINISHED:128-129 quotes a different pair of earlier 10M-ladder gains (+0.03 and +0.28 vs plain +3.08 and +4.25); both say the register bug means they do not count either way. The caption uses PLAN:114-116, the 'only result on size'. The progress board also says 'mark 1 fails'."
        },
        {
          "id": "s08",
          "duration": 44,
          "heading": "Open risks, said plainly",
          "caption": [
            "A leak is a right answer with zero thinking rounds. The average was 6.59 against a limit of 4.62.",
            "Deeper thinking can cost points, and the stop may fire too early.",
            "Web text stays locked until the sealed test questions are fingerprint-checked."
          ],
          "bars": [
            {
              "label": "Average",
              "value": 6.59,
              "color": "warn"
            },
            {
              "label": "Limit",
              "value": 4.62,
              "color": "placeholder"
            }
          ],
          "labels": {
            "axis": "Zero-round leak, points out of 100",
            "one": "A separate run on familiar questions (seed 200): Gemma reader 18.09, plain model 1.40.",
            "chip": "limit missed"
          },
          "cards": [
            {
              "title": "Depth costs points",
              "text": "On one test, 16 rounds cost 1.2 to 1.9."
            },
            {
              "title": "The stop may fire early",
              "text": "Our guess, never shown."
            },
            {
              "title": "Web text is locked",
              "text": "Sealed-test fingerprints must be checked first."
            }
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:31 (mean 6.59 against limit 4.62, plain B2 3.62 + 1.0), 111-112 (separate seed-200 in-distribution run, addendum 14: EGE 18.09 against 1.40 for plain B2 / B2V; not one of the six confirm copies)",
            "architecture/FINISHED-MODEL-2026-10-09.md:149-150 (16 rounds cost 1.2-1.9 points on one B2 probe), 66-69 (stop may fire early, suggested), 147-148 (web pool gate)"
          ],
          "notes": "Leak mark A (reader, missed, not cleared) is a different test from leak mark B (calculator, limit 5, cleared by the project owner Oct 9; ch05 s14). This scene is about A only. The bars are the six-copy confirm (FINISHED:31, addendum 15); the 18.09 / 1.40 line is a separate seed-200 in-distribution run against plain B2 (B2V), PASS-MARKS addendum 14 (FINISHED:111-112), so it is labelled as its own run and not as one of the six. 'Out of 100' follows the leak being a share of questions."
        },
        {
          "id": "s09",
          "duration": 37,
          "heading": "Hand-written pieces still on the path",
          "caption": [
            "Ordinary code a person wrote still sits on the path. Here are the counts, part by part.",
            "The pass mark is 0 for each. Only the stop is at 0 today.",
            "Group 2 is the plan to replace them with learned pieces. It is being built and has not run."
          ],
          "chip": "hand-written pieces",
          "columns": [
            {
              "name": "Stop",
              "count": 0
            },
            {
              "name": "Arithmetic",
              "count": 2
            },
            {
              "name": "Reading",
              "count": 6
            },
            {
              "name": "Writing",
              "count": 4
            },
            {
              "name": "New kinds",
              "count": 6
            }
          ],
          "labels": {
            "learned": "learned",
            "nosum": "Not added: one piece is counted twice.",
            "plan": "Plan: group 2 swaps them for learned pieces.",
            "planChip": "being built"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:84-86 (stop 0, arithmetic 2, reading 6, writing 4, new kinds 6; pass mark 0 each)",
            "no-hardcoding/INVENTORY-B3-2026-10-09.md:11-17 (summary; X1 is counted under both arithmetic and writing)"
          ],
          "notes": "No total is shown: X1 (operand span copy) is listed under part 2 and part 4, so adding gives a double count. 'New kinds' counts apply to training only (part 8b)."
        },
        {
          "id": "s10",
          "duration": 39,
          "heading": "The next gates, in order",
          "caption": [
            {
              "at": 0.02,
              "text": "In order: the size test finishes, then the experts test, the 100M fit check and all parts together at 3M."
            },
            {
              "at": 0.34,
              "text": "Then 10M and 30M, and a team readout on Oct 31, which is planned."
            },
            {
              "at": 0.66,
              "text": "One big run waits for clear results and for the plan to be 90% sure. Rented compute only if the project owner decides."
            }
          ],
          "chip": "plan only, no dates promised",
          "steps": [
            "G1 size test",
            "Experts test",
            "100M fit check",
            "All parts, 3M",
            "10M, then 30M",
            "Readout, Oct 31 (planned)",
            "One big run",
            "Rented compute: owner's call"
          ],
          "src": [
            "big-run/PLAN.md:38-39 (G1 then the post-G1 chain: GX stage 1, fit check, g2c3, B3 group 1 at 3M seed 400), 42-47 (10M, 30M, Oct 31 readout), 51 (the 90% bar)",
            "architecture/FINISHED-MODEL-2026-10-09.md:24-25 (no rentals; the owner: demonstrable results first)",
            "big-run/PLAN.md:62 (the SCORECARD section; the brief's 'PLAN sec. 5' is really the G1 gate at line 195)"
          ],
          "notes": "G1: as of Oct 9 its 3M seed 401 is finishing and the 10M arms follow (PLAN:38). The seed-401 files in the snapshot belong to earlier 8a runs, not G1. The 90% bar is the plan author's reading of a relayed rule (PLAN:51). Every date is 'planned'; the Nov to Dec range for the 100M run (PLAN:44-47) is left out as an estimate."
        },
        {
          "id": "s11",
          "duration": 45,
          "heading": "What would prove the idea wrong",
          "caption": [
            {
              "at": 0.02,
              "text": "Rule one: gaining no more from size than the plain model, on both copies, means STOP."
            },
            {
              "at": 0.33,
              "text": "Rule two: all parts at 3M must beat the plain partner by 3.0; under 1.0, find the broken part."
            },
            {
              "at": 0.66,
              "text": "Rule three: domain mode needed +30; its first try scored -0.48: proved wrong."
            }
          ],
          "gauges": [
            {
              "label": "G1: size gain",
              "zones": [
                "STOP",
                "unclear",
                "GO"
              ],
              "bounds": [
                "0",
                "+1.0"
              ],
              "chip": {
                "kind": "placeholder",
                "label": "not read yet"
              }
            },
            {
              "label": "All parts, 3M",
              "zones": [
                "find the cause",
                "between",
                "pass"
              ],
              "bounds": [
                "+1.0",
                "+3.0"
              ],
              "chip": {
                "kind": "placeholder",
                "label": "not run"
              }
            },
            {
              "label": "Domain mode",
              "zones": [
                "proved wrong",
                "between",
                "pass"
              ],
              "bounds": [
                "+10",
                "+30"
              ],
              "marker": "v1: -0.48",
              "chip": {
                "kind": "untested",
                "label": "v1 failed",
                "color": "warn"
              }
            }
          ],
          "tag": "not to scale",
          "past": "Already proved wrong: teacher data as a booster (+0.78, needed +15).",
          "src": [
            "big-run/PLAN.md:204 (G1 readout: GO if difference >= +1.0 on both seeds, STOP if <= 0 on both), 39 (STOP: replan, no B3 on this thinker)",
            "big-run/PLAN.md:223 (B3-1: pass at least +3.0 over g2c3; below +1.0 no seed 401, bisect)",
            "domain-mode/DESIGN-AND-MARKS-2026-10-09.md:88 (DM1 pass +30, proved wrong < +10 on seed 200), 171 (v1: DM1 -0.48, proved wrong)",
            "big-run/PLAN.md:136 (teacher data as a booster: PROVED WRONG, new kinds +0.78, needed +15)"
          ],
          "notes": "B3-1's failure branch is 'find which new part broke it' (bisect), not 'the idea is dead'; the zone says 'find the cause'. The gauges are drawn evenly and not to scale. The DM1 marker (-0.48) is the only measured point; the other two gates have no result yet."
        },
        {
          "id": "s12",
          "duration": 42,
          "heading": "What to remember",
          "caption": [
            "The thinking does the work, shown on one copy at the smallest size.",
            "The calculator can sit outside. Sleep is a promising research result. Most of the rest is built or planned, not proven.",
            "The plan's own judgment: nothing is ready to buy yet. No recipe has shown both halves of demonstrably works."
          ],
          "parts": [
            "Reads the question.",
            "Thinks in rounds.",
            "Does exact sums.",
            "Rings when done.",
            "Writes the answer."
          ],
          "chip": "the plan's own judgment",
          "notes_on": [
            "Nothing is ready to buy yet.",
            "Plan's count on Oct 9: 0 of 9 goals fully green. Its guess for Oct 31: 5 or 6."
          ],
          "src": [
            "kit/GLOSSARY.md (the five parts and the one analogy)",
            "big-run/PLAN.md:112-113 (bottom line 1: nothing is ready to buy), 80 ('Today: 0 of 9 fully green'), 87 (realistic read at Oct 31: 5 or 6)"
          ],
          "notes": "Both numbers are the plan's own judgment, labelled as such on screen. No ch00 chapter file exists in the worktree; the five-part sentences follow the glossary."
        }
      ]
    }
  }
};
