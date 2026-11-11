window.CONTENT = {
  "global": {
    "cardSeconds": 5,
    "endCard": {
      "duration": 13,
      "title": "That is the whole machine",
      "blurb": "Reader, thinker, stop switch, talker, plus an outside calculator the model uses: what each part does, how it learns, and what is still not proven."
    },
    "narrated": true
  },
  "order": [
    "ch00",
    "ch01",
    "ch03",
    "ch04",
    "ch05",
    "ch06",
    "ch07",
    "ch08",
    "ch09",
    "ch11",
    "ch12",
    "ch14"
  ],
  "chapters": {
    "ch00": {
      "kicker": "Start here",
      "title": "What you are about to see",
      "blurb": "This project is building a language model that thinks in careful steps. This opening section covers what it is, the colours and tags, and the words you need. Parts 1 to 10 and a wrap-up follow.",
      "accent": "thinker",
      "scenes": [
        {
          "id": "s01",
          "duration": 22.5,
          "heading": "A research project, not a product",
          "caption": [
            {
              "at": 0.0267,
              "text": "This is a research project. It is building a language model: a program that reads text and writes an answer."
            },
            {
              "at": 0.4019,
              "text": "Two of its goals: skills and careful thinking first, then learning from only a few examples."
            },
            {
              "at": 0.7137,
              "text": "It is not an app. GitHub lists 0 releases for it, and nothing here is finished."
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
            "note": "The first three boxes are the status tags you will see all video. The last is the finish line: nothing is there yet."
          },
          "src": [
            "creative-roadmap/gpt6pro-creative-roadmap-2026-10-06.md:30-31 (north star; other goals: skills and critical thinking first, learning from few examples)",
            "big-run/PLAN.md:72 (scorecard row 1: think first, learn from a few examples) and :79 (row 8: the goal)",
            "animations/storyboards-2026-10-09.md:20 (research model, not an app) and :26 (GitHub shows 0 releases and 0 tags)",
            "architecture/FINISHED-MODEL-2026-10-09.md:4 (the model we plan to ship; not finished)",
            "kit/GLOSSARY.md (status chips: grey plan only/placeholder, amber built never tested, green tested)"
          ],
          "notes": "The four boxes are a picture of the status ladder (glossary). 0 releases: storyboards sec. 2 (Oct 9) and a live read of the GitHub REST API on Oct 10 (repos/BenjaminHannan/learner/releases: 0; tags: 0; local git also has 0 tags). Only two of the project's goals are named; the far goal (an agent that beats Minecraft like a person, roadmap line 30) and 'beat 1-2B models at the same total size' are in the roadmap but not in this cut.",
          "atMap": [
            [
              0.014,
              0.0267
            ],
            [
              0.377,
              0.4019
            ],
            [
              0.6804,
              0.7137
            ]
          ]
        },
        {
          "id": "s02",
          "duration": 28,
          "heading": "Two goals it is trying to reach",
          "caption": [
            {
              "at": 0.0214,
              "text": "First goal: skills and careful thinking."
            },
            {
              "at": 0.1656,
              "text": "At the smallest size, 3 million learned numbers, an earlier design scored higher than an ordinary same-size model in all six separate training runs."
            },
            {
              "at": 0.6602,
              "text": "Second goal: learning from only a few examples. Only partly shown so far: brand-new kinds of rule are mostly missed."
            }
          ],
          "labels": {
            "steps": [
              {
                "t": "skills and careful thinking",
                "cl": "skills shown at 3M, earlier design"
              },
              {
                "t": "learning from few examples",
                "cl": "partly shown"
              }
            ]
          },
          "src": [
            "creative-roadmap/gpt6pro-creative-roadmap-2026-10-06.md:30-31 (other goals: skills and critical thinking first, learning from few examples)",
            "big-run/PLAN.md:72 (scorecard row 1 (a): shown at 3M, B2 +20.3 over a plain transformer, 6 of 6 seeds; (b) partly: held-out families 0-4%, new kinds about 11%)",
            "big-run/PLAN.md:131 (B2 at 3M, calculator inside, letter reader: 6 seeds, pooled-5 +20.3 over a same-size plain transformer, ahead on 6 of 6)",
            "whole-model-roadmap/whole-model-roadmap-2026-10-06.md:367 (B2 confirm, 6 of 6 seeds, PASS-1, +20.3 vs plain_tf, CI 19.4 to 21.3)",
            "creative-roadmap/gpt6pro-creative-roadmap-2026-10-06.md:66 (every model scores 0-4% on held-out task families)",
            "kit/GLOSSARY.md:50 (3M = about three million learned numbers, the smallest size)"
          ],
          "notes": "Goal 1's evidence (6 of 6, +20.3 on pooled-5 skills questions) belongs to the older B2 design at 3M (no Gemma reader, calculator inside); the video says 'earlier design'. What is shown for goal 1 is the score ahead of a same-size plain model, so the chip says 'skills shown'. Goal 2: held-out families 0-4% and new kinds about 11% are older-model scores; sleep lifted the first try to 71.3% on 6 parents with the project's own scripts, never on the finished design, so 'partly shown'. The 'partly shown' chip is green with a 'partly' label (a result exists, but only for older models; it was amber in the checked version, which read as 'built, never tested'). Two of the project's goals only; the far goal (an agent that beats Minecraft like a person, roadmap line 30) and 'beat 1-2B models' are not in this cut.",
          "atMap": [
            [
              0.0176,
              0.0214
            ],
            [
              0.1324,
              0.1656
            ],
            [
              0.62,
              0.6602
            ]
          ]
        },
        {
          "id": "s06",
          "duration": 38.5,
          "heading": "The whole machine in one picture",
          "caption": [
            {
              "at": 0.0156,
              "text": "The reader gives each letter a meaning from the whole question. Its main part is borrowed from others and frozen: our practice never changes it."
            },
            {
              "at": 0.3371,
              "text": "The thinker thinks in rounds, which are laps of looking and thinking. Our practice sets its settings from scratch."
            },
            {
              "at": 0.5577,
              "text": "The stop switch says done. It is built, but never run."
            },
            {
              "at": 0.6935,
              "text": "The talker writes one line a turn. Today it is a small stand-in."
            },
            {
              "at": 0.8479,
              "text": "Outside: a calculator. The talker's line calls it; the reader reads the reply."
            }
          ],
          "labels": {
            "jobs": [
              "reads the question",
              "thinks in rounds",
              "says when done",
              "writes the answer or a call",
              "outside tool: does exact sums"
            ],
            "chip": "stand-in today",
            "chipStop": "built, never tested"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:15-20 and table lines 31-38 (sec. 1-2)"
          ],
          "notes": "Part boxes come from S.modelMap (sub-labels fixed by the kit). Reader: the frozen Gemma part is borrowed (271,002,624 numbers); the small adapter and letter window on top are ours (table lines 32-33), hence 'main part'. 'Borrowed from others and frozen' is the glossary's definition (a part somebody else trained, not changed by our practice). Stop switch: built, never run (line 36). Talker: 'today a small stand-in; the English talker is unbuilt' (line 38). The amber chip under the stop switch was added in the checking pass. The chip reads 'built, never tested' (the legend wording); the source says never run (line 36), the same fact. Calculator is outside the model (Ben, Oct 2026): fifth caption and job text are for the outside tool; the model has four parts.",
          "atMap": [
            [
              0.0133,
              0.0156
            ],
            [
              0.2422,
              0.3371
            ],
            [
              0.4222,
              0.5577
            ],
            [
              0.5778,
              0.6935
            ],
            [
              0.7089,
              0.8479
            ]
          ]
        },
        {
          "id": "s08",
          "duration": 37,
          "heading": "One picture for the whole video",
          "caption": [
            {
              "at": 0.0162,
              "text": "One picture runs through the whole video: a student doing a word problem."
            },
            {
              "at": 0.1768,
              "text": "A translator reads the question. A team of note-takers thinks it over, round after round."
            },
            {
              "at": 0.362,
              "text": "The one who writes the final answer may write a request slip. A pocket calculator, outside the team, hands back a slip, and the translator reads it."
            },
            {
              "at": 0.6578,
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
                "t": "Stop switch",
                "p": "a little bell"
              },
              {
                "t": "Talker",
                "p": "writes the answer or the slip"
              },
              {
                "t": "Calculator",
                "p": "outside: a pocket calculator"
              }
            ]
          },
          "src": [
            "kit/GLOSSARY.md (the one analogy table)",
            "architecture/FINISHED-MODEL-2026-10-09.md:31-38 (part names)"
          ],
          "notes": "The student analogy is the project's shared teaching picture (glossary), not a measurement.",
          "illustration": "The cards are an analogy, not a diagram of the code.",
          "atMap": [
            [
              0.0143,
              0.0162
            ],
            [
              0.2143,
              0.1768
            ],
            [
              0.4381,
              0.362
            ],
            [
              0.6857,
              0.6578
            ]
          ]
        },
        {
          "id": "s09",
          "duration": 30.5,
          "heading": "How sure are we? Three tags",
          "caption": [
            {
              "at": 0.0197,
              "text": "Green: tested. A result file exists. Example: with the calculator outside, scores matched the earlier design in six runs, at the smallest size."
            },
            {
              "at": 0.4842,
              "text": "Amber: built, but never tested. The code exists, but no real training run was ever done. Example: the stop switch."
            },
            {
              "at": 0.761,
              "text": "Grey: placeholder. It does not exist yet. Example: the English talker."
            }
          ],
          "labels": {
            "rows": [
              {
                "name": "the outside calculator",
                "sub": "matched the earlier design, 6 runs"
              },
              {
                "name": "the stop switch",
                "sub": "code exists, no real run"
              },
              {
                "name": "the English talker",
                "sub": "about 25 million planned, not built"
              }
            ]
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:106 (sec. 5 item 1: T1SDR matched B2 over 6 seeds, pooled-5 +0.62, CI -0.23 to +1.46; calculator off scores 0.0)",
            "architecture/MARKS-D0-T1-2026-10-07.md:200 and :204 (Record 13: pooled-5 T1SDR minus B2 +0.62, 6 of 6 seeds within 1.0; 'at parity with B2 over six seeds')",
            "architecture/FINISHED-MODEL-2026-10-09.md:36 (stop switch: built, never run)",
            "architecture/FINISHED-MODEL-2026-10-09.md:38 (English talker unbuilt) and :21 (talker about 25M planned)",
            "kit/GLOSSARY.md:39-46 (status chips)"
          ],
          "notes": "Amber is the kit's 'untested' chip (built, never tested). The green example is the calculator moved outside the model (T1SDR) matching B2 (the earlier design, calculator inside) at the smallest size (3.24M, MARKS-D0-T1 line 76 context) over six copies; 'matched' is the source's word. Disclosed in the source and not on screen: Ben cleared the leak mark, and the swap mark is unscored on seed 205. Copies are named 'runs' here because the word 'copy' is defined in the Score and copy scene.",
          "atMap": [
            [
              0.0162,
              0.0197
            ],
            [
              0.29,
              0.4842
            ],
            [
              0.55,
              0.761
            ]
          ]
        },
        {
          "id": "s11",
          "duration": 21.5,
          "heading": "Two words: vector and round",
          "caption": [
            {
              "at": 0.0279,
              "text": "A vector is a list of numbers, like a note card. The reader turns each letter into one. “Picture only” means a drawing, not a measurement."
            },
            {
              "at": 0.5967,
              "text": "A round is one lap of looking at the whole question, passing notes, and thinking. The thinker does several laps."
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
          "illustration": "The shaded strip and the 1-2-3 lap counter are illustrations.",
          "atMap": [
            [
              0.0214,
              0.0279
            ],
            [
              0.45,
              0.5967
            ]
          ]
        },
        {
          "id": "s12",
          "duration": 26.5,
          "heading": "Two more words: call and reply",
          "caption": [
            {
              "at": 0.0226,
              "text": "A call is the talker's line: a text request to the outside calculator. Here, sub 12 5 means: take 5 away from 12."
            },
            {
              "at": 0.3817,
              "text": "The reply is the calculator's answer, also text: 7. The whole reader reads it. Together they read sub 12 5 = 7."
            },
            {
              "at": 0.7272,
              "text": "The talker writes calls on its own. A line that is not a call is the final answer."
            }
          ],
          "labels": {
            "callL": "call: talker's line",
            "calcL": "outside calculator",
            "replyL": "reply",
            "call": "sub 12 5",
            "reply": "7",
            "line": "sub 12 5 = 7",
            "ex": "made-up example"
          },
          "src": [
            "kit/GLOSSARY.md:26 (call, reply)",
            "architecture/FINISHED-MODEL-2026-10-09.md:35 and 37 (tested version: a call writer picks 1 of 8 operations or no call; calculator replies as text. New design, not tested: the talker writes the call at the end of a turn)"
          ],
          "notes": "The numbers 12, 5 and 7 are the glossary's example, not a result.",
          "atMap": [
            [
              0.0187,
              0.0226
            ],
            [
              0.43,
              0.3817
            ],
            [
              0.6883,
              0.7272
            ]
          ]
        },
        {
          "id": "s13",
          "duration": 20,
          "heading": "Two more words: practice and kept aside",
          "caption": [
            {
              "at": 0.03,
              "text": "Practice: the model tries a question, is told the right answer, and every setting is nudged a tiny bit. One nudge is one update."
            },
            {
              "at": 0.5422,
              "text": "Questions kept aside are never used in practice. They are saved for the exam, so the score is fair: the model has never seen them."
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
          "illustration": "The cards and the update counter are a picture, not real counts.",
          "atMap": [
            [
              0.02,
              0.03
            ],
            [
              0.4667,
              0.5422
            ]
          ]
        },
        {
          "id": "s14",
          "duration": 31,
          "heading": "Score and copy",
          "caption": [
            {
              "at": 0.0194,
              "text": "A score is points out of 100: the share of questions answered right. Here, 73.01 points on 6,040 questions kept aside."
            },
            {
              "at": 0.4186,
              "text": "A copy is one separate run of the model from its own random start. Six copies are six chances to see the same result."
            },
            {
              "at": 0.737,
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
            "careful": "one copy, 3 million learned numbers, earlier design"
          },
          "src": [
            "animations/source-g1-3m-s400.json (raw G1 result: G-B2 full.pooled5 73.01 = 4,410 of 6,040; G-PT full.pooled5 67.12 = 4,054 of 6,040; seed 400, 3M)",
            "architecture/FINISHED-MODEL-2026-10-09.md:109-110 (sec. 5 item 2: G1 first finished run, 3M, seed 400: 73.01 thinker on)",
            "big-run/PLAN.md:99 and :134 (3M seed 400 done: G-B2 73.01, G-PT 67.12) and :225 (pooled-5 on the 6,040 dev rows; G1's 3M lead for G-B2 over G-PT was +5.9 on one seed)",
            "kit/GLOSSARY.md:62 and :78 (pooled-5 = the 6,040 questions kept aside, five kinds pooled into one score out of 100); kit/GLOSSARY.md:30-32 (score, seed/copy)",
            "architecture/FINISHED-MODEL-2026-10-09.md:125-126 (item 7: G1 tests today's earlier design: calculator inside, 12 fixed rounds)"
          ],
          "notes": "73.01 is seed 400 at 3M (G1 first finished run; 4,410 of 6,040 = 73.01). Other chapters call it the older 12-round design; here 'earlier design'. A second 3M copy (seed 401, 73.7 vs 68.0, PLAN.md line 9, not recomputed by the project) finished after the chapter was written; the video shows seed 400 only and says one copy about that number, which stays true.",
          "illustration": "The six copy boxes are a picture of the idea; they are not six real results.",
          "atMap": [
            [
              0.0162,
              0.0194
            ],
            [
              0.2757,
              0.4186
            ],
            [
              0.565,
              0.737
            ]
          ]
        },
        {
          "id": "s15",
          "duration": 34,
          "heading": "The plain model: our yardstick",
          "caption": [
            {
              "at": 0.0176,
              "text": "A plain model is an ordinary model of the same size, trained on the same practice, with the same borrowed reader. It is our yardstick."
            },
            {
              "at": 0.324,
              "text": "On the same 6,040 questions kept aside, the plain model scored 67.12 points out of 100, and ours scored 73.01."
            },
            {
              "at": 0.7024,
              "text": "Careful: these two scores come from one copy, at the smallest size, on an earlier design. We do not claim it holds at bigger sizes."
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
            "care": "one copy, 3 million learned numbers, earlier design"
          },
          "src": [
            "animations/source-g1-3m-s400.json (G-B2 73.01 and G-PT 67.12, both of 6,040; learned parameters 3,544,913 and 3,495,936)",
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md:33-35 (G-PT = the plain step model with the same Gemma front, sized within 2% of G-B2) and :92 (1.4% apart at 3M)",
            "big-run/PLAN.md:53 (one clean 3M rung, 73.01 vs 67.12, a 10M answer still to come) and :72 (row 1: G-B2 73.01 vs G-PT 67.12 on one seed)",
            "architecture/FINISHED-MODEL-2026-10-09.md:109-110",
            "kit/GLOSSARY.md:32 (plain model), :62 and :78 (pooled-5 = the 6,040 questions kept aside)",
            "big-run/PLAN.md:225 (pooled-5 on the 6,040 dev rows; G1's 3M lead for G-B2 over G-PT was +5.9 on one seed)"
          ],
          "notes": "No difference is computed in the video (73.01 - 67.12 = 5.89, which PLAN.md:225 rounds to +5.9). The 6,040 is the pooled-5 held-out set. Both arms use the same borrowed Gemma reader (spec lines 33-35), so the gap is not the reader. Seed 401 (73.7 vs 68.0, PLAN.md:9, not recomputed by the project) is not shown.",
          "atMap": [
            [
              0.0154,
              0.0176
            ],
            [
              0.3333,
              0.324
            ],
            [
              0.6538,
              0.7024
            ]
          ]
        },
        {
          "id": "s19",
          "duration": 29.5,
          "heading": "Our promise to you",
          "caption": [
            {
              "at": 0.0203,
              "text": "Every real number in this video comes from a project file. Here is one example: the plain model's score, traced to its file."
            },
            {
              "at": 0.3429,
              "text": "Pictures that only illustrate carry a tag, like picture only or made-up example. They are never real measurements."
            },
            {
              "at": 0.633,
              "text": "What is not proven stays amber or grey. Nothing here is released, and no future date is promised to you."
            }
          ],
          "labels": {
            "num": 67.12,
            "tag": "big-run/PLAN.md",
            "chipA": "picture only",
            "chipB": "made-up example",
            "chipC": "built, never tested",
            "chipD": "plan only",
            "rel": "released: 0",
            "numL": "the plain model's score, points out of 100",
            "tagSub": "scorecard row 1, “Status today”",
            "tagsLead": "Tags on pictures that only illustrate:"
          },
          "src": [
            "big-run/PLAN.md:72 (scorecard row 1: G-PT 67.12, the plain model's score) and animations/source-g1-3m-s400.json (G-PT pooled5 67.12 of 6,040)",
            "animations/storyboards-2026-10-09.md:26 (GitHub shows 0 releases)",
            "brief ch00 point 7 (the honesty promise)"
          ],
          "notes": "The file tag shows how a number is traced to its source. The tag names the scorecard row and its 'Status today' column (the table in the SCORECARD section of PLAN.md, line 72 at the time of checking; that column holds the 67.12), not a line number, because PLAN.md is edited often. The tags are shown as dashed pills under a lead-in so they cannot be read as describing the real score above. The checking pass compared every number in this chapter with its source; the video does not put a file tag beside every number (the first draft promised that), so the caption now promises only that every real number comes from a project file and shows one traced example.",
          "atMap": [
            [
              0.0146,
              0.0203
            ],
            [
              0.3415,
              0.3429
            ],
            [
              0.6537,
              0.633
            ]
          ]
        }
      ]
    },
    "ch01": {
      "kicker": "Part 1 of 10",
      "title": "One question, start to finish",
      "blurb": "We follow one made-up question through every part of the model, step by step. Plain words first. Real numbers only where a source gives them.",
      "accent": "thinker",
      "scenes": [
        {
          "id": "s01",
          "duration": 21,
          "heading": "Where we are: four parts and a tool",
          "caption": [
            {
              "at": 0.0286,
              "text": "This chapter follows one question through the whole model."
            },
            {
              "at": 0.4057,
              "text": "The model has four parts: reader, thinker, stop switch and talker. It uses an outside calculator."
            },
            {
              "at": 0.7397,
              "text": "Some parts have a test result. All together, never tested."
            }
          ],
          "chip": "never tested all together",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 (lines 15-20)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 6 (lines 123-124)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 table (lines 31, 34, 36, 37, 38) for the per-part chips under the five boxes"
          ],
          "notes": "Map drawn by S.modelMap with the four model parts and the outside calculator; the map labels are drawn by the kit, not in this file. Third caption reworded by the checker: the old wording ('None of these parts has been tested all together') read as if no part had a result. Source: FINISHED-MODEL sec. 5 item 6 (calculator and Gemma never run together) and sec. 2 (stop switch never run, English talker unbuilt). Fix pass: each box now carries a status chip (Reader, Thinker, Calculator: \"tested at 3M\"; Stop switch: built, never tested; Talker: \"stand-in today\", grey) so the third caption can be checked on the picture. Reader and calculator use the same statuses as scene s15 (FM lines 31 and 37). The Thinker chip is new: the loop with the same weights every round was trained and tested at 3M in all B2/T1SDR runs (FM line 34 says only its 100M shape is untested; FM line 109-110 scores it at 3M); the checker should confirm. Talker: FM line 38 \"today a small stand-in\".",
          "part_chips": [
            "tested at 3M",
            "tested at 3M",
            "tested at 3M",
            "built, never tested",
            "stand-in today"
          ],
          "atMap": [
            [
              0.0231,
              0.0286
            ],
            [
              0.3397,
              0.4057
            ],
            [
              0.6564,
              0.7397
            ]
          ]
        },
        {
          "id": "s02",
          "duration": 18,
          "heading": "The question we will follow",
          "caption": [
            {
              "at": 0.0333,
              "text": "Here is the question. We made it up as an example."
            },
            {
              "at": 0.3239,
              "text": "The model works on letters, so every letter gets its own box."
            },
            {
              "at": 0.6343,
              "text": "The question has 71 characters, spaces included."
            }
          ],
          "question_a": "Tom has 12 apples. He gives away 5,",
          "question_b": "then buys 3. How many does he have?",
          "tag": "made-up example: a walk-through of the design, not a recorded run",
          "chars_note": "71 characters, spaces included (our count).",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (line 42, question text)",
            "animations/storyboards-2026-10-09.md idea 1 (line 53: example is made up)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 heading (line 40: step-by-step is T1SDR + H1 code with B3 group 1's changes, built but never run)",
            "architecture/model-deep-dive.html line 55 ('Made up for this page ... It is not a real row')"
          ],
          "notes": "Two letter rows: row A is characters 0-34, row B is characters 36-70. The space at the break (index 35) is not drawn. 71 = 35 (row A) + 1 (the space between the rows) + 35 (row B); counted by script by the checker, matches the author's count. Tag extended by the checker: FINISHED-MODEL sec. 3 (line 40) says this walk-through is code, and the Gemma step has never run, so no file records this question being run through the model.",
          "atMap": [
            [
              0.02,
              0.0333
            ],
            [
              0.3389,
              0.3239
            ],
            [
              0.6578,
              0.6343
            ]
          ]
        },
        {
          "id": "s03",
          "duration": 30,
          "heading": "Step 1: the reader reads once",
          "question_a": "Tom has 12 apples. He gives away 5,",
          "question_b": "then buys 3. How many does he have?",
          "caption": [
            {
              "at": 0.02,
              "text": "A borrowed reader (trained by someone else) reads the whole question once. Its name is EmbeddingGemma 2."
            },
            {
              "at": 0.2925,
              "text": "Frozen means our practice (training) never changes it."
            },
            {
              "at": 0.4569,
              "text": "Each letter gets 768 numbers from the reader: those of the word piece the letter sits in."
            },
            {
              "at": 0.7026,
              "text": "The reader has 271,002,624 numbers. We did not set them."
            }
          ],
          "reader_numbers": 271002624,
          "labels": [
            "Reader",
            "borrowed, frozen",
            "768 numbers per letter",
            "in the whole reader: numbers we did not set",
            "illustration: shading is decoration"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 reader row (line 31: 768 numbers, 271,002,624, borrowed frozen)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 1 (lines 43-45)"
          ],
          "notes": "Shading in the vector strips is decoration only (12 cells drawn instead of 768); the strips carry an 'illustration' tag. The word-piece grouping is not drawn: we did not show the real tokenisation. Third caption reworded by the checker to match FINISHED-MODEL line 31: each letter gets the 768-number state of the Gemma token it sits in. Fix pass: both lines of the question are drawn (as in s02). The big number is labelled \"in the whole reader: numbers we did not set\" so it is not read as a per-letter figure.",
          "atMap": [
            [
              0.015,
              0.02
            ],
            [
              0.2569,
              0.2925
            ],
            [
              0.4988,
              0.4569
            ],
            [
              0.7406,
              0.7026
            ]
          ]
        },
        {
          "id": "s04",
          "duration": 20.5,
          "heading": "The letter window sees neighbours",
          "question_a": "Tom has 12 apples. He gives away 5,",
          "question_b": "then buys 3. How many does he have?",
          "caption": [
            {
              "at": 0.0293,
              "text": "A small learned window lets each letter see 4 letters on each side."
            },
            {
              "at": 0.3192,
              "text": "It is ours, learned from scratch in our practice."
            },
            {
              "at": 0.5878,
              "text": "In small tests at the 3 million size, every reader without it failed the letter-code puzzles."
            }
          ],
          "labels": [
            "centre letter",
            "4 letters each side"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 letter window row (line 33: 4 letters each side)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 7 Q3 (lines 177-178: kept; cipher_map 100% down to 2.5-10%)",
            "custom_io/results/RESULTS-EG2.md on origin/claude/custom-reader-talker-4x309r, lines 120-121 (cipher_map in_dist per arm)",
            "custom_io/models/reader.py docstring on origin/claude/custom-reader-talker-4x309r at 17a356e62 (receptive field +-2 per block, +-4 with 2 blocks)"
          ],
          "notes": "The 4-letter window is the stated design (reader.py: two kernel-5 conv blocks, +-2 letters each, so +-4). Third caption scoped by the checker: RESULTS-EG2.md (diagnosis checks, lines 120-121) shows cipher_map in-distribution EGE with the window 97.50 / 95.00 (seeds 200, 201) against 5.00 / 2.50 for EGR (Gemma plus letters, no window) and 12.50 / 2.50 for R0 (letters, no window); all runs at the 3M size. FINISHED-MODEL sec. 7 Q3 rounds this to '100% down to 2.5-10%'; no number from it is on screen.",
          "atMap": [
            [
              0.0207,
              0.0293
            ],
            [
              0.3391,
              0.3192
            ],
            [
              0.6575,
              0.5878
            ]
          ]
        },
        {
          "id": "s05",
          "duration": 19.5,
          "heading": "Zoom out: what one round is",
          "caption": [
            {
              "at": 0.0308,
              "text": "The thinker is the part that loops. One lap around the question is one round."
            },
            {
              "at": 0.3722,
              "text": "In each round it looks at the whole question, passes notes, and thinks."
            },
            {
              "at": 0.7006,
              "text": "The same learned settings are used every round. Only its notes change."
            }
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
          "notes": "The loop is a picture of the design. Round counter is driven by the scene timeline.",
          "atMap": [
            [
              0.025,
              0.0308
            ],
            [
              0.3403,
              0.3722
            ],
            [
              0.6556,
              0.7006
            ]
          ]
        },
        {
          "id": "s06",
          "duration": 21,
          "heading": "Round 1: look, and no call yet",
          "question_a": "Tom has 12 apples. He gives away 5,",
          "question_b": "then buys 3. How many does he have?",
          "caption": [
            {
              "at": 0.0286,
              "text": "In round 1 the thinker looks at every letter and passes notes."
            },
            {
              "at": 0.2946,
              "text": "Tested version: no call (a request to the calculator) is written after round 1; the call slot stays empty."
            },
            {
              "at": 0.6796,
              "text": "In the version we tested, the first call comes after round 2."
            }
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
          "notes": "Tested version here means T1SDR (3M size, 6 copies), which was tested; H1 has the same timing on paper but has not been run. Second caption reworded by the checker: the source says no call is written after round 1 (code rule t = round - 1, calls need t >= 1), not that nothing needs calculating yet.",
          "atMap": [
            [
              0.0194,
              0.0286
            ],
            [
              0.3387,
              0.2946
            ],
            [
              0.6581,
              0.6796
            ]
          ]
        },
        {
          "id": "s07",
          "duration": 20.5,
          "heading": "Tested version, round 2: the call writer picks",
          "caption": [
            {
              "at": 0.0293,
              "text": "Tested version: after round 2 the call writer reads its first control vector (a list of numbers)."
            },
            {
              "at": 0.3889,
              "text": "It picks one of 8 operations, or writes no call. No call is a choice."
            },
            {
              "at": 0.7136,
              "text": "The 8 are add, sub, mul, div, mod, min, max and cmp."
            }
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
            "not an op",
            "New design: the talker writes the call at the end of a turn."
          ],
          "chips": [
            "tested version: 3M size, 6 separately trained copies"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 call writer row (line 35)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 calculator row (line 37: 8 operations)"
          ],
          "notes": "The call writer shown is the tested T1SDR one (3M size, 6 seeds; FINISHED-MODEL line 35 'shown in T1SDR' and line 37). Group 2 later writes the whole call as letters; that version is not tested. Chip label added by the checker so the green chip says what size and how many copies.",
          "atMap": [
            [
              0.0194,
              0.0293
            ],
            [
              0.3387,
              0.3889
            ],
            [
              0.6581,
              0.7136
            ]
          ]
        },
        {
          "id": "s08",
          "duration": 25.5,
          "heading": "Tested version: copying 12 and 5 from the question",
          "question_a": "Tom has 12 apples. He gives away 5,",
          "question_b": "then buys 3. How many does he have?",
          "caption": [
            {
              "at": 0.0235,
              "text": "Tested version: the thinker writes a call as text. A learned pointer finds each number's last digit."
            },
            {
              "at": 0.3126,
              "text": "The code copies one letter at a time to the left, until the learned stop head says stop."
            },
            {
              "at": 0.6157,
              "text": "Some steps are still hand-written code, like flipping the digits into reading order."
            }
          ],
          "call": "sub 12 5",
          "labels": [
            "pointer: learned",
            "stop head: learned",
            "flip: hand-written",
            "tested version: the call, as text",
            "New design: no pointer. The talker writes the call at the end of a turn."
          ],
          "chips": [
            "learned",
            "hand"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 2 (lines 48-50: pointer, copy, stop head)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 table (lines 96-98: span copy, last letter first)"
          ],
          "notes": "Letter indexes for the question row A: '1' of 12 is index 8, '2' is index 9, '5' is index 33. The copy goes from 9 back to 8, then stops at the space at index 7. Fix pass: both question lines are drawn; the copy arrow (2 then 1, leftward) and the stop head arrow (to the space at index 7) show the caption; flip box feeds the call. Captions 2 and 3 shortened to one line each with the same meaning (\"a learned part (the stop head)\" became \"the learned stop head\"; \"the copied digits\" became \"the digits\").",
          "atMap": [
            [
              0.0158,
              0.0235
            ],
            [
              0.3377,
              0.3126
            ],
            [
              0.6596,
              0.6157
            ]
          ]
        },
        {
          "id": "s09",
          "duration": 22,
          "heading": "Why use a calculator at all",
          "caption": [
            {
              "at": 0.0273,
              "text": "The calculator is an ordinary program. It is outside the model."
            },
            {
              "at": 0.2728,
              "text": "A call is a line of text. The reader reads the answer, also as text."
            },
            {
              "at": 0.5754,
              "text": "With the calculator switched off, questions that need a calculation scored 0.0 points out of 100 on all 6 copies."
            }
          ],
          "request": "sub 12 5",
          "zero_score": 0,
          "labels": [
            "Calculator",
            "points out of 100, calculator off (2,085 questions, 3M size)",
            "outside tool",
            "the call, as text"
          ],
          "chips": [
            "hand",
            "tested: all 6 copies"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 1 (lines 106-107: program questions score 0.0 with calculator off; MARKS-D0-T1 Record 13)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (line 76: calculator allowed as a tool)",
            "custom_io/results/RESULTS-T1SDR.md on origin/claude/custom-reader-talker-4x309r, 6-seed table (tool off 0.0 on seeds 200-205) and mark 3 (line 56)",
            "custom_io/results/*/T1SDR_s20x/RESULT.json extra.noexec (n 2085; program_families 0.0 / 0.048)"
          ],
          "notes": "The reason 'exact sums are easy for code and hard to learn' is our reasoning (suggested), not a measured result. It is not shown on screen as a fact. 'Program questions' in the sources (the noexec program set, 14 families, n = 2,085) is shown as 'questions that need a calculation'. Raw RESULT.json (extra.noexec.program_families): 0.000 on seeds 200, 201, 202, 204, 205 and 0.048 on seed 203 (1 of 2,085), which the sources print as 0.0; with the calculator on the same set scores 96.21 to 98.13. T1SDR at the 3M size. Fix pass: green chip \"tested: all 6 copies\" added next to the 0.0 (T1SDR 6-seed table, tool off 0.0 on seeds 200-205; 3M size, 2,085 questions as already checked). The caption uses non-breaking spaces so \"0.0 points out of 100\" is never split across lines.",
          "atMap": [
            [
              0.0194,
              0.0273
            ],
            [
              0.3387,
              0.2728
            ],
            [
              0.6581,
              0.5754
            ]
          ]
        },
        {
          "id": "s10",
          "duration": 19,
          "heading": "The calculator replies: 12 minus 5 is 7",
          "caption": [
            {
              "at": 0.0316,
              "text": "The outside calculator gets sub 12 5 and sends back 7, as plain text."
            },
            {
              "at": 0.3642,
              "text": "Built so far: the letter window alone reads the reply. New design: the whole reader, Gemma too."
            },
            {
              "at": 0.7521,
              "text": "Gemma and the calculator have never run together."
            }
          ],
          "request": "sub 12 5",
          "reply": "sub 12 5 = 7",
          "labels": [
            "Calculator",
            "Thinker's notes",
            "Reader",
            "outside tool"
          ],
          "chips": [
            "hand"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 3 (lines 51-52)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 5 (lines 120-122: replies read by the letter window only)"
          ],
          "notes": "The calculator and the Gemma reader have never run together (FINISHED-MODEL sec. 5 item 6). This picture combines them as the built design (B3 group 1), so the caption now says so. Replies read by the letter window only is the built design; the reason (replies carry nothing Gemma would add) is only suggested.",
          "atMap": [
            [
              0.0207,
              0.0316
            ],
            [
              0.3391,
              0.3642
            ],
            [
              0.6575,
              0.7521
            ]
          ]
        },
        {
          "id": "s11",
          "duration": 20.5,
          "heading": "Round 3: a second call",
          "question_b": "then buys 3. How many does he have?",
          "caption": [
            {
              "at": 0.0293,
              "text": "Round 3 now also sees sub 12 5 = 7."
            },
            {
              "at": 0.3229,
              "text": "Tested version: the call writer writes add 7 3, copying 7 from the reply and 3 from the question."
            },
            {
              "at": 0.7174,
              "text": "The calculator returns 10. The reader reads it, and it joins the notes."
            }
          ],
          "call2": "add 7 3",
          "reply2": "add 7 3 = 10",
          "reply1": "sub 12 5 = 7",
          "labels": [
            "Round 3",
            "reply: 10, read by the reader",
            "notes",
            "tested version: the call goes out"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 4 (line 53)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 call writer row (line 35: numbers copied from the question or an earlier reply)"
          ],
          "notes": "Index of '7' in the reply line 'sub 12 5 = 7' is 11. Index of '3' in question row B is 10. Fix pass: the call text is placed so its 7 sits under the 7 that ends the first notes line and its 3 under the 3 of the question (two parallel arrows, none through a letter); the arrows fade when the reply arrives and \"add 7 3 = 10\" slides up into the notes as a second line.",
          "atMap": [
            [
              0.0194,
              0.0293
            ],
            [
              0.3387,
              0.3229
            ],
            [
              0.6581,
              0.7174
            ]
          ]
        },
        {
          "id": "s12",
          "duration": 19,
          "heading": "Later rounds: calls and pauses",
          "caption": [
            {
              "at": 0.0316,
              "text": "Some rounds have nothing to calculate, so they write no call."
            },
            {
              "at": 0.3068,
              "text": "In the version we tested, calls come after rounds 2 to 8 only."
            },
            {
              "at": 0.6195,
              "text": "The newest version can call in any round from 2 to 32. Built, not tested."
            }
          ],
          "call1": "sub 12 5",
          "call2": "add 7 3",
          "labels": [
            "picture only",
            "empty box = no call",
            "rounds used by this question: not recorded",
            "rounds 9 to 32 (stop-switch version): no call drawn"
          ],
          "chips": [
            "untested"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 54-56: rounds with no call)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 60-65: call timing; B3 any round built, untested)",
            "animations/storyboards-2026-10-09.md idea 1 (line 54: rounds 3 and 4 are an illustration)"
          ],
          "notes": "How many rounds this question uses is not recorded in any file. Rounds shown after 3 are a picture only. The tested T1SDR runs a fixed 8 rounds (FINISHED-MODEL sec. 4, hand-code table); rounds 9 to 32 exist only in the stop-switch version (H1, built, never run), so the label says so.",
          "atMap": [
            [
              0.0187,
              0.0316
            ],
            [
              0.3385,
              0.3068
            ],
            [
              0.6583,
              0.6195
            ]
          ]
        },
        {
          "id": "s13",
          "duration": 19,
          "heading": "The stop switch: done or not",
          "caption": [
            {
              "at": 0.0316,
              "text": "After each round a small learned switch asks: is it done yet?"
            },
            {
              "at": 0.3256,
              "text": "It must run at least 1 round, and at most 32. The 32 is a safety limit."
            },
            {
              "at": 0.7135,
              "text": "A stop ends each turn. The switch is built, never tested."
            }
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
          "notes": "The switch turning on at round 4 is an illustration. No file records a stop round for this question.",
          "atMap": [
            [
              0.0231,
              0.0316
            ],
            [
              0.3397,
              0.3256
            ],
            [
              0.6564,
              0.7135
            ]
          ]
        },
        {
          "id": "s14",
          "duration": 20,
          "heading": "The talker writes the answer",
          "caption": [
            {
              "at": 0.03,
              "text": "The stand-in copies 10 from the last reply, where the thinker points."
            },
            {
              "at": 0.3093,
              "text": "It adds no thinking of its own, so the answer is just the copied 10."
            },
            {
              "at": 0.6421,
              "text": "The planned talker, about 25 million numbers, reads thoughts, no pointer, and writes calls."
            }
          ],
          "answer": "10",
          "last_reply": "add 7 3 = 10",
          "labels": [
            "Talker",
            "English talker: planned, no pointer",
            "stand-in today",
            "stand-in only: copies where the thinker points"
          ],
          "chips": [
            "placeholder"
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 6 (line 57)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 talker row (line 38: about 25M planned; small stand-in today)"
          ],
          "notes": "The answer 10 is the made-up example's answer. It is not a test result.",
          "atMap": [
            [
              0.024,
              0.03
            ],
            [
              0.34,
              0.3093
            ],
            [
              0.656,
              0.6421
            ]
          ]
        },
        {
          "id": "s15",
          "duration": 41.5,
          "heading": "What is tested",
          "caption": [
            {
              "at": 0.0145,
              "text": "Green: adding the Gemma reader gained 2.67 points out of 100 (6,040 questions) in 6 of 6 copies at 3M."
            },
            {
              "at": 0.2747,
              "text": "Green: calculator outside matched the old calculator-inside model in 6 copies. One check on no-thinking answers missed; the project owner cleared it."
            },
            {
              "at": 0.5508,
              "text": "Amber: calls in any round, stop switch. Built, never tested."
            },
            {
              "at": 0.6753,
              "text": "Grey: the English talker. A placeholder, not built yet."
            },
            {
              "at": 0.7841,
              "text": "Open question: with the Gemma reader, some answers use zero thinking rounds. Everything together: never tested."
            }
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 reader row (line 31: shown at 3M, EGE +2.67 over B2, 6 of 6 seeds, zero-round leak mark missed, mean 6.59 against 4.62)",
            "big-run/PLAN.md line 133 (EGE 3M: 6 seeds, +2.67 pooled-5 over B2, ahead on 6 of 6)",
            "custom_io/results/39-pc-ege-confirm/EGE_s202..207 and B2_s206..207 and custom_io/results/33-pc-confirm-b2/B2_s202..205 RESULT.json (recomputed gain per seed)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 1 (lines 106-108: T1SDR matched B2 over 6 seeds; mark 5 on 5 of 6)",
            "architecture/MARKS-D0-T1-2026-10-07.md Record 13 (line 198 onward: marks 1-3, 6 pass; mark 4 cleared by Ben; mark 5 seed 205 unscored)",
            "custom_io/results/RESULTS-T1SDR.md (6-seed confirm block)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 2 (lines 111-112: zero-round answers, cause not settled); sec. 2 lines 36 and 38; sec. 5 item 6",
            "animations/storyboards-2026-10-09.md idea 1 (line 64: legend wording)"
          ],
          "notes": "Rewritten by the checker. Caption 1: EGE (Gemma tokens added to letters, plus window) minus plain B2, pooled-5 (6,040 kept-aside questions: in_dist 1360 + answer 1200 + frame 1360 + vocab 800 + variant 1320), seeds 202-207: +1.14, +2.70, +3.44, +2.63, +3.54, +2.57, mean +2.67, ahead on 6 of 6 (recomputed from the RESULT.json files; same as FINISHED-MODEL line 31 and big-run PLAN.md line 133). Size: 3,500,881 trained numbers plus the frozen 271,002,624. The old caption said 'tested once at the 3M size' (G1 seed 400 only), which understates the evidence in FINISHED-MODEL line 31. Caption 2: T1SDR minus B2 over 6 seeds: pooled-5 mean +0.62, 95% CI -0.23 to +1.46, 6 of 6 seeds within 1.0, chain-5 99.6-99.8 (RESULTS-T1SDR.md). Leak mark 4 missed (donor 5.0-5.6 against 5; loops:0 12.94 on seed 201 against B2 10.81) and Ben cleared it 8:21 AM ET Oct 9 (MARKS-D0-T1 Record 13); mark 5 (reply swap) holds on 5 of 6 seeds, seed 205 unscored (checkpoint lost). Not on screen for space; recorded here. Caption 5: EGE 6-seed confirm mean zero-round in_dist 6.59 against plain B2 3.62 (limit 4.62), recomputed from RESULT.json; cause not settled (FINISHED-MODEL sec. 5 item 2). Chips: orange = open question (warning colour); each chip now has a part name beside it so the final still picture reads on its own. 'Copies' means seeds. 'The old model' in caption 2 is B2 (same design with the calculator inside); T1SDR is B2 with the calculator moved outside (tool.py docstring).",
          "rows": [
            "Gemma reader",
            "Outside calculator",
            "Calls in any round, stop switch",
            "English talker",
            "Zero-round answers",
            "Everything together"
          ],
          "chip_open": "open question",
          "chip_all": "never tested",
          "atMap": [
            [
              0.014,
              0.0145
            ],
            [
              0.223,
              0.2747
            ],
            [
              0.456,
              0.5508
            ],
            [
              0.581,
              0.6753
            ],
            [
              0.707,
              0.7841
            ]
          ]
        },
        {
          "id": "s16",
          "duration": 18.5,
          "heading": "Recap: what to remember",
          "caption": [
            {
              "at": 0.0324,
              "text": "The reader reads each turn's new text. The thinker thinks in rounds."
            },
            {
              "at": 0.3344,
              "text": "The stop switch ends the turn. The talker writes the answer or a call."
            },
            {
              "at": 0.6749,
              "text": "Now we open each box, one at a time."
            }
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 (lines 15-20)",
            "animations/storyboards-2026-10-09.md idea 1 (line 64: legend)"
          ],
          "notes": "Still final picture: the four-part model map with the outside calculator beside it, call and reply arcs drawn, all parts lit. Fix pass: heading changed from \"Recap: three things to remember\" to \"Recap: what to remember\" (the picture and captions cover five parts; no source claim involved). One short line under each box repeats the caption wording.",
          "labels": [
            "reads the new text",
            "thinks in rounds",
            "does the sums",
            "ends each turn",
            "calls or answers"
          ],
          "atMap": [
            [
              0.025,
              0.0324
            ],
            [
              0.3403,
              0.3344
            ],
            [
              0.6556,
              0.6749
            ]
          ]
        }
      ]
    },
    "ch03": {
      "kicker": "Part 2 of 10",
      "title": "The reader: giving every letter a meaning",
      "blurb": "The reader is a borrowed part. It reads the question once and gives every letter a meaning in context.",
      "accent": "reader",
      "scenes": [
        {
          "id": "s01",
          "duration": 18.5,
          "heading": "Where we are: the reader comes first",
          "caption": [
            {
              "at": 0.0324,
              "text": "The question enters the reader first. The reader is a borrowed model called Gemma, and it reads the whole question one time."
            },
            {
              "at": 0.5274,
              "text": "Picture only: a translator who already knows English well. We borrowed him, and we cannot change him."
            }
          ],
          "illustration": "analogy only: the translator is a picture, not a real part",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 and sec. 2 (Reader row)",
            "kit GLOSSARY.md (shared translator picture)"
          ],
          "notes": "Map is S.modelMap with highlight reader. Order of the five parts follows GLOSSARY.md. Checker edit: caption 1 now names Gemma as the reader (first use in the chapter), so s02 onward stands alone. Checker edit: the 'picture only' tag now says it is the translator that is only a picture (the map itself is the finished design). Fixer edit: a plain \"the question\" card with an arrow up into the Reader box was added (the caption says the question enters the reader first); the map labels of the dimmed parts are a darker grey (local override, same words).",
          "labels": {
            "question": "the question"
          },
          "atMap": [
            [
              0.025,
              0.0324
            ],
            [
              0.4979,
              0.5274
            ]
          ]
        },
        {
          "id": "s02",
          "duration": 20.5,
          "heading": "Letters versus word pieces",
          "caption": [
            {
              "at": 0.0293,
              "text": "Gemma cuts text into word pieces, called tokens."
            },
            {
              "at": 0.582,
              "text": "Our thinker, the part that does the thinking, works on letters: one spot for each letter."
            }
          ],
          "example": "Tom has 12 apples.",
          "illustration": "made-up example: where the cuts fall is a picture only, not Gemma's real cut",
          "src": [
            "architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 1 (lines 12-13: Gemma cuts text into tokens; the thinker has one spot per letter)"
          ],
          "notes": "Only the sentence is real. The token boxes are drawn by hand and are labelled as a made-up example. Checker edit: caption 2 now says in half a sentence what the thinker is. Fixer edit: letters and word-piece boxes are centred on the screen and larger; the arrows end on the boxes. No text or claim changed.",
          "atMap": [
            [
              0.0231,
              0.0293
            ],
            [
              0.4981,
              0.582
            ]
          ]
        },
        {
          "id": "s03",
          "duration": 21,
          "heading": "Measured: about 3 to 4.3 letters per token",
          "caption": [
            {
              "at": 0.0286,
              "text": "On 20,000 of our skill questions, one token covers 3.08 letters on average."
            },
            {
              "at": 0.5194,
              "text": "On 9,068 web-text chunks of 279 letters, one token covers 4.27 letters on average."
            }
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
            "architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 2 table, rows 1 and 2 (lines 38-39: 20,000 rows 3.08; 9,068 rows 4.27; my count 10-09, Gemma tokenizer.json at 914f7f89)"
          ],
          "notes": "A ratio (letters per token), not a score out of 100. The sec. 1 text rounds these to 3.1 and 4.3; the table values 3.08 and 4.27 are shown (table used). The row counts 20,000 and 9,068 are from the same table. Checker: Gemma tokenizer and the skill/web files are not on this machine, so the two ratios are the source's own count (not recomputed). Heading says 'about 3 to 4' because 4.27 is above 4. Checker edit: both bars now teal (the reader's tokenizer); indigo is the thinker's colour.",
          "atMap": [
            [
              0.025,
              0.0286
            ],
            [
              0.4979,
              0.5194
            ]
          ]
        },
        {
          "id": "s04",
          "duration": 17.5,
          "heading": "The reader reads once, then copies meaning",
          "caption": [
            {
              "at": 0.0343,
              "text": "Gemma reads the whole question one time."
            },
            {
              "at": 0.2978,
              "text": "Each token gets a row of 768 numbers that holds its meaning in context."
            },
            {
              "at": 0.6613,
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
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 1",
            "custom_io/models/eg.py lines 10-11 and line 25 [branch learner-new-g2; line 23 on custom-reader-talker-4x309r] (EG_DIM 768; H [B,T,768] is the state of the token that holds each prompt char)"
          ],
          "notes": "768 is Gemma's width. Older page architecture/model-deep-dive.html line 69 says 256 numbers per letter; that is the earlier design and is not shown. Fixer edit: the \"shaded cells are decoration\" note now arrives together with the 768 row; the row sits on the arrows' line and both arrows run edge to edge.",
          "atMap": [
            [
              0.05,
              0.0343
            ],
            [
              0.4,
              0.2978
            ],
            [
              0.7,
              0.6613
            ]
          ]
        },
        {
          "id": "s05",
          "duration": 32.5,
          "heading": "The borrowed reader: 271,002,624 numbers",
          "caption": [
            {
              "at": 0.0185,
              "text": "The reader holds 271,002,624 numbers, all set before our work began."
            },
            {
              "at": 0.2917,
              "text": "134,217,728 of them are a word table (one row per word piece); 136,784,896 are reading layers (a transformer) plus a step widening rows to 768."
            },
            {
              "at": 0.6843,
              "text": "It is frozen: our practice never changes it. Its own reading limit is 8,192 tokens, which is not our limit."
            }
          ],
          "labels": {
            "table": "word table 134,217,728",
            "tf": "transformer 136,784,896",
            "frozen": "borrowed, frozen"
          },
          "src": [
            "custom_io/models/eg.py lines 1-6 (frozen, never trained; text backbone 271,002,624 = 134,217,728 word table + 136,784,896 transformer and its 512 to 768 projection)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Reader row)",
            "architecture/TOKENS-EXPERIMENT-2026-10-09.md line 32 (8,192-token model card)"
          ],
          "notes": "Sum checked by hand: 134,217,728 + 136,784,896 = 271,002,624. The source calls the first part a 'word table' (an embedding table has one row per word piece by definition); the number of rows is not given in the sources read, so no row count is shown. Borrowed and frozen is shown as a teal text label, not a status chip. The 8,192-token card limit is the source's quote of the model card (not re-fetched). Checker edit: the transformer bar is teal (it is part of the reader), not the thinker's indigo. Checker edit: 'projection' replaced by its plain meaning (eg.py line 6: 512 -> 768 projection).",
          "atMap": [
            [
              0.0187,
              0.0185
            ],
            [
              0.3385,
              0.2917
            ],
            [
              0.6583,
              0.6843
            ]
          ]
        },
        {
          "id": "s06",
          "duration": 22,
          "heading": "The small models' converter plug",
          "caption": [
            {
              "at": 0.0273,
              "text": "In the small test models, a converter plug, one learned layer, turns Gemma's 768 numbers into the thinker's width."
            },
            {
              "at": 0.424,
              "text": "At width 256 it has 196,864 learned numbers. At full size there is no plug: Gemma's 512 numbers go straight in."
            }
          ],
          "labels": {
            "in": "768 in",
            "out": "thinker width",
            "plug": "converter plug (small models)",
            "full": "full size: no plug, Gemma's 512 go straight in"
          },
          "chip": "learned",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Gemma adapter row, line 32)",
            "custom_io/models/ledger.py lines 192-202 and 281-293 (eg_proj = nn.Linear(768, d), zero-initialised, applied to Gemma's state)"
          ],
          "notes": "Our check: 768 times 256 plus 256 bias = 196,864; 768 times 512 plus 512 = 393,728. Matches the source. The layer norm before the layer (1,536 numbers) is not counted in the source's figure either. Width 256 is the 3M-size model, width 512 the planned 100M thinker (FINISHED sec. 5 item 9). Checker edit: added the illustration tag (the vectors are decoration). Fixer edit: the \"picture only\" note now arrives together with the two cell rows; arrows run edge to edge.",
          "illustration": "picture only: cell counts and shading are decoration",
          "atMap": [
            [
              0.0273,
              0.0273
            ],
            [
              0.4977,
              0.424
            ]
          ]
        },
        {
          "id": "s07",
          "duration": 36,
          "heading": "Four parts added into one letter row",
          "caption": [
            {
              "at": 0.0167,
              "text": "First: which letter it is. A learned row of numbers."
            },
            {
              "at": 0.1951,
              "text": "Second: where it sits in the question. A learned table: 2,000 rows in the planned finished design (B3), 280 in the growth test (G1)."
            },
            {
              "at": 0.5081,
              "text": "Third: how far its letter sits from the end of its word. The count is hand-written; the row it picks is learned."
            },
            {
              "at": 0.7625,
              "text": "Fourth: Gemma's meaning is added on top, via a small plug (none at full size). The letter window reads the sum."
            }
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
            "custom_io/models/reader.py lines 1-3 (docstring: E_char + E_pos + E_place; place = index from the right end of the word) and lines 62, 71-84 (order: char + pos, then place, then extra added, then the conv blocks)",
            "custom_io/models/ledger.py lines 281-293 (read(): eg_proj(ln_eg(H)) passed as extra)",
            "custom_io/g8a/caps_b3.json (max_prompt 2000) and caps_g.json (max_prompt 280); custom_io/g8a/caps.py lines 130-132 (reader.MAX_PROMPT = caps max_prompt, the position table size)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (place code row; group 2 replaces the count) and sec. 7 Q2"
          ],
          "notes": "Order checked in code (branch learner-new-g2 and qtxfp4, identical reader.py): Gemma's projection is added after the three parts and before the conv window. Only the place COUNT (word_spans regex) is hand-written; the place ROW (nn.Embedding) is learned. B3 group 1 is built but never run, so the 2,000-row table is a planned setting; G1 (280) is what has run. Checker edit: box colours now follow the glossary (blue learned, brown hand-written, teal Gemma = reader); before, Gemma was coral (the call writer's colour) and the position table indigo (the thinker's colour). Checker edit: 'Part one..four' became 'First..Fourth' so the captions are not mistaken for the video's 'Part 2 of 8' numbering. Fixer edit: the four arrows now end on the top edge of the \"added together\" box. The Gemma box border is the reader teal (#0F8B8D), same as the Reader box; not green.",
          "atMap": [
            [
              0.0136,
              0.0167
            ],
            [
              0.2563,
              0.1951
            ],
            [
              0.4989,
              0.5081
            ],
            [
              0.7415,
              0.7625
            ]
          ]
        },
        {
          "id": "s08",
          "duration": 25.5,
          "heading": "The letter window: each letter sees 4 each side",
          "caption": [
            {
              "at": 0.0235,
              "text": "Two small learned layers read the summed row. They are ours, not borrowed."
            },
            {
              "at": 0.2566,
              "text": "Each layer looks 2 letters left and 2 right, so together a letter sees 4 letters each side."
            },
            {
              "at": 0.5597,
              "text": "The window adds about 0.7 million numbers at width 256, about 2.6 million at 512."
            }
          ],
          "labels": {
            "l1": "layer 1: 2 each side",
            "l2": "layer 2: 2 more each side"
          },
          "chip": "learned",
          "chip_label": "learned, ours",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (letter window row, line 33)",
            "custom_io/models/reader.py lines 5-6 and 46-54, 63 (two ConvBlocks, kernel 5, padding 2: plus or minus 2 each, plus or minus 4 in all; layers=2 is the Ledger default, ledger.py __init__ signature, reader_layers=2) [branch learner-new-g2]"
          ],
          "notes": "The window is learned, not borrowed. Exact counts from code (my count, not shown): per block conv d*d*5 + d plus LayerNorm 2d; two blocks = 656,896 at width 256 and 2,624,512 at width 512; the on-screen 0.7 million and 2.6 million are the source's rounded values. Fixer edit: picture moved down so the layer-2 label clears the heading; caption 3 shortened by two words so \"512.\" no longer sits alone on a second line (numbers and \"about\" unchanged).",
          "atMap": [
            [
              0.0194,
              0.0235
            ],
            [
              0.3387,
              0.2566
            ],
            [
              0.6581,
              0.5597
            ]
          ]
        },
        {
          "id": "s09",
          "duration": 36,
          "heading": "Without the window, cipher puzzles fall",
          "caption": [
            {
              "at": 0.0167,
              "text": "Letter-cipher puzzles are one kind of test question: 40 familiar-style ones per copy (a separate training run), scored out of 100."
            },
            {
              "at": 0.3623,
              "text": "With the window, Gemma plus letters scores 97.5 and 95.0 on two copies."
            },
            {
              "at": 0.5804,
              "text": "Without it, Gemma plus letters scores 5.0 and 2.5."
            },
            {
              "at": 0.7352,
              "text": "Letters alone, without it, score 12.5 and 2.5."
            }
          ],
          "labels": {
            "with": "Gemma + letters, with window",
            "without": "Gemma + letters, no window",
            "alone": "letters only, no window",
            "zero": "0",
            "full": "100",
            "scale": "points out of 100"
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
            "custom_io/results/46-r0ege-s200/EGE_s200 and 49-ege-s201/EGE_s201 RESULT.json (eg_embed true, 2 window layers): final_eval.in_dist.by_family.cipher_map 39/40 and 38/40",
            "custom_io/results/44-egr-s200/EGR_s200 and 45-egr-s201/EGR_s201 RESULT.json (eg_embed true, reader_layers 0: Gemma plus letters, no window): 2/40 and 1/40",
            "custom_io/results/46-r0ege-s200/R0_s200 and 48-r0-s201/R0_s201 RESULT.json (reader_layers 0, no eg_embed: letters alone, no window): 5/40 and 1/40",
            "swarm/gpt-swarm-team-2026-10-05.md lines 27 and 29 ('letter ciphers (cipher_map)'; 'Held-out test splits, 40 questions per family per split')"
          ],
          "notes": "Arms re-read in the result files (branch origin/claude/custom-reader-talker-4x309r): scores are cipher_map inside the in_dist split (same templates as practice, new questions), 40 questions per copy, so 39/40 = 97.5, 38/40 = 95.0, 2/40 = 5.0, 1/40 = 2.5, 5/40 = 12.5. Same two seeds (200, 201) in every arm: first bar of a group is seed 200. Disagreement (1): the brief and FINISHED sec. 2 and sec. 7 Q3 say 100% down to 2.5-10%; the results file says 97.5/95.0 with the window, 5.0/2.5 (EGR) and 12.5/2.5 (R0). Results file used. Checker edit: 'copy' is defined at first use; 'cipher_map' is called letter-cipher puzzles (swarm/gpt-swarm-team-2026-10-05.md line 27: 'letter ciphers (cipher_map)'; 40 questions per family per split, same file line 29). Added the third group (letters alone, 12.5 and 2.5) so every number in the caption is on the picture, and the 40-puzzle count. Fixer edit: a 0 to 100 scale (ticks and labels) was added under the six bars; the bars already ran on a 0 to 100 track (hbars max 100). No value changed.",
          "atMap": [
            [
              0.02,
              0.0167
            ],
            [
              0.27,
              0.3623
            ],
            [
              0.52,
              0.5804
            ],
            [
              0.7,
              0.7352
            ]
          ]
        },
        {
          "id": "s10",
          "duration": 26.5,
          "heading": "The position table: how long a question can be",
          "caption": [
            {
              "at": 0.0226,
              "text": "The position table has one row per spot, so it sets the longest question: 280 letters in the growth test (G1), 2,000 in planned B3."
            },
            {
              "at": 0.4519,
              "text": "In a sample of 4,000 bAbI test questions (a public set of story puzzles), 32% run over 280 letters and 1% over 2,000."
            }
          ],
          "numbers": {
            "sample": 4000,
            "over280": 32,
            "over2000": 1
          },
          "labels": {
            "sample": "4,000 bAbI test questions",
            "a": "over 280 letters",
            "b": "over 2,000 letters",
            "unit": "each square = 1%",
            "dark": "dark square: also over 280 letters"
          },
          "chip": "tested",
          "chip_label": "measured by count",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 7 Q2 (lines 173-176; 200 per task, bAbI test split)",
            "architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 7 (line 123: position table sized to the input cap, nn.Embedding(MAX_PROMPT, d))",
            "custom_io/g8a/caps_g.json and caps_b3.json (max_prompt 280 and 2000)"
          ],
          "notes": "Counts from FINISHED sec. 7 (the architecture thread's own sample; big-run/PLAN.md line 103 repeats it and says 'not rechecked by me'). Checker: the bAbI files are not on this machine, so 4,000 / 32% / 1% are not recounted. 200 per task x 20 tasks = 4,000. Not a score. Checker edit: the first caption now says what the table is for (it sets the longest question) and what bAbI is; chip label no longer names an internal file. Checker edit: the two counts use orange and dark ink; coral and purple belong to the call writer and the stop switch. Fixer edit: added the unit line (each square = 1%) and a colour key (orange swatch = over 280, dark swatch = over 2,000). The dark square is inside the 32 coloured squares because a question over 2,000 letters is also over 280 (logic, not a new count). Duration 33 to 36 for the extra words.",
          "atMap": [
            [
              0.0167,
              0.0226
            ],
            [
              0.4986,
              0.4519
            ]
          ]
        },
        {
          "id": "s11",
          "duration": 23.5,
          "heading": "A hand-written pattern marks the numbers",
          "illustration": "picture only: the marked cells are not a real question",
          "caption": [
            {
              "at": 0.0255,
              "text": "Tested version: a hand-written pattern finds numbers. The new design copies none."
            },
            {
              "at": 0.2726,
              "text": "It records where each number is, not its value."
            },
            {
              "at": 0.4647,
              "text": "Room to mark: 16 numbers in the calculator-outside model (T1SDR), 91 in the growth test (G1), 240 in planned B3."
            }
          ],
          "labels": {
            "regex": "hand-written pattern",
            "slots": "number slots",
            "t1sdr": "calculator-outside model (T1SDR)",
            "g1": "growth test (G1)",
            "b3": "planned finished design (B3)"
          },
          "numbers": {
            "t1sdr": 16,
            "g1": 91,
            "b3": 240
          },
          "chip": "hand-written",
          "chip_label": "hand-written",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (number finder row, line 89; ledger.py:206)",
            "custom_io/models/tool.py lines 10-12 (16 workspace slots for the prompt numbers only; the regex only says where a number is) [branch custom-reader-talker-4x309r, also learner-new-g2]",
            "custom_io/models/ledger.py lines 205-208 [branch custom-reader-talker-4x309r at 17a356e62; line 221 on learner-new-g2] (NUM_RE.finditer fills the first N_NUM slots; N_NUM = 16 in progparse.py line 8)",
            "custom_io/g8a/caps_g.json (n_num 91); custom_io/g8a/caps_b3.json (n_num 240); caps.py line 141 (pp.N_NUM = caps n_num)"
          ],
          "notes": "Planned replacement N1 (learned) is in B3 group 2, not built as a result. 16 (T1SDR) now also read in tool.py lines 10-12. Checker edit: bars now carry their plain names (they were unlabelled); code names stay as small tags after the plain name. Fixer edit: the hand-written-pattern chip now settles centred over the 16-cell row (it hung past the row end); the three marked cells are 3, 8 and 11 (picture only) so they sit under the chip.",
          "atMap": [
            [
              0.0207,
              0.0255
            ],
            [
              0.3391,
              0.2726
            ],
            [
              0.6575,
              0.4647
            ]
          ]
        },
        {
          "id": "s12",
          "duration": 21,
          "heading": "Calculator replies: read by the whole reader",
          "caption": [
            {
              "at": 0.0286,
              "text": "New design: each calculator reply, shown as sub 12 5 = 7, is read by Gemma plus the letter window."
            },
            {
              "at": 0.4306,
              "text": "Built B3 version: the window alone reads replies."
            },
            {
              "at": 0.6451,
              "text": "Never tested. The old reason, that Gemma adds nothing to a reply, was only suggested."
            }
          ],
          "example": "sub 12 5 = 7",
          "labels": {
            "from": "reply from the outside calculator",
            "win": "letter window",
            "gem": "Gemma",
            "old": "built B3 version only: window alone"
          },
          "chip": "untested",
          "chip_label": "being built, never tested",
          "illustration": "old B3 reasoning: suggested only",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 5 (lines 120-122; labelled suggested)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 3",
            "custom_io/models/b3.py lines 3-4 (B3 group 1: the calculator's entries are read by the letter reader alone, Tool.read_texts; Gemma sees each question once)"
          ],
          "notes": "B3 group 1 builds this way; it has never been run (FINISHED sec. 5 item 6: the outside calculator and Gemma have never run together). The reply path is built, the reason is suggested, not measured. Checker edit: the two boxes now carry labels (they were empty), and the caption says 'shown as' to match the glossary (the reply itself is 7). Fixer edit: the amber chip now appears from the first beat (it was only at the last caption) and uses the chapter-wide wording \"built, never tested\". The X on the Gemma path is the as-built design of B3 group 1 (b3.py lines 3-4; FINISHED sec. 5 item 5), never run (item 6); only the reason (a reply adds nothing for Gemma) is \"suggested\", and that tag stays on caption 3. Captions unchanged. Round 2 (Oct 11): the new design (FINISHED sec. 5 items 16-18) has the whole reader, Gemma plus the letter window, read every tool reply like the question; the X on the Gemma path now marks only the built B3 version (b3.py lines 3-4).",
          "atMap": [
            [
              0.0222,
              0.0286
            ],
            [
              0.3395,
              0.4306
            ],
            [
              0.6568,
              0.6451
            ]
          ]
        },
        {
          "id": "s13",
          "duration": 35,
          "heading": "The gain: +2.67 points out of 100",
          "caption": [
            {
              "at": 0.0171,
              "text": "On 6,040 test questions kept aside (five kinds, called Pooled-5), six separate training runs (copies) with the reader scored 75.9 to 77.2."
            },
            {
              "at": 0.4616,
              "text": "Eight copies of the same model without the reader scored 73.0 to 74.7."
            },
            {
              "at": 0.6793,
              "text": "On average the reader is ahead by 2.67 points out of 100, in all 6 copies (seeds), at 3M (about 3 million learned numbers)."
            }
          ],
          "numbers": {
            "gain": 2.67,
            "held": 6040,
            "copies": 6
          },
          "labels": {
            "ege": "with Gemma: 75.9 to 77.2 (6 copies)",
            "b2": "without: 73.0 to 74.7 (8 copies)",
            "how": "2.67 averages six per-copy gaps, not range end minus range end."
          },
          "warning": "Caveat: this check missed its leak mark (next scene).",
          "chip": "tested",
          "chip_label": "3M size, 6 copies",
          "src": [
            "custom_io/results/39-pc-ege-confirm/RESULTS-EG2.md line 108 (EGE 6-seed confirm, seeds 202-207: mean +2.67, ahead 6, per seed +1.14 +2.70 +3.44 +2.63 +3.54 +2.57) [branch origin/claude/custom-reader-talker-4x309r]",
            "custom_io/results/39-pc-ege-confirm/EGE_s202..s207 and B2_s206, B2_s207; custom_io/results/33-pc-confirm-b2/B2_s200..s205 RESULT.json (pooled-5 recomputed: EGE 75.88-77.19, plain B2 73.00-74.74)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 line 31 (EGE +2.67, 6 of 6 seeds)",
            "architecture/TOKENS-EXPERIMENT-2026-10-09.md line 26 and line 44 (EGE 6 seeds 75.88-77.19; plain B2 8 seeds 73.00-74.74)",
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md line 18"
          ],
          "notes": "Re-added from the raw RESULT.json files: pooled-5 = (correct over in_dist, answer, frame, vocab, variant) / 6,040. EGE seeds 202-207: 75.88, 76.72, 77.07, 77.10, 77.19, 76.41 (range 75.88-77.19). Plain B2 seeds 200-207: 73.00, 74.27, 74.74, 74.02, 73.63, 74.47, 73.64, 73.84 (range 73.00-74.74, EIGHT copies; the six matching copies 202-207 range 73.63-74.74). The +2.67 is the source's own average of the six same-seed gaps (EGE minus plain B2 of the same seed), recomputed here as 2.671; it is not the difference of the two ranges. Disagreement (2) from the author is resolved: the top-level custom_io/results/RESULTS-EG2.md (lines 114-116) lists the 6-seed block as 'NOT JUDGED (seeds 202-207 missing)' because it was written before those files were in place; the six EGE result files and the judged block (39-pc-ege-confirm/RESULTS-EG2.md lines 106-112, and PASS-MARKS.md lines 839-845) are on origin/claude/custom-reader-talker-4x309r only (the other branches hold the plain B2 files of queue 33 but not the EGE files). That 6-copy confirm's verdict is FAIL on the leak mark only (marks 1-3 pass); shown in s14. The old on-screen warning '6-copy result files are not in this repo' is removed because it is no longer true and was repo jargon. Fixer edit: caption 1 now says the plain fact first (6,040 test questions kept aside) and gives the code name as a tag; an on-screen line says what 2.67 is: the source's mean of the six per-copy gaps (RESULTS-EG2.md line 108: mean +2.67, per_seed +1.14 +2.70 +3.44 +2.63 +3.54 +2.57), not range end minus range end. No new number is shown. Duration 41 to 45 for the extra words.",
          "atMap": [
            [
              0.0133,
              0.0171
            ],
            [
              0.337,
              0.4616
            ],
            [
              0.6607,
              0.6793
            ]
          ]
        },
        {
          "id": "s14",
          "duration": 38.5,
          "heading": "Caveats: the leak warning light",
          "caption": [
            {
              "at": 0.0156,
              "text": "A leak means some answers are right with zero rounds of thinking."
            },
            {
              "at": 0.1607,
              "text": "Averaged over 6 copies, the zero-round leak is 6.59. The pass mark, set in advance as the no-reader average plus 1.0, was 4.62. Missed."
            },
            {
              "at": 0.5337,
              "text": "On seed 200, on familiar questions, the reader version scored 18.09 with zero rounds; the same model without it, 1.40."
            },
            {
              "at": 0.8468,
              "text": "Copies without the reader leak on some seeds too, so the cause is not settled."
            }
          ],
          "numbers": {
            "leak": 6.59,
            "limit": 4.62,
            "ege": 18.09,
            "other": 1.4
          },
          "labels": {
            "leak": "6-copy average",
            "limit": "limit 4.62",
            "ege": "reader version",
            "other": "without reader",
            "seed": "seed 200, zero rounds"
          },
          "chip": "tested",
          "chip_label": "tested: leak mark missed",
          "src": [
            "custom_io/results/39-pc-ege-confirm/RESULTS-EG2.md line 111 (loops0_mean 6.59, plain_b2_loops0_mean 3.62, mark 4 False) and EGE-CONFIRM-ANALYSIS.json (6.593 and 3.615; limit = 3.615 + 1.0 = 4.615) [branch origin/claude/custom-reader-talker-4x309r]",
            "custom_io/results/RESULTS-EG2.md lines 11-12 (EGE s200 loops0 18.09; plain B2 1.40 on the same seeds) and custom_io/PASS-MARKS.md lines 343-344, 375 and 378 (B2V 1.40; EGE seed 201 4.49 vs plain 4.34; plain B2 6.76 on screen seed 101) and lines 839-845 (6-seed result: loops:0 6.59 vs 3.62 + 1.0; 'the cause is not settled'; 'a Gemma-reader claim should carry the leak-mark failure beside the +2.67')",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 line 31 (leak mean 6.59 against a limit of 4.62) and sec. 5 item 2 (lines 110-112, 18.09 vs 1.40) and item 4 (plain B2 included on some seeds)"
          ],
          "notes": "Raw files: EGE_s200 loops:0 in_dist = 246/1,360 = 18.09; B2V_s200 (plain B2 on the rented 5090, 40-egw-s200) = 19/1,360 = 1.40; queue-33 B2_s200 (PC) = 0/1,360 = 0.00, so '1.40' is the B2V copy the source compares against. Plain copies with a leak: B2_s201 10.81, B2_s207 11.91, B2_s203 5.66 (recomputed). The 2-copy screen also failed its variant and leak marks (RESULTS-EG2 EGE block). The 1.40 comparison is labelled 'the same model without it' (B2V = plain B2, same recipe, other machine). Chip changed from amber to green: these numbers are measured results; the open part (the cause) is said in the caption. 'Familiar questions' = the in_dist split (same templates as practice), 1,360 questions. Fixer edit: the 6-copy bar now starts 0.9 s before caption 2 appears and lands as it fades in, so the number never trails the caption that quotes 6.59.",
          "atMap": [
            [
              0.02,
              0.0156
            ],
            [
              0.17,
              0.1607
            ],
            [
              0.46,
              0.5337
            ],
            [
              0.74,
              0.8468
            ]
          ]
        },
        {
          "id": "s15",
          "duration": 19,
          "heading": "Open question: tokens instead of letters",
          "illustration": "picture only: the boxes show the idea, not a measured run",
          "caption": [
            {
              "at": 0.0316,
              "text": "A test called TK would let the thinker read one spot per token (word piece) instead of one per letter."
            },
            {
              "at": 0.4759,
              "text": "The code and a PC job file exist, but it has never been run, so there is no result. Letters or tokens is still undecided."
            }
          ],
          "chip": "untested",
          "chip_label": "built, never tested",
          "src": [
            "architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 1 and sec. 3 (the thinker alone reads one pooled spot per token; the letter reader still runs on every letter)",
            "custom_io/models/ledger.py lines 51-58, 141, 153-154, 295-298 (tok_think code and tok_spots) and custom_io/train.py lines 229-230 [branch learner-new-g2]",
            "custom_io/queue_local/8aTK-pc-3.txt and 8aTK-card.md (job files and card; start waits for a free PC gap and the project owner's go)",
            "branch origin/claude/8a-g-pc-results: only 8aG1d and 8aG1e results; no 8aTK result (checked 2026-10-10)",
            "big-run/PLAN.md line 182 (TK: 'built and reviewed but not run'); architecture/FINISHED-MODEL-2026-10-09.md sec. 6 lines 155-157 ('Letters or tokens is decided before the 30M freeze')"
          ],
          "notes": "Disagreement (3) resolved: TOKENS sec. 8 was written before any build; the code (tok_think, test_tok_think.py) and the queue files now exist, and no result file exists, so the amber 'built, never tested' chip is right. Cut rule: the removed 'Chapter 12 covers it' is replaced by a plain statement that stands alone. The earlier word-piece losses (3.1 and 5.4 points) are not shown. Fixer edit: caption 1 reworded (same facts) so its second line is not a single word; the two rows now carry the labels \"letters\" and \"tokens\". Duration 24 to 25 for the two labels.",
          "labels": {
            "letters": "letters",
            "tokens": "tokens"
          },
          "atMap": [
            [
              0.024,
              0.0316
            ],
            [
              0.498,
              0.4759
            ]
          ]
        },
        {
          "id": "s16",
          "duration": 25.5,
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
            {
              "at": 0.0235,
              "text": "The reader is borrowed and frozen. It reads the question once."
            },
            {
              "at": 0.2286,
              "text": "Each letter gets a meaning in context, plus a window of 4 letters each side."
            },
            {
              "at": 0.4896,
              "text": "Without the window, the Gemma version scored 5.0 and 2.5 out of 100 on cipher puzzles, in two copies."
            }
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 and sec. 5",
            "custom_io/results/RESULTS-EG2.md lines 120-121"
          ],
          "notes": "Recap only; every number repeats an earlier scene (s09). Checker edit: 'falls to' became 'scored ... in two copies' to keep the strength of s09. Fixer edit: a green chip \"2 copies, one kind\" (same wording and status as s09) now sits under the \"No window\" card; the card row and the five-part map share their left and right edges; dimmed map labels are a darker grey. Duration 29 to 30 for the extra words.",
          "chip": "tested",
          "chip_label": "2 copies, one kind",
          "atMap": [
            [
              0.02,
              0.0235
            ],
            [
              0.3389,
              0.2286
            ],
            [
              0.6578,
              0.4896
            ]
          ]
        }
      ]
    },
    "ch04": {
      "kicker": "Part 3 of 10",
      "title": "The thinker: rounds of looking and passing notes",
      "blurb": "The thinker is the part that does the thinking. It works in rounds: it looks at the question, passes notes, and thinks again.",
      "accent": "thinker",
      "scenes": [
        {
          "id": "s01",
          "duration": 21.5,
          "heading": "Where we are: the thinker",
          "caption": [
            {
              "at": 0.0279,
              "text": "This is the thinker, the second part of the model. It does the thinking."
            },
            {
              "at": 0.3913,
              "text": "It is ours. It starts from scratch and learns only from our practice."
            },
            {
              "at": 0.6677,
              "text": "The planned size is about 100 million numbers. That size has never been tested."
            }
          ],
          "chip": "never tested at 100M",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 (about 100M planned) and sec. 2 (Thinker row: yes, from scratch; shape untested at 100M)"
          ],
          "labels": {
            "talker": "stand-in today"
          },
          "atMap": [
            [
              0.025,
              0.0279
            ],
            [
              0.3403,
              0.3913
            ],
            [
              0.6556,
              0.6677
            ]
          ]
        },
        {
          "id": "s02",
          "duration": 22,
          "heading": "Picture only: a team of note-takers",
          "caption": [
            {
              "at": 0.0273,
              "text": "Picture only. Think of a small team of note-takers sitting around one question."
            },
            {
              "at": 0.2974,
              "text": "Each round, every note-taker looks at the whole question again."
            },
            {
              "at": 0.5188,
              "text": "Then they pass notes to each other and write down what they now believe."
            },
            {
              "at": 0.8052,
              "text": "The same team, with the same habits, every round."
            }
          ],
          "tag": "picture only",
          "labels": {
            "q": "The question",
            "n": "Note-taker"
          },
          "src": [
            "kit/GLOSSARY.md (thinker row: the shared picture; no numbers)"
          ],
          "atMap": [
            [
              0.0222,
              0.0273
            ],
            [
              0.2602,
              0.2974
            ],
            [
              0.4981,
              0.5188
            ],
            [
              0.7361,
              0.8052
            ]
          ]
        },
        {
          "id": "s03",
          "duration": 24.5,
          "heading": "Vectors: 8 control, 36 memory",
          "caption": [
            {
              "at": 0.0245,
              "text": "A vector is a list of numbers, like a note card with a row of numbers."
            },
            {
              "at": 0.3146,
              "text": "The thinker keeps 8 control vectors. Two of them steer the work."
            },
            {
              "at": 0.5426,
              "text": "It also keeps 36 memory vectors, where its notes are kept."
            },
            {
              "at": 0.7561,
              "text": "Older builds had 17 vectors: 8 control and 9 memory."
            }
          ],
          "chip": "never tested at 100M",
          "labels": {
            "ctrl": "8 control vectors",
            "mem": "36 memory vectors",
            "old": "Older build: 8 + 9 = 17",
            "steer": "These two steer the work"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Thinker row: 8 + 36 under the B3 caps; T1SDR and H1 had 8 + 9 = 17) and sec. 8 (44 vectors = 8 + 36)",
            "custom_io/g8a/caps_b3.json (n_reg 36) on origin/claude/project-thread-qtxfp4",
            "custom_io/models/ledger.py line 71 (N_CTRL 8), same branch",
            "custom_io/g8a/caps.py line 24 (TODAY n_reg 9, the older 17)",
            "architecture/model-deep-dive.html line 108 and no-hardcoding/INPUT-UNITS-2026-10-07.md line 37 (heads read only control 0 and control 1: two steer the work)"
          ],
          "tag": "shading is decoration",
          "atMap": [
            [
              0.0176,
              0.0245
            ],
            [
              0.2581,
              0.3146
            ],
            [
              0.4985,
              0.5426
            ],
            [
              0.739,
              0.7561
            ]
          ]
        },
        {
          "id": "s04",
          "duration": 23.5,
          "heading": "Tested version: control vector 0 drives the call writer",
          "caption": [
            {
              "at": 0.0255,
              "text": "In the tested version, after each round from round 2 on, the call writer reads control vector 0."
            },
            {
              "at": 0.3544,
              "text": "It either writes a request for the outside calculator, like sub 12 5, or writes nothing."
            },
            {
              "at": 0.7268,
              "text": "The numbers in the request are usually copied from the question or an earlier reply."
            }
          ],
          "chip": "tested in older design (3M, 6 copies)",
          "labels": {
            "c0": "Control vector 0",
            "cw": "Call writer",
            "slip": "sub 12 5",
            "none": "or nothing"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1, and sec. 2 (Call writer row: shown in T1SDR; Calculator row: T1SDR at 3M, 6 seeds)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 item 2 (tool.py:329-374 copies the numbers; calls need t >= 1, so none after round 1) and sec. 4 (span copy used for 98% of written operands)"
          ],
          "chip2": "new design: talker writes the call; never run",
          "atMap": [
            [
              0.0187,
              0.0255
            ],
            [
              0.3385,
              0.3544
            ],
            [
              0.6583,
              0.7268
            ]
          ]
        },
        {
          "id": "s05",
          "duration": 36,
          "heading": "Do controls 2 to 7 matter?",
          "caption": [
            {
              "at": 0.0167,
              "text": "Controls 2 to 7 feed no output. They only pass information along when the notes look at each other."
            },
            {
              "at": 0.2479,
              "text": "In an older build, switching them off at test time cost 1.6 points on the main test."
            },
            {
              "at": 0.4963,
              "text": "On the multi-step test they cost 7.8 points: 99.4 fell to 91.6."
            },
            {
              "at": 0.7483,
              "text": "Those numbers are one copy (seed 200). All six copies of that older design lost points, very unevenly."
            }
          ],
          "tag": "older design, 1 of 6 copies shown",
          "labels": {
            "on": "All controls on",
            "off": "Controls 2 to 7 off",
            "axis": "Multi-step test, points out of 100",
            "main": "Main test, points lost"
          },
          "values": {
            "on": 99.4,
            "off": 91.6,
            "mainLoss": 1.6
          },
          "src": [
            "architecture/model-deep-dive.html line 108 (zeroing controls 2-7: 1.6 on pooled-5, 7.8 on chains, 99.4 to 91.6, seed s200; older 17-vector design)",
            "no-hardcoding/D0-RESULT-2026-10-07.md table and line 20 (ctl27 on seeds 200-205: pooled-5 -1.62, -0.61, -0.78, -8.79, -0.81, -13.64; chain-5 -7.8, -0.6, -1.0, -30.8, -0.8, -36.9; every seed loses, very unevenly)",
            "no-hardcoding/INPUT-UNITS-2026-10-07.md line 37 (heads read only controls 0 and 1; 2-7 are scratch through attention)"
          ],
          "notes": "Seed 200 numbers: pooled-5 change -1.62 (shown as 1.6), chain-5 change -7.8, 99.4 to 91.6 (99.4 - 7.8 = 91.6). Six copies (seeds 200 to 205) all lost points, range -0.61 to -13.64 on pooled-5 and -0.6 to -36.9 on chain-5 (D0-RESULT table). The bars show only seed 200. Older B2 design, calculator inside, 17 vectors.",
          "atMap": [
            [
              0.0143,
              0.0167
            ],
            [
              0.2565,
              0.2479
            ],
            [
              0.4988,
              0.4963
            ],
            [
              0.7411,
              0.7483
            ]
          ]
        },
        {
          "id": "s06",
          "duration": 23.5,
          "heading": "Round step 1: look at everything",
          "caption": [
            {
              "at": 0.0255,
              "text": "Each letter of the question is one box. A borrowed reader, Gemma, has already given each letter its meaning."
            },
            {
              "at": 0.407,
              "text": "Each note vector looks at every letter. Later it also looks at each reply the whole reader has read."
            },
            {
              "at": 0.7511,
              "text": "The shading inside each note is a picture only, not real numbers."
            }
          ],
          "tag": "picture only",
          "labels": {
            "q": "Tom has 12 apples.",
            "look": "Look",
            "tv": "Tested version: replies were read by the letter window only. New design: the whole reader."
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Thinker row: every letter and every calculator reply) and sec. 3 item 1 (Gemma reads the question once)",
            "custom_io/models/ledger.py, class CBlock (cross-attention to the letters and replies)"
          ],
          "atMap": [
            [
              0.0214,
              0.0255
            ],
            [
              0.3393,
              0.407
            ],
            [
              0.6571,
              0.7511
            ]
          ]
        },
        {
          "id": "s07",
          "duration": 34,
          "heading": "Round steps 2 and 3: compare, then think",
          "caption": [
            {
              "at": 0.0176,
              "text": "Step 2: the note vectors look at each other. In code this is called self-attention."
            },
            {
              "at": 0.2134,
              "text": "Each note reads the other notes and keeps what matters from them."
            },
            {
              "at": 0.3777,
              "text": "The letters are not compared with each other inside the thinker."
            },
            {
              "at": 0.5315,
              "text": "Step 3: each note goes through a small network."
            },
            {
              "at": 0.6741,
              "text": "At the 100M step it widens to 4.8 times as many numbers, then squeezes back."
            },
            {
              "at": 0.8888,
              "text": "Then the notes go on to the next round."
            }
          ],
          "labels": {
            "compare": "Compare notes",
            "think": "Think: small network",
            "widen": "Widen 4.8 times",
            "q": "Tom has 12 apples.",
            "letters": "Letters are not compared"
          },
          "src": [
            "custom_io/models/ledger.py, class CBlock (self-attention; MLP with hidden = mlp x width)",
            "custom_io/g8a/configs.py line 37 on origin/claude/project-thread-qtxfp4 (100M rung: width 512, 8 heads, mlp 4.8, 21 blocks; the 30M rung uses mlp 6.0 at line 36)",
            "architecture/important-links-2026-10-09.md sec. 1, lines 12-14 (letters do not compare inside the thinker)",
            "architecture/running-summary-2026-10-08.md line 22 (notes talk to each other, then pass through an MLP)"
          ],
          "tag": "shading is decoration",
          "atMap": [
            [
              0.0143,
              0.0176
            ],
            [
              0.1758,
              0.2134
            ],
            [
              0.3373,
              0.3777
            ],
            [
              0.4988,
              0.5315
            ],
            [
              0.6603,
              0.6741
            ],
            [
              0.8218,
              0.8888
            ]
          ]
        },
        {
          "id": "s08",
          "duration": 21.5,
          "heading": "Same blocks, every round",
          "caption": [
            {
              "at": 0.0279,
              "text": "One look, compare and think unit is a block. The same blocks run in every round."
            },
            {
              "at": 0.3542,
              "text": "The learned numbers are the same in every round. Same team, same habits."
            },
            {
              "at": 0.6306,
              "text": "A round stamp, a learned tag for the round number, is added to the notes each round."
            }
          ],
          "chip": "older design ran this way",
          "tag": "round stamp",
          "src": [
            "custom_io/models/ledger.py, forward loop (the same self.core blocks each round; step_emb[t] added each round)",
            "custom_io/models/b3.py line 144 (B3 adds step_emb[ts] before each think)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Thinker row: same weights every round)"
          ],
          "labels": {
            "block": "Block"
          },
          "sketch": "picture only: 3 blocks drawn, not the real count",
          "atMap": [
            [
              0.0207,
              0.0279
            ],
            [
              0.3391,
              0.3542
            ],
            [
              0.6575,
              0.6306
            ]
          ]
        },
        {
          "id": "s09",
          "duration": 38.5,
          "heading": "Why some questions need several rounds",
          "caption": [
            {
              "at": 0.0156,
              "text": "Tested version. Tom has 12 apples, gives away 5, then buys 3. After round 2, the call writer writes sub 12 5."
            },
            {
              "at": 0.2861,
              "text": "It copies 12 and 5. The outside calculator replies 7. The reader reads it, and adds it to the notes."
            },
            {
              "at": 0.5054,
              "text": "Round 3 sees that reply. After it, the call writer writes add 7 3, and the calculator replies 10."
            },
            {
              "at": 0.7154,
              "text": "Today's stand-in talker copies 10; the planned one has no pointer. New design: the talker writes calls, and replies start the next turn."
            }
          ],
          "chip": "traced from code, never run as a whole",
          "labels": {
            "r2": "After round 2: sub 12 5",
            "r2r": "Reply: 7",
            "r3": "After round 3: add 7 3",
            "r3r": "Reply: 10",
            "ans": "Answer: 10",
            "reader": "Reader",
            "notes": "Added to the notes",
            "standin": "stand-in talker, today",
            "out": "outside calculator",
            "plan": "Today's talker is a stand-in. The planned talker reads the thinker's final thoughts and writes words, with no pointer.",
            "tv": "Tested design (call writer)"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 items 2-6 (tool.py:329-374, tool.py:155-170, tool.py:368-374)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 header (B3 group 1 changes are built but have never run)"
          ],
          "atMap": [
            [
              0.0133,
              0.0156
            ],
            [
              0.2561,
              0.2861
            ],
            [
              0.4989,
              0.5054
            ],
            [
              0.7417,
              0.7154
            ]
          ]
        },
        {
          "id": "s10",
          "duration": 23,
          "heading": "The bell: when to stop",
          "caption": [
            {
              "at": 0.0261,
              "text": "After each round, a tiny learned stop switch, the bell, asks: is this settled, or should it think more?"
            },
            {
              "at": 0.3776,
              "text": "It must think at least 1 round. It can never go past 32 rounds."
            },
            {
              "at": 0.6516,
              "text": "It learns from a settled label: stop once no later round would have been right."
            }
          ],
          "chip": "built, never run",
          "labels": {
            "min": "At least 1",
            "max": "At most 32",
            "bell": "The bell: learned stop switch"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Learned stop row) and sec. 3 item 5",
            "custom_io/models/tool_h1.py line 20 (at least 1 round, hard cap 32) and line 42 (CAP = 32)"
          ],
          "tag": "shading is decoration",
          "atMap": [
            [
              0.0194,
              0.0261
            ],
            [
              0.3387,
              0.3776
            ],
            [
              0.6581,
              0.6516
            ]
          ]
        },
        {
          "id": "s11",
          "duration": 27,
          "heading": "One block: 4,624,281 numbers",
          "caption": [
            {
              "at": 0.0222,
              "text": "A block is one look, compare and think unit, built from attention and a small network."
            },
            {
              "at": 0.282,
              "text": "Counting every learned number in one block, where each vector holds 512 numbers (its width), gives 4,624,281."
            },
            {
              "at": 0.5919,
              "text": "Our arithmetic: 21 blocks alone give 97.1 million. An older plan said 30 blocks, which would give about 139 million."
            }
          ],
          "chip": "our arithmetic",
          "labels": {
            "b21": "21 blocks",
            "b30": "30 blocks",
            "b30old": "older plan"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 9 (their count; 100M = 21 blocks at width 512)",
            "custom_io/models/ledger.py, class CBlock (layer sizes; we recounted by hand: 4,624,281 exactly at width 512, mlp 4.8)",
            "custom_io/g8a/configs.py line 37 on origin/claude/project-thread-qtxfp4 (100M rung: width 512, 8 heads, mlp 4.8, 21 blocks)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 8 table (big-run PLAN sec. 2, 6 said 'about 30 blocks, width 512'; true: about 21 blocks)"
          ],
          "notes": "Computed by hand: 21 x 4,624,281 = 97,109,901; 30 x 4,624,281 = 138,728,430. Per block: LayerNorms 4,096 + q 262,656 + kv 525,312 + o 262,656 + qkv 787,968 + p 262,656 + fc 1,260,441 + out 1,258,496.",
          "values": {
            "block": 4624281,
            "b21": 21,
            "b30": 30
          },
          "atMap": [
            [
              0.02,
              0.0222
            ],
            [
              0.3389,
              0.282
            ],
            [
              0.6578,
              0.5919
            ]
          ]
        },
        {
          "id": "s12",
          "duration": 29.5,
          "heading": "Four sizes, counted from the build",
          "caption": [
            {
              "at": 0.0203,
              "text": "The learned part of the model comes in four sizes, named 3M, 10M, 30M and 100M for their rough size."
            },
            {
              "at": 0.3184,
              "text": "These are counts from the build. The finished design (B3) has not been run at any of these sizes yet."
            },
            {
              "at": 0.6046,
              "text": "As built so far, without the planned talker, the whole model at the 100 million step is 373.1 million numbers, borrowed reader included."
            }
          ],
          "chip": "counted, never run",
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
            "animations/model-explainer-build/sources/pr-56-b3-group1-and-token-test.md line 15 (sizes at caps_b3, trained numbers) and line 17 ('Runs: none yet')",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 (373.1M whole at 100M; ladder 3M, 10M, 30M, 100M) and sec. 2 (271,002,624 frozen reader)"
          ],
          "notes": "Bars are trained numbers at caps_b3 (they include the Gemma adapter and the letter window, not only the thinker blocks). 102,116,618 + 271,002,624 = 373,119,242 = 373.1 million, which matches FINISHED sec. 1. The planned 25M talker is not built and is not in 373.1M.",
          "atMap": [
            [
              0.0162,
              0.0203
            ],
            [
              0.3378,
              0.3184
            ],
            [
              0.6595,
              0.6046
            ]
          ]
        },
        {
          "id": "s13",
          "duration": 45.5,
          "heading": "Long text: is the thinker cheap?",
          "caption": [
            {
              "at": 0.0132,
              "text": "An average question has 81 letters. Every letter against every letter: 81 times 81 is 6,561 checks."
            },
            {
              "at": 0.2819,
              "text": "Notes look at letters instead. A rough count: 44 notes, each looking at 81 letters and 27 number slots, gives 4,752 checks per round."
            },
            {
              "at": 0.5568,
              "text": "Over 8 rounds, the older count, that is 4,752 times 8 = 38,016. At 81 letters, no work is saved."
            },
            {
              "at": 0.8068,
              "text": "Its gain is structure, not speed. By this count, much longer text would favour the notes, but that is untested."
            }
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
          "notes": "Computed by hand: 81 x 81 = 6,561; 44 x (81 + 27) = 4,752; 4,752 x 8 = 38,016 (the source says about 38,000). The 27 slots and the 8 rounds belong to the older build (calculator inside); the source calls the whole thing a rough count, nothing was run.",
          "src": [
            "architecture/important-links-2026-10-09.md sec. 2, lines 22-24 (6,561; 4,752; about 38,000; at this length the thinker does not save work)",
            "architecture/important-links-2026-10-09.md sec. 1, lines 12-14 (letters do not compare inside the thinker)",
            "architecture/running-summary-2026-10-08.md line 48 (questions average 81 letters)"
          ],
          "atMap": [
            [
              0.014,
              0.0132
            ],
            [
              0.2564,
              0.2819
            ],
            [
              0.4988,
              0.5568
            ],
            [
              0.7413,
              0.8068
            ]
          ]
        },
        {
          "id": "s14",
          "duration": 30,
          "heading": "First test: thinking on, then off",
          "caption": [
            {
              "at": 0.02,
              "text": "In the first completed test (older design), one copy at the smallest size scored 73.01 points out of 100 on 6,040 kept-aside questions, thinking on."
            },
            {
              "at": 0.5478,
              "text": "With thinking switched off (zero rounds), the same copy scored 0.66 points."
            },
            {
              "at": 0.7691,
              "text": "That is one copy at one size. Part 8 explains the test and its checks."
            }
          ],
          "chip": "older design, not B3 (3M, one copy)",
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
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 2 and item 7 (that design had the calculator inside, 12 fixed rounds)",
            "origin/claude/8a-g-pc-results results/8a-g/pc/8aG1d-pc/8aG1d-3M-s400/B2/RESULT.json (pooled over the 5 panels: 4,410 of 6,040 = 73.01; lesion loops:0: 40 of 6,040 = 0.66; n_loops 12, eg_embed true)"
          ],
          "notes": "G1 3M seed 400, B2 arm (calculator inside, 12 fixed rounds, Gemma reader), 3,544,913 trained numbers: pooled over the 5 panels 4,410 of 6,040 = 73.01; with zero rounds (loops:0) 40 of 6,040 = 0.66. A second finished copy (3M seed 401: 4,450 of 6,040 = 73.68; zero rounds 0 of 6,040) is in the results branch dated Oct 10 but FINISHED-MODEL does not cite it yet, so it is not shown.",
          "atMap": [
            [
              0.0182,
              0.02
            ],
            [
              0.3384,
              0.5478
            ],
            [
              0.6586,
              0.7691
            ]
          ]
        },
        {
          "id": "s15",
          "duration": 35.5,
          "heading": "Not known yet, and what to remember",
          "caption": [
            {
              "at": 0.0169,
              "text": "Not known: the thinker has never been tested at 100 million numbers."
            },
            {
              "at": 0.1742,
              "text": "Not known: whether many rounds hurt. One older probe, on one seed, found 16 rounds cost 1.2 to 1.9 points."
            },
            {
              "at": 0.4382,
              "text": "Experts (many small specialist networks, a few used at a time) are a separate idea, not yet tested and not covered here."
            },
            {
              "at": 0.6961,
              "text": "Remember: the thinker looks, passes notes and thinks, in rounds. The same blocks run every round. A learned bell is built to say when to stop."
            }
          ],
          "chip": "bell: not tested yet",
          "labels": {
            "r": "Recap",
            "talker": "stand-in today"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (shape untested at 100M), sec. 5 item 13 (depth cost, open risk; the learned stop is meant to avoid it), sec. 5 item 10 (experts join only if both GX stages pass; no expert test has run on this thinker, EXPERTS-TEST-2026-10-09.md sec. 1)",
            "no-hardcoding/INPUT-UNITS-2026-10-07.md line 39 (16 rounds cost 1.2-1.9 points, 40-loops-probe, one seed; FINISHED cites line 31, which is the wrong line)"
          ],
          "atMap": [
            [
              0.0136,
              0.0169
            ],
            [
              0.2563,
              0.1742
            ],
            [
              0.4989,
              0.4382
            ],
            [
              0.7415,
              0.6961
            ]
          ]
        }
      ]
    },
    "ch05": {
      "kicker": "Part 4 of 10",
      "title": "Asking the calculator for help",
      "blurb": "The model can use an ordinary calculator, outside the model, for exact sums. In the new design (being built), the talker writes the call as plain text at the end of a turn, the calculator writes back plain text, and the whole reader reads the reply. The results here are from the tested version.",
      "accent": "call",
      "scenes": [
        {
          "id": "s01",
          "duration": 23.5,
          "heading": "Where we are: the calculator sits outside",
          "caption": [
            {
              "at": 0.0255,
              "text": "In the new design, the talker's line calls the calculator, an outside tool, at the end of a turn. The reply starts the next turn, and the whole reader reads it."
            },
            {
              "at": 0.552,
              "text": "Rule (project rules, Oct 7): hand-written code may run only as an outside tool that the model chooses to call."
            }
          ],
          "labels": {
            "chip": "new design: being built, not tested yet"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (parts table) and sec. 4 (rules dated 10-07)"
          ],
          "notes": "FIX PASS: call writer is now wired to the thinker (it reads its vector, s03) and to the calculator (it hands over the slip, s08); dimmed part labels darkened one step.",
          "atMap": [
            [
              0.0273,
              0.0255
            ],
            [
              0.4977,
              0.552
            ]
          ]
        },
        {
          "id": "s02",
          "duration": 20.5,
          "heading": "Why a calculator? Code adds exactly",
          "caption": [
            {
              "at": 0.0293,
              "text": "Code adds two numbers exactly, every time."
            },
            {
              "at": 0.3968,
              "text": "A learned network has to learn each sum from practice."
            },
            {
              "at": 0.6345,
              "text": "In the new design, the talker writes its sum on a text slip (made-up numbers here) and sends it to a calculator outside the model. The whole reader reads the reply."
            }
          ],
          "labels": {
            "slip": "call: sub 12 5",
            "back": "reply: 7",
            "calc": "calculator",
            "why": "our reasoning, not a measured result",
            "slipnote": "written by the talker, as text",
            "calcsub": "outside the model",
            "backnote": "comes back as text",
            "reader": "reader",
            "readersub": "whole reader reads it"
          },
          "src": [
            "GLOSSARY.md (call writer and calculator pictures)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (hand code only as a tool)"
          ],
          "notes": "The 'why' sentences are our reasoning and are labelled on screen.",
          "atMap": [
            [
              0.0231,
              0.0293
            ],
            [
              0.3397,
              0.3968
            ],
            [
              0.6564,
              0.6345
            ]
          ]
        },
        {
          "id": "s03",
          "duration": 20.5,
          "heading": "Tested version: after a round, the call writer reads one vector",
          "caption": [
            {
              "at": 0.0293,
              "text": "In the tested version, after a round (one lap of the thinker), the call writer reads the thinker's first control vector, a list of numbers."
            },
            {
              "at": 0.5282,
              "text": "It writes one of nine choices: no call, or one of the eight operations. The new design drops this call writer: the talker writes the call."
            }
          ],
          "labels": {
            "v0": "control vector 0",
            "none": "no call",
            "ops": "8 operations",
            "cw": "call writer",
            "pic": "picture only: the shading is decoration",
            "cwnote": "tested version only",
            "chip": "tested version, not the new design"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (call writer row)",
            "custom_io/models/tool.py:15 at 17a356e62 (op head on control token 0; NOOP = no call); call timing tool.py:338 (calls need t >= 1, i.e. after round 2)",
            "custom_io/models/progparse.py:11 (OPS list: NOOP plus 8 operations; at 17a356e62 and on the B3 branch)"
          ],
          "notes": "The code header calls control vector 0 'control token 0'. Same first vector. 'After a round' (not 'every round'): no call can follow round 1 (tool.py:338), see scene s09. Nine choices = NOOP plus 8 operations (progparse.py:11).",
          "atMap": [
            [
              0.0231,
              0.0293
            ],
            [
              0.4981,
              0.5282
            ]
          ]
        },
        {
          "id": "s04",
          "duration": 36.5,
          "heading": "The calculator's eight operations, one line each",
          "caption": [
            {
              "at": 0.0164,
              "text": "The outside calculator has eight operations, with made-up numbers 12 and 5. We worked out each result by hand; ? means the call cannot run."
            }
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
            "custom_io/models/progparse.py:11 (OPS) and :21-30 (ex: exact semantics; DIV only when exact)",
            "custom_io/models/tool.py:93-103 at 17a356e62 (calc: '?' when it cannot run)",
            "example results computed by hand from those lines, with made-up numbers 12 and 5"
          ],
          "notes": "12 divided by 5 is not whole, so div gives '?'. mod 12 5 = 2 because 12 = 2 x 5 + 2. cmp returns 1, 0 or -1 as in progparse ex. FIX PASS: caption now says that ? means the call cannot run (div 12 5 is not exact, tool.py:93-103); no result or claim changed. A no-break space keeps the ? with 'means'.",
          "atMap": [
            [
              0.0136,
              0.0164
            ]
          ]
        },
        {
          "id": "s05",
          "duration": 45,
          "heading": "Tested version: copying digits with a pointer, a step left, a stop",
          "question": "Tom has 12 apples. (made-up example)",
          "caption": [
            {
              "at": 0.0133,
              "text": "In the tested version, to write the 12 in a call, the call writer's learned pointer lands on its last digit, the 2."
            },
            {
              "at": 0.2248,
              "text": "The copy then steps one letter left and copies the 1."
            },
            {
              "at": 0.3742,
              "text": "A learned stop head says when to stop."
            },
            {
              "at": 0.5165,
              "text": "In the tested version, the copy trick was used for 98% of written operands and, by today's stand-in talker, for 91.5% of answers, on all six separate copies (T1SDR). The planned talker and the new design use no pointer or copying."
            },
            {
              "at": 0.8708,
              "text": "Copied here means the copy trick was used, not that the copy was right."
            }
          ],
          "labels": {
            "ptr": "pointer",
            "stop": "stop head",
            "out": "written last digit first",
            "chip": "tested version, 3 million learned numbers (3M)",
            "d2": "2",
            "d1": "1",
            "num": "12"
          },
          "bars": [
            {
              "label": "operands copied",
              "value": 98
            },
            {
              "label": "answers copied (stand-in talker)",
              "value": 91.5
            }
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 2 (lines 46-50): worked Tom example and copy rule",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (span copy row): 98% of written operands and 91.5% of answers on every T1SDR seed",
            "custom_io/models/tool.py:222-247 (span copy: one letter left until the learned stop head says stop)",
            "custom_io/results/70-vast-t1sdr/70-t1sdr-s200/T1SDR_s200/RESULT.json (also s201; 80-vast-t1sdr-confirm s204, s205; 80b-pc-t1sdr-confirm s202, s203), key extra.span_use: operand 98.0769 (1581 of 1612 operand sides), answer 91.5 (of 400 rows), identical on all six seeds; computed at custom_io/models/tool.py:659-689"
          ],
          "notes": "The 98% and 91.5% are shares of uses, not accuracy: free run on 400 test questions that use the calculator (the call-accuracy rows), 1,612 operand sides, of which 1,581 took the copy path (98.0769); 366 of 400 answers were in copy mode (91.5). The same values appear on all six seeds in the raw RESULT.json files (extra.span_use; computed at tool.py:659-689 at 17a356e62). FINISHED sec. 4 gives the same 98% and 91.5%. 3M: the T1SDR copies have 3,314,132 learned numbers (RESULT.json n_params). The start-of-text stop and the 40-letter ceiling are hand-written rules (see s11). 'Copies' = separate trainings of the same model (seeds 200-205). FIX PASS: last caption now reads 'Copied here means the copy trick was used, not that the copy was right', the same word as the bar labels; same claim as before (shares of use, not accuracy).",
          "atMap": [
            [
              0.0133,
              0.0133
            ],
            [
              0.2076,
              0.2248
            ],
            [
              0.4018,
              0.3742
            ],
            [
              0.596,
              0.5165
            ],
            [
              0.7902,
              0.8708
            ]
          ]
        },
        {
          "id": "s06",
          "duration": 25.5,
          "heading": "Call-writer builds: a number not in the text, 21 cells",
          "caption": [
            {
              "at": 0.0235,
              "text": "In the tested version, some call numbers are in neither the question nor a reply, and the call writer builds such a number one digit at a time."
            },
            {
              "at": 0.4855,
              "text": "Tested copies had 11 cells. The never-run build of the finished design has 21, last digit first; the code flips the text. The new design has no call writer."
            }
          ],
          "labels": {
            "cells": "21 cells: 20 for the longest 64-bit whole number, 1 for the end mark",
            "first": "0 goes in first, then 1",
            "z": "0",
            "o": "1",
            "end": "end",
            "chip": "built, never run",
            "pic": "picture only: 10 is a made-up number",
            "unused": "unused here"
          },
          "src": [
            "custom_io/models/tool.py:85 on origin/claude/project-thread-qtxfp4 (B3 group 1): CELLS = 21, comment: longest int64 string 20 characters, then end mark; was 11",
            "custom_io/models/tool.py:84 at 17a356e62 (T1SDR as tested): CELLS = 11 (up to 9 digits and a sign, then end mark); tool.py:40-41 (cells are for numbers the writer composes itself, e.g. a constant not in the text); tool.py:186-188 (decode_cells flips the text)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 2 (21 slots, last digit first) and sec. 4 (operand slots and last letter first rows)",
            "architecture/AUDIT-2026-10-09.md finding B13-13 (CELLS = 11, composed operand limited to 10 characters in T1SDR)",
            "custom_io/data.py (Vocab.decode: stops at the first EOS, so cells after the end mark are not read) on origin/claude/project-thread-qtxfp4"
          ],
          "notes": "CORRECTED. The first draft used the 10 in 'add 7 3 = 10' as the example of a number built in the cells, but that 10 is the calculator's reply, copied by the talker; in the Tom example no number is built in cells. The cells are for numbers the writer makes up itself (tool.py:40-41). The picture now shows a made-up 10 and says so. Also the 21-cell version is the B3 group 1 build (built, never run); the tested T1SDR copies had CELLS = 11 (tool.py:84 at 17a356e62). Both facts are now on screen. The 21 = 20 + 1 is the code comment's own sum. FIX PASS: '(B3 group 1)' removed from the caption (code name stays in src); the 18 cells after the end mark are dimmed and labelled 'unused here' (decode stops at the first end mark: custom_io/data.py Vocab.decode, and tool.py docstring 'up to the first EOS').",
          "atMap": [
            [
              0.0158,
              0.0235
            ],
            [
              0.4987,
              0.4855
            ]
          ]
        },
        {
          "id": "s07",
          "duration": 20.5,
          "heading": "The outside calculator: plain Python, no learned numbers",
          "caption": [
            {
              "at": 0.0293,
              "text": "The calculator is ordinary Python code, outside the model. It has 0 learned numbers."
            },
            {
              "at": 0.3366,
              "text": "In the new design, it reads a call (made-up numbers here) and writes the reply as text, which starts the next turn for the whole reader. A call it cannot run gets a question mark."
            }
          ],
          "labels": {
            "in": "call in: sub 12 5",
            "out": "reply out: 7",
            "in2": "call in: div 12 5",
            "out2": "reply out: ?",
            "calc": "calculator",
            "tag": "hand code, allowed as a tool",
            "calcsub": "outside the model",
            "frm": "from the talker, as text",
            "to": "to the whole reader, as text"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (calculator row: size 0)",
            "custom_io/models/tool.py:93-103 at 17a356e62 (calc)",
            "custom_io/models/progparse.py:21-30 (ex)"
          ],
          "notes": "FIX PASS: the picture now shows two calls through the same calculator: sub 12 5 gives 7, div 12 5 gives ? (labels in2/out2 replace 'bad'); the reply box no longer reads 7 for the div call.",
          "atMap": [
            [
              0.0214,
              0.0293
            ],
            [
              0.4982,
              0.3366
            ]
          ]
        },
        {
          "id": "s08",
          "duration": 37,
          "heading": "Tested version: the reply goes through the reader into the notes",
          "caption": [
            {
              "at": 0.0162,
              "text": "In the tested version, in our made-up Tom example, after round 2 the call writer writes sub 12 5 as text, and the outside calculator replies."
            },
            {
              "at": 0.3023,
              "text": "The reply, sub 12 5 = 7, comes back as text. In the tested version the reader's letter window reads it, and it is added to the notes. The new design uses the whole reader, Gemma plus the window."
            },
            {
              "at": 0.7139,
              "text": "The question is not read again. After round 3 the call writer writes add 7 3, and the calculator replies 10."
            }
          ],
          "labels": {
            "q": "question: not read again",
            "notes": "thinker's notes",
            "cw": "call writer",
            "calc": "calculator",
            "rd2": "after round 2",
            "rd3": "after round 3",
            "r1": "sub 12 5 = 7",
            "r2": "add 7 3 = 10",
            "cwsub": "tested version only",
            "calcsub": "outside the model",
            "reader": "reader",
            "readersub": "letter window (tested)",
            "newrd": "new design: whole reader, Gemma plus the window",
            "callTxt": "call, as text",
            "replyTxt": "reply, as text"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 steps 2-4 (lines 46-53): worked Tom example",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (letter window row) and sec. 5 item 5 (replies read by the letter window only)",
            "custom_io/models/tool.py:155-170, 368-374 (reply read as a short string; thinker keeps its vectors)"
          ],
          "notes": "Calls follow a round (call k follows round k + 1), so the second call is written after round 3, not in it (FINISHED sec. 3 step 4). The Tom numbers are the project's made-up example. 'Read by the letter window only, not by Gemma' is how B3 group 1 builds it (FINISHED sec. 5 item 5, suggested); not said on screen. FIX PASS: curved arrows now drawn on a layer above the notes card, so their arrowheads show; caption reworded so it wraps evenly ('the calculator replies 10').",
          "atMap": [
            [
              0.0143,
              0.0162
            ],
            [
              0.3373,
              0.3023
            ],
            [
              0.6603,
              0.7139
            ]
          ]
        },
        {
          "id": "s09",
          "duration": 24,
          "heading": "Timing in the tested version: calls follow rounds 2 to 8",
          "caption": [
            {
              "at": 0.025,
              "text": "In the tested version, the first call follows round 2."
            },
            {
              "at": 0.228,
              "text": "Call k follows round k plus 1, up to call 7 after round 8."
            },
            {
              "at": 0.5739,
              "text": "The tested copies ran 8 rounds. In the built learned-stop code, rounds 9 to 32 cannot call."
            }
          ],
          "labels": {
            "none": "rounds 9-32 (built code): no call",
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
            ],
            "chip2": "built, never run"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 60-62)",
            "custom_io/models/tool.py:338, 350 (call timing; no call after round 8 in the tested code)",
            "custom_io/models/tool.py at 17a356e62: :118 (n_loops=8 default), :326, :338 (1 <= t <= N_RES = 7), :350 (k = t - 1); architecture/FINISHED-MODEL-2026-10-09.md sec. 4 hand table (fixed rounds: 8 in T1SDR); the 32-round cap belongs to H1, built, never run (sec. 2 Learned stop row)"
          ],
          "notes": "CORRECTED. The first draft said 'rounds 9 to 32 cannot call' under a 'tested' chip. T1SDR ran a fixed 8 rounds, so rounds 9 to 32 only exist in the H1 learned-stop code, which has never run. Now said that way. Call k follows round k + 1: t = 1..7 in code is rounds 2..8. FIX PASS: amber 'built, never run' chip added under the 'rounds 9-32 (built code)' box (learned-stop code, built, never run: FINISHED sec. 2 Learned stop row).",
          "atMap": [
            [
              0.0158,
              0.025
            ],
            [
              0.3377,
              0.228
            ],
            [
              0.6596,
              0.5739
            ]
          ]
        },
        {
          "id": "s10",
          "duration": 26.5,
          "heading": "Built, not run: any round, and a tape of 16",
          "caption": [
            {
              "at": 0.0226,
              "text": "The project owner chose any time for when a call may follow."
            },
            {
              "at": 0.2334,
              "text": "The finished design's first build lets a call follow any round from 2 to 32."
            },
            {
              "at": 0.5024,
              "text": "The tape (the list of calls and replies so far) holds 16 calls."
            },
            {
              "at": 0.7267,
              "text": "In training, 1 row in 4 gets 0, 1 or 2 extra thinking rounds before each call."
            }
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
            "custom_io/models/b3.py:26 on origin/claude/project-thread-qtxfp4 tip 6ca0234 (TAPE_MIN = 16; line 23 at the PR #56 commit e070556ce5)",
            "custom_io/g8a/configs.py:95 on the same tip (B3_G1 gap_p=0.25; line 90 at e070556ce5)"
          ],
          "notes": "1 row in 4 is gap_p = 0.25 (configs.py:95); FINISHED sec. 3 says 'a quarter of the rows'. The tape of 4 filled slots is only a picture. FIX PASS: '(B3 group 1)' removed from the caption (code name stays in src); tape label and 'picture only' tag share one line above the slots.",
          "atMap": [
            [
              0.0154,
              0.0226
            ],
            [
              0.2571,
              0.2334
            ],
            [
              0.4987,
              0.5024
            ],
            [
              0.7404,
              0.7267
            ]
          ]
        },
        {
          "id": "s11",
          "duration": 30,
          "heading": "Still hand-written, and what build 2 changes",
          "caption": [
            {
              "at": 0.02,
              "text": "In the call-writer builds, some parts are still ordinary code a person wrote. Four of them are shown here in brown boxes."
            },
            {
              "at": 0.3252,
              "text": "The operation name comes from a fixed list of 8, so a new tool could not be called yet."
            },
            {
              "at": 0.5948,
              "text": "The finished design's second build writes the whole call as letters, operation name included."
            },
            {
              "at": 0.8048,
              "text": "It is built as code and has never run."
            }
          ],
          "labels": {
            "ops": "operation from a fixed list of 8",
            "num": "number finder (regex)",
            "copy": "copy rules: start, step left, stop",
            "flip": "last letter first, text flipped",
            "chip": "built, never run",
            "g2call": "sub 12 5",
            "pic": "picture only: example call"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (hand code table: op word, number finder, span copy rules, last letter first; group 2 row)",
            "custom_io/models/ledger.py:206 (number finder regex)",
            "custom_io/models/tool.py:188, 191-197, 222-247 (last letter first; span copy rules)",
            "reviews/pc-handoff-g2-2026-10-09.md and GROUP2-HANDOFF.md on origin/claude/learner-new-g2 (group 2 code built, CPU tests pass, never run on the PC as of Oct 9 evening)"
          ],
          "notes": "FINISHED sec. 4 lists more hand parts than the four shown (word splitter, 108-character list, worked steps, layout codes, operand slots). FIX PASS: '(B3 group 2)' and 'next build' replaced by 'second build' (heading 'build 2'); amber chip reads 'built, never run' like s06, s10 and s15; boxes spread across the width.",
          "atMap": [
            [
              0.0143,
              0.02
            ],
            [
              0.2565,
              0.3252
            ],
            [
              0.4988,
              0.5948
            ],
            [
              0.7411,
              0.8048
            ]
          ]
        },
        {
          "id": "s12",
          "duration": 41.5,
          "heading": "The evidence: tested version, 6 copies, calculator outside",
          "caption": [
            {
              "at": 0.0145,
              "text": "Each copy starts from its own random start."
            },
            {
              "at": 0.1724,
              "text": "The tested version, T1SDR, where the calculator is an outside tool, was compared with a similar model, B2, where the calculator is inside."
            },
            {
              "at": 0.4016,
              "text": "Pooled-5 (6,040 questions kept aside), T1SDR minus B2: plus 0.62; likely range minus 0.23 to plus 1.46."
            },
            {
              "at": 0.7878,
              "text": "No copy fell over 1.0 below B2. The range includes 0: no clear difference."
            }
          ],
          "labels": {
            "ob": "B2: calc inside",
            "out": "T1SDR: plus 0.62",
            "rng": "likely range",
            "chip": "tested version: 3M, 6 copies",
            "ticks": [
              "-1",
              "0",
              "1",
              "2"
            ],
            "axis": "points, T1SDR minus B2"
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
            "GLOSSARY.md (pooled-5: 6,040 kept-aside questions; chain-5: 1,000 multi-step questions)",
            "custom_io/results/RESULTS-T1SDR.md lines 50-72 (6-seed block and table; branch tip 611ed3f4f, first written at 54a12b0d0): per-seed pooled-5 difference +1.94/-0.15/+0.18/+0.89/+0.96/-0.12, chain-5 T1SDR 99.7/99.7/99.8/99.6/99.7/99.8, B2 99.4/99.6/99.6/99.5/99.6/99.7, tool off 0.0",
            "raw RESULT.json for T1SDR s200-s205 (see s05) and B2 (custom_io/results/33-pc-confirm-b2/B2_s200..s205): recomputed pooled-5 over 6,040 questions (in_dist 1360 + answer 1200 + frame 1360 + vocab 800 + variant 1320), mean difference 0.618, sd 0.806, 95% CI -0.23 to +1.46; chain-5 n = 1000; tool-off set n = 2085"
          ],
          "notes": "Record 13 is relayed, not rechecked; the numbers were rechecked here from the raw RESULT.json files of all twelve runs and match. CORRECTED: the first draft said 'all six copies were within 1.0 of B2'. The mark is one-sided (no copy more than 1.0 BELOW B2); copy A was +1.94 above. Now said that way. Added: the range crosses 0, so the result is 'no clear difference', not 'better' (FINISHED sec. 5 item 1: 'matched'). 'a similar model': T1SDR is B2 with the calculator outside plus copy fixes and drills (tool.py docstring), not a one-change twin. Tool off is 0.0 on five copies and 0.05 on copy D (rounds to 0.0), n = 2,085 questions per copy. The 6,040 count matches GLOSSARY.md and the raw files. FIX PASS: the chain-5 and calculator-off captions moved to the new scene s12b so each result has its own picture; labels 'likely range' and 'plus 0.62' added on the drawing.",
          "atMap": [
            [
              0.0171,
              0.0145
            ],
            [
              0.2579,
              0.1724
            ],
            [
              0.4986,
              0.4016
            ],
            [
              0.7393,
              0.7878
            ]
          ]
        },
        {
          "id": "s12b",
          "duration": 27.5,
          "heading": "More evidence: chain-5 and calculator off",
          "caption": [
            {
              "at": 0.0218,
              "text": "Chain-5, 1,000 multi-step questions: 99.6 to 99.8 with the calculator outside, mean 99.72. Inside: 99.4 to 99.7."
            },
            {
              "at": 0.6177,
              "text": "Calculator switched off: the 2,085 questions that need it score 0.0."
            }
          ],
          "labels": {
            "outside": "calculator outside",
            "inside": "calculator inside",
            "mean": "mean",
            "ticks": [
              "99.4",
              "99.6",
              "99.8"
            ],
            "axis": "score out of 100; bar spans the 6 copies",
            "off": "calculator off",
            "zero": "0.0",
            "offsub": "2,085 questions that need it",
            "chip": "tested version: 3M, 6 copies"
          },
          "chain": {
            "outLo": 99.6,
            "outHi": 99.8,
            "outMean": 99.72,
            "inLo": 99.4,
            "inHi": 99.7
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 1: chain-5 99.6-99.8 (mean 99.72; B2 99.4-99.7); with the calculator switched off program questions score 0.0",
            "architecture/MARKS-D0-T1-2026-10-07.md Record 13 (lines 198-205): chain-5 and tool off 0.0",
            "custom_io/results/RESULTS-T1SDR.md lines 50-72 (branch tip 611ed3f4f): chain-5 T1SDR 99.7/99.7/99.8/99.6/99.7/99.8, B2 99.4/99.6/99.6/99.5/99.6/99.7, tool off 0.0",
            "raw RESULT.json for T1SDR s200-s205 and B2 (custom_io/results/33-pc-confirm-b2/B2_s200..s205): chain5.intact n = 1000; extra.noexec.program_families n = 2085 (see s12 and verify.md)"
          ],
          "notes": "NEW SCENE (fix pass). The last two captions of s12 (chain-5 and calculator off) were moved here verbatim, and the picture now draws them. Chain-5 bars: the bar spans the lowest to highest of the six copies (T1SDR 99.6 to 99.8, B2 99.4 to 99.7, per-seed values in verify.md), the dot is the T1SDR mean 99.72. 'Score out of 100' = percent of the 1,000 chain-5 questions answered right (GLOSSARY: score). 0.0 = the 2,085 questions that need the calculator, with the calculator switched off, on all six copies (0.05 on one copy, rounds to 0.0). The axis range 99.3 to 99.9 is only the drawing scale.",
          "atMap": [
            [
              0.02,
              0.0218
            ],
            [
              0.4983,
              0.6177
            ]
          ]
        },
        {
          "id": "s13",
          "duration": 43,
          "heading": "Check 1: the swap test (tested version)",
          "caption": [
            {
              "at": 0.014,
              "text": "Swap test: add and sub are secretly swapped inside the calculator. The answer should follow the new reply."
            },
            {
              "at": 0.2646,
              "text": "Pass line: 99% or more of counted rows follow the swap. Rows with two possible sources are not counted."
            },
            {
              "at": 0.4616,
              "text": "Five copies: 99.28 to 99.87, all at 99 or more."
            },
            {
              "at": 0.6344,
              "text": "The run's own first reading was 97.1 to 97.6. Its scoring rule was corrected after the misses were studied."
            },
            {
              "at": 0.8701,
              "text": "The sixth copy's saved model was lost, so it is not scored."
            }
          ],
          "labels": {
            "pass": "pass line: 99",
            "lost": "copy F: not scored",
            "chip": "tested version: 5 of 6 copies"
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
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 1 (swap holds on 5 of 6 copies; checkpoint lost)",
            "architecture/MARKS-D0-T1-2026-10-07.md lines 190-196 (Amendment 12: unambiguous rows only, lower of two readings, fixed before the six-seed re-score); custom_io/PASS-MARKS.md line 777 (origin/claude/custom-reader-talker-4x309r): run's own text match 97.1-97.6; lines 772 and 830: seed 205 checkpoint lost; raw T1SDR RESULT.json extra.opswap.swap_match 97.47/97.23/97.11/97.34/97.23/97.59 (seeds 200-205); tool.py:25, 97-98 (opswap swaps add and sub)"
          ],
          "notes": "Copies A-F are seeds 200-205 in order (our labels). Seed 205 is F and is unscored. The 99% pass line is the Amendment 12 definition in the marks file: a row counts only if unambiguous (about 7% of rows were set aside), and each seed is scored by the LOWER of two readings. ADDED caveat: the run's own first reading (text match) was 97.1-97.6. Amendment 12 was ruled after the swap-miss breakdown was read (the marks file itself calls it a post-result scorer definition, bound in the stricter direction between its two corrected readings) and was fixed before the six-seed re-score. 'Lost': both stopped rented boxes were deleted at 10:38 AM ET Oct 9 (PASS-MARKS addendum 23). FIX PASS: pass line shortened so the chips sit below it, not beside it. Grey chip = no result exists for copy F on this check (checkpoint lost).",
          "atMap": [
            [
              0.0136,
              0.014
            ],
            [
              0.2077,
              0.2646
            ],
            [
              0.4018,
              0.4616
            ],
            [
              0.5959,
              0.6344
            ],
            [
              0.79,
              0.8701
            ]
          ]
        },
        {
          "id": "s14",
          "duration": 46,
          "heading": "Check 2: the leak test (tested version), missed then cleared",
          "caption": [
            {
              "at": 0.013,
              "text": "Leak check: swap in another question's thinking, then count answers still right, out of 100 (1,360 questions)."
            },
            {
              "at": 0.2501,
              "text": "Limit written down before the run: 5. Five of six copies read above it, from 5.07 to 5.59."
            },
            {
              "at": 0.4464,
              "text": "B2 (calculator inside) read 3.09 to 3.75 on the same check."
            },
            {
              "at": 0.6213,
              "text": "It failed the limit. The project owner cleared it on Oct 9; it is disclosed, not a clean pass."
            },
            {
              "at": 0.7971,
              "text": "Separate reading, zero rounds of thinking: one copy read 12.94, against 10.81 for B2."
            }
          ],
          "labels": {
            "lim": "limit: 5",
            "chip": "missed, then cleared by owner",
            "b2": "B2"
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
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (calculator row: leak mark cleared 8:21 AM ET 10-09)",
            "custom_io/models/tool.py:25-27 and custom_io/PASS-MARKS.md lines 462-464 (origin/claude/custom-reader-talker-4x309r): donor = another row's whole thinker output with the current question; loops:0 = no rounds",
            "raw RESULT.json lesions.donor.in_dist.exact (T1SDR s200-s205: 5.59/5.15/5.59/5.07/5.00/5.59, n = 1360 questions) and lesions.loops:0 (s201 12.94); B2 (33-pc-confirm-b2) donor 3.09-3.75, loops:0 s201 10.81"
          ],
          "notes": "Copies A-F are seeds 200-205 in order (our labels). The plotted bars are the DONOR read (another question's thinking swapped in), scored on 1,360 in-distribution questions; the loops:0 (zero rounds) read is the separate 12.94 on copy B (seed 201). CORRECTED: the first draft called the bars 'right answers with zero rounds' and called B2 'the plain model without the calculator'; B2 has the calculator INSIDE (GLOSSARY: plain model is a different thing). The limit is 5 (mark 4: both reads <= 5 on every seed). Five values are above 5; E is exactly 5.00, at the limit. Orange (warning) is used for the chip and bars because amber means built-never-tested. The 1,360 is the size of the in-distribution split (RESULT.json lesions.donor.in_dist.n); the score is the percent of those questions still answered right. FIX PASS: bars above the limit (A, B, C, D, F) stay orange; E (5.00, exactly at the limit) is grey; a B2 row (3.09 to 3.75, the caption's numbers) is drawn on the same axis; the last caption now says it is a separate reading (zero rounds), not another bar.",
          "b2": {
            "lo": 3.09,
            "hi": 3.75
          },
          "atMap": [
            [
              0.0133,
              0.013
            ],
            [
              0.2076,
              0.2501
            ],
            [
              0.4018,
              0.4464
            ],
            [
              0.596,
              0.6213
            ],
            [
              0.7902,
              0.7971
            ]
          ]
        },
        {
          "id": "s15",
          "duration": 31.5,
          "heading": "What is tested, and what is not",
          "caption": [
            {
              "at": 0.019,
              "text": "Tested version: the calculator outside the model, at 3M, over six copies (swap check on five; leak check cleared by the owner)."
            },
            {
              "at": 0.351,
              "text": "Never run together: the borrowed Gemma reader with the outside calculator."
            },
            {
              "at": 0.5177,
              "text": "Built, never run: calls at any round."
            },
            {
              "at": 0.6384,
              "text": "Remember: in the new design (being built), the talker's line calls the calculator and the whole reader reads the reply. The tested version used a copy trick, with a learned stop."
            }
          ],
          "labels": {
            "t": "tested version: calculator outside, 3M",
            "n": "built, never run: Gemma with calc",
            "b": "built, never run: any round",
            "rem1": "New design (being built): the talker's line calls the calculator.",
            "rem2": "Its reply starts the next turn; the whole reader reads it.",
            "rem3": "Tested version: a copy trick, with a learned stop, writes most numbers."
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (calculator row), sec. 5 item 6 (Gemma and calculator never run together), sec. 3 (any-round built, untested)",
            "architecture/MARKS-D0-T1-2026-10-07.md Record 13 (6 copies; mark 5 on 5)"
          ],
          "notes": "'Writes most numbers': 98% of written operands and 91.5% of answers took the copy path (s05); it is a share of uses, not a claim about digits or accuracy. FIX PASS: status chips stacked on top, divider, then the three remember lines below it; Gemma chip now says 'built, never run' (B3 group 1 joins them in code, never run: FINISHED sec. 5 item 6).",
          "atMap": [
            [
              0.0143,
              0.019
            ],
            [
              0.2565,
              0.351
            ],
            [
              0.4988,
              0.5177
            ],
            [
              0.7411,
              0.6384
            ]
          ]
        }
      ]
    },
    "ch06": {
      "kicker": "Part 5 of 10",
      "title": "Deciding when it is done",
      "blurb": "The model stops thinking on its own. A small learned switch looks after each round and decides whether the thinking is finished. This part is built, but it has never been run.",
      "accent": "stop",
      "scenes": [
        {
          "id": "s01",
          "duration": 20.5,
          "heading": "Where we are: the stop switch",
          "caption": [
            {
              "at": 0.0293,
              "text": "The model thinks in rounds, one lap at a time."
            },
            {
              "at": 0.5259,
              "text": "The stop switch decides when thinking stops."
            },
            {
              "at": 0.7425,
              "text": "It is built, but it has never been run."
            }
          ],
          "chip": "built, never tested",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 (one paragraph) and sec. 2 (Learned stop row, line 36: built, never run)"
          ],
          "atMap": [
            [
              0.0214,
              0.0293
            ],
            [
              0.3393,
              0.5259
            ],
            [
              0.6571,
              0.7425
            ]
          ]
        },
        {
          "id": "s02",
          "duration": 18.5,
          "heading": "The problem: a fixed dial is a guess",
          "caption": [
            {
              "at": 0.0324,
              "text": "The older design had a dial: the same number of rounds for every question, set by hand (12 in the tested model, 8 in another)."
            },
            {
              "at": 0.5873,
              "text": "Easy questions may need fewer rounds. Hard questions may need more."
            }
          ],
          "dial": "12 rounds, set by hand",
          "easy": "easy question",
          "hard": "hard question",
          "picture": "picture only: one fixed dial for every question",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (table row: fixed number of rounds, 8 in T1SDR, 12 in G1, line 94)",
            "results/8a-g/pc/8aG1d-pc/8aG1d-3M-s400/B2/RESULT.json config.cfg.n_loops = 12 (branch origin/claude/8a-g-pc-results)"
          ],
          "notes": "Easy-needs-fewer and hard-needs-more is the reason for the learned stop (framing, suggested); the evidence for it is on the next two scenes. Dial = number of rounds allowed (GLOSSARY).",
          "key": "1 square = 1 round",
          "atMap": [
            [
              0.02,
              0.0324
            ],
            [
              0.4983,
              0.5873
            ]
          ]
        },
        {
          "id": "s03",
          "duration": 29.5,
          "heading": "Evidence: fewer rounds scored lower",
          "caption": [
            {
              "at": 0.0203,
              "text": "We turned the dial down on one trained copy, with no new practice."
            },
            {
              "at": 0.2218,
              "text": "Points out of 100, on 6,040 questions kept aside (called pooled-5)."
            },
            {
              "at": 0.4895,
              "text": "Trained at 12 rounds it scored 73.01. With 2 rounds, 29.30. With 1 round, 20.00. With 0 rounds, 0.66."
            }
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
          "chip": "tested: older design, one copy, 3 million numbers",
          "note": "G1 size test, older design: calculator inside, 12 fixed rounds",
          "src": [
            "animations/source-g1-3m-s400.json G-B2 (full pooled5 73.01, right 4410 of 6040; by_thinking_rounds loops:0 0.66, loops:1 20.0, loops:2 29.3; trained_rounds 12)",
            "results/8a-g/pc/8aG1d-pc/8aG1d-3M-s400/B2/RESULT.json (branch origin/claude/8a-g-pc-results): final_eval + lesions loops:0/1/2 summed over the five splits, recomputed by the checker: 4410, 40, 1208, 1770 of 6040",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 2 (73.01 with thinker on, 0.66 with it off, 3M seed 400)"
          ],
          "notes": "Points are scores out of 100 (right / 6,040 x 100): 4410/6040 = 73.01, 1770/6040 = 29.30, 1208/6040 = 20.00, 40/6040 = 0.66. The 0 to 2 round rows are the same trained copy with its dial turned down (loops:K), no new practice. 3M = about 3 million learned numbers (3,544,913 in this run). Bars are all indigo (thinker rounds); purple would wrongly suggest a stop switch, and G1 has none.",
          "atMap": [
            [
              0.0176,
              0.0203
            ],
            [
              0.3382,
              0.2218
            ],
            [
              0.6588,
              0.4895
            ]
          ]
        },
        {
          "id": "s04",
          "duration": 30.5,
          "heading": "Multi-step questions needed more rounds",
          "caption": [
            {
              "at": 0.0197,
              "text": "Chain-5 is a set of 1,000 multi-step questions, scored on the same trained copy."
            },
            {
              "at": 0.3094,
              "text": "On pooled-5, 1 round scored 20.00. On chain-5 it scored 0.0, and 1.1 at 2 rounds."
            },
            {
              "at": 0.6306,
              "text": "At the full 12 rounds chain-5 scored 99.9. So this copy needed more rounds on multi-step questions than on pooled-5."
            }
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
              "label": "12 rounds (trained)",
              "value": 99.9
            }
          ],
          "chip": "tested: older design, one copy, 3 million numbers",
          "note": "chain-5 score out of 100, same older design",
          "src": [
            "animations/source-g1-3m-s400.json G-B2 chain5 (loops:0 0.0, loops:1 0.0, loops:2 1.1, intact 99.9); by_thinking_rounds loops:1 20.0 (pooled-5)",
            "results/8a-g/pc/8aG1d-pc/8aG1d-3M-s400/B2/RESULT.json chain5 (branch origin/claude/8a-g-pc-results): n = 1000 for every row; intact 99.9 (999 of 1000), loops:1 0.0, loops:2 1.1 (11 of 1000), loops:0 0.0"
          ],
          "notes": "The source file's key for the full setting is 'intact' (no lesion = the 12 trained rounds; loops:24 also gives 99.9). The raw RESULT.json shows chain-5 has 1,000 questions, so the count is stated. 'Needed more rounds' is read from one trained copy; the heading says needed, not need. Older B2 copies (q33) show the same shape: chain-5 2.2 to 3.0 at 1 round (fast-slow-2026-10-08.md line 18).",
          "atMap": [
            [
              0.0171,
              0.0197
            ],
            [
              0.3381,
              0.3094
            ],
            [
              0.659,
              0.6306
            ]
          ]
        },
        {
          "id": "s05",
          "duration": 26,
          "heading": "Too many rounds can cost points",
          "caption": [
            {
              "at": 0.0231,
              "text": "Older models were trained for 8 rounds. In a round-count test on two copies, the score on practice-like questions stopped rising at 8 rounds."
            },
            {
              "at": 0.4655,
              "text": "On all 8 copies we checked (those two and six more), running 16 rounds scored 0.8 to 1.9 points lower than 8 rounds."
            },
            {
              "at": 0.8314,
              "text": "So too few rounds hurt, and too many may hurt too."
            }
          ],
          "big": "0.8 to 1.9 points lower",
          "eight": "8 rounds: score stops rising",
          "sixteen": "16 rounds: lower",
          "chip": "tested: older design, 8 copies",
          "src": [
            "custom_io/results/40-loops-probe/PROBE.json M1 (branch origin/claude/custom-reader-talker-4x309r): B2 seeds 100 and 101, in_dist at 8 / 16 rounds = 89.35 / 88.21 and 90.53 / 89.68; flat from 8 to 9 rounds",
            "custom_io/results/33-pc-confirm-b2/B2_s200..s205/RESULT.json (same branch): in_dist at the trained 8 rounds vs lesions loops:16 = 90.51/88.60, 91.54/89.93, 89.78/88.38, 91.03/89.26, 89.63/88.82, 90.66/89.41; RESULTS-EG2.md line 29 gives -1.91 and -1.62 for seeds 200 and 201",
            "no-hardcoding/INPUT-UNITS-2026-10-07.md line 39 and architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 13 (line 149): 'one probe, 1.2-1.9' (the raw files show 8 copies and 0.8 to 1.9; see notes)",
            "architecture/fast-slow-2026-10-08.md line 21 (1.6 to 1.9 worse, q33 seeds)"
          ],
          "notes": "CHECKER CHANGE. FINISHED item 13 and INPUT-UNITS line 39 say 'one probe/one seed, 1.2-1.9'; fast-slow says '1.6 to 1.9'. The raw files give 16 rounds minus 8 rounds on in_dist of -1.15 and -0.85 (probe seeds 100, 101) and -1.91, -1.62, -1.40, -1.76, -0.81, -1.25 (q33 seeds 200 to 205): all 8 copies lower, range 0.81 to 1.91. So the screen says 0.8 to 1.9 and 'all 8 copies'. 'Stopped rising at 8' is from the two probe copies only. All are older B2 copies (trained at 8 rounds, calculator inside, about 3.3 million numbers); the finished model runs up to 32 rounds with a learned stop.",
          "atMap": [
            [
              0.0171,
              0.0231
            ],
            [
              0.3381,
              0.4655
            ],
            [
              0.659,
              0.8314
            ]
          ]
        },
        {
          "id": "s06",
          "duration": 31,
          "heading": "After each round, a small head says stop or go",
          "caption": [
            {
              "at": 0.0194,
              "text": "After every round, the stop switch, a small head, reads one of the thinker's note cards."
            },
            {
              "at": 0.259,
              "text": "It gives a number from 0 to 1. At 0.5 or more, the thinking stops."
            },
            {
              "at": 0.4737,
              "text": "It always runs at least 1 round, and never more than 32."
            },
            {
              "at": 0.6539,
              "text": "The stop switch has 257 numbers when each card has 256, and 513 when each has 512."
            }
          ],
          "thinker": "Thinker",
          "head": "Stop switch",
          "line": "0.5 = stop line",
          "picture": "picture only: the meter is not a real run",
          "chip": "built, never tested",
          "src": [
            "custom_io/models/tool_h1.py (branch origin/claude/project-thread-qtxfp4) line 10 (stop = Linear(d,1), 257 params, on ln_z(control 1)), lines 42-44 (CAP = 32, P_STOP = 0.5)",
            "custom_io/models/tool_h1.py lines 19-21 (run rule: first round with sigmoid >= 0.5, at least 1 round, cap 32)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Learned stop row, line 36: width + 1, 257 at 256, 513 at 512, never run)"
          ],
          "notes": "The stop head reads control vector 1 only (one note card), not all the thinker's notes; the caption says one card. Width = numbers per note card; 256 at the 3M size, 512 at the 100M size (FINISHED sec. 2 thinker row).",
          "atMap": [
            [
              0.0158,
              0.0194
            ],
            [
              0.2572,
              0.259
            ],
            [
              0.4987,
              0.4737
            ],
            [
              0.7401,
              0.6539
            ]
          ]
        },
        {
          "id": "s07",
          "duration": 22,
          "heading": "One stop for the whole answer",
          "caption": [
            {
              "at": 0.0273,
              "text": "Built version: one stop for the whole answer. New design: one stop per turn."
            },
            {
              "at": 0.3136,
              "text": "Built version, not tested: the thinker may call an outside calculator, from round 2 up to 32."
            },
            {
              "at": 0.6487,
              "text": "Built code: about a quarter of questions add 0 to 2 rounds before a call. New design: the talker writes calls."
            }
          ],
          "round": "built version: rounds (10 of 32 shown)",
          "call": "call",
          "bell": "stop",
          "picture": "made-up example: no real run",
          "chip": "built, never tested",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 60-66: calls inside the thinking; one stop for the whole answer)",
            "architecture/B3-GROUP1-BUILD-2026-10-09.md sec. 3 (lines 53-54: gap_p 0.25, gaps g in {0,1,2}; line 104: B3_G1 config gap_p 0.25)",
            "custom_io/models/tool_h1.py lines 5-21 and custom_io/models/b3.py lines 6-12 (branch origin/claude/project-thread-qtxfp4): one stop per turn; any_round; gap_p"
          ],
          "notes": "'Round 2' follows FINISHED sec. 3 (code index t = round - 1, calls need t >= 1). b3.py and B3-GROUP1-BUILD write 'after any round t >= 1' with the 0-based t, so they agree. The 'gap_p = 0.25' default is 'suggested, fixed now, not tuned' (B3-GROUP1-BUILD line 53).",
          "atMap": [
            [
              0.0187,
              0.0273
            ],
            [
              0.3385,
              0.3136
            ],
            [
              0.6583,
              0.6487
            ]
          ]
        },
        {
          "id": "s08",
          "duration": 20.5,
          "heading": "How it is taught: the settled label",
          "caption": [
            {
              "at": 0.0293,
              "text": "Training gives every round a label: stop, or keep going."
            },
            {
              "at": 0.3635,
              "text": "The label says stop when the answer is right now, or when no later round is right."
            },
            {
              "at": 0.7231,
              "text": "So the stop switch is also taught to stop on questions it cannot solve."
            }
          ],
          "rowA": "made-up question A: first right at round 4",
          "rowB": "made-up question B: never right",
          "go": "go",
          "stop": "stop",
          "picture": "made-up example: no real run",
          "chip": "built, never tested",
          "src": [
            "custom_io/models/tool_h1.py lines 52-57 (def settled: label = right now, or no later round is right; branch origin/claude/project-thread-qtxfp4)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 item 5 (lines 54-56)"
          ],
          "atMap": [
            [
              0.0194,
              0.0293
            ],
            [
              0.3387,
              0.3635
            ],
            [
              0.6581,
              0.7231
            ]
          ]
        },
        {
          "id": "s09",
          "duration": 26,
          "heading": "The fix: count the label only in full batches",
          "caption": [
            {
              "at": 0.0231,
              "text": "Practice uses batches of questions, and some batches run only 8 rounds. There, a question first right at round 10 looks never right."
            },
            {
              "at": 0.408,
              "text": "So the label says stop at round 1, and the stop switch would learn to stop too early."
            },
            {
              "at": 0.7053,
              "text": "Fix: the stop switch learns only from batches that run all 32 rounds, about 1 in 4."
            }
          ],
          "short": "8-round batch: not counted",
          "full": "32-round batch (12 of 32 shown): counted",
          "go": "go",
          "stop": "stop",
          "picture": "made-up example: no real run",
          "chip": "built, never tested",
          "src": [
            "custom_io/models/tool_h1.py lines 13-16 and line 237 (w_stop = 1.0 if label == 'right' or n >= cap else 0.0; branch origin/claude/project-thread-qtxfp4, commit 8fce7247a8): a batch of n < 32 rounds cannot see later rounds; stop loss counted only when n >= 32, about 1 batch in 4, about half of all trained rounds",
            "big-run/PLAN.md Amendment 1:25 PM ET (audit B13-2; allowed before any B3 run; line 238): 'a row that is right only after round n looked settled at every earlier round and taught the head to stop early'; no run has happened"
          ],
          "notes": "The made-up question (first right at round 10) is an illustration of the mechanism, not a stop round from any real question. The PLAN says no H1R or B3 run has happened, so the head never actually learned the early stop: the caption says 'would learn'. Batches draw K from {4, 8, 16, 32} (tool_h1.py lines 22-24), so 1 in 4 is the 32 draw.",
          "atMap": [
            [
              0.0154,
              0.0231
            ],
            [
              0.3376,
              0.408
            ],
            [
              0.6598,
              0.7053
            ]
          ]
        },
        {
          "id": "s10",
          "duration": 23.5,
          "heading": "The risk: a stop that fires too early",
          "caption": [
            {
              "at": 0.0255,
              "text": "The label only sees the rounds a question actually ran."
            },
            {
              "at": 0.2808,
              "text": "So a stop that fires early may never be shown a later right answer (suggested)."
            },
            {
              "at": 0.5651,
              "text": "The first run is planned to report how often questions stop early, and their answers. This is reported only, not a pass mark."
            }
          ],
          "chip": "first run planned",
          "ran": "made-up example: rounds it ran",
          "go": "go",
          "stop": "stop",
          "unseen": "later rounds: never seen",
          "early": "early stop",
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 66-69: risk, suggested; B3 3M readout reports it)",
            "big-run/PLAN.md addendum 12:25 PM ET (line 232: early-stop share and the answers on those rows are reported, not gated); Amendment 1:25 PM ET (line 238: it stays reporting-only)"
          ],
          "atMap": [
            [
              0.0187,
              0.0255
            ],
            [
              0.3385,
              0.2808
            ],
            [
              0.6583,
              0.5651
            ]
          ]
        },
        {
          "id": "s11",
          "duration": 39,
          "heading": "How it will be judged: marks set in advance",
          "caption": [
            {
              "at": 0.0154,
              "text": "Key pass marks (bars the test must reach) were written before any run. They are targets, not results."
            },
            {
              "at": 0.2136,
              "text": "On average, 1-step questions must use at most half the rounds of the longest ones (code: 11 steps; plan: 12)."
            },
            {
              "at": 0.4582,
              "text": "Always-32 is the same model forced to think all 32 rounds. Practised questions: within 1 point. Longer chains: within 2."
            },
            {
              "at": 0.7296,
              "text": "It fails if it never stops early (rounds within 10% of 32), or if longer chains fall over 5 below always-32."
            }
          ],
          "barA": "1-step questions: rounds (target)",
          "barB": "longest questions: rounds (target)",
          "ruleA": "at most half of the longest",
          "target": "target, not a result",
          "chip": "plan only",
          "src": [
            "big-run/PLAN.md sec. 5 row 5 (line 76: practised within 1, longer chains within 2 of always-32, rounds on 1-step <= half those on 12-step, fails if it never stops early)",
            "big-run/PLAN.md B3-4 (line 228: average rounds on 1-step at most half those on 12-step; longer chains within 2 of the loops:32 lesion; proved wrong if average rounds are within 10% of the cap of 32 on every family, or longer chains are more than 5 below the lesion)",
            "big-run/PLAN.md sec. 5 note (b) (line 236: n_res is 11 under caps_b3, so read '12-step' as 11-step)",
            "whole-model-roadmap/whole-model-roadmap-2026-10-06.md line 508 (row 2d: practised skills within 1 point; held-out longer chains within 2 of always-32; 1-step average rounds at most half those on 12-step ones; never stops early = average rounds within 10% of the cap)"
          ],
          "notes": "The PLAN does not state the unit of 'within 1'; the roadmap row 2d says 'within 1 point'. The same model with the stop ignored is the loops:32 lesion (free, no extra training). 'Always-32' is PLAN row 5 and roadmap wording. 'Practised within 1 point' is in PLAN row 5 and roadmap 2d only; B3-4 restates the 1-step-half and longer-chains-within-2 marks and adds the more-than-5 fail line, so the caption says 'some of the pass marks'. Dashed bars are empty on purpose: no result exists.",
          "atMap": [
            [
              0.0133,
              0.0154
            ],
            [
              0.2561,
              0.2136
            ],
            [
              0.4989,
              0.4582
            ],
            [
              0.7417,
              0.7296
            ]
          ]
        },
        {
          "id": "s12",
          "duration": 32,
          "heading": "If it fails: no build switch removes the stop",
          "caption": [
            {
              "at": 0.0187,
              "text": "No build switch removes the stop. The switches cover things like Gemma and calls, not the stop."
            },
            {
              "at": 0.2491,
              "text": "A trained copy can still be run with the stop ignored and a forced number of rounds, as a test."
            },
            {
              "at": 0.5129,
              "text": "The nearest model with no stop is the outside-calculator model (T1SDR), with a fixed 8 rounds."
            },
            {
              "at": 0.7537,
              "text": "The stop has never run. Its first run is planned after the separate G1 size test finishes (not covered here)."
            }
          ],
          "chip": "built, never tested",
          "sw1": "switch: borrowed reader (Gemma)",
          "sw2": "switch: calls at any round",
          "noSw": "stop: no switch",
          "fallback": "no stop: T1SDR, fixed 8 rounds",
          "src": [
            "custom_io/models/b3.py docstring lines 1-17 (switches: eg_embed, any_round, no_slots, tok_think; the stop is part of H1R; branch origin/claude/project-thread-qtxfp4)",
            "custom_io/models/tool_h1.py line 25 (loops:K = exactly K rounds with the stop head ignored) and big-run/PLAN.md line 228 (loops:32, a free lesion, no extra training)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (line 94: fixed rounds, 8 in T1SDR, 12 in G1) and sec. 2 (line 36: first run after G1)"
          ],
          "notes": "The brief said the stop can only be removed by running T1SDR. The code shows no stop switch at build time; H1R is T1SDR plus the learned stop (b3.py docstring line 1). At test time a copy can be run with the stop ignored (loops:K). T1SDR is named here as the nearest model without a stop. No source found calls it the fallback, so the video does not say that. G1 is a separate size test (not covered in this video); the first B3 run is planned after it, a plan and not a date.",
          "atMap": [
            [
              0.0136,
              0.0187
            ],
            [
              0.2563,
              0.2491
            ],
            [
              0.4989,
              0.5129
            ],
            [
              0.7415,
              0.7537
            ]
          ]
        },
        {
          "id": "s13",
          "duration": 31.5,
          "heading": "Fast and slow: one thinker, not two",
          "caption": [
            {
              "at": 0.019,
              "text": "People talk about fast thinking and slow thinking. Few rounds is like the fast kind, many rounds like the slow kind."
            },
            {
              "at": 0.3517,
              "text": "We suggest one looped thinker gives both, so no separate fast and slow model is needed (suggested, not tested)."
            },
            {
              "at": 0.6221,
              "text": "To remember: the stop switch decides, the limit is 32 rounds, and the stop is built but not yet run."
            }
          ],
          "one": "one looped thinker",
          "fast": "fast: few rounds",
          "slow": "slow: many rounds",
          "chip": "idea (suggested)",
          "src": [
            "architecture/fast-slow-2026-10-08.md sec. 1 (short answer, suggested) and sec. 5 (no new test proposed)",
            "custom_io/models/tool_h1.py lines 42-44 (cap 32, stop line 0.5; branch origin/claude/project-thread-qtxfp4)"
          ],
          "recapA": "the stop switch decides",
          "recapB": "limit: 32 rounds",
          "atMap": [
            [
              0.0167,
              0.019
            ],
            [
              0.338,
              0.3517
            ],
            [
              0.6593,
              0.6221
            ]
          ]
        }
      ]
    },
    "ch07": {
      "kicker": "Part 6 of 10",
      "title": "Writing down the answer",
      "blurb": "The plan: the talker reads the thinker's final thoughts and writes each turn's line, calls and answer, in words, with no pointer. Today it is a small stand-in. The talker that writes English is a placeholder.",
      "accent": "talker",
      "scenes": [
        {
          "id": "s01",
          "duration": 26,
          "heading": "Where we are: the talker writes the answer",
          "caption": [
            {
              "at": 0.0231,
              "text": "This is the last part inside the model: the talker."
            },
            {
              "at": 0.2104,
              "text": "Its only job is to write each turn's last line. It adds no thinking."
            },
            {
              "at": 0.4527,
              "text": "New design, untested: thoughts in, calls and answer out. No pointer."
            },
            {
              "at": 0.6712,
              "text": "Today's talker is a small stand-in. It also copies from the question and the notes, where the thinker points."
            }
          ],
          "labels": {
            "question": "the question",
            "replies": "the notes, with the calculator's replies",
            "state": "thinker's final state (picture only)",
            "points": "thoughts in",
            "talker": "Talker",
            "talkerSub": "adds no thinking",
            "answer": "answer",
            "ten": "10",
            "tag": "made-up example",
            "chip": "small stand-in, tested inside the model",
            "today": "today's stand-in only"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 Talker row (line 38): writes only the final answer from the thinker's final state; today a small stand-in",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 (lines 19-20): talker copies exact names and digits where the thinker points, adds no thinking of its own",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 4 (line 115): may copy from the question and the calculator replies, only where the thinker points",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 6 (line 57): the 10 copied from the last reply (made-up Tom example)"
          ],
          "notes": "The talker's input is the thinker's final state, NOT 'notes' (ch09 s07 labelled the talker box 'notes'; FINISHED sec. 5 item 4 says the notebook memory is not read by the talker). BUILDER PLAN: modelMap highlight talker at y 215 h 150. Below: left two small cards (question, replies) at x 100; thinker-state S.vec top middle (x ~620,y 470); Talker box pink x 900 y 540 w 380 h 150; answer box x 1440 w 300 with big pink 10; soft arrows question->talker, replies->talker; a thinker-coloured arrow state->talker labelled points; chip 'made-up example' near answer; placeholder chip label 'small stand-in today' under the talker at the last caption. CHECKER: chip changed from grey placeholder to green tested (\"small stand-in, tested inside the model\"): the stand-in exists and ran in the six T1SDR 3M runs (grey means does not exist). The shaded state vector is now labelled \"(picture only)\". The made-up tag moved above the answer box to make room.",
          "atMap": [
            [
              0.02,
              0.0231
            ],
            [
              0.2,
              0.2104
            ],
            [
              0.38,
              0.4527
            ],
            [
              0.6,
              0.6712
            ]
          ]
        },
        {
          "id": "s02",
          "duration": 29,
          "heading": "Today's stand-in: three ways to write",
          "caption": [
            {
              "at": 0.0207,
              "text": "Today's talker is a small stand-in with three ways to write an answer."
            },
            {
              "at": 0.2256,
              "text": "Span copy takes a stretch of letters from the question or the notes."
            },
            {
              "at": 0.4383,
              "text": "A word pointer, a learned pick of a spot, takes one whole word from the question."
            },
            {
              "at": 0.6802,
              "text": "Letter slots spell the answer when it is not in the text. The planned talker has no pointer."
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
          "notes": "All three examples are made up (picture only). Word pointer: tool.py answers() copies word w of the row's prompt, found by a hand-written word splitter (FINISHED sec. 4 table, tool.py:411). BUILDER PLAN: three cards x 100/686/1272, y 230, w 546, h 400 (title pink 48px bold; below it from-text mono 36px, an arrow drawn after the cards, and the result in a pink-edged box). Cards appear on captions 1-3; the 'gone' S.note at y 690 w 1720 appears about 0.72; tag chip placeholder 'made-up examples' at x 100 y 770. CHECKER: caption 3 now explains \"pointer\" in half a sentence (first use in the chapter). Checked tool.py @17a356e62: answers() lines 406-418, row_gold() 426-446 (span mode only when the answer is a number token of the context; WORD rows copy a word of the prompt; yes/no and unmatched answers are letter slots, ledger.py doc line 26).",
          "atMap": [
            [
              0.02,
              0.0207
            ],
            [
              0.23,
              0.2256
            ],
            [
              0.43,
              0.4383
            ],
            [
              0.62,
              0.6802
            ]
          ]
        },
        {
          "id": "s03",
          "duration": 28.5,
          "heading": "Today's stand-in, span copy: a pointer, a step left, a stop",
          "caption": [
            {
              "at": 0.0211,
              "text": "In today's stand-in, a pointer lands on the last digit of the last reply: the 0."
            },
            {
              "at": 0.2672,
              "text": "The copy steps one letter left and takes the 1."
            },
            {
              "at": 0.4381,
              "text": "Next to the left is a space. A small learned part, the stop head, says stop."
            },
            {
              "at": 0.6842,
              "text": "The digits came out last first, 0 then 1. Plain code flips them to read 10. The plan has no pointer."
            }
          ],
          "labels": {
            "reply1": "sub 12 5 = 7",
            "reply2": "add 7 3 = 10",
            "tagEarlier": "earlier reply",
            "tagLast": "last reply",
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
          "notes": "The strings are made-up example replies (picture only). In the T1S docstring the answer pointer reads control vector 1 while the call writer reads vector 0 (tool.py line 41); the video only says 'the thinker's final state'. BUILDER PLAN (copy ch05 s05): two letter rows from S.letters at x 170: reply1 at y 215 size 60 (dim, soft colour), reply2 at y 330 size 80. Pointer box (thinker colour) under index 11 (the 0); tint cells pale pink (#F9C5DA). Output boxes at x 1250 and 1370, y 330 for 0 then 1; stop head box (stop purple) pulses; last caption: final big 10 pops, then the two chips (learned = blue, hand = brown) at y 600/670. CHECKER: caption 3 now names the stop head as \"a small learned part\". Learned = pointer, copy gate, stop head (custom-io/audit-2026-10-09/FINISHED-fixes.md line 26); the one-letter-left step, the 40-letter ceiling and the flip are code. FIXER: tags \"earlier reply\" and \"last reply\" name the two lines the caption talks about; scene 40 -> 42 s for the 4 words.",
          "atMap": [
            [
              0.02,
              0.0211
            ],
            [
              0.23,
              0.2672
            ],
            [
              0.4,
              0.4381
            ],
            [
              0.58,
              0.6842
            ]
          ]
        },
        {
          "id": "s04",
          "duration": 35,
          "heading": "Stand-in span copy: how often, what is hand-written",
          "caption": [
            {
              "at": 0.0171,
              "text": "In the tested version, in all 6 copies of the 3-million-number model with an outside calculator (T1SDR), the stand-in's span copy wrote 91.5% of answers."
            },
            {
              "at": 0.4098,
              "text": "That counts how often it was used on 400 familiar calculator questions, not how often it was right."
            },
            {
              "at": 0.6306,
              "text": "The stand-in's pointer and stop head are learned. Three small pieces are hand-written code."
            },
            {
              "at": 0.8106,
              "text": "The plan: one learned writer, for calls and answers, replaces them. Not run."
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
            "chip": "tested at 3M, 6 copies",
            "barNote": "share of uses, not accuracy; both from the tested version",
            "hand": [
              "step one letter left",
              "split text into words",
              "flip last-first text"
            ],
            "handChip": "hand-written",
            "plan": "one learned writer: calls and answers",
            "planChip": "plan only, not run"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 table 'Span copy rules' (line 96): used for 98% of written operands and 91.5% of answers on every T1SDR seed; replaced by O1, the one learned writer",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 table 'Word splitter' (line 90) and 'Last letter first' (line 98)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (lines 84-86): B3 group 2 build started 12:15 PM ET 10-09, code only, its 3M run waits for G1",
            "animations/model-explainer-build/chapters-out/ch05/ch05.json s05 notes: shares of uses, not accuracy",
            "custom_io/results/70-vast-t1sdr/70-t1sdr-s200/T1SDR_s200/RESULT.json extra.span_use = {operand 98.0769, answer 91.5, n_sides 1612, n_rows 400}; the same four numbers in 70-t1sdr-s201, 80-t1sdr-s204, 80-t1sdr-s205, 80b-pc T1SDR_s202 and T1SDR_s203 (branch origin/claude/custom-reader-talker-4x309r); n_params 3,314,132, 24,000 updates",
            "custom_io/models/tool.py @17a356e62 lines 650-689: span_use is measured on 400 in-distribution dev rows that have worked steps (subsample(prows, 400)), free run; \"answer\" = share of those rows where the mode head picked span copy (lmode argmax = 0); \"operand\" = share of 1,612 written call numbers that took the span path",
            "custom-io/audit-2026-10-09/FINISHED-fixes.md line 26: \"Used for 98.08% of written operands and 91.5% of answers on every seed (span_use)\""
          ],
          "notes": "Shares of uses, not scores. FINISHED sec. 4 is the only source found; the raw per-seed file was not located (same as ch05). No talker-only test exists; the T1SDR runs are the 3M runs where the calculator outside matched B2 over 6 copies (sec. 5 item 1). BUILDER PLAN: left, S.hbars (two rows, suf %, dec 1/0, x 100 y 250 w 600) + chip tested at y 480; right, three brown S.box (hand code) stacked at x 1000..1800, y 230/330/430, arrow to a grey box 'one learned writer' (placeholder colour) at y 570 with chip 'plan only, not run'. CHECKER: SCOPE ADDED: the 91.5 is over 400 familiar (in-distribution) test questions that use the calculator, not over all answers, and is identical on all six seeds (366 of 400). The 98 is 98.08 rounded as in FINISHED sec. 4 (98%). Neither is accuracy. \"Three small pieces\" = the three hand-made answer printers named in B3-GROUP2-BUILD sec. 0 (copy a number backwards, slice a word, fill reversed letter slots); layout/position codes on the copy keys are a further hand part not drawn here. FIXER: heading now says \"hand-written\" like the chips.",
          "atMap": [
            [
              0.02,
              0.0171
            ],
            [
              0.24,
              0.4098
            ],
            [
              0.44,
              0.6306
            ],
            [
              0.64,
              0.8106
            ]
          ]
        },
        {
          "id": "s05",
          "duration": 24.5,
          "heading": "Today's letter slots: spelling an answer",
          "caption": [
            {
              "at": 0.0245,
              "text": "When the answer is not in the text, today's stand-in spells it in letter slots."
            },
            {
              "at": 0.2962,
              "text": "Today there are 9 places: room for 8 letters and an end mark. Each place picks a letter, or copies one."
            },
            {
              "at": 0.6554,
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
            "custom_io/models/ledger.py lines 62-63 @17a356e62 (lines 71-72 on qtxfp4): N_REG = 9; GEN_MAX = N_REG - 1 (8 chars + EOS)",
            "custom_io/models/tool.py @17a356e62 line 417 (letter answer decoded then reversed: out.append(self.vocab.decode(gen_ids[i])[::-1])) and docstring lines 19-20 (GEN pointer-generator copies from the prompt and the entries)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 table 'Last letter first' (line 98)"
          ],
          "notes": "'yes' is a made-up answer. Each slot is a pointer-generator: vocabulary readout or copy attention over the context letters. BUILDER PLAN: nine slot boxes (x 160 + i*104, y 330, 90x110, label empty), 8 plain + the 9th labelled 'end' tinted purple-ish soft; fill slots 0..2 with s, e, y then the end mark in slot 3 on captions 2-3 (pop). Then flip: a new mono word 'yes' types out in a pink box below with the flip note. Tag chip placeholder 'made-up answer'. Empty slots 4-7 stay empty/pale. CHECKER: caption 2 now says \"Today\" (B3 under caps_b3 has 36 places, 35 letters; see s06). \"yes\" example fits ledger.py line 26 (\"yes/no and unmatched answers are GEN\").",
          "atMap": [
            [
              0.02,
              0.0245
            ],
            [
              0.22,
              0.2962
            ],
            [
              0.48,
              0.6554
            ]
          ]
        },
        {
          "id": "s06",
          "duration": 38,
          "heading": "The 8-letter limit, and the 35-letter path",
          "caption": [
            {
              "at": 0.0158,
              "text": "Today's letter slots hold 8 letters. A longer training answer would be cut to 8."
            },
            {
              "at": 0.2146,
              "text": "That never happened: 0 of 200,000 training answers were longer than 8."
            },
            {
              "at": 0.3759,
              "text": "But hiding a word of 9 to 12 letters, in fill-in-the-blank practice, would hit it."
            },
            {
              "at": 0.5511,
              "text": "The finished design (B3) writes up to 35 letters and counts any longer answer."
            },
            {
              "at": 0.7168,
              "text": "A count above 0 fails its pass mark, set in advance. Blanks of 9 to 12 letters are safe only here."
            }
          ],
          "labels": {
            "word": "umbrellas",
            "cutLabel": "cut off",
            "tag": "made-up word",
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
            "end": "end",
            "zeroOf": "0 of",
            "chipCount": "counted"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (lines 79-82): T1SDR and H1 hold 8 answer letters; tool.py:510 cuts a longer non-drill training answer to 8; 0 of 200,000 training answers over 8 (FINISHED-fixes.md lines 5 and 37: sk200k train.jsonl, 200,000 rows, 0 over 8); data.py:109 refuses longer ones; B3 under caps_b3 writes up to 35 letters and counts a longer answer (gen_answer_over); a run with any count above 0 fails its sealed mark; blanks of 9-12 letters safe only on the caps path",
            "custom_io/models/tool.py @17a356e62 line 510 (ans[:GEN_MAX][::-1]) and custom_io/data.py @17a356e62 line 109 (assert answer length <= MAX_ANS)",
            "custom_io/g8a/caps_b3.json (max_ans 35) and custom_io/capcount.py:17 (gen_answer_over)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 11 (lines 140-145): blanks of 3-12 letters; 9-12 need the 35-letter path",
            "custom_io/models/tool.py on origin/claude/project-thread-qtxfp4 lines 555-557: capcount.hit(\"gen_answer_over\") is called and the target is then still clipped to GEN_MAX (35 under caps_b3, cap_audit.py line 40: GEN_MAX = n_reg - 1, caps_b3.json n_reg 36); capcount.py line 17 says \"the register targets are cut\""
          ],
          "notes": "'umbrellas' (9 letters) is a made-up word that shows what a cut would do (the last letter is lost); picture only. The 0-of-200,000 count is for T1SDR runs. B3 group 1 is built, never run. BUILDER PLAN: top, nine boxes: first 8 hold u,m,b,r,e,l,l,a and a 9th red-outlined box 's' that gets a 'cut off' tag and fades to dim; middle, big counting '0 of 200,000' text (S.count to 200000 with comma, then fixed '0 of'); bottom, two bars 8 vs 35 letters (S.bar scaled to 35, labels), chips tested/untested: 'shown in the code' (use hand-neutral chip), 'built, never run' amber. Caption 5 text note: sealed mark rule shown as S.note. CHECKER: FIXED: the old caption said B3 counts longer answers \"never cutting them\". The code counts AND still cuts (tool.py:555-557 on qtxfp4, capcount.py:17); FINISHED sec. 4 only says \"counts a longer answer\". Also \"sealed mark\" is now \"pass mark, set in advance\", B3 is introduced as \"the finished design (B3)\", and fill-in-the-blank is explained at first use because this scene comes before s10. Removed unused label \"zero\" (\"0 of\" and the counting number are drawn from zeroOf and the count to 200,000). Scene length 45 s (audit cap). FIXER: the 0 of 200,000 is a COUNT over the T1SDR training file (FINISHED sec. 4 line 80; FINISHED-fixes.md lines 5 and 37), not a plan, so it carries the green chip \"counted\". \"in the code\" chip and the \"today\" bar are brown (hand-written), not grey. Caption 2 starts at 0.17 so the 0.18 contact-sheet frame misses the caption cross-fade. Scene is at the 109-word cap for 45 s.",
          "atMap": [
            [
              0.02,
              0.0158
            ],
            [
              0.17,
              0.2146
            ],
            [
              0.31,
              0.3759
            ],
            [
              0.47,
              0.5511
            ],
            [
              0.63,
              0.7168
            ]
          ]
        },
        {
          "id": "s07",
          "duration": 35,
          "heading": "The planned English talker is not built",
          "caption": [
            {
              "at": 0.0171,
              "text": "The plan's talker, about 25 million numbers (25M), reads the thinker's final thoughts and writes English, with no pointer."
            },
            {
              "at": 0.2482,
              "text": "It is not built. As built, the 100M-thinker design is 373.1M in all: 271.0M borrowed, frozen reader (Gemma) plus 102.1M trained."
            },
            {
              "at": 0.7213,
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
                "label": "trained: thinker and small parts",
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
            "big-run/PLAN.md line 28 (about 373M whole as built: 271.0M Gemma + 102.1M trained thinker and heads, about 398M with a 25M talker added), line 150 and line 274 (same figures)"
          ],
          "notes": "The 25M talker is a plan; its bar is drawn grey and outlined only. The 373.1M total does not include it. The planned total is quoted as 397M in FINISHED sec. 1 and 398M in PLAN line 148 (different thinker sizes); the video avoids the planned total. BUILDER PLAN: stacked horizontal strip, widths proportional to 271.0 : 102.1 : 25 across 1500 px (x 160, y 330, h 110): teal, indigo, grey (placeholder fill, outline). Counting labels under each (S.count dec 1, suffix M). Bracket/arrow over the first two parts counting to 373.1M; placeholder chip over the grey part. Note at y 640 appears with caption 3. CHECKER: caption 2 now says the figure is the 100M-thinker design as built (B3 group 1 at the 100M rung, FINISHED sec. 1 lines 21-23); 271,002,624 = 271.0M; 271.0 + 102.1 = 373.1. \"M\" explained at first use; Gemma named as the borrowed reader. Bar label \"trained thinker and heads\" -> \"trained: thinker and small parts\" (102.1M includes the Gemma adapter and the letter window, FINISHED line 22). FIXER: 30 px gap before the dashed 25M box (not part of the to-scale widths); bracket ends at the 102.1M block.",
          "atMap": [
            [
              0.02,
              0.0171
            ],
            [
              0.25,
              0.2482
            ],
            [
              0.5,
              0.7213
            ]
          ]
        },
        {
          "id": "s08",
          "duration": 34.5,
          "heading": "Older tests of talking English",
          "caption": [
            {
              "at": 0.0174,
              "text": "These tests are older, from a design built on borrowed language models. Not today's talker."
            },
            {
              "at": 0.2741,
              "text": "With a 350-million-number language model as reader and talker, our system scored 66.1. With 1.2 billion: 92.6."
            },
            {
              "at": 0.6088,
              "text": "A small copy talker scored 13.6 on question kinds it never practised. The language-model talker scored 78.2."
            }
          ],
          "labels": {
            "head": "older design, not today's talker",
            "unit": "points out of 100",
            "panelA": "350M language model as reader and talker",
            "rowsA": [
              {
                "label": "350M system",
                "value": 66.1
              },
              {
                "label": "1.2B system",
                "value": 92.6
              }
            ],
            "subA": "192 reworded questions, 6-run average",
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
            "subB": "384 questions of unpractised kinds, 6-run average",
            "chip": "tested, older design",
            "risk": "Talking English from scratch: not shown"
          },
          "src": [
            "notes/hearer-talker/RESULTS-SMALL-LM.md lines 8-16 (verdict table lines 10-11): 1.2B system 92.6% vs 350M system 66.1% (60.9-72.0) on the fresh in-family set FRESH-EN-R3 (192 questions), 6 paired seeds; both marks fail",
            "reader-talker-compare/RESULTS-CT.md lines 8-15: copy talker 13.6 vs allptr 78.2 on 384 unseen-kind questions (mean of 6 paired seeds); verdict FAILS",
            "architecture/redesign-ideas-2026-10-07.md sec. 6 (line 92): the same two pairs, quoted as earlier results",
            "big-run/PLAN.md line 141: \"Talking English from scratch | Not shown, the second big risk | 350M reader+talker 66.1 vs 92.6; copy talker unseen kinds 13.6 vs 78.2\"",
            "idea-swarm/raw/areas/talker.json lines 88, 93, 570, 1350: marks the copy talker as the old 1.2B line",
            "notes/hearer-talker/PASS-MARKS-SMALL-LM.md lines 12-13 (192 questions, seeds 0-5, 1.2B mean 92.6) and reader-talker-compare/armB-report.md line 38 (about 2M copy-and-gate talker)"
          ],
          "notes": "Two different pairs, two different tests. A: 350M language model used as both reader and talker vs the 1.2B system, exact-match % on 192 fresh questions in the same family. B: the roughly 2M-number copy-and-gate talker (span start/end pointers, a word head, a copy/word gate) vs the language-model talker ('allptr') on 384 questions of question kinds never practised. Both are the older 1.2B-reader line (separate from today's B2/T1SDR talker); the superseded banner on reader-talker-compare/verdict.md says do not act on its recommendation. Copy talker on practised kinds with generated wording scored 97.4 vs 99.7 (RESULTS-CT.md line 18); not shown on screen. PR #54 numbers are NOT used (only in the memory index). BUILDER PLAN: two hbars blocks (x 160/y 300 and y 560, w 640 labelW 360) revealed with captions 2 and 3; panel titles 36px; sub lines 32px soft; header chip tested label 'tested, older design' top right; risk text appears at about 0.62 in an amber/grey S.note. CHECKER: The 66.1 is the 350M SYSTEM (our trained core plus a 350M language model), not the bare 350M model (bare 350M scored 33.9 zero-shot and 50.0 8-shot, RESULTS-SMALL-LM.md line 12); rows renamed 350M system / 1.2B system. 192 questions = FRESH-EN-R3, practised kinds in human wording (RESULTS-CT.md line 19), so \"fresh\" was replaced by \"reworded\". 92.6 = mean of 6 round-4 seeds (PASS-MARKS-SMALL-LM.md line 13). PLAN line 141 quotes the same two pairs.",
          "atMap": [
            [
              0.02,
              0.0174
            ],
            [
              0.25,
              0.2741
            ],
            [
              0.5,
              0.6088
            ]
          ]
        },
        {
          "id": "s09",
          "duration": 36.5,
          "heading": "Could the talker answer alone?",
          "caption": [
            {
              "at": 0.0164,
              "text": "One check turned the thinking off on one trained copy at 3M. This is the older design: calculator inside, 12 rounds."
            },
            {
              "at": 0.2685,
              "text": "Thinking on scored 73.01. Thinking off scored 0.66, on 6,040 questions kept aside."
            },
            {
              "at": 0.5368,
              "text": "That hints the talker cannot answer alone. One copy is only a hint."
            },
            {
              "at": 0.7111,
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
            "chip": "tested: one copy, a hint only",
            "earlier": "18.09",
            "earlierLabel": "of 100, an earlier Gemma-reader copy, zero rounds, 1,360 familiar questions",
            "note": "Gemma's meaning also reaches the talker's copying step. Our rules allow it."
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 2 (lines 109-112): G1 3M seed 400: 73.01 thinker on, 0.66 thinker off; Gemma-reader arms do answer some questions with zero rounds (EGE 18.09 in-distribution on seed 200)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 items 3-4 (lines 113-119): Gemma also reaches the talker's copy keys, allowed; 'cannot' is not shown (suggested)",
            "animations/source-g1-3m-s400.json (recomputed from results/8a-g/pc/8aG1d-pc/8aG1d-3M-s400/B2/RESULT.json on origin/claude/8a-g-pc-results): final_eval summed over the 5 splits = 4,410 of 6,040 = 73.01; lesions loops:0 = 40 of 6,040 = 0.66; config n_loops 12, eg_embed true, n_params 3,544,913. Re-summed by the checker from the raw file: match",
            "custom_io/PASS-MARKS.md addendum 14 (line 344) and addendum 15 (line 375) on origin/claude/custom-reader-talker-4x309r; raw: custom_io/results/46-r0ege-s200/EGE_s200/RESULT.json lesions loops:0 in_dist 246 of 1,360 = 18.09 (seed 201: 61 of 1,360 = 4.49); config copy+eg_embed, n_params 3,500,881. (memory/gemma-reader-results.md was not found on this machine)"
          ],
          "notes": "Label this whole scene 'suggested', not shown. 73.01 and 0.66 are the older design (calculator inside, 12 fixed rounds), as ch06 s03 says. The 18.09 comes from a different earlier model (EGE, Gemma added before the letter window) on a familiar-question set, so it must NOT share a bar chart with the 6,040-question scores. No leak limit is quoted (4.62 vs 5 conflict between ch03 and ch05). BUILDER PLAN: left, two S.hbars (x 100, y 300, w 600) with unit text; chip 'suggested, one copy'; right, a card (x 1000 y 280 w 780 h 260) with big counting 18.09 (amber) and the small label; S.note for the Gemma copy-keys line at y 620. CHECKER: chip changed from amber to green tested: a result exists (G1 3M seed 400, 4,410 and 40 of 6,040); the wording says it is one copy and only a hint. Card border amber -> orange (warning) because the 18.09 is a caution, not an untested build. 18.09 is the in-distribution split only (1,360 questions) of a different, earlier model (EGE, seed 200), so it stays off the bar chart. \"copy keys\" replaced by \"copying step\". FIXER: note \"Allowed.\" -> \"Our rules allow it.\" (FINISHED sec. 5 item 3: allowed by the project owner's 10-08 rule on reader help). \"12 rounds\" is right for this copy: G1 seed 400 config n_loops = 12 (FINISHED sec. 5 item 7); the 8 rounds belong to T1SDR. Scene 44 -> 45 s for the 3 extra words.",
          "atMap": [
            [
              0.02,
              0.0164
            ],
            [
              0.26,
              0.2685
            ],
            [
              0.44,
              0.5368
            ],
            [
              0.6,
              0.7111
            ]
          ]
        },
        {
          "id": "s10",
          "duration": 27.5,
          "heading": "Web text teaches reading, not writing",
          "caption": [
            {
              "at": 0.0218,
              "text": "Free web text, called FineWeb-Edu, enters practice as fill-in-the-blank rows."
            },
            {
              "at": 0.2749,
              "text": "One word of 3 to 12 letters is hidden, and the model must name it."
            },
            {
              "at": 0.517,
              "text": "So this kind of practice teaches reading English, not writing it."
            },
            {
              "at": 0.7071,
              "text": "By plan, 84% of the practice text in the planned big training run is web text."
            }
          ],
          "labels": {
            "sentence": "The cat sat on the",
            "blank": "____",
            "fill": "mat",
            "tag": "made-up sentence",
            "range": "one word of 3 to 12 letters hidden",
            "chunk": "Chunk shown: up to 280 letters in the growth test (G1), up to 2,000 planned for the finished design",
            "web": "web text 84%",
            "own": "our own rows 16%",
            "chip": "plan only"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 11 (lines 140-145): FineWeb-Edu enters as fill-in-the-blank rows, one word of 3-12 letters blanked (custom_io/g8a/cloze.py:1-25), at most 280 letters in G1, up to 2,000 in B3's long-chunk pool; so the run teaches reading English, not writing it",
            "big-run/PLAN.md line 151 (and 275): about 2.5B word pieces seen, 16% our text and 84% FineWeb-Edu (roadmap sec. 1.2); data-pool/DATA-POOL-PLAN-2026-10-06.md line 11: web share 84% of the tokens for the 600M rung (suggested mix)",
            "architecture/redesign-ideas-2026-10-07.md sec. 6 (line 94): free human-written web text (FineWeb-Edu) approved for the bigger rungs",
            "custom_io/g8a/cloze.py @origin/claude/project-thread-qtxfp4 lines 1-18 and 21-22: rows made by a script, one word of 3..12 letters (WORD_MIN, WORD_MAX) blanked, chunk up to 280 characters"
          ],
          "notes": "The cat sentence is made up (picture only); the real rows use FineWeb-Edu chunks. The 84/16 split is a plan figure from PLAN line 149, measured in word pieces; 'our own rows' = rows made by our code generators plus the 171,940 TEACH rows (PLAN line 149). The web pool has a gate: it must not be used for training until protected-panel hashes are merged and checked (FINISHED sec. 5 item 12). BUILDER PLAN: left, big mono sentence 'The cat sat on the ____' (S.type) then 'mat' pops in the blank in pink; range tag below; right, chunk note and a two-part stacked bar 84/16 (S.card widths 84% and 16% of 700 px) with chip 'plan only' appearing with caption 4. CHECKER: \"the big run\" is now \"the planned big training run\" so the scene stands alone. The 84 is a plan share of word pieces seen, not a measurement. FIXER: web-text bar darker with a thicker outline. OPEN FOR CHECKER: caption 3 says \"the run\" without saying which; FINISHED sec. 5 item 11 states it as a design consequence, not a measured result.",
          "atMap": [
            [
              0.02,
              0.0218
            ],
            [
              0.22,
              0.2749
            ],
            [
              0.44,
              0.517
            ],
            [
              0.6,
              0.7071
            ]
          ]
        },
        {
          "id": "s11",
          "duration": 32.5,
          "heading": "What would have to be true to win the race",
          "caption": [
            {
              "at": 0.0185,
              "text": "The plan's final proof is a race against small public models, such as SmolLM2-360M."
            },
            {
              "at": 0.2877,
              "text": "To win, it must be ahead by at least 3 points on our own kept-aside tests, and ahead on a question set called bAbI."
            },
            {
              "at": 0.5915,
              "text": "The whole size is counted, borrowed numbers too. The race needs the English talker, which does not exist yet."
            }
          ],
          "labels": {
            "steps": [
              "English talker needed",
              "Race models of its size",
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
            "note": "Plan: the talker and the race are not expected by the Oct 31 results readout"
          },
          "src": [
            "big-run/PLAN.md line 79 (scorecard row 8): race ahead of SmolLM2-360M by >= +3 on our sealed sets and ahead on bAbI, whole size counted; untested; the race needs the open-English talker; line 142: \"Beating rivals ... Never run ... the final proof; needs the talker above\"",
            "big-run/PLAN.md line 288 (R4, the race): rivals SmolLM2-360M, LFM2-350M, Qwen3-0.6B, size class 350M to 600M, >= +3 on our sealed sets and ahead on bAbI, whole size counted",
            "big-run/PLAN.md line 89: Oct 31 readout; \"Not closable by then: 1c (talker), 8\"; line 45: 10-31 ladder readout"
          ],
          "notes": "Plan only, nothing run. The video does not say which size model races: PLAN row 8 races the 30M thinker model (about 301M whole as built) while FINISHED keeps the 100M thinker (373.1M whole as built). The Oct 31 date is a plan, stated as 'plan'. BUILDER PLAN: three step boxes left to right (x 160/700/1240, y 300, w 480, h 190) with arrows drawn between; chip under each; the first box pulses at caption 3; S.note with the Oct 31 line at y 620 appears about 0.7. CHECKER: \"sealed tests\" -> \"kept-aside tests\" (plain word). Step 2 \"same-size model\" -> \"models of its size\" (R4 rivals are the 350M-600M size class). Note box colour amber -> grey (it is a plan, not a built thing). FIXER: first box \"English talker built\" -> \"English talker needed\" (it sat above the grey chip \"not built\"); chips centred under their boxes. OPEN FOR CHECKER: the Oct 31 note says \"cannot\"; PLAN.md line 89 says \"Not closable by then\" and line 45 also lists a 30M race score at that readout.",
          "atMap": [
            [
              0.02,
              0.0185
            ],
            [
              0.24,
              0.2877
            ],
            [
              0.5,
              0.5915
            ]
          ]
        },
        {
          "id": "s12",
          "duration": 22,
          "heading": "What to remember about the talker",
          "caption": [
            {
              "at": 0.0273,
              "text": "The plan: thoughts in, calls and answer out, no pointer."
            },
            {
              "at": 0.2487,
              "text": "Today's stand-in copies by pointer. Tested only at 3M."
            },
            {
              "at": 0.4777,
              "text": "The English talker is a placeholder. Today's model gives short answers, not sentences."
            }
          ],
          "labels": {
            "cards": [
              "Writes calls and the answer",
              "Today: a small stand-in",
              "English talker: not built"
            ],
            "chips": [
              {
                "kind": "learned",
                "label": "stand-in pointer, stop head: learned"
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
          "notes": "The brief's recap said 'copy talker tested at small size'. No talker-only test exists; the stand-in ran inside T1SDR 3M runs, so the chip says 'ran in 3M tests, never alone'. BUILDER PLAN: three cards (x 100/686/1272, y 260, w 546, h 170, label 44px) appear one per caption; the four chips sit below in two rows (y 520 and 600) and appear with their card's caption (learned with card 1, tested and untested with card 2, placeholder with card 3). CHECKER: caption 3: \"The model cannot chat\" -> \"Today's model gives short answers, not sentences\" (redesign-ideas-2026-10-07.md sec. 6: \"does not produce sentences\"). FIXER: chip \"stand-in pointer, stop head: learned\" (the span copy's own pointer and stop head, FINISHED line 38, not the map's Thinker or Stop switch) sits under its card; unlit map boxes get darker text and 30 px sub-labels.",
          "atMap": [
            [
              0.02,
              0.0273
            ],
            [
              0.28,
              0.2487
            ],
            [
              0.5,
              0.4777
            ]
          ]
        }
      ]
    },
    "ch08": {
      "kicker": "Part 7 of 10",
      "title": "Practice, one small nudge at a time",
      "blurb": "How the model learns: it tries a question, is shown the right answer, and each learned setting moves a tiny bit. This part covers the practice loop, the data, the fairness rules and the cost.",
      "accent": "learned",
      "scenes": [
        {
          "id": "s01",
          "duration": 21.5,
          "heading": "Where we are: practice sets the numbers",
          "caption": [
            {
              "at": 0.0279,
              "text": "Practice sets the numbers inside the thinker, the stop switch (built, not yet run) and the talker (a small stand-in so far; in the new design it writes the calls)."
            },
            {
              "at": 0.6353,
              "text": "The borrowed reader stays frozen. The outside calculator is plain code and needs no practice."
            }
          ],
          "labels": {
            "reader": "frozen",
            "thinker": "learned",
            "calc": "outside tool",
            "stop": "built, never run",
            "talker": "learned stand-in"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 2 table (lines 29-38: reader borrowed and frozen; thinker, call writer, stop, talker learned; calculator hand code, allowed as a tool; line 36 stop 'built, never run'; line 38 talker 'today a small stand-in')",
            "kit/GLOSSARY.md (frozen, hand-written, learned)"
          ],
          "notes": "The stop switch (H1) is built but never run (amber chip 'built, never run'); the talker today is a small stand-in that is learned from scratch (blue chip 'learned stand-in'); the English talker is unbuilt (FINISHED line 38). The call writer is not a fifth box on the map: it is part of the thinker's output heads (FINISHED line 35), so the picture draws a small 'call writer' box inside the Thinker box. Fix pass: the stop chip said 'learned' and the talker chip said 'learned' beside a caption that said built-not-run and stand-in; the caption named a call writer that had no box.",
          "atMap": [
            [
              0.0235,
              0.0279
            ],
            [
              0.498,
              0.6353
            ]
          ]
        },
        {
          "id": "s02",
          "duration": 17.5,
          "heading": "The loop: try, check, nudge",
          "caption": [
            {
              "at": 0.0343,
              "text": "The model tries a question."
            },
            {
              "at": 0.2674,
              "text": "It is shown the right answer."
            },
            {
              "at": 0.4641,
              "text": "Then every learned setting moves a tiny bit. One nudge is one update."
            }
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
          "notes": "The question, the wrong try and the needle angles are all made up to show the idea. 'Every learned setting': the borrowed reader stays frozen (previous scene), so it does not move.",
          "atMap": [
            [
              0.0231,
              0.0343
            ],
            [
              0.3397,
              0.2674
            ],
            [
              0.6564,
              0.4641
            ]
          ]
        },
        {
          "id": "s03",
          "duration": 28,
          "heading": "24,000 updates of 256 rows each",
          "caption": [
            {
              "at": 0.0214,
              "text": "Each update looks at 256 practice rows, then nudges every learned setting once."
            },
            {
              "at": 0.26,
              "text": "The 3M test copy, with 3.5 million learned settings, did 24,000 updates."
            },
            {
              "at": 0.5215,
              "text": "Our multiplication: 24,000 × 256 = 6,144,000 row draws. The pool has 1,418,702 rows, so rows come round again."
            }
          ],
          "labels": {
            "updates": "updates",
            "rows": "rows per update",
            "draws": "row draws",
            "mult": "our multiplication",
            "div": "÷ 1,418,702 pool rows = about 4.3 draws each",
            "chip": "3M, one copy (seed 400)"
          },
          "src": [
            "origin/claude/8a-g-pc-results results/8a-g/pc/8aG1d-pc/8aG1d-3M-s400/B2/RESULT.json: config.steps 24000, config.batch 256 (accum 4 splits the same 256 rows), n_params 3,544,913",
            "same folder, pool_MANIFEST.json: rows 1,418,702; schedule.row_draws 6,144,000; schedule.passes 4.331",
            "animations/source-g1-3m-s400.json G-B2 updates 24000, learned_params 3544913",
            "architecture/EXPERTS-TEST-2026-10-09.md lines 36-38 (24,000 updates of 256 rows)",
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md line 166 (pool train file 1,418,702 rows)",
            "whole-model-roadmap/8A-SPEC-2026-10-07.md line 253 (B1: about 3.9 passes, an estimate before the run)"
          ],
          "notes": "Computed by us: 24,000 x 256 = 6,144,000; 6,144,000 / 1,418,702 = 4.33 (the run's own pool_MANIFEST.json also lists row_draws 6,144,000 and passes 4.331). The spec's earlier estimate was about 3.9 passes; we show the measured division, labelled. Not 6.1 million different questions. 3.5 million = 3,544,913 learned numbers of the 3M copy (the frozen reader's 271.0M is not counted here). 'every learned setting': the borrowed reader is frozen.",
          "nums": {
            "updates": 24000,
            "rows": 256,
            "draws": 6144000
          },
          "atMap": [
            [
              0.0185,
              0.0214
            ],
            [
              0.3385,
              0.26
            ],
            [
              0.6585,
              0.5215
            ]
          ]
        },
        {
          "id": "s04",
          "duration": 27,
          "heading": "The recipe: how each nudge is made",
          "caption": [
            {
              "at": 0.0222,
              "text": "AdamW is the nudging rule. The learning rate is how big a nudge may be."
            },
            {
              "at": 0.2729,
              "text": "It starts small, peaks at 1e-3 after a 300-update warm-up, then falls to 10% of the peak."
            },
            {
              "at": 0.6507,
              "text": "Sums run in short numbers (bf16), rows come shuffled, and the start is random."
            }
          ],
          "labels": {
            "adamw": "AdamW",
            "bf16": "bf16",
            "shuf": "shuffled",
            "rand": "random start",
            "clip": "push-size cap 1.0 (grad clip)",
            "y": "size of nudge",
            "x1": "24,000 updates",
            "warm": "warm-up",
            "peak": "1e-3",
            "tenth": "10% of peak",
            "pic": "picture only"
          },
          "src": [
            "origin/claude/8a-g-pc-results results/8a-g/pc/8aG1d-pc/8aG1d-3M-s400/B2/RESULT.json config: lr 0.001, warmup 300, grad_clip 1.0, order 'shuffled', bf16 true, batch 256, steps 24000",
            "origin/claude/project-thread-f1to6a custom_io/train.py lines 14-20 (lr_at: linear warm-up, then cosine down to 10% of base), line 201 (clip_grad_norm_ at grad_clip), line 166 (AdamW)",
            "architecture/EXPERTS-TEST-2026-10-09.md lines 36-38 (AdamW, lr 1e-3, grad clip 1.0, bf16, 24,000 updates of 256 rows)",
            "architecture/model-deep-dive.html line 165 (older page, same recipe wording)",
            "whole-model-roadmap/8A-SPEC-2026-10-07.md line 93 (as q33: AdamW, bf16, batch 256)"
          ],
          "notes": "Warm-up length 300 updates is in the run's RESULT.json config and is the train.py default; the schedule shape (linear warm-up, cosine fall to 10% of peak) is train.py lines 14-20. The curve is still a picture only: its warm-up is drawn far wider than 300 of 24,000 updates. 'Push-size cap' = gradient clipping at 1.0 (it caps the raw push before AdamW, not the learning rate; the first label said 'nudge cap', which read as a second cap on nudge size). bf16 = the sums run in a 16-bit number format (autocast), so 'stored short' was changed to 'run in short numbers'.",
          "atMap": [
            [
              0.0185,
              0.0222
            ],
            [
              0.3385,
              0.2729
            ],
            [
              0.6585,
              0.6507
            ]
          ]
        },
        {
          "id": "s05",
          "duration": 36,
          "heading": "What it practises on",
          "caption": [
            {
              "at": 0.0167,
              "text": "The 3M test copy practised on a pool of 60 million pieces of text (GPT-2 word pieces)."
            },
            {
              "at": 0.2455,
              "text": "By word pieces: own text 38%, web text 62%. By rows: own 811,663, web 607,039."
            },
            {
              "at": 0.6764,
              "text": "Our rows: skills questions and English passages made by our code, plus teaching rows (TEACH) a 1.2-billion-number teacher model wrote earlier."
            }
          ],
          "labels": {
            "own": "our own text",
            "web": "web text",
            "skills": "skills questions (our code)",
            "teach": "teaching rows (TEACH)",
            "pool": "share of 60 million pieces",
            "chip": "tested: 3M copy",
            "skillsN": "501,456 rows",
            "english": "English passages (our code)",
            "englishN": "255,495 rows",
            "teachN": "54,712 rows",
            "rowsHead": "our own text, counted in rows, not pieces: 811,663"
          },
          "src": [
            "origin/claude/8a-g-pc-results results/8a-g/pc/8aG1d-pc/8aG1d-3M-s400/pool_MANIFEST.json: rows 1,418,702; pieces 60,008,319; own rows 811,663 (share 0.38009): skills 501,456, english 255,495, teach 54,712 taken; web rows 607,039 (share 0.61991)",
            "whole-model-roadmap/8A-10M-RESULT-2026-10-08.md line 5 (60M-piece pool: 38% our questions, 62% web fill-in rows)",
            "whole-model-roadmap/8A-SPEC-2026-10-07.md lines 71-74 (20M/60M/190M word pieces, GPT-2 count; 38% own text = generator rows plus TEACH; 62% web)",
            "data-pool/DATA-POOL-PLAN-2026-10-06.md line 163 (own text: 12 English kinds + 34 skills families + all 171,940 TEACH rows; the 22.8M-piece prefix is what the 3M and 10M rungs read)",
            "custom_io/g8a/pool.py lines 12-16, 25-26 (own72 rows by rung; web pieces exact GPT-2 count, own pieces estimated from characters)",
            "whole-model-roadmap/whole-model-roadmap-2026-10-06.md lines 250, 265, 393 (TEACH 171,940 kept rows, PR #46; written by the 1.2B teacher; no new teacher rows)"
          ],
          "notes": "Shares are of word pieces, not of rows (by rows own is 57%, web 43%). The first version showed '200,000 skills questions' and '171,940 TEACH rows': those are the sizes of the older whole stock; the 3M copy's own pool manifest shows 501,456 skills rows, 255,495 English-passage rows and 54,712 TEACH rows (a prefix of the 171,940). Own-text pieces are estimated from characters (web pieces are an exact GPT-2 count), so '60 million' is the target 60,000,000 and the manifest total is 60,008,319. TEACHING_TO_TEST_CONTRACT.md is an older design memo, unrelated, and was not used. Fix pass: the 38% bar is a share of PIECES but the three boxes below it count ROWS (they sum to 811,663), and the old picture dropped 'by pieces' in the last panel. The bar title now says 'share of 60 million pieces', the bar's web label no longer says 'rows', and the three boxes sit in a full-width panel headed 'our own text, counted in rows, not pieces: 811,663' (501,456 + 255,495 + 54,712 = 811,663; MANIFEST own.rows).",
          "nums": {
            "own": 38,
            "web": 62
          },
          "atMap": [
            [
              0.0145,
              0.0167
            ],
            [
              0.3373,
              0.2455
            ],
            [
              0.6602,
              0.6764
            ]
          ]
        },
        {
          "id": "s06",
          "duration": 32,
          "heading": "Web text: fill in the missing word",
          "caption": [
            {
              "at": 0.0187,
              "text": "FineWeb-Edu web text: a script blanks one word of 3 to 12 letters, and the model must name it."
            },
            {
              "at": 0.3969,
              "text": "Each prompt holds at most 280 letters, blank included, in the 3M runs; the finished design's long pool goes up to 2,000."
            },
            {
              "at": 0.725,
              "text": "It learns to read English, not write it. Rows without steps add a faint no-call label, weight 0.1."
            }
          ],
          "labels": {
            "pre": "Plants make food from",
            "post": ", water and air.",
            "word": "sunlight",
            "ex": "made-up example",
            "b1": "280 letters",
            "b2": "2,000 letters",
            "b1chip": "tested at 3M",
            "b2chip": "never run",
            "w": "no-call weight"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 11 (lines 140-146)",
            "custom_io/g8a/cloze.py lines 12, 21-22 (origin/claude/project-thread-f1to6a: prompt <= 280 chars with blank; chunk text itself capped at 279; blanked word 3..12 letters; rows made by a script)",
            "custom_io/models/ledger.py line 131 (origin/claude/project-thread-f1to6a: w_noop=0.1 default; used at line 507) and, on the B3 branch, ledger.py line 140 / tool.py line 125 (w_noop=0.1)",
            "origin/claude/8a-g-pc-results 8aG1d-3M-s400/RESULT.json caps.max_prompt 280 (the 3M runs); origin/claude/project-thread-qtxfp4 custom_io/g8a/caps_b3.json max_prompt 2000 and job.py --cloze-long"
          ],
          "notes": "FineWeb-Edu = free human-written web text. The example sentence is made up; real rows come from FineWeb-Edu. The 2,000-letter pool (cloze_long, --cloze-long) is built but never run.",
          "nums": {
            "b1": 280,
            "b2": 2000,
            "w": 0.1,
            "lo": 3,
            "hi": 12
          },
          "atMap": [
            [
              0.0152,
              0.0187
            ],
            [
              0.3376,
              0.3969
            ],
            [
              0.6599,
              0.725
            ]
          ]
        },
        {
          "id": "s07",
          "duration": 22.5,
          "heading": "Worked steps: practising each call",
          "caption": [
            {
              "at": 0.0267,
              "text": "Built version: where a row has worked steps, the key gives the right call each round."
            },
            {
              "at": 0.3384,
              "text": "Call loss: was the call slip right? After the last call, the right slip is no call."
            },
            {
              "at": 0.666,
              "text": "Answer loss: is the final answer right? Counted from the last call round on (built version)."
            }
          ],
          "labels": {
            "round": "round",
            "r1": "2",
            "r2": "3",
            "r3": "4",
            "key": "answer key",
            "cw": "call writer (built)",
            "c1": "sub 12 5 = 7",
            "c2": "add 7 3 = 10",
            "c3": "no call",
            "ans": "answer 10",
            "callLoss": "call loss",
            "ansLoss": "answer loss",
            "ex": "made-up example",
            "chip": "built version: never run"
          },
          "src": [
            "architecture/B3-GROUP1-BUILD-2026-10-09.md lines 53-60 (teacher forcing: op loss on the gold call each call round and no-call after the last; answer loss from the last call round on)",
            "architecture/model-deep-dive.html line 165 (older write-up: losses for operation, pointers, answer, spelling)"
          ],
          "notes": "This is the finished design's loss schedule (B3 group 1): built, never run. The 3M test copy was an older design with its own losses. Round numbers: no call can follow round 1 (calls need code round index t >= 1), so the first call follows round 2, the second round 3, and 'no call' is trained from round 4 (FINISHED sec. 3 steps 2-5; B3-GROUP1-BUILD lines 47, 57-58). The first version labelled the columns 1, 2, 3, which put a call after round 1. The example is made up.",
          "atMap": [
            [
              0.0167,
              0.0267
            ],
            [
              0.338,
              0.3384
            ],
            [
              0.6593,
              0.666
            ]
          ]
        },
        {
          "id": "s08",
          "duration": 29,
          "heading": "Teacher forcing: practice follows the key",
          "caption": [
            {
              "at": 0.0207,
              "text": "Teacher forcing, built version: the reader reads the key's call and reply, even after a wrong guess."
            },
            {
              "at": 0.2749,
              "text": "At test time there is no key. New design, untested: the talker writes the calls."
            },
            {
              "at": 0.5044,
              "text": "Not every row has steps: 124,991 of the 200,000 skills rows (62.5%) the earlier 3M models used have none."
            }
          ],
          "labels": {
            "lane1": "practice",
            "lane2": "test",
            "k": "key's call",
            "r": "calculator's reply",
            "rd": "reader",
            "n": "next round",
            "g": "own guess: graded",
            "o": "own call",
            "none": "no steps"
          },
          "src": [
            "architecture/B3-GROUP1-BUILD-2026-10-09.md lines 49-53, 67-71 (running with no teacher vs teacher forcing; gold calls fed in a free run give the same thinker states)",
            "custom_io/models/tool.py lines 351-352 (commit 17a356e62: in training, shown[:, k] follows the gold op; free run uses the model's own op)",
            "architecture/FINISHED-MODEL-2026-10-09.md line 143 (62.5% of the skills rows the 3M models trained on have no worked steps)",
            "custom-io/audit-2026-10-09/FINISHED-fixes.md line 90 (124,991 of the 200,000 skills rows = 62.5%)",
            "architecture/model-deep-dive.html line 165 (older page: only 11 arithmetic families have teacher steps; not shown on screen)"
          ],
          "notes": "Teacher forcing itself is shown in the T1SDR/H1 code (tool.py 351-352); the any-round version with think-only gap rounds is B3 group 1, built, never run. The 62.5% is 124,991 of the 200,000-row skills set the earlier (T1SDR) 3M models trained on; the G1 3M pool holds 501,456 skills rows, whose no-steps share is not stated in the sources, so the caption names the earlier 200,000-row set. The older page's '11 families' disagrees; the caption no longer mentions it (a viewer cannot see that page).",
          "nums": {
            "share": 62.5
          },
          "atMap": [
            [
              0.019,
              0.0207
            ],
            [
              0.3386,
              0.2749
            ],
            [
              0.6582,
              0.5044
            ]
          ]
        },
        {
          "id": "s09",
          "duration": 36,
          "heading": "Fair practice: three rules",
          "caption": [
            {
              "at": 0.0167,
              "text": "Rule 1: no answer is cut short. A longer answer is counted, and any count above 0 fails the pass mark."
            },
            {
              "at": 0.3166,
              "text": "Rule 2: exam questions are kept apart: 6,040 rows are never used in practice, though question styles can repeat."
            },
            {
              "at": 0.6474,
              "text": "Rule 3: web text is scanned against exam sets. A last scan, on sealed sets, was pending Oct 9; the 3M runs began before it."
            }
          ],
          "labels": {
            "c1": "No answer cut short",
            "c1a": "Earlier runs (T1SDR): 0 of 200,000 training answers over 8 letters",
            "c1b": "Finished design (B3): cap of 35 letters",
            "c1chip": "built, never run",
            "c2": "Kept aside",
            "c3": "Web gate",
            "c3chip": "check pending (Oct 9)"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 4 lines 79-82 (0 of 200,000 over 8 letters in T1SDR runs; B3 caps_b3 writes up to 35 letters, counts longer ones; any count above 0 fails its sealed mark)",
            "no-hardcoding/PLAN-AND-MARKS-2026-10-07.md sec. 2 (nothing is cut off; every limit listed with rows touched) and no-hardcoding/LIMIT-COUNTS-2026-10-07.json",
            "whole-model-roadmap/8A-SPEC-2026-10-07.md line 115 (pooled-5 = 6,040 dev rows), lines 84-90 and A1 lines 179-184 (overlap scan; never trained on the dev splits; 3M runs may start before the protected-panel check)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 12 (web pool gate; hash file waits on a Mac job); data-pool/DATA-POOL-PLAN-2026-10-06.md sec. 6, lines 108-128 ('Not yet cleared': protected-panel hashes; the pool must not be used for training until merged)",
            "data-pool/DATA-POOL-PLAN-2026-10-06.md lines 120-125 (11% of the old 200,000 skills prompts share 13-word template frames with the skills exam splits; generator rows rely on the hold-out splits, the 13-gram result is reported, not gated)"
          ],
          "notes": "Present as a rule plus a check, not a guarantee. Rule 2 says rows, not styles: the exam splits come from the same generators, and the data-pool scan found shared template frames (11% of the old skills prompts), so the caption says question styles can repeat. Rule 3: the scan against indexed exam sets runs; the scan against the protected (sealed) sets was still waiting on a Mac hash job on Oct 9 (FINISHED sec. 5 item 12; 8A-SPEC addendum A1 let the 3M runs start first). 8a's B2 had answers cut to 8 letters by a settings bug (8A-10M-RESULT correction); G1 is the fixed re-run. 6,040 = 1360+1200+1360+800+1320 (LIMIT-COUNTS dev splits). Fix pass: the square strips are drawings, not counts. A grey 'picture only' chip and a one-line colour key (blue practice, grey kept aside or web text, orange box the scan, red tick the cap) sit under the cards; their words are stored under the 'illustration' key, which the audit does not count. The 'check pending (Oct 9)' chip is now grey (a job that has not run: the hash file waits on a Mac job, FINISHED sec. 5 item 12).",
          "nums": {
            "kept": 6040
          },
          "illustration": {
            "pic": "picture only",
            "cap": "red tick: the cap",
            "blue": "blue: practice",
            "grey": "grey: kept aside or web",
            "orange": "orange box: the scan"
          },
          "atMap": [
            [
              0.0133,
              0.0167
            ],
            [
              0.337,
              0.3166
            ],
            [
              0.6607,
              0.6474
            ]
          ]
        },
        {
          "id": "s10",
          "duration": 48,
          "heading": "Time: our model versus the plain model",
          "caption": [
            {
              "at": 0.0125,
              "text": "Ours did 24,000 updates on the project's PC: 1.02 updates a second, 6.51 hours."
            },
            {
              "at": 0.2597,
              "text": "The plain model, a standard transformer of about the same size, also did 24,000 updates: 2.8 a second, 2.38 hours."
            },
            {
              "at": 0.4682,
              "text": "Our division: 6.51 ÷ 2.38, about 2.7 times longer. Our other 3M copy took 16.3 hours; a memory spill is the suggested cause."
            },
            {
              "at": 0.775,
              "text": "A plan, not a result: the 100M run (about 100 million numbers) is estimated at 3 to 5 weeks on this PC."
            }
          ],
          "labels": {
            "ours": "our model",
            "plain": "plain model",
            "hrs": "hours",
            "chip": "tested: 3M, faster copy",
            "plan": "plan only",
            "weeks": "100M: 3 to 5 weeks",
            "ratio": "times longer (our division)"
          },
          "src": [
            "origin/claude/8a-g-pc-results results/8a-g/pc/8aG1d-pc/8aG1d-3M-s400/B2/RESULT.json: steps 24000, steps_per_s 1.0246, train_s 23422.6 (= 6.51 h), n_params 3,544,913; PT/RESULT.json: steps 24000, steps_per_s 2.8013, train_s 8567.6 (= 2.38 h), n_params 3,495,936",
            "animations/source-g1-3m-s400.json G-B2 updates_per_s 1.02, train_hours 6.51; G-PT updates_per_s 2.8, train_hours 2.38",
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md line 402 (addendum Q: 3M s401 G-B2 0.41 updates/s, 16.3 h; G-PT 2.96 updates/s, 2.3 h; slow arm's reserved memory 16,220 MiB, the whole card, against 11,750 on s400; cause suggested)",
            "big-run/PLAN.md line 9 (revision 10-10: speed anomaly on seed 401, 0.408 against 1.025 steps/s, cause untested) and line 278 (sec. 6: 6 x 2 to 2.7 x 1.5 x 1.3 = about 23 to 32 days, so 3 to 5 weeks, suggested; not run)"
          ],
          "notes": "Computed by us: 6.51 / 2.38 = 2.74, shown as 'about 2.7 times longer' (the raw seconds give 23,422.6 / 8,567.6 = 2.73). Both arms of seed 400 logged steps 24000 in RESULT.json (the earlier caption said the plain model's count was not logged; the raw file has it). Seed 401's G-B2 arm took 16.3 h (0.41 updates/s) against 2.3 h for its plain arm, a 7-fold gap; the slow run's graphics memory was full (shown) and a memory spill is the suggested cause (not tested), so 2.7 is the faster copy and the caption says so (no extra on-screen label: the scene is at the 45 s limit). Older design (calculator inside, 12 rounds), not the finished one. The 3-to-5-week figure is a plan estimate that the PC speed check will replace. Fix pass: the chip said 'one copy' while the caption named a second copy. The bars are the seed-400 copy, the faster of our two 3M copies; the chip now says 'faster copy' and the caption says 'other 3M copy' (same 16.3 h, seed 401, same suggested cause).",
          "nums": {
            "oursH": 6.51,
            "plainH": 2.38,
            "ratio": 2.7
          },
          "atMap": [
            [
              0.0133,
              0.0125
            ],
            [
              0.2561,
              0.2597
            ],
            [
              0.4989,
              0.4682
            ],
            [
              0.7417,
              0.775
            ]
          ]
        },
        {
          "id": "s11",
          "duration": 30,
          "heading": "Why the thinker is harder to train",
          "caption": [
            {
              "at": 0.02,
              "text": "The same blocks run every round, so the lesson from a wrong answer must travel back through all of them."
            },
            {
              "at": 0.3202,
              "text": "To save memory, training redoes some work instead of storing it: about a third more compute (plan estimate)."
            },
            {
              "at": 0.6062,
              "text": "Depth has a known cost: on one old probe, 16 rounds cost 1.2 to 1.9 points. At 100 million numbers it is an open risk."
            }
          ],
          "labels": {
            "rounds": "rounds",
            "fwd": "answer goes forward",
            "back": "the lesson goes back",
            "chip": "never run at 100M",
            "pic": "picture only",
            "r1": "1",
            "r2": "2",
            "r3": "3",
            "dots": "...",
            "r32": "32",
            "probe": "tested: old probe, one seed",
            "redo": "later rounds: work redone, not stored",
            "cap32": "up to 32 rounds"
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 13 (line 149: 16 rounds cost 1.2-1.9 points on one B2 probe; open risk for 100M) and line 186 (H1 back-propagates through every round with checkpointing)",
            "custom_io/models/tool_h1.py lines 18-20 and 68-71 (commit 17a356e62: rounds 9..32 gradient-checkpointed, same values, less memory)",
            "big-run/PLAN.md sec. 6 line 278 (checkpointing recomputes about a third more)",
            "no-hardcoding/INPUT-UNITS-2026-10-07.md line 39 (16 rounds cost 1.2-1.9 points, one seed, 40-loops-probe; FINISHED cites line 31)"
          ],
          "notes": "The 'third more' is a suggested plan estimate. The 100M fit in 16 GB with 32 rounds is untested. Fix pass: the outlined box is round 32 (the design allows up to 32 rounds, tool_h1.py CAP = 32), labelled 'up to 32 rounds'; the 16-round probe stays a caption fact and gets its own chip 'tested: old probe, one seed' (INPUT-UNITS line 39: one seed, 40-loops-probe, an older B2 design). The cream fill now marks only the later rounds ('...' and 32) with the key 'later rounds: work redone, not stored': tool_h1.py lines 18-20, 68-71 checkpoints rounds 9..32 only (the drawing is still a picture; '...' stands for rounds 4 to 31). The 'never run' chip now says 'never run at 100M'.",
          "atMap": [
            [
              0.014,
              0.02
            ],
            [
              0.3372,
              0.3202
            ],
            [
              0.6605,
              0.6062
            ]
          ]
        },
        {
          "id": "s12",
          "duration": 17,
          "heading": "What changes after practice",
          "caption": [
            {
              "at": 0.0353,
              "text": "The model's size stays the same. Only the values of its settings change, by many tiny nudges."
            },
            {
              "at": 0.5789,
              "text": "Real before-and-after values are not shown here. This is an idea, drawn as a picture."
            }
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
          "notes": "All needle positions are decoration.",
          "atMap": [
            [
              0.03,
              0.0353
            ],
            [
              0.4975,
              0.5789
            ]
          ]
        },
        {
          "id": "s13",
          "duration": 31,
          "heading": "Recap: what to remember",
          "caption": [
            {
              "at": 0.0194,
              "text": "Practice is a loop: try, check the key, nudge. The 3M test ran 24,000 updates, each looking at 256 rows."
            },
            {
              "at": 0.336,
              "text": "Rows are questions and passages from our code, teaching rows and web blanks, with exam questions kept apart."
            },
            {
              "at": 0.5915,
              "text": "On one 3M copy ours took about 2.7 times longer than the plain model; the finished design is not trained yet."
            }
          ],
          "labels": {
            "t1": "the loop",
            "t2": "the rows",
            "t3": "the cost",
            "upd": "updates",
            "rpu": "rows per update",
            "rCode": "our code",
            "rTeach": "teaching",
            "rWeb": "web blanks",
            "kept": "rows kept aside",
            "x": "times longer",
            "ours": "ours",
            "plain": "plain",
            "chip": "tested: 3M, faster copy"
          },
          "src": [
            "see scenes s02, s03, s05, s06, s09, s10 of this chapter",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 6 (B3 group 1's first run comes after G1)"
          ],
          "notes": "Recap only; every number is shown earlier. Fix pass: unit lines added under 24,000 (updates) and 256 (rows per update); '6,040' is labelled 'rows kept aside' (the exam rows, s09); the three square rows are labelled (our code, teaching, web blanks, in caption order) and carry a 'picture only' chip; the cost card has the same green chip as s10 ('tested: 3M, faster copy') and labels for its two bars; caption 1 rewritten as two plain sentences with the same two numbers.",
          "nums": {
            "updates": 24000,
            "rows": 256,
            "kept": 6040,
            "ratio": 2.7
          },
          "illustration": {
            "pic": "squares: picture only"
          },
          "atMap": [
            [
              0.0154,
              0.0194
            ],
            [
              0.3376,
              0.336
            ],
            [
              0.6598,
              0.5915
            ]
          ]
        }
      ]
    },
    "ch09": {
      "kicker": "Part 8 of 10",
      "title": "Does the thinking really do the work?",
      "blurb": "We turn the thinking down, round by round, and break other parts on purpose, to see whether the answers fall with it.",
      "accent": "thinker",
      "scenes": [
        {
          "id": "s01",
          "duration": 18.5,
          "heading": "Where we are: the thinker",
          "caption": [
            {
              "at": 0.0324,
              "text": "This part is the thinker, a team of note-takers that works in rounds."
            },
            {
              "at": 0.5055,
              "text": "We claim the thinking does the work. This chapter tests that claim."
            }
          ],
          "note": "One round = one lap: look at the whole question, pass notes, think.",
          "src": [
            "animations/model-explainer-build/kit/GLOSSARY.md (thinker, round)",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 1 and 2 (Thinker row: 'same weights every round')",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 7 ('G1 tests today's model (calculator inside, 12 fixed rounds, hand number slots)') and sec. 4 table row 'Fixed number of rounds (8 in T1SDR, 12 in G1)'",
            "branch origin/claude/project-thread-f1to6a custom_io/models/ledger.py docstring lines 1-8 (parameter-free exact executor inside the model; loop count n_loops)"
          ],
          "design": "Results as of Oct 9. The model tested is an older design: 12 fixed rounds, calculator built in, no learned stop switch.",
          "notes": "The four-part map (calculator outside) always draws the finished design (outside calculator, learned stop). The model tested in this chapter (G-B2, 3M, copy 400) has the calculator built in as an exact executor inside the model and 12 fixed rounds with no learned stop, so the extra note says so. Dated 'as of Oct 9' on purpose.",
          "atMap": [
            [
              0.0207,
              0.0324
            ],
            [
              0.4983,
              0.5055
            ]
          ]
        },
        {
          "id": "s02",
          "duration": 18,
          "heading": "A score with nothing to compare",
          "caption": [
            {
              "at": 0.0333,
              "text": "Our model scored 73.01 points out of 100 on 6,040 questions kept aside."
            },
            {
              "at": 0.4839,
              "text": "That is 4,410 right. But is it the thinking that earns them?"
            }
          ],
          "score": 73.01,
          "unit": "points out of 100",
          "right": 4410,
          "rightLabel": "right, out of 6,040",
          "chip": "tested: one training run (a copy), smallest size, 3,544,913 learned numbers",
          "src": [
            "animations/source-g1-3m-s400.json (G-B2 full: right 4410, of 6040, pooled5 73.01)",
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md sec. 12 (addendum G): 73.01 (4,410/6,040), 3M s400",
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 2: 'Shown on one seed'"
          ],
          "notes": "Tested once: 3M size (3,544,913 numbers it learned), seed 400, run on the project's own PC. Re-added from the raw RESULT.json (branch claude/8a-g-pc-results) by me: 1170+863+1178+715+484 = 4410 right of 1360+1200+1360+800+1320 = 6040; 100 x 4410/6040 = 73.01. Chip: 'copy' = one training run with its own random start (seed 400); 3,544,913 = n_params in B2/RESULT.json, the numbers the model learned (the borrowed, frozen Gemma reader, 271,002,624, is on top). Fix pass: the design tag (same fact as the s01 callout) now sits on the number panel with the 73.01, so the caption \"Our model scored 73.01\" is not read as the finished design.",
          "design": "Older design: 12 fixed rounds, calculator built in.",
          "atMap": [
            [
              0.0222,
              0.0333
            ],
            [
              0.4981,
              0.4839
            ]
          ]
        },
        {
          "id": "s03",
          "duration": 19.5,
          "heading": "What the 6,040 questions are",
          "caption": [
            {
              "at": 0.0308,
              "text": "To score it, we use 6,040 questions kept aside."
            },
            {
              "at": 0.3898,
              "text": "They come in five kinds, from familiar to new."
            },
            {
              "at": 0.6213,
              "text": "They add up to 6,040. The test is called pooled-5."
            }
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
          "notes": "The per-kind question counts are the n fields of the raw file; they sum to 6040. 'Familiar templates' is in_dist (same templates as practice, new questions). Fix pass: on-screen gloss for the code name pooled-5, worded from kit/GLOSSARY.md (pooled-5 = the 6,040 questions kept aside, five kinds pooled into one score out of 100).",
          "gloss": "pooled-5: five kinds pooled into one score out of 100",
          "atMap": [
            [
              0.0231,
              0.0308
            ],
            [
              0.3397,
              0.3898
            ],
            [
              0.6564,
              0.6213
            ]
          ]
        },
        {
          "id": "s04",
          "duration": 27.5,
          "heading": "Turning the thinking down",
          "caption": [
            {
              "at": 0.0218,
              "text": "Trained with 12 rounds, it scores 73.01 at 12."
            },
            {
              "at": 0.2694,
              "text": "Turn the rounds dial down, with no new practice: 2 rounds scores 29.30."
            },
            {
              "at": 0.5349,
              "text": "1 round: 20.00."
            },
            {
              "at": 0.6537,
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
          "notes": "0.66, 73.01 are in the spec; 29.30, 20.00 and the right-counts 1,770 / 1,208 / 40 are re-added from the raw RESULT.json files (sum of correct over in_dist, answer, frame, vocab, variant, divided by 6,040). The 12-round row is the model as trained ('full'); the raw file has no separate loops:12 entry.",
          "testedChip": "tested: one copy, older design",
          "atMap": [
            [
              0.02,
              0.0218
            ],
            [
              0.2,
              0.2694
            ],
            [
              0.4,
              0.5349
            ],
            [
              0.58,
              0.6537
            ]
          ]
        },
        {
          "id": "s05",
          "duration": 27.5,
          "heading": "More rounds: no gain",
          "caption": [
            {
              "at": 0.0218,
              "text": "Now turn the dial past its practice, to 24 rounds."
            },
            {
              "at": 0.2493,
              "text": "The score does not rise: 72.57, which is 27 fewer right (4,410 minus 4,383)."
            },
            {
              "at": 0.6722,
              "text": "The design we plan to ship adds a learned stop switch, which picks the number of rounds."
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
          "notes": "27 = 4,410 minus 4,383, my subtraction (right answers at 12 rounds minus at 24 rounds). 24 = twice the 12 trained rounds (the raw file's 2 x n_loops lesion).",
          "testedChip": "tested: one copy, older design",
          "atMap": [
            [
              0.02,
              0.0218
            ],
            [
              0.3389,
              0.2493
            ],
            [
              0.6578,
              0.6722
            ]
          ]
        },
        {
          "id": "s06",
          "duration": 24,
          "heading": "Multi-step questions fall hardest",
          "caption": [
            {
              "at": 0.025,
              "text": "A second test, called chain-5: 1,000 multi-step questions kept aside."
            },
            {
              "at": 0.3487,
              "text": "Each calculator step takes its own round, so cutting rounds should hurt most."
            },
            {
              "at": 0.6164,
              "text": "1 round: 0.0. 2 rounds: 1.1. 12 and 24 rounds: 99.9."
            }
          ],
          "example": "Tom has 12 apples. He gives away 5, then buys 3.",
          "illustration": "made-up example",
          "scoreHead": "chain-5 test, 1,000 questions: points out of 100",
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
            "custom-io/gpt-b2-leak-and-credit-2026-10-05.md (chain-5 = 5 multi-step arithmetic families, 1,000 rows)",
            "branch origin/claude/project-thread-f1to6a custom_io/models/ledger.py docstring lines 5-8 ('at t = 1..7 control token 0 picks the op ... (K iterations = K-1 writes)'); architecture/model-deep-dive.html 'Rounds 1 to 7' ('round 0 just look, no step')"
          ],
          "notes": "Not the separate 'multistep' subset (480 rows per split). The Tom example is made up (deep-dive: 'Made up for this page'); its two steps are an illustration of one step per round, in the older design page's words. 12 rounds = the model as trained (chain5 'intact'). Rounds per step: in the model tested, K rounds write K-1 calculator steps (ledger.py docstring) and round 0 only looks (deep-dive), so the two-step Tom example needs three rounds; the old label 'two steps, two rounds' was wrong. The caption says 'should hurt most' (a reading, not a measurement): the numbers show chain-5 falling further than the main test at 1 and 2 rounds (0.0 and 1.1 against 20.00 and 29.30), but custom-io/gpt-b2-leak-and-credit-2026-10-05.md also suggests the answer heads are only trained at the full round count, so the cause is not settled. The heading now states only what was measured. Fix pass: the chart header now names the test (chain-5, 1,000 questions) and carries the green tested chip, so the bars are not read as the made-up Tom example result.",
          "stepsLabel": "two steps, three rounds: the first only looks",
          "testedChip": "tested: one copy, older design",
          "atMap": [
            [
              0.0167,
              0.025
            ],
            [
              0.338,
              0.3487
            ],
            [
              0.6593,
              0.6164
            ]
          ]
        },
        {
          "id": "s07",
          "duration": 25,
          "heading": "Break the notes, the answer breaks",
          "caption": [
            {
              "at": 0.024,
              "text": "A lesion test: break one part, and see if the answer breaks."
            },
            {
              "at": 0.2904,
              "text": "Give the talker, which writes the answer, another question's notes: the score falls to 4.19 on familiar questions."
            },
            {
              "at": 0.6456,
              "text": "Shuffle the notes between questions: 6.80."
            }
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
              "extra": "750 of 1,360 gave the other's answer"
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
          "notes": "Same model and seed as the rest of the chapter (G-B2, 3M, seed 400), not the older design numbers in model-deep-dive.html (3.8% / 7.9%). 86.03 and 4.19 are on the 1,360 familiar-template questions only (the donor test's in_dist split; 1,170 right intact, 57 right with a donor's notes, 750 of 1,360 gave the donor's answer). 6.80 = 411/6040, intact 73.01. Shuffle is the notes rolled by one row (each question gets the next question's notes). 55.15 was shown as a bare number under 'points out of 100'; it is a share of answers (750 of 1,360 = 55.147), so the count is written instead.",
          "scoreHead": "points out of 100",
          "testedChip": "tested: one copy, older design",
          "atMap": [
            [
              0.0162,
              0.024
            ],
            [
              0.3378,
              0.2904
            ],
            [
              0.6595,
              0.6456
            ]
          ]
        },
        {
          "id": "s08",
          "duration": 26.5,
          "heading": "Break the calculator, the answer breaks",
          "caption": [
            {
              "at": 0.0226,
              "text": "Swap add and subtract in the calculator (plain code that does the sums), and the answers follow."
            },
            {
              "at": 0.3008,
              "text": "Of 831 answers the swap changes, 830 followed it."
            },
            {
              "at": 0.5763,
              "text": "Switch it off: the score is 0.0 on 2,085 questions that need it."
            }
          ],
          "labels": {
            "thinker": "Thinker",
            "calc": "Calculator",
            "model": "OLDER DESIGN TESTED HERE",
            "outside": "built in: does the sums",
            "call": "call",
            "reply": "reply",
            "contrast": "The finished model keeps the calculator outside.",
            "talker": "Talker",
            "add": "add",
            "sub": "subtract"
          },
          "illustration": "picture only",
          "cards": [
            {
              "title": "Add and subtract swapped",
              "value": 99.9,
              "sub": "830 of 831 answers followed the swap"
            },
            {
              "title": "Calculator off",
              "was": 100,
              "to": 0,
              "sub": "was 100.0, on 2,085 questions"
            }
          ],
          "src": [
            "branch claude/8a-g-pc-results B2/RESULT.json extra.opswap (n_affected 831, swap_match 99.88, stays_intact 0.0) and extra.noexec (n 2085, intact 100.0, program_families 0.0)",
            "branch origin/claude/project-thread-qtxfp4 custom_io/models/ledger.py lines 640-695 (how noexec program rows and opswap affected rows are chosen) and custom_io/PASS-MARKS.md lines 66-67, 434-445",
            "animations/model-explainer-build/chapters-out/ch09/g1-3m-s400-extract.json"
          ],
          "notes": "830 of 831 = 99.88, shown as 99.9. 'Answers the swap changes' = chain-5 rows the intact model got right, answered by a calculator result, where swapping add and subtract changes that result (ledger.py swap_stats: aff). 'Questions that need it' = rows whose right answer is a calculator result (noexec program rows, n 2085): 100.0 with the calculator on, 0.0 off. 99.9 (830 of 831) is a share of the affected answers, not a score, so the shared heading no longer says 'points out of 100'. The 0.0 is a score on the 2,085 rows that need the calculator. In this tested model the calculator is an exact executor inside the model (ledger.py), the older design; see s01. Fix pass: the \"was 100.0\" line now names its question set (2,085 questions), as the caption does.",
          "scoreHead": "out of every 100 counted",
          "testedChip": "tested: one copy, older design",
          "atMap": [
            [
              0.0171,
              0.0226
            ],
            [
              0.3381,
              0.3008
            ],
            [
              0.659,
              0.5763
            ]
          ]
        },
        {
          "id": "s09",
          "duration": 33.5,
          "heading": "A small leak with no thinking",
          "caption": [
            {
              "at": 0.0179,
              "text": "At zero rounds a model should score near zero. Some runs did not."
            },
            {
              "at": 0.2256,
              "text": "An earlier version, copy 200: with the borrowed Gemma reader 18.09, without it 1.40. Its other copy, 201: 4.49 and 4.34."
            },
            {
              "at": 0.6785,
              "text": "Our copy 400: 0.96 here, 0.66 on all 6,040. Cause not settled."
            }
          ],
          "subtitle": "points out of 100, zero rounds, familiar questions",
          "markLabel": "pass mark: at most",
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
            "branch claude/8a-g-pc-results B2/RESULT.json lesions.loops:0.in_dist: 13 right of 1360 = 0.96",
            "custom_io/results/RESULTS-EG2.md lines 11-12 (branch origin/claude/custom-reader-talker-4x309r): mark 5 loops0 EGE seed 200 18.09, seed 201 4.49; plain B2 seed 200 1.40, seed 201 4.34; PASS-MARKS addendum 14 line 366-367 ('the loops:0 score varies widely across runs that share the talker design')"
          ],
          "notes": "All three bars are the zero-round score on the familiar-template questions (in_dist, 1,360 questions per copy), not the 6,040-question pooled-5 (0.66). The seed-200 numbers come from the earlier version of the model (8 rounds, older settings), before the G1 fix; the seed-400 copy is G1 (12 rounds). 'Gemma' = EGE, B2 with the borrowed reader in front; 'No Gemma' = B2V on the same seed. 0.96 = 13/1360 (my division). Mark 5 = 'loops:0 in_dist <= 5' in PASS-MARKS addendum 4/14; big-run PLAN scorecard row 2 uses the same idea ('thinker-off <= half the full score'). Copy 201 numbers (4.49 with Gemma, 4.34 without) added to the caption so the 18.09 against 1.40 pair is not read as a steady Gemma effect: the source says the zero-round score varies widely between copies and the cause is not settled. The mark is a ceiling (loops:0 in_dist <= 5), so the label says 'at most'. Fix pass: the bars were drawn on a 0 to 20 track; they now use the same 0 to 100 track as the other scenes (axis labels 0 and 100), so 18.09 fills 18 percent of the track and the pass mark of 5 sits at 5 percent.",
          "testedChip": "tested: one copy per bar",
          "axis": [
            "0",
            "100"
          ],
          "atMap": [
            [
              0.0162,
              0.0179
            ],
            [
              0.3378,
              0.2256
            ],
            [
              0.6595,
              0.6785
            ]
          ]
        },
        {
          "id": "s10",
          "duration": 33.5,
          "heading": "Side by side with a plain model",
          "caption": [
            {
              "at": 0.0179,
              "text": "On this one copy, ours scores 5.9 points more than the plain model (our subtraction: 73.01 minus 67.12)."
            },
            {
              "at": 0.3734,
              "text": "But it took 2.7 times longer to train in this run (our division: 6.51 by 2.38 hours)."
            },
            {
              "at": 0.6588,
              "text": "Add a calculator to the plain model, no retraining: 69.62 and 99.0. Gap: 3.39 points (our subtraction)."
            }
          ],
          "heads": {
            "ours": "Ours, with thinker",
            "plain": "Plain model",
            "calc": "Plain + calculator"
          },
          "headSubs": {
            "ours": "3,544,913",
            "plain": "3,495,936",
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
            "custom_io/README.md and custom_io/models/plain_tf_steps.py line 2 ('calc' lesion: a calculator fills each a op b = while decoding, same weights, no retraining)",
            "branch origin/claude/project-thread-f1to6a custom_io/models/plain_tf_steps.py lines 1-3 (plain model writes worked steps, then ' # ', then the answer, arithmetic families only); big-run/PLAN.md line 239 (steps for 11 families only)"
          ],
          "notes": "5.9 = 73.01 - 67.12 = 5.89 (my subtraction). 2.7 = 6.51 / 2.38 = 2.735 (my division; the speed ratio 2.80 / 1.02 = 2.745 also gives 2.7). 3.39 = 73.01 - 69.62 (my subtraction). 69.62 = 4205/6040 summed from PT/RESULT.json lesions.calc over the five splits. The plain model writes its worked steps out as text and then the answer (plain_tf_steps_g, 4 layers, width 256). One copy, seed 400, 3M. The size row 'numbers it learned' = n_params (trainable); both arms also use the same frozen Gemma reader (271,002,624). 'This one copy' and 'in this run': one seed, one PC run; the training-time ratio depends on the shared PC, so it is not a general speed claim. The plain model is the plain step-writing model (G-PT), the yardstick the spec picked by default; the spec lists the choice of plain model as open for the project owner. Fix pass: the 3.39 gap is the main-test row, ours (73.01) minus plain + calculator (69.62); the two cells are outlined on the picture, and the gap note names the pair. The green chip uses the kit default word \"tested\" (no extra words, because this scene is at the 45 s limit).",
          "plainNote": "The plain model writes arithmetic steps as text.",
          "sizeLabel": "Size, numbers it learned",
          "gapNote": "Gap: ours minus plain + calculator",
          "atMap": [
            [
              0.0133,
              0.0179
            ],
            [
              0.337,
              0.3734
            ],
            [
              0.6607,
              0.6588
            ]
          ]
        },
        {
          "id": "s11",
          "duration": 19,
          "heading": "What this does not show",
          "caption": [
            {
              "at": 0.0316,
              "text": "As of Oct 9, one copy at the smallest size is a first result, not proof."
            },
            {
              "at": 0.4394,
              "text": "This is the older design, with 12 fixed rounds and the calculator built in. It says nothing yet about bigger sizes."
            }
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
              "text": "As of Oct 9: a second copy and the 10M size"
            },
            {
              "kind": "untested",
              "label": "never tested",
              "text": "The finished design's learned stop switch"
            },
            {
              "kind": "placeholder",
              "label": "unsettled",
              "text": "Why zero-round answers happen"
            }
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md sec. 5 items 2, 4, 7 (G1 tests today's model: calculator inside, 12 fixed rounds; 'shown on one seed') and sec. 2 (Learned stop: built, never run)",
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md sec. 12-13 (addenda G, H: seed 401 and the 10M arms not yet in) and sec. 3 (mark 1 needs both sizes)",
            "big-run/PLAN.md scorecard row 2 ('shown at 3M, one seed ... Not yet at 10M, nor with Gemma and the outside calculator joined')"
          ],
          "notes": "Seed 401 (3M) and the 10M arms were still running or queued in the project notes of Oct 9; no result file for them existed on branch claude/8a-g-pc-results. Fix pass: the 'unsettled' chip uses the glossary grey (placeholder: no answer yet) instead of a warning orange the glossary does not define. Dated 'as of Oct 9' (the project notes of that day). Row 3 now names the part that is built and never run (the learned stop switch), not the whole finished design, which is only partly built (group 2 and the English talker are not).",
          "atMap": [
            [
              0.0176,
              0.0316
            ],
            [
              0.4985,
              0.4394
            ]
          ]
        },
        {
          "id": "s12",
          "duration": 24.5,
          "heading": "What to remember",
          "caption": [
            {
              "at": 0.0245,
              "text": "Three things to remember."
            }
          ],
          "lines": [
            "Less thinking, lower score: 73.01 to 0.66.",
            "Multi-step answers fall hardest: 99.9 to 0.0 at one round.",
            "One copy, smallest size, as of Oct 9: first result, not proof."
          ],
          "src": [
            "animations/source-g1-3m-s400.json",
            "scenes s02 to s11 of this chapter"
          ],
          "scoreHead": "points out of 100",
          "atMap": [
            [
              0.0316,
              0.0245
            ]
          ]
        }
      ]
    },
    "ch11": {
      "kicker": "Part 9 of 10",
      "title": "Learning while it sleeps",
      "blurb": "After a day of practice, the model studies what it found and settles it in. Here is how the sleep modes work, what they scored, and what is only planned.",
      "accent": "learned",
      "scenes": [
        {
          "id": "s01",
          "duration": 21.5,
          "heading": "Sleep sorts out the day",
          "caption": [
            {
              "at": 0.0279,
              "text": "People sort out the day's lessons while they sleep."
            },
            {
              "at": 0.2379,
              "text": "This model gets a night too: a day of practice, then a night of study."
            },
            {
              "at": 0.5475,
              "text": "Sleep is not a sixth part. It is a way of learning, tested so far only in research on earlier-design copies."
            }
          ],
          "L": {
            "day": "Day: practice",
            "night": "Night: sleep",
            "tiles": [
              "2→5",
              "4→9",
              "7→15"
            ],
            "settled": "settled in",
            "chip": "research result",
            "note": "Earlier-design copies, not the finished model",
            "pic": "picture only"
          },
          "src": [
            "animations/model-explainer-build/sources/pr-53-consolidation-sleep.md:4 (the model must run its own sleep)",
            "architecture/CREATIVE-SLEEP-IN-RUN1-2026-10-11.md:15-16 (all results on B2-lineage parents, none on B3)",
            "animations/engage/new-parts/FACTS-sleep.md:14,16 (sleep definition, scope)"
          ],
          "notes": "First caption is framing (people sleep), no number. Day/night boxes are a picture only.",
          "atMap": [
            [
              0.03,
              0.0279
            ],
            [
              0.3,
              0.2379
            ],
            [
              0.62,
              0.5475
            ]
          ]
        },
        {
          "id": "s02",
          "duration": 27.5,
          "heading": "By day: a puzzle with a hidden rule",
          "caption": [
            {
              "at": 0.0218,
              "text": "By day the model gets puzzles with a hidden rule: 2 gives 5, 4 gives 9, 7 gives 15."
            },
            {
              "at": 0.3158,
              "text": "It tries rules. A try counts only if it fits every example, so no answer key is needed."
            },
            {
              "at": 0.5969,
              "text": "Only x times 2 plus 1 fits all three, so 10 gives 21. That try is kept, and the night studies it."
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
            "keep": "kept for the night",
            "tag": "made-up example in the style of the test"
          },
          "src": [
            "creative-roadmap/creative-roadmap-page.html:248-256 (examples 2->5, 4->9, 7->15; tries x+3, x*2+1, x*3-1 fit 1, 3, 1 of 3; 'a try counts only if it fits every example'; kept and slept on)"
          ],
          "notes": "10 -> 21 is our arithmetic (10 x 2 + 1). The whole puzzle is a made-up example.",
          "atMap": [
            [
              0.03,
              0.0218
            ],
            [
              0.3,
              0.3158
            ],
            [
              0.62,
              0.5969
            ]
          ]
        },
        {
          "id": "s03",
          "duration": 34,
          "heading": "The old sleep and the newer sleep",
          "caption": [
            {
              "at": 0.0176,
              "text": "The old sleep scored 71.3 out of 100 on first tries and needed 558 to 610 updates by its formula. An update is a small nudge to every setting."
            },
            {
              "at": 0.4306,
              "text": "The newer sleep used 256 updates a night and averaged 76.1 over six copies."
            },
            {
              "at": 0.6579,
              "text": "But this is not a paired comparison. 71.3 is the old sleep's stored number, from its own near-copy starting copies. Each copy slept once."
            }
          ],
          "L": {
            "head": "first-try score, out of 100",
            "old": "Old sleep",
            "new": "New sleep",
            "oldVal": 71.3,
            "newVal": 76.1,
            "stepsHead": "updates",
            "oldSteps": "old sleep",
            "oldStepsVal": 558,
            "oldSuf": " to 610, by its formula",
            "newSteps": "new sleep, each night",
            "newStepsVal": 256,
            "stamp": "not a paired comparison",
            "chip": "research result"
          },
          "src": [
            "animations/model-explainer-build/sources/pr-53-consolidation-sleep.md:8 (76.1 mean of six parents; 71.3 needed), :9 (256 updates; 558-610 by its formula), :27 (not a paired comparison; 71.3 is the research loop's stored number on near-copy parents), :28 (one training run per parent)"
          ],
          "notes": "Old sleep = research-loop sleep, new sleep = consolidation sleep. 41.6 start and +/-2.5 are left out: no readable primary file.",
          "atMap": [
            [
              0.03,
              0.0176
            ],
            [
              0.36,
              0.4306
            ],
            [
              0.68,
              0.6579
            ]
          ]
        },
        {
          "id": "s04",
          "duration": 31.5,
          "heading": "One night of the newer sleep",
          "caption": [
            {
              "at": 0.019,
              "text": "The model makes its own tries, then sleeps for 256 updates of 1,024 rows. A row is one practice question."
            },
            {
              "at": 0.4133,
              "text": "Half the rows are fresh dreams: new questions written from a program it found, so none is read twice. Half are fresh skills rows."
            },
            {
              "at": 0.7267,
              "text": "Every 32 updates it checks itself on 128 held questions, and keeps its best saved model."
            }
          ],
          "L": {
            "tries": "Its own tries",
            "search": "Chain search",
            "rows": "rows",
            "rowsTo": 1024,
            "dreams": "Fresh dreams",
            "skills": "Fresh skills rows",
            "updates": "updates",
            "total": 256,
            "check": "check on 128 held questions",
            "keep": "keep best saved model",
            "pic": "picture only"
          },
          "src": [
            "animations/model-explainer-build/sources/pr-53-consolidation-sleep.md:15-18 (recipe: own tries, chain search, 256 updates of 1,024 rows, half fresh dreams, half fresh skills rows, check every 32 updates on 128 held questions, keep best checkpoint)"
          ],
          "notes": "Flags drawn are one per 32 updates (256 / 32 = 8, not written on screen). Picture only.",
          "atMap": [
            [
              0.03,
              0.019
            ],
            [
              0.36,
              0.4133
            ],
            [
              0.7,
              0.7267
            ]
          ]
        },
        {
          "id": "s05",
          "duration": 35,
          "heading": "Did sleep earn the credit?",
          "caption": [
            {
              "at": 0.0171,
              "text": "Did old skills get worse than before the sleep? No. Pooled over the six copies they rose by 0.52 points, likely range 0.31 to 0.74."
            },
            {
              "at": 0.4061,
              "text": "But a control that only practised the same skills rows raised them by 2.11, range 1.88 to 2.32."
            },
            {
              "at": 0.6946,
              "text": "So sleep did not beat plain practice: sleep minus control is −1.58. The gain is not shown to come from the sleep."
            }
          ],
          "L": {
            "axisHead": "change in old-skill score, in points",
            "ticks": [
              -2,
              0,
              2
            ],
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
            "animations/model-explainer-build/sources/pr-53-consolidation-sleep.md:11 (+0.52 [0.31, 0.74]), :12 (-1.58 [-1.79, -1.37]), :22 (replay-only control +2.11 [1.88, 2.32]; the +0.52 is not shown to come from the new skill)"
          ],
          "notes": "Range of -1.58 is drawn as a bar but its end numbers are not written.",
          "atMap": [
            [
              0.03,
              0.0171
            ],
            [
              0.36,
              0.4061
            ],
            [
              0.7,
              0.6946
            ]
          ]
        },
        {
          "id": "s06",
          "duration": 58,
          "heading": "New since Oct 9: two nights in a row",
          "caption": [
            {
              "at": 0.0103,
              "text": "A two-night recipe, SCM2, passed its test on 2 copies: night, a day of search, night. Reported, not rechecked."
            },
            {
              "at": 0.2388,
              "text": "Skills score, out of 100. Copy 1: 86.7 before, 82.9 after the standard two nights, 87.8 after SCM2."
            },
            {
              "at": 0.485,
              "text": "Copy 2: 87.8 before, 84.7 after the standard two nights, 89.3 after SCM2. No forgetting."
            },
            {
              "at": 0.6884,
              "text": "Learning kept up. On multi-step puzzles, first try against the standard two nights was −1.9 and +1.9. The pass mark was no worse than −2."
            },
            {
              "at": 0.9026,
              "text": "Only 2 copies so far. A check on more copies is still to come."
            }
          ],
          "L": {
            "head": "skills score after two nights, out of 100",
            "groups": [
              "Copy 1",
              "Copy 2"
            ],
            "cols": [
              "before",
              "standard two nights",
              "SCM2"
            ],
            "vals": [
              [
                86.7,
                82.9,
                87.8
              ],
              [
                87.8,
                84.7,
                89.3
              ]
            ],
            "mHead": "multi-step first try, SCM2 minus standard",
            "mVals": [
              "−1.9",
              "+1.9"
            ],
            "mark": "mark: no worse than −2",
            "chip": "passed, 2 copies",
            "warn": "reported, not rechecked; more copies still to come",
            "day1": "night 1",
            "day2": "day of search",
            "night1": "night 1",
            "night2": "night 2"
          },
          "src": [
            "fast-sleep/sleep7d/README.md:397 (skills in_dist N' / W2 / SCM2: 86.7 / 82.9 / 87.8 and 87.8 / 84.7 / 89.3), :398 (harm -1.1, -1.5, pass), :399 (multi-step first try SCM2 - W2 -1.9 and +1.9, mark >= -2, pass), :410 (verdict: passes on both parents)",
            "architecture/CREATIVE-SLEEP-IN-RUN1-2026-10-11.md:23 (SCM2 is the night recipe; two nights with a day of search between; pass on 2 parents; 6-parent confirm waits)",
            "animations/engage/new-parts/FACTS-sleep.md:67,136 (reported by the creative thread, not rechecked; 2-copy DEV screen)"
          ],
          "notes": "'Before' = the copy before the nights (N'). 'Standard two nights' = W2. The model's own row picking is not claimed to help (FACTS Z-26).",
          "atMap": [
            [
              0.03,
              0.0103
            ],
            [
              0.24,
              0.2388
            ],
            [
              0.46,
              0.485
            ],
            [
              0.68,
              0.6884
            ],
            [
              0.88,
              0.9026
            ]
          ]
        },
        {
          "id": "s07",
          "duration": 34,
          "heading": "Planned: sleep inside the first big run",
          "caption": [
            {
              "at": 0.0176,
              "text": "Planned, not done: sleep becomes part of the first big training run."
            },
            {
              "at": 0.1819,
              "text": "The 100M training itself stays as it is. After it comes a day-and-night phase, and the SCM2 nights are its recipe."
            },
            {
              "at": 0.4619,
              "text": "First it must pass on smaller test models, at 3M and then 10M. Those tests have not run yet. Results so far are from earlier-design copies."
            },
            {
              "at": 0.7952,
              "text": "Planned time: about a week after the main training. An estimate, not measured."
            }
          ],
          "L": {
            "main": "Main training, 100M",
            "phase": "Day-and-night phase",
            "ship": "Shipped model",
            "day": "day",
            "night": "night",
            "gate1": "test at 3M",
            "gate2": "test at 10M",
            "notRun": "not run yet",
            "chip": "planned",
            "est": "about a week, estimate"
          },
          "src": [
            "architecture/CREATIVE-SLEEP-IN-RUN1-2026-10-11.md:9-12 (100M pretraining unchanged, plus a day-and-night phase; recipes must pass on 3M and 10M first), :15-16 (all results on B2-lineage parents, none on B3), :23 (SCM2 nights), :56-62 (CB-1 3M, CB-2 10M), :64-67 (about a week of PC after pretraining; not measured), :66 (2 nights plus searches)"
          ],
          "notes": "Plan only. Night code (CB-0) is built (same file :84-94) but its test on a 3M model has not run (:90).",
          "atMap": [
            [
              0.03,
              0.0176
            ],
            [
              0.25,
              0.1819
            ],
            [
              0.55,
              0.4619
            ],
            [
              0.82,
              0.7952
            ]
          ]
        },
        {
          "id": "s08",
          "duration": 26,
          "heading": "What to remember",
          "caption": [
            {
              "at": 0.0231,
              "text": "Sleep is a night of study after a day of practice. The newer sleep scored 76.1 in 256 updates, not in a paired test."
            },
            {
              "at": 0.44,
              "text": "Two nights in a row kept old skills on 2 copies. Sleep in the first big run is planned, not done."
            },
            {
              "at": 0.7785,
              "text": "Next, Part 10: Creative mode: what it does when it gets stuck."
            }
          ],
          "L": {
            "cards": [
              "76.1 in 256 updates, not a paired test",
              "2 nights, no forgetting, 2 copies",
              "Planned for the first big run"
            ],
            "chips": [
              "tested",
              "tested",
              "placeholder"
            ],
            "chipLabels": [
              "research result",
              "reported, not rechecked",
              "planned"
            ],
            "next": "Next: Part 10",
            "nextT": "Creative mode: what it does when it gets stuck"
          },
          "src": [
            "animations/model-explainer-build/sources/pr-53-consolidation-sleep.md:8-9,27",
            "fast-sleep/sleep7d/README.md:397-399",
            "architecture/CREATIVE-SLEEP-IN-RUN1-2026-10-11.md:9-12",
            "content/global.json part 10 title"
          ],
          "notes": "Recap of earlier scenes. Teaser names the topic only.",
          "atMap": [
            [
              0.03,
              0.0231
            ],
            [
              0.4,
              0.44
            ],
            [
              0.72,
              0.7785
            ]
          ]
        }
      ]
    },
    "ch12": {
      "kicker": "Part 10 of 10",
      "title": "Creative mode: what it does when it gets stuck",
      "blurb": "When the model is stuck on a question, it tries many ideas and checks each one against the examples. This part says how that works, what an earlier test found, and what is still only planned as of Oct 11.",
      "accent": "learned",
      "scenes": [
        {
          "id": "s01",
          "duration": 18.5,
          "heading": "Stuck on a puzzle? You try ideas",
          "caption": [
            {
              "at": 0.0324,
              "text": "Picture yourself stuck on a puzzle. What do you do?"
            },
            {
              "at": 0.3636,
              "text": "You try an idea, check it, and try another one."
            },
            {
              "at": 0.6441,
              "text": "Our model can do the same, but only when it is stuck."
            }
          ],
          "ideas": [
            "idea 1",
            "idea 2",
            "idea 3"
          ],
          "puzzle": "stuck?",
          "chip": "creative mode: only when stuck",
          "picture": "picture only",
          "src": [
            "creative-roadmap/creative-roadmap-2026-10-06.md line 107 (Settled, Ben 10-05: creativity is only for when the model runs into trouble on a task)"
          ],
          "notes": "Hook. No numbers. Picture only.",
          "no": "no",
          "yes": "fits!",
          "atMap": [
            [
              0.0231,
              0.0324
            ],
            [
              0.3397,
              0.3636
            ],
            [
              0.6564,
              0.6441
            ]
          ]
        },
        {
          "id": "s02",
          "duration": 20.5,
          "heading": "How it notices it is stuck",
          "caption": [
            {
              "at": 0.0293,
              "text": "First the model makes one careful best-guess try, with creative mode switched off."
            },
            {
              "at": 0.3192,
              "text": "Then it checks that try on the question's own examples."
            },
            {
              "at": 0.6316,
              "text": "If the try does not fit the examples, the model counts itself stuck."
            }
          ],
          "q": "a made-up rule",
          "examples": [
            "3 gives 9",
            "4 gives 16"
          ],
          "try": "best guess: add the number to itself",
          "result": "3 gives 6: does not fit",
          "badge": "STUCK",
          "chip": "a fixed script, tested only on older small copies",
          "picture": "made-up example",
          "src": [
            "architecture/CREATIVE-SLEEP-IN-RUN1-2026-10-11.md line 20 (stuck test: greedy try with creative off, checked on the question's own examples; fails = stuck; built as a fixed script)",
            "architecture/CREATIVE-SLEEP-IN-RUN1-2026-10-11.md lines 14-16 (passed only on B2-lineage parents)"
          ],
          "notes": "3 gives 9 and 4 gives 16 are a made-up example (the rule 'times itself'), labelled on screen.",
          "atMap": [
            [
              0.02,
              0.0293
            ],
            [
              0.3389,
              0.3192
            ],
            [
              0.6578,
              0.6316
            ]
          ]
        },
        {
          "id": "s03",
          "duration": 22,
          "heading": "Stuck first: lots of tries",
          "caption": [
            {
              "at": 0.0273,
              "text": "Only then does it try lots of ideas: 32 sampled tries."
            },
            {
              "at": 0.2902,
              "text": "If none of the 32 fits, it gets 480 more, so 512 in all."
            },
            {
              "at": 0.7665,
              "text": "A question it already solved gets no extra tries."
            }
          ],
          "tries32": "32 tries",
          "more480": "+ 480 more tries",
          "total512": "512 in all",
          "picture": "picture only: which tries fit is made up",
          "chip": "tested on older small copies only",
          "src": [
            "creative-roadmap/creative-roadmap-2026-10-06.md lines 643-649 (job 8: 32 samples, then 480 more for questions with no example-fitting try, 512 in all; solved questions get nothing more)",
            "architecture/CREATIVE-SLEEP-IN-RUN1-2026-10-11.md line 21 (32 sampled tries, then 480 more only where none fits)"
          ],
          "notes": "The grid is a picture. Number of dots equals the numbers 32 and 480; which dots are crossed or green is made up.",
          "solved": "already solved: no extra tries",
          "atMap": [
            [
              0.0158,
              0.0273
            ],
            [
              0.3377,
              0.2902
            ],
            [
              0.6596,
              0.7665
            ]
          ]
        },
        {
          "id": "s04",
          "duration": 28,
          "heading": "The example checker keeps what fits",
          "caption": [
            {
              "at": 0.0214,
              "text": "A checker runs every try on the examples that came with the question. It needs no answer key."
            },
            {
              "at": 0.356,
              "text": "A try that fits every example is kept. The rest are thrown away."
            },
            {
              "at": 0.5683,
              "text": "For each question it keeps at most 2 different fitting tries."
            }
          ],
          "examples": "examples: 3 gives 9, 4 gives 16",
          "tries": [
            {
              "t": "add 3 to the number",
              "r": "3 gives 6: no"
            },
            {
              "t": "times itself",
              "r": "9 and 16: fits"
            },
            {
              "t": "times 3",
              "r": "4 gives 12: no"
            },
            {
              "t": "add 6",
              "r": "4 gives 10: no"
            }
          ],
          "kept": "kept to practise on",
          "picture": "made-up example",
          "chip": "a Python script today; the checker for the new design is the main build risk",
          "src": [
            "architecture/CREATIVE-SLEEP-IN-RUN1-2026-10-11.md line 22 (example checker, Python harness) and lines 38-48 (checker on the new design is the main build risk)",
            "creative-roadmap/creative-roadmap-2026-10-06.md line 648 (at most 2 distinct fitting tries per question, a fixed setting in job 8)"
          ],
          "notes": "All the numbers in the tries are a made-up example. First try 'add 3' gives 6 for input 3 (not 9). 'add 6' gives 9 for 3 and 10 for 4. 'times 3': 3 gives 9 (fits), 4 gives 12 (no).",
          "cap2": "at most 2 kept",
          "atMap": [
            [
              0.0167,
              0.0214
            ],
            [
              0.338,
              0.356
            ],
            [
              0.6593,
              0.5683
            ]
          ]
        },
        {
          "id": "s05",
          "duration": 37.5,
          "heading": "The earlier test, and a near miss",
          "caption": [
            {
              "at": 0.016,
              "text": "We tried it on an older small design, on two trial copies, with development questions."
            },
            {
              "at": 0.2004,
              "text": "The search worked: it found 180 and 237 checked tries on multi-step questions. The bars were 75 and 90."
            },
            {
              "at": 0.485,
              "text": "After two nights, first-try scores on multi-step questions rose 10.4 and 9.7 points. The bar was 10."
            },
            {
              "at": 0.7365,
              "text": "Copy B gained 15 of 154 questions where 16 were needed. Not a pass, and not proved wrong."
            }
          ],
          "leftTitle": "checked tries found",
          "rightTitle": "first-try gain, points",
          "left": [
            {
              "label": "Copy A (bar 75)",
              "value": 180
            },
            {
              "label": "Copy B (bar 90)",
              "value": 237
            }
          ],
          "right": [
            {
              "label": "Copy A (bar 10)",
              "value": 10.4
            },
            {
              "label": "Copy B (bar 10)",
              "value": 9.7
            }
          ],
          "miss": "Copy B: gained 15 of 154 questions, 16 needed",
          "chip": "older small design, 2 copies, development questions",
          "src": [
            "creative-roadmap/creative-roadmap-2026-10-06.md line 661 (job 8 result; shown, DEV, s100 / s101; climb mark missed as written on s101 by less than one question)",
            "creative-roadmap/creative-roadmap-2026-10-06.md line 663 (night-1 multi-step records 180 / 237, needed 75 / 90)",
            "creative-roadmap/creative-roadmap-2026-10-06.md line 665 (multi-step first try +10.4 / +9.7; 15 of 154 where the mark needed 16)",
            "creative-roadmap/creative-roadmap-2026-10-06.md lines 647-650 (climb bar +10 on both parents)"
          ],
          "notes": "Copy A = seed s100, copy B = seed s101. 'Checked tries' = the roadmap's multi-step records (night 1). Gain = multi-step first try after night 2 minus before (points). The stricter reading stands: not a pass as written, not proved wrong.",
          "verdict": "not a pass, not proved wrong",
          "atMap": [
            [
              0.0136,
              0.016
            ],
            [
              0.2563,
              0.2004
            ],
            [
              0.4989,
              0.485
            ],
            [
              0.7415,
              0.7365
            ]
          ]
        },
        {
          "id": "s06",
          "duration": 36,
          "heading": "At night it practises what it found",
          "caption": [
            {
              "at": 0.0167,
              "text": "At night it practises on its own checked tries. That is the sleep from Part 9."
            },
            {
              "at": 0.2115,
              "text": "Two nights, with a day of search between them."
            },
            {
              "at": 0.3369,
              "text": "On two copies, harm to old skills was -1.1 and -1.5 points. Below zero means no forgetting."
            },
            {
              "at": 0.6031,
              "text": "Multi-step first tries matched the standard nights: -1.9 and +1.9 points. A check on six copies has not been run."
            }
          ],
          "steps": [
            "day 1: search",
            "night 1: practise",
            "day 2: search",
            "night 2: practise"
          ],
          "cardA": "old skills, harm in points",
          "cardB": "multi-step first try vs standard nights, points",
          "a": [
            -1.1,
            -1.5
          ],
          "b": [
            -1.9,
            1.9
          ],
          "chip": "passed on 2 older small copies only",
          "src": [
            "architecture/CREATIVE-SLEEP-IN-RUN1-2026-10-11.md line 23 (SCM2 nights: 2 nights with a day of search between; PASS on 2 parents: no forgetting -1.1 / -1.5, multi-step first try -1.9 / +1.9 vs W2; 6-parent confirm waits for job 9)",
            "creative-roadmap/creative-roadmap-2026-10-06.md line 100 (two nights at the middle rate matched the standard two nights' climb, no lost skills)"
          ],
          "notes": "Part 9 is 'Learning while it sleeps'.",
          "atMap": [
            [
              0.0158,
              0.0167
            ],
            [
              0.2572,
              0.2115
            ],
            [
              0.4987,
              0.3369
            ],
            [
              0.7401,
              0.6031
            ]
          ]
        },
        {
          "id": "s07",
          "duration": 42,
          "heading": "Where it stands as of Oct 11",
          "caption": [
            {
              "at": 0.0143,
              "text": "As of Oct 11, creative mode is planned for the first big run, in a day-and-night phase after the main training."
            },
            {
              "at": 0.2389,
              "text": "It has four parts: the stuck test, the stuck-first search, the example checker, and the nights."
            },
            {
              "at": 0.5051,
              "text": "Dropped from that run: the small creative add-on, because it did not survive the nights."
            },
            {
              "at": 0.6652,
              "text": "Sealed tests at 3M and 10M are planned, not yet run. So far it passed only on older small designs."
            }
          ],
          "parts": [
            "stuck test",
            "stuck-first search",
            "example checker",
            "nights"
          ],
          "partsChip": "built (unit tests only), not yet run on the big design",
          "dropped": "dropped: creative add-on",
          "tests": "sealed tests at 3M and 10M",
          "testsChip": "planned, not yet run",
          "src": [
            "architecture/CREATIVE-SLEEP-IN-RUN1-2026-10-11.md lines 8-12 (run-1 = pretraining plus a day-and-night phase) and line 27 (run-1 creative mode = stuck test + stuck-first search + example checker + SCM2 nights; add-on dropped)",
            "architecture/CREATIVE-SLEEP-IN-RUN1-2026-10-11.md line 25 (adapter F: not in run-1, does not survive the worker's sleep)",
            "architecture/CREATIVE-SLEEP-IN-RUN1-2026-10-11.md lines 50-55 (sealed CB-1 at 3M and CB-2 at 10M) and lines 84-98 (CB-0 built, unit tests only; mark 2 needs the 3M checkpoint)",
            "architecture/CREATIVE-SLEEP-IN-RUN1-2026-10-11.md lines 14-16 (all passed only on B2-lineage parents)"
          ],
          "notes": "Status only. Nothing has run on the new design.",
          "atMap": [
            [
              0.0143,
              0.0143
            ],
            [
              0.2565,
              0.2389
            ],
            [
              0.4988,
              0.5051
            ],
            [
              0.7411,
              0.6652
            ]
          ]
        }
      ]
    },
    "ch14": {
      "kicker": "Wrap-up",
      "title": "What is proven, what is not, what comes next",
      "blurb": "An honest ledger as of Oct 9: which parts have a result, which are only built or planned, the open risks, and what comes next.",
      "accent": "tested",
      "scenes": [
        {
          "id": "s01",
          "duration": 33,
          "heading": "Where we stand on Oct 9",
          "caption": [
            {
              "at": 0.0182,
              "text": "The honest ledger, as of Oct 9: what has a result, and what does not."
            },
            {
              "at": 0.3971,
              "text": "The reader and thinker have results at 3M, about three million learned numbers. So does the outside calculator."
            },
            {
              "at": 0.7231,
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
              "text": "Adding Gemma: +2.67 points in 6 of 6 copies. One safety mark missed."
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
              "text": "Outside tool, plain code. Two checks not clean."
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
                  "label": "English: not built"
                }
              ],
              "text": ""
            }
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:29-38 (parts table: reader row 31, thinker 34, call writer 35, learned stop 36, calculator 37, talker 38)",
            "architecture/FINISHED-MODEL-2026-10-09.md:62-64 (calls at any round: built, untested)",
            "big-run/PLAN.md:75 and :136 (the learned stop is built, never run), :133 (EGE 3M: +2.67 over B2, ahead on 6 of 6), :135 (calculator outside passed at 3M, leak mark cleared by the owner)",
            "architecture/MARKS-D0-T1-2026-10-07.md:200-203 (Record 13: marks 1-3 and 6 pass; mark 5 holds on 5 of 6; mark 4 leak not a sealed pass, cleared by the owner)"
          ],
          "notes": "Reader +2.67, 6 of 6 seeds (RESULTS-EG2 line 108: per seed +1.14 +2.70 +3.44 +2.63 +3.54 +2.57), but the 6-seed confirm missed its zero-round leak mark (6.59 vs 4.62), FINISHED:31; the leak is explained in s08. Checker edits: the +2.67 is the gain from adding Gemma to B2 (the box now says 'Adding Gemma'); calculator text now says 'Two checks not clean' (swap check 5 of 6, leak check missed then cleared by the owner, shown in s05), because FINISHED:37 and MARKS Record 13 say the calculator confirm is 'PASS with mark 4 cleared by Ben and mark 5 unscored on seed 205', not a clean pass. Calculator column covers the call writer (tested in T1SDR, 6 seeds) and the any-round change (B3 group 1, built, never run, FINISHED:62-64). Talker: FINISHED:38 says 'today a small stand-in; the English talker is unbuilt'; the brief's 'stand-in works' is not a stated test result, so the chip only says 'stand-in only'. 3M = about three million learned numbers (T1SDR n_params 3,314,132; G-B2 3,544,913; GLOSSARY wording). Duration 43 -> 45 for the 7 added words. Fixer edits: Talker chip 'stand-in only' -> 'English: not built' so it says what the caption and s07 say (FINISHED:38: a small stand-in today, the English talker unbuilt; the map box already says 'stand-in today'). 100M chip left amber on purpose: the 100M rung exists as a config and a counted size (g8a/configs.py RUNGS['100M'], FINISHED:21-22) but its pool is 'not built' and it has never been run or fit-checked (PLAN:29, :93), so 'built, never run' is the right colour.",
          "atMap": [
            [
              0.02,
              0.0182
            ],
            [
              0.33,
              0.3971
            ],
            [
              0.66,
              0.7231
            ]
          ]
        },
        {
          "id": "s03",
          "duration": 29.5,
          "heading": "Result one: the thinking does the work",
          "caption": [
            {
              "at": 0.0203,
              "text": "Result one. On 6,040 questions kept aside, the model scored 73.01 out of 100 with its thinking on."
            },
            {
              "at": 0.3669,
              "text": "With thinking switched off it scored 0.66. A plain model of the same size scored 67.12."
            },
            {
              "at": 0.6693,
              "text": "So the thinking does the work, on one copy at the smallest size. Bigger sizes are untested."
            }
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
            "gap": "Gap over the plain model: +5.9 points",
            "caveat": "Older design: calculator inside, 12 fixed rounds. Second copy and 10M were not in by Oct 9."
          },
          "src": [
            "animations/source-g1-3m-s400.json and branch origin/claude/8a-g-pc-results results/8a-g/pc/8aG1d-pc/8aG1d-3M-s400/{B2,PT}/RESULT.json (G-B2 4,410 of 6,040 = 73.01; loops:0 40 of 6,040 = 0.66; G-PT 4,054 of 6,040 = 67.12; n_loops 12; recomputed by the checker)",
            "whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md:187-189 (addendum G: same numbers; one rung of one seed)",
            "architecture/FINISHED-MODEL-2026-10-09.md:109-110 (shown on one seed), :125-126 (G1 tests the calculator-inside, 12-round model), :94 (12 rounds in G1)",
            "big-run/PLAN.md:74 and :225 (G1's 3M lead for G-B2 over G-PT was +5.9 on one seed); :99 and :134 (3M seed 401 and the 10M arms still to run on Oct 9)"
          ],
          "notes": "Same numbers as ch04 s14, ch06 s03, ch09 s04. 73.01 belongs to the older design with the calculator inside and 12 fixed rounds (the Gemma-fronted G-B2 arm, 3M, seed 400); the finished design has not produced a number yet. The +5.9 gap is quoted from PLAN:74/:225, not computed here (73.01 - 67.12 = 5.89). The plain model G-PT has the same Gemma front and is within 1.4% of the size (3,495,936 vs 3,544,913). Checker edits: gap note now says 'points'; the caveat now says 'were not in by Oct 9' so it stays true after the date (the PLAN.md revision note of Oct 10 reports a second 3M copy, seed 401, 73.7 vs 68.0, not recomputed by the project; the video is dated Oct 9 and says one copy). Duration 40 -> 41. Fixer edit (JS timing only): the Thinking-off and Plain-model counts now start 0.15 s and 0.65 s after caption 2 appears and finish about 1.8 s later, so no frame shows a number still counting while the caption names the final value.",
          "atMap": [
            [
              0.0146,
              0.0203
            ],
            [
              0.3374,
              0.3669
            ],
            [
              0.6602,
              0.6693
            ]
          ]
        },
        {
          "id": "s04",
          "duration": 31,
          "heading": "Result two: the calculator can sit outside",
          "caption": [
            {
              "at": 0.0194,
              "text": "Result two. The calculator is plain code outside the model. In the tested version the thinker writes a slip; the reader reads the reply."
            },
            {
              "at": 0.3378,
              "text": "Over 6 copies it scored 0.62 points above a similar calculator-inside design. The likely range includes zero."
            },
            {
              "at": 0.7185,
              "text": "With the calculator switched off, the questions that need it score 0.0, so the model really uses it."
            }
          ],
          "labels": {
            "slip": "sub 12 5",
            "calc": "Outside calculator",
            "replyNote": "read by the reader",
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
            "off": "Calculator off: 0.0"
          },
          "values": {
            "lo": -0.23,
            "mid": 0.62,
            "hi": 1.46
          },
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:106-107 (T1SDR matched B2 over 6 seeds: pooled-5 +0.62, CI -0.23 to +1.46; calculator off scores 0.0)",
            "architecture/MARKS-D0-T1-2026-10-07.md:200 and :204 (Record 13: +0.62, CI -0.23 to +1.46; tool off 0.0)",
            "branch origin/claude/custom-reader-talker-4x309r custom_io/results/{70-vast-t1sdr,80-vast-t1sdr-confirm,80b-pc-t1sdr-confirm}/T1SDR_s200..s205 and 33-pc-confirm-b2/B2_s200..s205 RESULT.json (pooled-5 differences recomputed by the checker; extra.noexec.program_families 0.0 on 2,085 questions, 0.048 on s203)",
            "architecture/FINISHED-MODEL-2026-10-09.md:42-57 (the sub 12 5 = 7 example)"
          ],
          "notes": "The slip 'sub 12 5' and reply '7' are the project's made-up example (Tom's apples), a picture, not a result. The number-line is drawn to scale for the three numbers only (400 px per point). Recomputed from the raw files: per-seed T1SDR minus B2 on pooled-5 (6,040 questions) +1.937, -0.149, +0.182, +0.894, +0.960, -0.116; mean 0.618 = +0.62; sd 0.806, t(5) = 2.571, CI -0.228 to +1.464 = -0.23 to +1.46. Calculator off: extra.noexec.program_families = 0.0 on five copies and 0.048 on s203, over 2,085 questions that need the calculator. Chain-5 99.6-99.8 (FINISHED:106) is left out. Brief says 'matched'; the source says matched with +0.62 and a range that includes 0, so the caption says so. T1SDR is not a one-change twin of B2 (copy fixes and drills), so the caption says 'a similar calculator-inside design' (as ch05 s12). Checker edits: caption 3 says 'the questions that need it' instead of 'program questions'; the swap-check caption and note moved to the new s05 together with the leak check, which this scene did not mention at all. Duration 44 -> 38. Fixer edits (JS only): the green 'tested: 6 copies' chip moved from under the made-up '7' box to the left end of the number line it describes (the +0.62 measurement); the made-up reply box border is calculator slate, not tested-green.",
          "atMap": [
            [
              0.02,
              0.0194
            ],
            [
              0.3,
              0.3378
            ],
            [
              0.62,
              0.7185
            ]
          ]
        },
        {
          "id": "s05",
          "duration": 26.5,
          "heading": "Two calculator checks were not clean",
          "caption": [
            {
              "at": 0.0226,
              "text": "The calculator had six pass marks. Four passed; two were not clean."
            },
            {
              "at": 0.3408,
              "text": "Swap check: with add and sub swapped, answers followed the reply on 5 of 6 copies; the sixth was lost."
            },
            {
              "at": 0.6594,
              "text": "Wrong-thinking leak check: five of six copies read above the limit of 5. The project owner cleared it on Oct 9."
            }
          ],
          "cards": [
            {
              "title": "Swap check",
              "big": "5 of 6",
              "text": "First reading 97.1 to 97.6, pass line 99; passed after the scoring rule was corrected.",
              "chip": {
                "kind": "untested",
                "label": "incomplete",
                "color": "warn"
              }
            },
            {
              "title": "Wrong-thinking leak check",
              "big": "5.00 to 5.59",
              "text": "Right answers with another question's thinking swapped in, out of 100. Limit 5.",
              "chip": {
                "kind": "untested",
                "label": "limit missed, owner-cleared",
                "color": "warn"
              }
            }
          ],
          "src": [
            "architecture/MARKS-D0-T1-2026-10-07.md:198-205 (Record 13: marks 1-3 and 6 pass; mark 5 holds on 5 of 6, seed 205 unscored, checkpoint lost; mark 4 leak did not pass as sealed, donor 5.59/5.15/5.59/5.07/5.00/5.59 against a flat line 5; Ben cleared it 8:21 AM ET 10-09; 'the report must carry both facts')",
            "architecture/MARKS-D0-T1-2026-10-07.md:47-55 and :81 (Amendment 2: the 6-seed confirm runs marks 1-6)",
            "architecture/FINISHED-MODEL-2026-10-09.md:37 (leak mark cleared) and :106-108 (mark 5 holds on 5 of 6 seeds; seed 205 unscored)",
            "branch origin/claude/custom-reader-talker-4x309r custom_io/results/*t1sdr*/T1SDR_s200..s205 RESULT.json: lesions.donor.in_dist.exact 5.588, 5.147, 5.588, 5.074, 5.000, 5.588 (n = 1,360); extra.opswap.swap_match 97.47, 97.23, 97.11, 97.34, 97.23, 97.59; custom_io/PASS-MARKS.md:462-464 (limit) and :777 (first reading); MARKS:189-196 (Amendment 12 scoring rule)"
          ],
          "notes": "NEW scene written by the checker. Reason: s04 and the ledger show the calculator as tested over 6 copies, but MARKS Record 13 says the confirm is a PASS only with mark 4 (leak) cleared by the owner and mark 5 (swap) unscored on seed 205, 'the report must carry both facts'; the old s04 carried only the swap fact (and called the missing copy 'one file'). Six marks: Amendment 2 (MARKS:78-81) runs 'marks 1-6'; Record 13: marks 1-3 and 6 pass = four. Swap: pass line 99 (MARKS:201); the run's own first reading was 97.1 to 97.6 (raw swap_match 97.11-97.59, recomputed); the Amendment 12 definition was written after those results were read (MARKS:189), so the card says it passed after the scoring rule was corrected, as ch05 s13 does. Leak: this is the calculator's own leak check (another question's thinking swapped in, count answers still right, in points out of 100 over 1,360 familiar questions), a different test from the reader's zero-round leak in s08. Five of six copies read above the limit 5 (5.07 to 5.59); the sixth read exactly 5.00. The big number shows the range over all six copies (5.00 to 5.59). Fixer edits: the leak card and caption 3 are named 'Wrong-thinking leak check' so this limit of 5 (1,360 familiar questions, another question's thinking swapped in) is not mixed up with the reader's zero-round leak limit of 4.62 (s08). Duration 43 -> 44 for the 2 added words.",
          "atMap": [
            [
              0.02,
              0.0226
            ],
            [
              0.3,
              0.3408
            ],
            [
              0.64,
              0.6594
            ]
          ]
        },
        {
          "id": "s07",
          "duration": 33,
          "heading": "What has never been done",
          "caption": [
            {
              "at": 0.0182,
              "text": "Never run together: the Gemma reader, outside calculator, any-round calls and learned stop."
            },
            {
              "at": 0.2187,
              "text": "The first run is planned at 3M, after the size test (does bigger help?) finishes."
            },
            {
              "at": 0.4204,
              "text": "Bigger sizes are unproven: from 3M to 10M an earlier test gained +0.49 points for ours, +3.77 for plain, but had a setting bug."
            },
            {
              "at": 0.8401,
              "text": "The English talker and the race are planned. Games are paused."
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
                "label": "not redone"
              }
            },
            {
              "text": "English talker",
              "chip": {
                "kind": "placeholder",
                "label": "planned, not built"
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
            "architecture/FINISHED-MODEL-2026-10-09.md:123-124 (outside calculator and Gemma never run together; first run B3 group 1 at 3M seed 400 after G1), :62-64 (calls at any round built, untested), :36 (learned stop built, never run)",
            "big-run/PLAN.md:117-120 (B2 +0.49 from 3M to 10M, plain step model +3.77 (shown); B2 ran with 9 letter slots instead of 36 and answers cut to 8 letters), :132 (table row, 6 seeds / 5 seeds), :134 (G1 re-run in progress)",
            "whole-model-roadmap/8A-10M-RESULT-2026-10-08.md:49 and :68 (3M to 10M: +0.49, CI -0.74 to +1.72; plain step model +3.77 over 5 seeds)",
            "architecture/FINISHED-MODEL-2026-10-09.md:38 (English talker unbuilt), :167 (games paused); big-run/PLAN.md:35 and :79 (SmolLM2-360M race, planned, needs the open-English talker)"
          ],
          "notes": "The pieces sliding together is a picture of the plan, not a measurement. The +0.49 (6 seeds) and +3.77 (plain step model, 5 seeds) are gains from 3M to 10M on pooled-5, from 8A-10M-RESULT:68; the caption now says 'from 3M to 10M ... gained'. FINISHED:128-129 quotes a different pair of earlier 10M-ladder gains (+0.03 and +0.28 vs plain +3.08 and +4.25); these are the seed 400 and 401 rows of the same table (8A-10M-RESULT:62-63), and FINISHED says the register bug means they do not count either way. The caption uses PLAN:117-120, the 'only result on size'. Checker edits: caption 1 'All parts together has never run' -> 'Never run together' (it lists four pieces, not all parts: no English talker exists); caption 2 explains 'size test' in three words (G1 is the removed 'does bigger help' part); caption 4 'games come later' -> 'Games are paused' (FINISHED:167; the card already says paused). Duration 43 -> 45 for the added words. Fixer edits: card chip 'not done' -> 'not redone' (the caption says an earlier test ran with a setting bug; only the fixed-settings run is not done); caption 4 'The talker and the race come later' -> 'The English talker and the race are planned' (cards: English talker not built, race planned; FINISHED:21 and :38 talker about 25M planned; PLAN:35 and :79 race planned) so nothing sounds like a later part of this video. Still open for the coordinator: the +0.49 / +3.77 sentence about the removed size chapter is longer than one clause.",
          "atMap": [
            [
              0.02,
              0.0182
            ],
            [
              0.22,
              0.2187
            ],
            [
              0.4,
              0.4204
            ],
            [
              0.72,
              0.8401
            ]
          ]
        },
        {
          "id": "s08",
          "duration": 28,
          "heading": "Open risks, said plainly",
          "caption": [
            {
              "at": 0.0214,
              "text": "A leak is a right answer with zero thinking rounds. Six Gemma-reader copies averaged 6.59 against a limit of 4.62."
            },
            {
              "at": 0.4688,
              "text": "Deeper thinking can cost points; the stop may fire too early."
            },
            {
              "at": 0.7105,
              "text": "The big run's web text stays locked until the sealed test questions are fingerprint-checked."
            }
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
            "one": "Separate run, familiar questions (seed 200): Gemma reader 18.09, same model without it 1.40.",
            "chip": "limit missed"
          },
          "cards": [
            {
              "title": "Depth costs points",
              "text": "On one test, 16 rounds cost 1.2 to 1.9 points."
            },
            {
              "title": "Stop may fire early",
              "text": "Our guess, never shown."
            },
            {
              "title": "Big-run web text is locked",
              "text": "Sealed-test fingerprints must be checked first."
            }
          ],
          "src": [
            "architecture/FINISHED-MODEL-2026-10-09.md:31 (mean 6.59 against limit 4.62, plain B2 3.62 + 1.0), :111-112 (separate seed-200 in-distribution run: EGE 18.09 against 1.40 for B2V, cause not settled)",
            "branch origin/claude/custom-reader-talker-4x309r custom_io/results/39-pc-ege-confirm/RESULTS-EG2.md:111 (loops0_mean 6.59, plain_b2_loops0_mean 3.62, mark 4 False); custom_io/PASS-MARKS.md:344 and :375 (18.09; B2V 1.40)",
            "architecture/FINISHED-MODEL-2026-10-09.md:149-150 (16 rounds cost 1.2-1.9 points on one B2 probe); no-hardcoding/INPUT-UNITS-2026-10-07.md:39 (40-loops-probe, one seed); :66-69 (stop may fire early, suggested); :147-148 (web pool gate)",
            "big-run/PLAN.md:77, :139 and :184 (B3 3M pool 62% web; protected-panel hash check: no pass on record, must pass before the ship build); data-pool/DATA-POOL-PLAN-2026-10-06.md:162-164 (small-rung web slices already used; hashes not merged yet)"
          ],
          "notes": "Leak mark A (reader, missed, not cleared) is a different test from leak mark B (calculator, s05). This scene is about A only. The bars are the six-copy confirm (EGE seeds 202-207; FINISHED:31, addendum 15); 'Six Gemma-reader copies' names whose leak it is. The 18.09 / 1.40 line is a separate seed-200 in-distribution run (2-seed screen, EGE_s200 246 of 1,360 = 18.09; B2V_s200 19 of 1,360 = 1.40), PASS-MARKS addendum 14, so it is labelled as its own run and not as one of the six. The comparison is the same model WITHOUT the Gemma reader (B2V = B2 letters only), not the 'plain model' of the other scenes; the old label 'plain model' was wrong against the GLOSSARY. Rounds: FINISHED:149 says 'On one B2 probe, 16 rounds cost 1.2-1.9 points'. Raw check: probe 40-loops-probe B2_s100 in_dist 89.35 at 8 rounds and 88.21 at 16 (-1.15; -1.87 on no-call questions); B2_s101 -0.85; q33 B2_s200 90.51 -> 88.60 (-1.91) and B2_s201 91.54 -> 89.93 (-1.62). So the cost is 0.85 to 1.91 points over four B2 copies; the card keeps the source's '1.2 to 1.9 on one test' (one probe copy, all questions to no-call questions) and now says 'points'. Web text: FINISHED:147-148 says the pool 'must not be used for training until the protected-panel hashes are merged and checked', but the 3M test pools already hold web rows (PLAN:77: the B3 3M pool is 62% web; DATA-POOL-PLAN:162-164: web slices are 62% of the 8a pools, 'Ben chose start now for 8a; the check must pass before 8c'; PLAN:139 and :184: must pass before the ship build). The caption and card therefore say 'the big run's web text'. Checker edits: caption 1 names the Gemma reader and the 6 copies; the 'one' label no longer calls the without-Gemma model 'plain'; card 1 adds 'points'; card 3 and caption 3 scoped to the big run; card 2 title shortened for the reading budget. 'Out of 100' follows the leak being a share of questions. Fixer edit (JS only): the two leak bars are drawn on the stated 0 to 100 scale (max 100, same scale as s03), so 6.59 and 4.62 show as slivers; values unchanged.",
          "atMap": [
            [
              0.0133,
              0.0214
            ],
            [
              0.337,
              0.4688
            ],
            [
              0.6607,
              0.7105
            ]
          ]
        },
        {
          "id": "s10",
          "duration": 33,
          "heading": "The next gates, in order",
          "caption": [
            {
              "at": 0.0182,
              "text": "In order: the size test finishes, then a test of experts (many small specialist networks, not covered here)."
            },
            {
              "at": 0.2827,
              "text": "Then a 100M fit check (memory and speed) and the four pieces together at 3M."
            },
            {
              "at": 0.5,
              "text": "Then hand-written pieces are replaced, 10M and 30M follow, and a results readout is planned for Oct 31."
            },
            {
              "at": 0.7697,
              "text": "One big run waits for clear results and for the plan to be 90% sure it passes its marks."
            }
          ],
          "chip": "plan only: dates are suggestions",
          "steps": [
            "Size test (G1)",
            "Experts test",
            "100M fit check",
            "Four pieces, 3M",
            "10M, then 30M",
            "Readout, Oct 31 (planned)",
            "One big run",
            "Rented compute: owner's call"
          ],
          "src": [
            "big-run/PLAN.md:40-41 (G1 finishes, then the post-G1 chain in order: GX stage 1, fc100 fit check, g2c3, B3 group 1 at 3M seed 400), :43 (group 2 replaces hand code, then B3 10M with groups 1 and 2), :44 (B3 30M), :45 (10-31 ladder readout), :29 (fit check = memory and speed)",
            "big-run/PLAN.md:53 (the 90% bar: the plan author's reading of a relayed rule), :28 and :50 (no rentals; Vast credit is the owner's call)",
            "architecture/FINISHED-MODEL-2026-10-09.md:24-25 (no rentals; the owner: demonstrable results first), :136-139 (experts: GX stage 1 on the PC), :123-124 (first run B3 group 1 at 3M after G1), :100-102 (group 1 = the four pieces + 2,000-letter inputs; group 2 = the hand-code replacements)",
            "big-run/PLAN.md:62-64 (the SCORECARD section; the brief's 'PLAN sec. 5' is really the G1 gate at line 197)"
          ],
          "notes": "G1: as of Oct 9 its 3M seed 401 is finishing and the 10M arms follow (PLAN:40). The seed-401 files in the snapshot belong to earlier 8a runs, not G1. The 90% bar is the plan author's reading of a relayed rule (PLAN:53). Every date is 'planned'; the Nov to Dec range for the 100M run (PLAN:46-49) is left out as an estimate. The PLAN.md revision note of 10-10 says the G1 gate moves out by 2-3 days; the video is dated Oct 9 and promises no dates. Checker edits: (1) 'the experts test' was a pointer to the removed ideas chapter; it now says what it is in six words and that it is not covered here (cut rule). (2) 'all parts together at 3M' -> 'the four pieces together at 3M': B3 group 1 is the Gemma reader + outside calculator + any-round calls + learned stop (+2,000-letter inputs), not all parts (no English talker, hand-written pieces still on the path). (3) The chain skipped B3 group 2 (replace hand-written pieces), which PLAN:43 puts before B3 10M; added to caption 3. (4) 'team readout' -> 'results readout' (PLAN:45: the ladder readout is the 'demonstrable results' the owner asked to see). (5) 90% clause now says what the 90% is about (PLAN:53: 'does what its written marks say'); 'rented compute' stays in the last box (PLAN:28). (6) 'G1 size test' -> 'Size test (G1)' (plain name first). The two-box fit check text 'memory and speed' is PLAN:29. g2c3 (the plain control at the B3 caps) is left out; it is a test arm, not a gate. Durations 39 -> 45. Fixer edit: chip 'plan only, no dates promised' -> 'plan only: dates are suggestions', so it no longer contradicts the Oct 31 box; PLAN:47 labels every date in the path 'suggested'. The Oct 31 box and caption are unchanged.",
          "atMap": [
            [
              0.02,
              0.0182
            ],
            [
              0.22,
              0.2827
            ],
            [
              0.44,
              0.5
            ],
            [
              0.66,
              0.7697
            ]
          ]
        },
        {
          "id": "s12",
          "duration": 31,
          "heading": "What to remember",
          "caption": [
            {
              "at": 0.0194,
              "text": "The thinking does the work, shown on one copy at the smallest size."
            },
            {
              "at": 0.2445,
              "text": "The calculator can sit outside, shown on 6 copies at 3M, with two checks not clean. Most of the rest is built or planned."
            },
            {
              "at": 0.5695,
              "text": "The plan's judgment: nothing is ready to buy. It works at 3M, but nobody has shown it improves faster with size than a plain model."
            }
          ],
          "parts": [
            "Reads the question.",
            "Thinks in rounds.",
            "Outside tool: does exact sums.",
            "Rings when done.",
            "Stand-in today. Writes words."
          ],
          "chip": "the plan's own judgment",
          "design": "New design, being built, not tested: works in turns; the talker's line calls the calculator; the whole reader reads the reply.",
          "notes_on": [
            "Nothing is ready to buy yet.",
            "Plan's count on Oct 9: 0 of 9 goals fully green. Its guess for Oct 31: 5 or 6."
          ],
          "src": [
            "kit/GLOSSARY.md (the four parts, the outside calculator and the one analogy)",
            "big-run/PLAN.md:115-116 (bottom line 1: nothing is ready to buy; it works at 3M, nobody has shown it gets better with size faster than a plain model), :82 ('Today: 0 of 9 fully green'), :89 (realistic read at Oct 31: 5 or 6)",
            "big-run/PLAN.md:74 and :133-134 (size claim untested for the model as specified); architecture/FINISHED-MODEL-2026-10-09.md:109-110 and :106-108"
          ],
          "notes": "Both numbers are the plan's own judgment, labelled as such on screen. No ch00 chapter file exists in the worktree; the five-part sentences follow the glossary. Checker edits: (1) caption 2 had 'Sleep is a promising research result': sleep is not in this video (no kept chapter mentions it) and the plan calls it 'Mixed; not on the run's path' (PLAN:140), not promising, so the sentence is dropped rather than left dangling. (2) 'The calculator can sit outside' now carries its strength (6 copies, 3M, two checks not clean: s05). (3) 'No recipe has shown both halves of demonstrably works' was unexplained; replaced by the two halves in PLAN:115-116 (it works at 3M; not shown to improve faster with size than a plain model). (4) 'Plan's own judgment' -> 'The plan's judgment' in the caption (the chip keeps 'the plan's own judgment'). Duration 42 -> 45. Fixer edit (JS only): added one status chip per part under the one-liners (kit default words: tested, tested, tested, built never tested, placeholder; same statuses as s01), so 'Most of the rest is built or planned' is visible; plan chip and notes moved down to make room.",
          "atMap": [
            [
              0.0133,
              0.0194
            ],
            [
              0.337,
              0.2445
            ],
            [
              0.6607,
              0.5695
            ]
          ]
        }
      ]
    }
  }
};
