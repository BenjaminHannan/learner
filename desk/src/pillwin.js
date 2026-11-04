'use strict';
// The status pill: a small always-on-top, frameless, transparent window pinned top-center under the menu bar. It shows
// across apps and Spaces (even over full-screen apps), never steals focus, and lets clicks pass through everywhere
// except over the pill itself. Collapsed it is one line with Glim; hovering expands it into a details card.
const { BrowserWindow, screen } = require('electron');
const path = require('path');
const Platform = require('../renderer/platform');

const W = 420, H = 300;

// The real notch from the screen helper (`deskhelper notch`): its width varies with the Mac and its display scaling (185-250 pt),
// and it is known even when the menu bar is hidden (full-screen app at launch, auto-hide), where workArea.y says 0 and the
// icon used to fall back to a floating circle under the camera. null when the helper is missing or the screen has no notch.
function notchSize() {
  try {
    const { findHelper } = require('./tools/screen');
    const bin = findHelper({}, process.resourcesPath, process.platform);
    const r = bin ? JSON.parse(require('child_process').execFileSync(bin, ['notch'], { timeout: 2000 }).toString()) : null;
    return r && r.height > 0 ? { width: Math.round(r.width) || 200, height: Math.round(r.height) } : null;
  } catch (e) { return null; }
}

class PillWindow {
  constructor({ dark }) {
    this.view = { visible: false };
    this.enabled = true;
    this.hideTimer = null;
    const po = Platform.pillOptions(process.platform, W, H); // Mac: NSPanel on all Spaces. Windows: frameless 'screen-saver'-level window, no 'panel' type
    this.win = new BrowserWindow({
      ...po.options,
      webPreferences: { preload: path.join(__dirname, '..', 'preload-pill.js'), contextIsolation: true, sandbox: false, nodeIntegration: false, backgroundThrottling: false }
    });
    try { this.win.setAlwaysOnTop(true, po.level); } catch (e) { /* platform without levels */ }
    if (po.allWorkspaces) { try { this.win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true, skipTransformProcessType: true }); } catch (e) { /* ignore */ } }
    try { if (po.hideInMissionControl) this.win.setHiddenInMissionControl(true); } catch (e) { /* ignore */ }
    this.win.setIgnoreMouseEvents(true, { forward: true });
    this.position();
    this.win.loadFile(path.join(__dirname, '..', 'renderer', 'pill.html'));
    this.ready = new Promise((r) => this.win.webContents.once('did-finish-load', r));
    this.onDisplay = () => this.position();
    for (const ev of ['display-metrics-changed', 'display-added', 'display-removed']) screen.on(ev, this.onDisplay);
  }
  position() {
    if (this.win.isDestroyed()) return;
    const d = screen.getPrimaryDisplay();
    const a = d.workArea; // starts below the menu bar on macOS
    // remember the tallest menu bar / notch band seen; full-screen apps report 0 and would slide the pill under the camera
    const notch = process.platform === 'darwin' ? notchSize() : null;
    this.topInset = Math.max(this.topInset || 0, a.y - d.bounds.y, notch ? notch.height : 0);
    const pos = Platform.pillPosition(a, W, d.bounds.y + this.topInset);
    // the window starts at the very top of the screen; the pill hangs down by `pt`, and on a notched Mac the idle icon sits IN the
    // menu-bar band around the camera (black, fused to the notch). Electron has no notch size, so the screen helper measures it.
    this.geo = { pt: pos.y - d.bounds.y, notchH: notch ? notch.height : 0, notchW: notch ? notch.width : 0 };
    this.win.setBounds({ x: pos.x, y: d.bounds.y, width: W, height: H + this.geo.pt });
    if (this.fence) this.setFence(this.fenceRect); // the window moved: move the fence with it
    if (this.view && this.lastSent) this.win.webContents.send('pill-view', { ...this.lastSent, geo: this.geo });
  }
  // Ben Nov 3: `deskhelper fence` keeps the cursor off the top edge over the island (so a full-screen app's menu bar stays hidden there).
  // r: the island's {left, right} in window px, or null. Started lazily; restarted if it dies (at most every 30 s).
  setFence(r) {
    if (process.platform !== 'darwin' || this.win.isDestroyed()) return;
    this.fenceRect = r;
    const x = this.win.getBounds().x, line = r ? (x + r.left) + ' ' + (x + r.right) : 'off';
    if (!this.fence && r && Date.now() - (this.fenceStarted || 0) > 30000) {
      try {
        const { findHelper } = require('./tools/screen');
        const bin = findHelper({}, process.resourcesPath, process.platform);
        if (bin) {
          this.fenceStarted = Date.now();
          const c = require('child_process').spawn(bin, ['fence'], { stdio: ['pipe', 'ignore', 'pipe'] });
          c.on('exit', () => { if (this.fence === c) this.fence = null; });
          c.on('error', () => { if (this.fence === c) this.fence = null; });
          c.stdin.on('error', () => {});
          c.stderr.on('data', (d) => console.log('[fence]', String(d).trim()));
          this.fence = c;
        }
      } catch (e) { this.fence = null; }
    }
    if (this.fence) { try { this.fence.stdin.write(line + '\n'); } catch (e) { /* ignore */ } }
  }
  setInteractive(on) { if (!this.win.isDestroyed()) this.win.setIgnoreMouseEvents(!on, { forward: true }); this.setVeil(on); }
  // Ben Nov 3: while the cursor is on Glim, the menu bar (app menus, icons, clock) hides: a black strip the height of the notch band
  // covers the whole top of the screen, under the island, and goes away when the cursor leaves. Notched Macs only.
  setVeil(on) {
    if (process.platform !== 'darwin' || !this.geo || !this.geo.notchH) return;
    if (on && !this.veil) {
      try {
        this.veil = new BrowserWindow({ show: false, frame: false, transparent: false, hasShadow: false, resizable: false, movable: false, focusable: false,
          skipTaskbar: true, fullscreenable: false, enableLargerThanScreen: true, type: 'panel', backgroundColor: '#000000', webPreferences: { sandbox: true } });
        this.veil.setIgnoreMouseEvents(true);
        this.veil.setAlwaysOnTop(true, 'screen-saver');
        try { this.veil.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true, skipTransformProcessType: true }); } catch (e) { /* ignore */ }
        try { this.veil.setHiddenInMissionControl(true); } catch (e) { /* ignore */ }
        this.veil.loadURL('data:text/html,<body style="margin:0;background:%23000"></body>');
        this.win.setAlwaysOnTop(true, 'screen-saver', 1); // the island stays above the strip
      } catch (e) { this.veil = null; return; }
    }
    if (!this.veil || this.veil.isDestroyed()) return;
    if (on) {
      const d = screen.getPrimaryDisplay();
      this.veil.setBounds({ x: d.bounds.x, y: d.bounds.y, width: d.bounds.width, height: this.topInset || this.geo.notchH });
      if (!this.veil.isVisible()) this.veil.showInactive();
      this.win.moveTop();
    } else if (this.veil.isVisible()) this.veil.hide();
  }
  // v: PillState.view(); hidden: true when the chat window is in front (the pill would be redundant)
  update(v, hidden) {
    this.view = v;
    if (this.win.isDestroyed()) return;
    // idle: a small Glim icon so Ben can tell it is there while he is in another window
    if (!v.visible && process.platform === 'darwin') v = { ...v, visible: true, status: 'idle', mood: 'idle', line: '', top: null, others: [] };
    const show = this.enabled && v.visible && !hidden;
    this.lastSent = { ...v, visible: show };
    this.win.webContents.send('pill-view', { ...this.lastSent, geo: this.geo });
    clearTimeout(this.hideTimer);
    if (show) { if (!this.win.isVisible()) this.win.showInactive(); }
    else if (this.win.isVisible()) { this.setInteractive(false); this.hideTimer = setTimeout(() => { if (!this.win.isDestroyed()) this.win.hide(); }, 450); }
  }
  destroy() { try { if (this.fence) this.fence.kill(); } catch (e) { /* ignore */ } try { if (this.veil && !this.veil.isDestroyed()) this.veil.destroy(); } catch (e) { /* ignore */ }
    for (const ev of ['display-metrics-changed', 'display-added', 'display-removed']) screen.removeListener(ev, this.onDisplay); clearTimeout(this.hideTimer); try { if (!this.win.isDestroyed()) this.win.destroy(); } catch (e) { /* ignore */ } }
}

module.exports = { PillWindow, W, H };
