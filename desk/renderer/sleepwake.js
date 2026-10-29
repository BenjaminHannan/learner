'use strict';
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.SleepWake = factory();
})(typeof window !== 'undefined' ? window : globalThis, () => {
  async function waitForReady({ wake, state, timeoutMs = 240000, pollMs = 250,
    now = Date.now, wait = (ms) => new Promise((r) => setTimeout(r, ms)) }) {
    const end = now() + timeoutMs;
    // Bound IPC failures as well as the backend's asynchronous wake transition.
    const bounded = async (fn) => {
      const remaining = end - now();
      if (remaining <= 0) throw new Error('Waking took too long. Your message is still here; try Turn on, then send it.');
      let timer;
      try {
        return await Promise.race([Promise.resolve().then(fn), new Promise((_, reject) => {
          timer = setTimeout(() => reject(new Error('Waking took too long. Your message is still here; try Turn on, then send it.')), remaining);
        })]);
      } finally { clearTimeout(timer); }
    };
    const r = await bounded(wake);
    if (!r || r.error || r.ok === false) throw new Error((r && r.error) || 'Could not wake Glim. Your message is still here.');
    for (;;) {
      const s = await bounded(state);
      if (s && s.error) throw new Error(s.error);
      if (s && !s.asleep && !s.waking && !s.starting && s.modelReady === true) return;
      await wait(Math.min(pollMs, Math.max(0, end - now())));
    }
  }
  return { waitForReady };
});
