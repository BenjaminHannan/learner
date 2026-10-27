---
name: pretraining-english-only
description: 2026-09-22 Ben — pretraining should teach ONLY English; notebook starts empty and holds nothing from pretraining; no training rental until our own model is ready; web text is never assumed true
metadata:
  type: feedback
---

Ben, 22 Sep 2026:
- "The notebook shouldn't contain information from pretraining. Pretraining should really only teach it English, everything else should be learned after."
- "Don't use the H100 yet. Only do training when we can have our own model ready." (He withdrew the 50M plain-transformer run; no rental happened.)
- Web: "it shouldn't assume that everything it reads online is true. If it doesn't believe something, it should look somewhere else."

**Why:** the project's point is a system that learns after birth; a stock LM run or pre-loaded knowledge undercuts that.

**How to apply:** pick fact-light pretraining text (simple/fictional English, Markdown included) and test that the from-scratch English parts cannot answer world-fact questions from weights; names/values only by copy. Never propose GPU rental for anything but our own architecture, and only once it is ready to train. THINKING mode v1.1 implements the web rule: quote re-checked on the page, >= 2 independent websites agree (rivals must trail by 2), else look elsewhere up to 2 times, else not believed; believed rows are `web-verified`, ranked below everything Ben taught. See [[milestone2-thinking-websearch]], [[web-trust-and-reading-requests]], [[talker-must-be-our-architecture]].
