# Why does a small self-teaching model learn joined formulas only in the exact forms it practised?

You are an expert in small neural program-executing models, compositional generalisation, curriculum design and
self-generated practice. Everything you need is below; please answer from it directly. If a fact you need is missing, say exactly what it is and how it would change your
answer. Mark every claim as **shown by the data below**, **suggested**, or **untested**.

I am a high-school senior building this with AI help. End with a plain-language summary I can follow (under 150 words).

Scope: only one small experiment, a 3.3M-parameter calculator-calling model teaching itself spreadsheets ("domain
mode"). It is not about my larger "village" model; do not mix the two.

## 1. The task

A prompt is a tiny spreadsheet and one formula; the model answers by writing calculator calls, then the answer.

| shape | example prompt | calls (the tool's working) |
|---|---|---|
| near (like the help page) | `A: 50 84 94 46 \| B: 62 90 44 56 ; =SUM(A1:A4)` | ADD 50 84; ADD 134 94; ADD 228 46 |
| two kinds joined ("F4", the key test) | `A: 49 20 65 \| B: 78 59 92 ; =SUM(B2:B3)+MAX(B2:B3)` | ADD 59 92; MAX 59 92; ADD 151 92 |
| the other F4 layout | `... ; =(MIN(A1:A3))*(A2+B1*2)` | MIN, MIN, ADD/MUL for the cell part, then MUL |
| far (the real goal) | 5-6 row grids, ranges of 5-6 cells, another column, AND two kinds joined | 3-7 calls |

F4 = 420 rows: near grids (2-4 rows, 2-digit values), kind K from 7 scored kinds (SUM, MAX, MIN, PRODUCT, cell
arithmetic `A1+B2*2`, division `A1/B1`, ABS), partner J from the other 6, joined as `K+J` (half) or `(K)*(J)` (half).
Far without MOD/compare ("F5") is about 0-1% for every model below.

## 2. The model (3.28M parameters, width 256)

- Input: one token per character; a "place" code per character. Reader: embeddings, then 2 convolution blocks
  (window 5), then LayerNorm, so the reader only sees local context.
- Number slots: the first 16 digit runs of the prompt (row digits inside `B5` count) plus constants 1, 2, 10, 100 and up
  to 7 result slots (one per call).
- Thinker: 8 control + 9 register tokens; 8 loop iterations of the same 2 blocks (cross-attend to number summaries,
  the visible tape of earlier calls as text such as `59 + 92 = 151`, and the prompt characters; then self-attention;
  then an MLP).
- Heads per round (max 7): an operation head (NOOP, ADD, SUB, MUL, DIV, MOD, MIN, MAX, CMP); operands written as text,
  by copying a whole number from prompt or tape with a pointer, or character by character. A plain calculator runs the
  call and its text joins the tape. After the loop the registers write the answer.
- Training: teacher forcing (gold tape revealed one entry per round); losses are op cross-entropy, operand
  log-likelihood (either order for ADD/MUL/MIN/MAX) and answer characters.
- Pre-trained on about 200k rows of small arithmetic and reading skills, never on spreadsheets.

## 3. The self-practice loop ("domain mode")

Given only a help page (10 examples, one per kind, all on the same 3-row, 2-column grid of single digits:
`=SUM(A1:A3)`, `=MAX(A1:A3)`, `=MIN(B1:B3)`, `=PRODUCT(A1:A3)`, `=A1+B2*2`, `=A1/B1`, `=MOD(A2,B2)`, `=ABS(A1-B1)`,
`=COUNTIF(A1:A2,">3")`, `=IF(A1>B1,A2,B2)`) and the tool (it computes a formula's working, or `?`):
- Practice maker ("A10 edits"): take an example, change digit-run lengths, insert or delete digit runs, rename letters,
  swap symbols; the tool checks each draft (a `?` draft is thrown away and another drawn).
- The model tries each problem; its own try is kept only when it equals the tool's working, else it trains on the
  tool's working.
- Each night a low-rank add-on (rank 8, base frozen) is trained on the day's rows plus replay; the add-on is switched
  on only for this tool's questions, so old skills are untouched. Stops when its own quiz stops rising.
- Result (shown, 2 seeds): near 2-4% -> 40-57%; far stays 0-2%.
- v9 added a "swap tool" before day 1: replace one well-formed piece (whole tokens, balanced brackets) of a help
  example with a piece of any help example, keep what the tool runs (rings 2 and 3, about 4,000 examples). Single
  far factors rose (bigger grid 19 -> 30%, long range 14 -> 32%); joined formulas stayed 1.4%.

## 4. Direct learnability tests (shown; all start from the pre-trained checkpoint, 4,000 updates, batch 64, no replay, 12,000 tool-worked rows = 6,000 joined + 6,000 single-kind; marks fixed before each)

LA = add-on, base frozen (rank 8 unless stated; lr 1e-3). LB = every weight (lr 1e-4). F4 = the test's joins.

| test | where the 6,000 joined training rows came from | LA F4 | LB F4 | other cells |
|---|---|---|---|---|
| L1 | hand-written generator: `K+J` and `(K)*(J)`, all kind pairs, near grids | 69.3 | 88.8 | fit 80 / 97 |
| L2 | the mode's swap tool (209 forms, dominated by `=A1+PRODUCT(..)` and `=A1+MAX(..)`) | 2.1 | - | own joins 42 |
| L3 | generator, only `+`, 14 of 21 kind pairs | - | - | new pairs: LA 15.5, LB 46.2; unseen layout `(K)*(J)`: 0.9 / 0.5 |
| L4 | swap tool + a join step (`P s Q` in 6 forms, Q any value piece of the help page; mostly digits glued on) | 4.0 | 2.9 | own joins 37 / 71 |
| L5 | generator, 5 layouts (`K+J`, `K-J`, `K*J`, `(K)+(J)`, `(K)-(J)`), `(K)*(J)` held out | 23.8 | 45.7 | unseen layout: LA 5.2, LB 36.7; new pairs LA 9.8, LB 28.3 |
| L6 | L5 data, add-on rank 64 | 44.3 | (45.7) | new pairs 56.9, unseen layout 13.6; no forgetting |
| L7 | L5 data, every weight plus an anti-forgetting K-FAC projection guard | - | 13.6 | old skills 90 -> 82 (unguarded 90 -> 37); unseen layout 9.3 |
| L8 | the mode's own recursive substitution: replace a value slot of a help example by a value piece of the help page, bare or bracketed, up to 3 deep, equal quota per layout | 4.3 (rank 64) | 3.1 | own joins 77.6 / 91.2; near 63 / 81 |

L8 detail (shown): its 6,000 joined rows had 156 formula layouts, mostly a range call glued to a cell expression with
extra brackets (`=((MIN(B1:B3))*A2)`, `=A1+(SUM(A1:A3))`, `=(A2)*(MAX(A1:A3))`, `=SUM(A1:A3)+(B2)*2`); **0.0%** had two
calls side by side joined by one top-level `+` or `*`. Both arms learned their own joins well and the test's not at all.

L9 (running now, marks fixed): the joined rows are made by joining two WHOLE help formulas (the piece that, replaced by
`1`, leaves a prompt the tool answers `1` with no steps) with a help-page symbol in 6 generic forms (`P s Q`, `Q s P`,
`(P) s (Q)`, `(Q) s (P)`, postfix x2), equal quota per accepted (form, symbol). Its ring of 780 examples has 449 with two
calls side by side. Pass: rank-64 add-on F4 >= 25; proved wrong <= 8. **Shown on the way:** the mode's A10 edit step
breaks about 9,999 of 10,000 drafts of such joins (an edited reference leaves the grid, a `-` goes negative, a `/` is no
longer exact), so a real self-practice night would almost never keep one (L8's joins survived about 1 in 700).

## 5. What I want from you

1. Explain the pattern: the model learns whatever join forms it practises (fit 37-97%) but carries to an unpractised
   join form only weakly (best: unseen layout 36.7 with every weight after 5 practised layouts; 13.6 with the rank-64
   add-on; ~0-5 otherwise). Rank the explanations (data: which forms appear; architecture: the local convolution
   reader, the 16 number slots, the per-round op head; training: teacher forcing, rows per form; model size) and label
   each shown / suggested / untested. Is this "no compositional generalisation at 3M" or something cheaper to fix?
2. Is L9 a fair test of a self-practice loop or does it smuggle in the test's grammar? Where is the line between "the
   model invents practice from what it was shown" and "the designer writes the test's generator"?
3. Given only the help page and the tool, what practice maker would teach joining as a skill, and how should the edit
   step keep composed drafts valid without knowing the domain? At most three changes, one at a time, each with pass
   marks fixed in advance and the result that would prove it wrong. Prefer changes the deployed model can apply itself
   (an outside tool it calls, its own practice choices); hand-written code is allowed only as an outside tool.
4. Would you instead test a bigger model (a pre-trained 10M version exists, 30M later; CPU only, about 3 hours per 3M test), or an
   outside tool that splits a formula into pieces the model already solves and recombines their results? What single
   test would tell the two apart?
5. A plain-language summary for me, under 150 words.
