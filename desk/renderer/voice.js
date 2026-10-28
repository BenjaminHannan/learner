'use strict';
// "Get voice (1.6 GB)": one button shown next to the "Voice needs the local speech model" error (call and dictation).
// VoiceGet.wire(desk, button, textEl, shown): shown(bool) per error; progress text goes into textEl. After success the user presses the mic again.
(function (root) {
  const LABEL = 'Get voice (1.6 GB)';
  let busy = false; // one install at a time, shared by the call and dictation buttons
  function wire(desk, btn, textEl) {
    let off = null;
    btn.onclick = async () => {
      if (busy) return;
      busy = true; btn.disabled = true; textEl.textContent = 'Starting…';
      if (off) off();
      off = desk.voice.onProgress((p) => { textEl.textContent = p.stage === 'error' ? p.label : p.label + (p.pct ? ' (' + p.pct + '%)' : '…'); });
      let r; try { r = await desk.voice.install(); } finally { busy = false; }
      if (typeof off === 'function') off(); off = null;
      btn.disabled = false;
      if (r && r.error) { textEl.textContent = r.error; btn.textContent = 'Try again'; return; }
      textEl.textContent = 'Voice is ready. Press the mic or the phone again.'; btn.hidden = true;
    };
    return (needsVoice) => { if (busy) return; btn.hidden = !needsVoice; btn.disabled = false; btn.textContent = LABEL; }; // never reset a running install
  }
  root.VoiceGet = { wire, LABEL };
})(typeof window !== 'undefined' ? window : globalThis);
