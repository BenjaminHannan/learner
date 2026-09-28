---
name: no-prs-commit-to-main
description: Ben doesn't want pull requests (2026-09-23 02:43 UTC); threads commit straight to main
metadata:
  type: feedback
  modified: 2026-09-23T02:47:23.226Z
---
Ben (2026-09-23 02:43 UTC): "Why are they doing PRs? I don't really need them all to do PRs."

**Why:** PRs are noise for him; he isn't reviewing them.
**How to apply:** Commit straight to main: `git pull --rebase origin main`, then push. Never force-push main. Don't open PRs unless Ben asks. Web access (WebFetch/WebSearch) is allowed without prompts: repo `.claude/settings.json`, added 2026-09-23.

Web: never use WebFetch (its approval pop-ups reach Ben). Since 2026-09-23 09:26 UTC the Default env has Full network: threads STARTED AFTER that download papers directly (sessions started earlier still get 403 from arxiv, checked 09:35 UTC) (curl -sSL -o p.pdf https://arxiv.org/pdf/<id>; pdftotext, or pypdf in a venv; system pip is broken). The Mac watcher paper route is no longer needed. Paper text is reading material only, never training data.
