# SECURE-LOGIN pass marks (fixed 2026-11-05, before any code)

Ben's ruling 2026-11-05: logins come in through a secure app form, never through chat; Glim opens the form without a "may I?";
a saved login is then used by Glim by itself. (This replaces the 2026-11-04 "passwords in chat are fine" prompt line.)

| # | Mark | Pass if | Fails if (the result that proves it wrong) |
|---|------|---------|--------------------------------------------|
| S1 | No leak to the thread, model or logs | Electron test with a TEMP userData profile + THROWAWAY keychain: a random test password (e.g. `Sx-<random>-9q!`) is typed into the ask_login form; afterwards `grep -r -F <pw>` over the whole temp userData (threads, logs, diary, notes, gateway/training logs, logins.json) finds **0 files**, and the tool result + every model message the agent built hold **0** copies | any file or any model message / tool result containing the password |
| S2 | Model gets no secret in any tool result | unit test: ask_login and browser_sign_in results (saved / cancelled / queued / already-saved / signed-in paths) are exactly `{saved, site}` (+ a fixed next-step hint) and never contain the password or username's password; the agent's tool runner scrub still drops any slip | a password string in any tool result text, summary or preview |
| S3 | Fake-site e2e: ask -> save -> autofill | local https test page with a sign-in form; no saved login: browser_sign_in / ask_login opens the app form (one BrowserWindow, password field `type=password`), test fills it + Save -> login in the test keychain -> the page is filled and submitted by the app; the server receives the right user + password | form not app-owned, password not masked, server gets nothing / wrong values |
| S4 | Fake-site e2e: saved-login reuse | a fresh page of the same origin: browser_sign_in fills and submits with **no form opened** | a form opens again, or the server gets nothing |
| S5 | One form per site, no repeated asking | two ask_login calls for the same site while a form is open -> one window; a Mote (Ben away) gets `{saved:false}` + "queued" at once, one notification, and a second Mote call for the same site does not notify again | two windows for one site, or a second notification |
| S6 | No "may I?" gate | safety-levels: ask_login is never refused or sent for approval at any level setting; browser_sign_in keeps today's 'passwords' (def free) / banking rows | ask_login refused or approval-gated |
| S7 | Prompt rules | system prompt + Mote prompt + DO_IT note + browser_sign_in "no saved login" text say: saved login -> browser_sign_in; none -> ask_login; never ask for a password in chat. The "passwords in chat are fine" line is gone; the password-in-chat self-check is on again and points to ask_login | the old line remains, or any prompt text still tells Glim to ask for a password in chat |
| S8 | Desk suite | full `node --test` in desk/: no failures beyond the known list (first-reply thinking cap, 8192-token context check, agentbench, realpath, login1-electron, fake-sleepmode scripts) | any new failure |
| S9 | Never Ben's real data | tests use temp userData + throwaway keychain / MemoryBox only; Ben's keychain search list unchanged | a test touches the real userData or login keychain |

Install only after ONE-GLIM cutover.log shows "CUTOVER DONE" and Ben idle >= 5 min.
