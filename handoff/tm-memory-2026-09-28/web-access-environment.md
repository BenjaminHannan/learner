---
name: web-access-environment
description: Why cloud threads can't download papers (Trusted network env) and the fix Ben must tap (Full network + pick env in Project settings)
metadata:
  type: project
---
Checked 2026-09-23 03:20 UTC (web-access thread):
- Project threads run in Anthropic's built-in default environment (session env id env_011111111111111111111119), network level **Trusted**. The proxy returns 403 on CONNECT for arxiv.org, export.arxiv.org, semanticscholar, wikipedia, huggingface.co, google, aclanthology, openreview. github and code.claude.com work.
- Ben's own environment "Default" (env_01X7Yt1s88fnHgTzWmoi8EkD) is also Trusted, and the project hasn't selected it.
- Fix needs Ben (settings only reach NEW threads): edit an environment's Network access to **Full** via the cloud icon above the message box at claude.ai/code (hover env, gear), then pick it in Project settings > Environment. After that, papers download with curl + pdftotext in the thread; no WebFetch needed.
- Re-checked 2026-09-23 09:24 UTC: project now uses Ben's "Default" env (env_01X7Yt1s88fnHgTzWmoi8EkD), confirmed by get_session, but it is STILL "trusted network access". arxiv, huggingface, wikipedia, semanticscholar all 403 at the proxy. Remaining fix: Ben sets Network access = Full on Default (Project settings > Environment).
- 09:26 UTC: Ben set Default to Full. It applied LIVE, even in an already-running thread: arxiv PDF 200 (2.2 MB), huggingface 200, wikipedia 200, export.arxiv API 200; Semantic Scholar API 429 (rate limit, not a block). Cloud container has no pdftotext, and pip pypdf crashes on a broken system `cryptography`; use a venv or apt poppler-utils for PDF-to-text.
- The WebFetch "Allow Claude to fetch" prompt persisted despite repo allow rule ["WebFetch"] in auto mode; cause not found in docs. Auto-mode classifier blocked editing .claude/settings.json ([Self-Modification]) without Ben's explicit word. Keep never using WebFetch. See [[no-prs-commit-to-main]].
- 09:30 UTC (Paper download retest thread): PDF-to-text works. `apt-get install -y -q poppler-utils` installs pdftotext in ~1 min; arxiv 1706.03762 -> 6106 words. A fresh venv (`python3 -m venv /tmp/pdfvenv`, pip install pypdf pdfminer.six) also works: pypdf 15 pages / 6008 words, pdfminer 5825 words. Avoid the system pip.
