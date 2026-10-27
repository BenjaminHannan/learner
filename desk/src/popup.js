'use strict';
// The browser popup: a floating window (child of the chat window) that hosts one agent's real page. It exists from the
// agent's first browser use but stays hidden until Ben clicks the live card (or a sign-in is needed). Closing it only
// hides it; the agent keeps working. The page itself is a WebContentsView sized by us (toolbar + optional banner on top).
const { BrowserWindow } = require('electron');
const path = require('path');

const TOOLBAR_H = 58;
const BANNER_H = 60;

class Popup {
  constructor({ parent, view, title, dark, quitting }) {
    this.parent = parent;           // only used to position the popup over the chat window
    this.view = view;
    this.banner = false;
    this.loaded = false;
    this.opened = false;
    this.destroying = false;
    this.quitting = quitting || (() => false);
    this.win = new BrowserWindow({
      width: 1120, height: 780, minWidth: 640, minHeight: 480, show: false, opacity: 0.01,
      title: title || 'Browser', backgroundColor: dark ? '#17120f' : '#faf6f0',
      webPreferences: { preload: path.join(__dirname, '..', 'preload-popup.js'), contextIsolation: true, sandbox: false, nodeIntegration: false, backgroundThrottling: false }
    });
    this.win.setMenuBarVisibility(false);
    this.win.contentView.addChildView(view);
    this.layout();
    this.win.on('resize', () => this.layout());
    this.win.on('close', (e) => { if (!this.destroying && !this.quitting()) { e.preventDefault(); this.background(); } });
    this.wcId = this.win.webContents.id;
    this.background();
  }
  layout() {
    if (this.win.isDestroyed()) return;
    const [w, h] = this.win.getContentSize();
    const top = TOOLBAR_H + (this.banner ? BANNER_H : 0);
    this.view.setBounds({ x: 0, y: top, width: Math.max(0, w), height: Math.max(0, h - top) });
  }
  ensureChrome() {
    if (this.loaded) return Promise.resolve();
    this.loaded = true;
    this.chromeReady = this.win.loadFile(path.join(__dirname, '..', 'renderer', 'popup.html'));
    return this.chromeReady;
  }
  send(ch, p) { if (!this.win.isDestroyed() && this.loaded && !this.win.webContents.isLoading()) this.win.webContents.send(ch, p); }
  sendState(s) { this.lastState = s; this.send('popup-state', s); }
  setBanner(on) { this.banner = !!on; this.layout(); this.send('popup-banner', this.banner); }
  setActive(a) { this.active = !!a; this.send('popup-active', this.active); }

  // Background: the window is "shown" but see-through, click-through, unfocusable and on every Space. A page in a hidden
  // window cannot be captured (live card thumbnails) or typed into, so it must count as visible to Chromium.
  background() {
    const w = this.win;
    if (w.isDestroyed()) return;
    this.opened = false;
    this.banner = false; this.layout();
    w.setIgnoreMouseEvents(true);
    w.setOpacity(0.01);
    try { w.setFocusable(false); } catch (e) { /* ignore */ }
    try { w.setSkipTaskbar(true); w.setHasShadow(false); } catch (e) { /* ignore */ }
    try { w.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true, skipTransformProcessType: true }); } catch (e) { /* ignore */ }
    this.place(false);
    w.showInactive();
  }
  place(open) {
    const w = this.win;
    const d = require('electron').screen.getPrimaryDisplay().workArea;
    let b = { x: d.x, y: d.y, width: d.width, height: d.height };
    if (this.parent && !this.parent.isDestroyed() && this.parent.isVisible()) b = this.parent.getBounds();
    const bw = Math.min(1180, Math.max(640, b.width - 80)), bh = Math.min(820, Math.max(480, b.height - 60));
    w.setBounds({ x: Math.round(b.x + (b.width - bw) / 2), y: Math.round(b.y + Math.max(20, (b.height - bh) / 2)), width: open ? bw : 1120, height: open ? bh : 780 });
  }
  async show(opts) {
    opts = opts || {};
    await this.ensureChrome();
    const w = this.win;
    if (w.isDestroyed()) return;
    this.opened = true;
    this.place(true);
    this.setBanner(!!opts.banner);
    w.setIgnoreMouseEvents(false);
    try { w.setFocusable(true); } catch (e) { /* ignore */ }
    w.setOpacity(1);
    try { w.setSkipTaskbar(false); w.setHasShadow(true); w.setVisibleOnAllWorkspaces(false); } catch (e) { /* ignore */ }
    w.show(); w.focus();
    this.layout();
    // the chrome page may have loaded after we sent; push everything again
    if (this.lastState) this.send('popup-state', this.lastState);
    this.send('popup-banner', this.banner);
    this.send('popup-active', !!this.active);
  }
  hide() { this.background(); }
  isVisible() { return this.opened; }
  destroy() {
    this.destroying = true;
    try { if (!this.win.isDestroyed()) { this.win.contentView.removeChildView(this.view); this.win.destroy(); } } catch (e) { /* ignore */ }
  }
}

module.exports = { Popup, TOOLBAR_H, BANNER_H };
