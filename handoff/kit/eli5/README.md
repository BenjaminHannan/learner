# Explainer kit for Ben (Thread manager, 2026-09-28)

Ben's "eli5" pages: an HTML artifact for someone who knows nothing about the topic. Big pictures, few words.

- `eli5-head.css`: the fonts (Archivo, Atkinson Hyperlegible, JetBrains Mono from Google Fonts) and colour tokens for light and dark, used on every explainer since 09-26. Build a page as `<title>Two To Four Words</title>` + this file + your cards.
- `example-director.html`: a finished page (hero card, one idea per card, inline SVG pictures, real numbers to scale, footer with sources).
- `check.js`: finds SVG labels that overlap or leave their picture, and horizontal scroll, at 400 px light and 720 px dark. Chromium and Playwright are preinstalled in cloud sessions: `NODE_PATH=$(npm root -g) node handoff/kit/eli5/check.js page.html`.

Rules Ben set (his own skill text, 09-26): 5 to 8 cards in beginner order; each card one big picture that carries the idea alone, a headline of about 8 words and at most one short sentence; everyday comparisons instead of jargon; real numbers only, rounded, drawn to scale; guesses labelled ("our best guess"); open with a hero card, end with "what happens next" if there is one; readable on a phone and in both themes; sources in a small footer.

## Roadmap section (required from 10:53 UTC 09-29, Ben)
Every explainer page ends (or opens, after the answer) with a "Where this fits" roadmap: three parts drawn as a simple strip or list, in the page's own style: DONE (what earlier steps showed), THIS STEP (what this task tests and its pass mark), NEXT (what follows if it passes, and if it fails). Source: handoff/director-roadmap.md and handoff/director-board.md. Same word rules as the rest of the page: plain words, counts as "x of N".

## Pictures first (Ben, 13:33 UTC 09-29)
Lead with pictures: a how-it-works SVG diagram at the top, results as bar/line charts with the pass mark drawn as a line, and the roadmap as a box strip (done / this step / next). Short captions only. Draw charts to one scale, label every mark, use theme colour tokens so both light and dark read, and run check.js (no OUT/OVL, scroll width equals viewport). example-director.html shows the style.
