# Explainer kit for Ben (Thread manager, 2026-09-28)

Ben's "eli5" pages: an HTML artifact for someone who knows nothing about the topic. Big pictures, few words.

- `eli5-head.css`: the fonts (Archivo, Atkinson Hyperlegible, JetBrains Mono from Google Fonts) and colour tokens for light and dark, used on every explainer since 09-26. Build a page as `<title>Two To Four Words</title>` + this file + your cards.
- `example-director.html`: a finished page (hero card, one idea per card, inline SVG pictures, real numbers to scale, footer with sources).
- `check.js`: finds SVG labels that overlap or leave their picture, and horizontal scroll, at 400 px light and 720 px dark. Chromium and Playwright are preinstalled in cloud sessions: `NODE_PATH=$(npm root -g) node handoff/kit/eli5/check.js page.html`.

Rules Ben set (his own skill text, 09-26): 5 to 8 cards in beginner order; each card one big picture that carries the idea alone, a headline of about 8 words and at most one short sentence; everyday comparisons instead of jargon; real numbers only, rounded, drawn to scale; guesses labelled ("our best guess"); open with a hero card, end with "what happens next" if there is one; readable on a phone and in both themes; sources in a small footer.
