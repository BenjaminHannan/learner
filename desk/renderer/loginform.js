'use strict';
// SECURE-LOGIN form (renderer/loginform.html). The values go to the main process once, on Save, and the fields are cleared.
(async () => {
  const $ = (id) => document.getElementById(id);
  const api = window.pmLoginForm;
  let info = null; try { info = await api.info(); } catch (e) { info = null; }
  if (!info) { $('title').textContent = 'This sign-in form has expired.'; $('save').disabled = true; return; }
  $('title').textContent = 'Sign in to ' + info.host;
  $('why').textContent = info.reason ? 'Glim: ' + info.reason : 'Glim needs this login to sign in for you.';
  $('u').focus();
  let busy = false;
  $('f').addEventListener('submit', async (ev) => {
    ev.preventDefault(); if (busy) return;
    const u = $('u').value.trim(), p = $('p').value;
    if (!u || !p) { $('err').textContent = 'Both the username and the password are needed.'; return; }
    busy = true; $('save').disabled = true; $('err').textContent = '';
    let r = null; try { r = await api.save(u, p); } catch (e) { r = { ok: false, error: 'Could not save it.' }; }
    if (!r || !r.ok) { busy = false; $('save').disabled = false; $('err').textContent = (r && r.error) || 'Could not save it.'; return; }
    $('p').value = ''; $('u').value = '';
  });
  $('cancel').addEventListener('click', () => { $('p').value = ''; api.cancel(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { $('p').value = ''; api.cancel(); } });
})();
