'use strict';
// The status pill: a small always-on-top, frameless, transparent window pinned top-center under the menu bar. It shows
// across apps and Spaces (even over full-screen apps), never steals focus, and lets clicks pass through everywhere
// except over the pill itself. Collapsed it is one line with Glim; hovering expands it into a details card.
const { BrowserWindow, screen } = require('electron');
const path = require('path');

const W = 420, H = 300;

class PillWindow {
  constructor({ dark }) {
    this.view = { visible: false };
    this.enabled = true;
    this.hideTimer = null;
    this.win = new BrowserWindow({
      width: W, height: H, show: false, transparent: true, frame: false, hasShadow: false, resizable: false, movable: false,
      focusable: false, skipTaskbar: true, ...(process.platform === 'darwin' ? { type: 'panel' } : {}), alwaysOnTop: true, fullscreenable: false, backgroundColor: '#00000000',
      webPreferences: { preload: path.join(__dirname, '..', 'preload-pill.js'), contextIsolation: true, sandbox: false, nodeIntegration: false, backgroundThrottling: false }
    });
    try { this.win.setAlwaysOnTop(true, 'screen-saver'); } catch (e) { /* platform without levels */ }
    try { this.win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true, skipTransformProcessType: true }); } catch (e) { /* ignore */ }
    try { if (process.platform === 'darwin') this.win.setHiddenInMissionControl(true); } catch (e) { /* ignore */ }
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
    this.win.setBounds({ x: Math.round(a.x + (a.width - W) / 2), y: Math.round(a.y + 6), width: W, height: H });
  }
  setInteractive(on) { if (!this.win.isDestroyed()) this.win.setIgnoreMouseEvents(!on, { forward: true }); }
  // v: PillState.view(); hidden: true when the chat window is in front (the pill would be redundant)
  update(v, hidden) {
    this.view = v;
    if (this.win.isDestroyed()) return;
    const show = this.enabled && v.visible && !hidden;
    this.win.webContents.send('pill-view', { ...v, visible: show });
    clearTimeout(this.hideTimer);
    if (show) { if (!this.win.isVisible()) this.win.showInactive(); }
    else if (this.win.isVisible()) { this.setInteractive(false); this.hideTimer = setTimeout(() => { if (!this.win.isDestroyed()) this.win.hide(); }, 450); }
  }
  destroy() { for (const ev of ['display-metrics-changed', 'display-added', 'display-removed']) screen.removeListener(ev, this.onDisplay); clearTimeout(this.hideTimer); try { if (!this.win.isDestroyed()) this.win.destroy(); } catch (e) { /* ignore */ } }
}

module.exports = { PillWindow, W, H };
