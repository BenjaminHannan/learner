# Guide for chapter authors (read all of it first; it is short on purpose)

You are one of 15 authors. Together you are making ONE long silent explainer video (HyperFrames, 1920x1080, 30 fps) that explains
every part of a research AI model so that a smart high-school student who has never heard of any of it can understand all of it.
You write ONE chapter: its content file and its scene-building file. Someone else assembles the chapters; a checker will compare
every number you put on screen against the sources. Nothing is published to anyone from your work.

Read, in this order: this guide, GLOSSARY.md (the words and analogies every chapter shares), your brief in briefs/chNN.md,
examples/ch99-demo.js + examples/ch99.json (every kit helper used once), then your sources.

## 1. Rules that cannot bend

1. **Real content only.** Every number, name, date and claim on screen comes from the sources named in your brief or from a file you
   found and read yourself. No invented results, no "roughly" numbers you did not read. A number you computed (a subtraction, a ratio)
   is allowed only if the caption says what was done to get it ("our subtraction: 73.01 minus 67.12") and `notes` in the scene says how.
2. **Made-up things are labelled.** Tom's apples is an example the project made up. Any picture that only illustrates (shaded vectors,
   a "done?" switch turning green after round 4) carries a small visible tag such as "illustration" (S.chip('placeholder',{label:'illustration'})
   or a caption phrase). Never let an illustration look like a measurement.
3. **Status honesty.** Everything is one of: tested (a result exists), built but never tested, placeholder (does not exist yet), or an
   idea/plan. Show it with the status chips (green, amber, grey). If a thing was tested only once, at the smallest size, on one seed,
   say exactly that on screen. Never write "proves", "solves" or "beats" unless the source says it was shown and says on what.
4. **Newest source wins.** `/mnt/project-files/architecture/FINISHED-MODEL-2026-10-09.md` is the source of truth for how the finished model
   works. Older pages (model-deep-dive.html, model-architecture.html, older roadmap notes) describe earlier designs: 17 thinker vectors,
   8 rounds, a calculator inside the model. Use them for explanations of ideas, never for the current numbers or structure. If two sources
   disagree, show the newer/source-of-truth one and write the disagreement in notes.md.
5. **ELI5.** Short words, one idea per sentence, define every term the first time it appears in your chapter (in half a sentence),
   say what a number means ("points out of 100", "of 6,040 questions kept aside"). A code name (G1, B2, T1SDR, H1) may appear only as a small
   tag next to its plain-word name, so people can cross-reference. The plain word comes first.
6. **No paid or external services.** Do not call any API, cloud service or rental machine. Do not install anything. Do not touch the
   internet except to read the allowed sources (GitHub MCP read tools are fine if a brief says so). Do NOT call any `mcp__hearthbot__*`
   tool: you cannot talk to the user; your final message goes to your coordinator.
7. **Stay in your lane.** Write only inside your working folder and, at the end, copy your deliverables to your own folder under
   `/mnt/project-files/animations/model-explainer-build/chapters-out/chNN/`. Never edit the kit files (kit.js, main.js, style.css,
   tools/*). If you need something the kit lacks, build it inside your own chapter file as a local helper, and list it under KIT REQUESTS in notes.md.
8. **Do not read or open** any protected/sealed panel (GOLD-PRIVATE, reserved, blind panels). You do not need them.
9. The machine has 4 CPUs shared by many authors. Run check/shots sparingly (see section 7). Never run `hyperframes render`.

## 2. What a good chapter is

Depth is the point. The viewer should be able to explain your chapter to a friend afterwards. Aim for this arc (reorder if your topic needs it):

1. **Where are we**: the five-part map (S.modelMap with your part highlighted) and one sentence on what this part does.
2. **An everyday picture** of the part (use the analogy in GLOSSARY.md; do not invent a new one) and one tiny worked example with real text or numbers.
3. **The mechanism, step by step**, animated: things move, numbers count, arrows draw. This is most of the chapter.
4. **The numbers**: sizes, settings, counts, each with its meaning in plain words.
5. **The evidence**: what test, what score out of 100, how many questions, how many separate copies (seeds), with status chips.
6. **What is not known / what could go wrong**, said plainly, with the amber or grey chip.
7. **Recap**: three short lines, "what to remember".

Rules of thumb:
- A chapter has 8 to 16 scenes of 12 to 40 seconds. Never pad. A scene that does not teach something new gets cut; a scene longer than 45 s gets split.
- At least 60% of scenes must animate a mechanism (movement, drawing, counting, a comparison building up), not just reveal lines of text.
- Per scene: ONE idea. A heading (one line, 48 characters or fewer, plain words) and a caption (the sentence a narrator would say).
- A long scene uses a caption ARRAY (2 to 4 sentences shown one after another in the same box), and the picture changes in step with each
  sentence using `S.capAt(i)` (the start time of caption i).
- The last 20% of every scene is a still, complete, tidy picture so the viewer can read it. Nothing important in the first 0.6 s (fade in) or the last 0.6 s (fade out).
- Be specific. "The thinker looks at all 81 letters" beats "the thinker looks at the input". Show the real example text.

## 3. Reading speed budget (checked by tools/audit.mjs)

All visible words in a scene (heading, caption(s), labels, notes, numbers counted as words) must fit:
`duration >= 3 + words / 2.6` seconds, and each caption sentence at least `1.2 + its words / 2.8` seconds.
Captions: at most 26 words / 150 characters each (two lines). If you need more words, split into more captions or more scenes.
On-screen text outside the caption: keep short labels (1 to 6 words). Fewer than 40 non-caption words per scene.

## 4. Files you produce

```
content/chNN.json   every word, number and timing on screen for your chapter (JSON; no code)
chapters/chNN.js    Kit.chapter('chNN', function (Ch) { Ch.scene('s01', function (S) { ... }); ... });
notes.md            handoff note (section 8)
```

### content/chNN.json

```json
{
  "kicker": "Part 3 of 14",
  "title": "The reader",
  "blurb": "One or two plain sentences that say what this part is for.",
  "accent": "reader",
  "scenes": [
    {
      "id": "s01",
      "duration": 24,
      "heading": "Where we are: the reader comes first",
      "caption": ["First sentence.", "Second sentence, shown after the first."],
      "src": ["architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Reader row)"],
      "notes": "optional: how a computed number was computed, or why a choice was made",
      "anything_else_your_builder_reads": "free fields named however you like"
    }
  ]
}
```
- `accent` is a palette key (reader, thinker, call, calc, stop, talker, tested, untested, learned, placeholder, hand) or a hex colour. It colours the chapter chip, title card and caption bar.
- Scene `id`s are `s01`, `s02`, ... and must match `Ch.scene('s01', ...)` in your JS. Scene order in the JSON is play order.
- **Every string that appears on screen lives in the JSON** (labels inside boxes, chip labels, numbers, example text). The builder reads `S.c.something`.
  Only symbols ("→", "+", "=", "×", "...") and the default chip words may be written in code. Numbers that animate are JSON numbers, with the display
  options (decimals, suffix) chosen in the builder with `S.count`.
- The point: "slow down the second scene" changes only `duration`; "change this number" changes only one JSON value. Always place beats with `S.at(fraction)`
  or `S.capAt(i)`, never with absolute seconds, so a longer scene stretches its beats.
- `src` (array, required) lists where each fact in the scene came from: file path (under /mnt/project-files or the repo) plus section/line. The checker reads it.
- Do not write your own `title card` scene: the title card (kicker, title, blurb) and the end of chapter fade are automatic. The chapter chip and the progress bar are automatic too.

### chapters/chNN.js

```js
Kit.chapter('ch03', function (Ch) {
  const C = Kit.C;                                   // palette
  Ch.scene('s01', function (S) {
    const c = S.c;                                   // this scene's JSON
    const m = S.modelMap({ x: 100, y: 260, w: 1720, h: 200, highlight: 'reader' });
    S.stagger([m.parts.reader, m.parts.thinker], S.at(0.1), 0.4);
    ...
  });
});
```

## 5. Kit API (kit.js; read it if unsure, it is 330 lines)

Canvas is 1920x1080. Coordinates are CSS pixels from the top-left. Elements are created hidden; you MUST reveal each one (show/pop/stagger/sweep/type/draw), otherwise it never appears.
Creation order is z-order (later = on top). `S.g` is the scene layer (append your own DOM there only if you must); `S.tl` is the one GSAP timeline.

Time: `S.at(f)` fraction f (0..1) of this scene; `S.sec(s)` seconds into the scene; `S.capAt(i)` start of caption i; `S.d` duration; `S.c` content.

Make things (all take `{x,y,w,h,...}`; all return the element unless noted):
- `S.text(str,{x,y,w=1200,size=40,weight,color,align,mono,lh,italic,nowrap,html})`
- `S.box({x,y,w,h,label,sub,color,fill,size,subSize,border,r,textColor})`   (label and sub are centred inside)
- `S.card({x,y,w,h,fill,color,r})`   (empty rounded card; put text on top)
- `S.note(str,{x,y,w,color,size,fill,html})`   (callout with coloured left edge, auto height)
- `S.chip(kind,{x,y,label,size,color})`   kind: tested | untested | placeholder | hand | learned (default words: tested, built, never tested, placeholder, hand-written, learned)
- `S.bar({x,y,w,h,value,max,color})` -> `{track,fill,...}`; `S.grow(bar,t,dur,valueEl,{dec,pre,suf,comma})` grows it and counts the label
- `S.hbars({x,y,w,labelW,rowH,gap,max,dec,suf,items:[{label,value,color,suf,dec}]})` -> `{rows, reveal(t,gap,dur)}` labelled bars with counting numbers
- `S.letters(str,{x,y,size,gap,color,fill})` -> `{cells[], byIndex[], cx(i), cy, left, right, w, h}` a row of letter boxes; `cx(i)` aims arrows at character i
- `S.vec({x,y,n,cell,gap,dir:'h'|'v',color,seed})`   a strip of shaded cells = "a list of numbers" (shading is decoration)
- `S.svg({x,y,w,h})` -> `<svg>` layer; `S.arrow(svg,x1,y1,x2,y2,{color,width,head})`, `S.curve(svg,x1,y1,x2,y2,{bend,color,width,head})`,
  `S.path(svg,[[x,y],...],{color,width,head})` return `{line,head}` to be drawn with `S.draw`; `S.svgEl(svg,'rect'|'circle'|'path',attrs)` for custom shapes
- `S.modelMap({x,y,w,h,highlight})` -> `{parts:{reader,thinker,calc,stop,talker}, arrows[], svg}` the shared five-part map
- `K.rng(seed)` deterministic random numbers (never `Math.random`)

Animate (each returns the time it ends, so you can chain `t = S.show(...)`):
- `S.show(e,t,{dur,x,y,s,ease})` fade+slide in; `S.hide(e,t,dur)`; `S.pop(e,t)` pop in; `S.stagger(list,t,gap,{...})`; `S.sweep(list,t,total)` many small things, evenly
- `S.draw(arrowOrCurve,t,dur)`; `S.type(textEl,str,t,dur)` typewriter; `S.count(el,{from,to,dec,pre,suf,comma},t,dur)` number counts
- `S.move(e,t,dur,{x,y})` slide by an offset from its home spot; `S.pulse(e,t)`; `S.tint(e,t,{border,fill,color,dur})` recolour
- Raw GSAP is allowed through `S.tl` but only with the seek-safe rules below.

## 6. Seek-safe rules (the renderer jumps to any time, so scenes must be pure functions of time)

- Build everything synchronously when the scene function runs. Create all elements up front; never create/remove elements inside a callback.
- No `setTimeout`, `requestAnimationFrame`, `Date.now`, `Math.random`, `fetch`, no CSS animations or transitions, no `repeat:-1`.
- Every tween states its visible END state with absolute values. No relative `+=` / `-=` on a property that another tween also touches.
- Two tweens must not change the same property of the same element at overlapping times.
- Do not centre with `transform: translate(-50%)` on anything GSAP moves. Give x, w and use `align:'center'`.
- Do not measure geometry (`getBoundingClientRect`, `getTotalLength`) during animation. The kit computes arrow lengths for you.
- SVG strokes draw on only through `S.draw`. Animate opacity through the kit helpers (autoAlpha), not by setting `visibility` yourself.
- Text height is not known in advance: leave room (about 1.3 x size per line).

## 7. Layout and look

- Safe zones: top-left chapter chip at y 34-90 (automatic); heading at y 118-180 (automatic); **your graphics: y 190 to 840, x 80 to 1840**;
  caption box bottom 50 px (automatic; two lines occupy y 887-1030). Nothing of yours below y 840.
- Type: nothing readable smaller than 30 px. Labels 32-44 px, example text 48-60 px, big numbers 90-150 px, status chips 28 px.
- Max about 6 things on screen at once beyond the heading and caption. White space is good. Align things on a grid; equal gaps.
- Colours = meaning (never decorative): reader teal, thinker indigo, call coral, calculator slate, stop purple, talker pink, tested green, built-never-tested amber,
  placeholder grey, hand-written brown, learned blue, warning orange. Use `Kit.C`. Put dark text on light fills (the contrast check enforces it).
- Same thing, same colour in every chapter (see GLOSSARY.md). Do not invent new colours for parts.
- Fonts: Inter for text, DejaVu Sans Mono for code and letters (`mono:true`). Nothing else.

## 8. Your loop (all commands run inside your working copy)

```bash
KIT=/mnt/project-files/animations/model-explainer-build/kit
W=/tmp/claude-0/-home-user-learner/01bcea25-2484-5edd-8248-d1fe6e738ef5/scratchpad/hf/work/chNN      # use your own chapter number
mkdir -p "$W" && cp -r "$KIT"/. "$W"/ && cd "$W" && rm -rf snapshots && mkdir -p chapters content
# 1. write content/chNN.json and chapters/chNN.js
node tools/merge.mjs && node tools/mkindex.mjs --only chNN     # builds content.js and index.html for your chapter alone
node tools/audit.mjs chNN                                      # reading-time audit: fix every "TOO SHORT"
npx --yes hyperframes@0.8.143 check .                          # lint + layout + motion + contrast: must say "Check passed"
node tools/shots.mjs chNN                                      # 4 frames per scene -> snapshots/chNN/sheet-01.jpg ... open each with the Read tool
node tools/shots.mjs chNN s05 --per 6                          # re-check one scene closely
```
Look at EVERY sheet. Check: text cut off or overflowing a box, things overlapping, anything below y 840, an arrow that does not end at its target,
a number that ends on the wrong value, an empty-looking scene, a label too small to read, colours that do not match the glossary, an illustration that looks like a
measurement. Fix, then re-run. Plan on two full passes; use `--per 2` for the second pass if you only need to confirm. `check` needs a first sheet look before it is useful for layout.

Work in this order to save effort: (1) content JSON for the whole chapter first (this is where truth is decided); (2) builders for 2-3 scenes, check them;
(3) remaining scenes; (4) full audit/check/shots; (5) fix; (6) deliver.

## 9. Delivering

Copy to `/mnt/project-files/animations/model-explainer-build/chapters-out/chNN/`: `content/chNN.json` as `chNN.json`, `chapters/chNN.js` as `chNN.js`,
`notes.md`, and the final `snapshots/chNN/sheet-*.jpg`. Then answer with at most 200 words: scene count, total seconds, the audit line, what you are least sure about.

### notes.md (required, short)
- SOURCES READ (paths) and which one decided each disputed fact.
- NUMBERS I COMPUTED (value, formula, inputs) and NUMBERS AS WRITTEN IN SOURCES (list the headline ones with file:line).
- DISAGREEMENTS between sources and what the video shows.
- ILLUSTRATIONS (scene id, what is only illustrative).
- OPEN QUESTIONS for the project owner (only if real).
- KIT REQUESTS (things you wished the kit had; keep to what you actually worked around).
- Anything the next chapter's author must know (terms you introduced, analogies you used).

## 10. If you get stuck

A source is missing or contradicts the brief: keep going with what you can verify, drop the claim from the video if you cannot, and say so in notes.md. Do not guess.
A kit helper misbehaves: work around it locally and report it. Keep your working copy; do not edit the master kit.
