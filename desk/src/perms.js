'use strict';
// Permissions card helpers (pure, unit-tested): which .app bundle to drag into System Settings, the pane URLs, and how the
// two ways of asking macOS (Electron's own API and the deskhelper binary) combine into one row each.
const path = require('path');

// Walk up from the running executable to the directory ending in ".app" (…/Premonition Desk.app/Contents/MacOS/Premonition Desk).
// In dev there is no bundle around Electron, so fall back to the executable itself.
function appBundlePath(exe, execPath) {
  let p = String(exe || '');
  for (let i = 0; i < 8 && p && p !== path.dirname(p); i++) {
    if (p.endsWith('.app')) return p;
    p = path.dirname(p);
  }
  return execPath || exe || '';
}

const BASE = 'x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?';
const OLD = 'x-apple.systempreferences:com.apple.preference.security?';
const ROWS = [
  { id: 'accessibility', label: 'Accessibility', why: 'Lets Glim click and type in other Mac apps.', pane: 'Privacy_Accessibility' },
  { id: 'screen', label: 'Screen Recording', why: 'Lets Glim see what is on your screen.', pane: 'Privacy_ScreenCapture' },
  { id: 'automation', label: 'Automation', why: 'Optional: lets Glim control apps like Finder or Mail.', pane: 'Privacy_Automation', optional: true }
];
const paneUrls = (id) => { const r = ROWS.find((x) => x.id === id); return r ? { url: BASE + r.pane, fallback: OLD + r.pane } : null; };

// helper: result of `deskhelper check` ({accessibility, screenRecording} or {error}) or null when there is no helper.
// electron: {accessibility: bool|null, screen: bool|null} from systemPreferences. A row is on only when everything that can answer says yes;
// "app" is Electron's answer, "helper" is deskhelper's. Automation has no status (macOS asks per app the first time).
function combine(helper, electron) {
  const h = helper && !helper.error ? helper : null;
  const e = electron || {};
  const pick = (id, hv, ev) => {
    const vals = [hv, ev].filter((v) => typeof v === 'boolean');
    return { id, granted: vals.length ? vals.every(Boolean) : null, app: typeof ev === 'boolean' ? ev : null, helper: typeof hv === 'boolean' ? hv : null };
  };
  const rows = [pick('accessibility', h && h.accessibility, e.accessibility), pick('screen', h && h.screenRecording, e.screen), { id: 'automation', granted: null, app: null, helper: null }];
  // deskhelper says no while the app itself is allowed: macOS lists the helper binary separately, so offer it as a tile too
  const helperTile = !!h && rows.slice(0, 2).some((r) => r.helper === false && r.app === true);
  const missing = rows.slice(0, 2).some((r) => r.granted === false);
  return { rows, helperTile, missing };
}

module.exports = { appBundlePath, paneUrls, combine, ROWS };

// Open a Privacy pane; if the new-style URL is refused (older macOS), try the old form. Resolves true/false.
async function openPane(shell, id) {
  const u = paneUrls(id);
  if (!u) return false;
  try { await shell.openExternal(u.url); return true; } catch (e) { /* fall back */ }
  try { await shell.openExternal(u.fallback); return true; } catch (e) { return false; }
}

// IPC handler for the drag tile: only the main window's webContents may start a drag, and only of our own bundle (or deskhelper).
// deps: {getSender: () => the main window's webContents, getFiles: () => {app, helper}, getIcon: () => nativeImage}
function makeDragHandler(deps) {
  return (event, which) => {
    const sender = deps.getSender();
    if (!sender || !event || event.sender !== sender) return false;
    const files = deps.getFiles() || {};
    const file = which === 'helper' ? files.helper : files.app;
    if (!file) return false;
    try { event.sender.startDrag({ file, icon: deps.getIcon(which) }); return true; } catch (e) { return false; }
  };
}

module.exports.openPane = openPane;
module.exports.makeDragHandler = makeDragHandler;
