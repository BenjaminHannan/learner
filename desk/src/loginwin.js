'use strict';
// SECURE-LOGIN: the app's own sign-in form window (renderer/loginform.html + preload-loginform.js). One small window per site.
// It is the app's, not a web page's: no web content, no navigation, no new windows, its own sandboxed session.
const path = require('path');

// o: {BrowserWindow, onClosed(token), wins: Map token -> BrowserWindow (main.js checks IPC senders against it)}
function formOpener(o) {
  const wins = o.wins;
  return ({ token, host, focus }) => {
    const w = new o.BrowserWindow({
      width: 380, height: 340, resizable: false, minimizable: false, maximizable: false, fullscreenable: false, alwaysOnTop: true,
      title: 'Sign in to ' + host + ' — Glim', show: false, skipTaskbar: false,
      webPreferences: { preload: path.join(__dirname, '..', 'preload-loginform.js'), contextIsolation: true, sandbox: true, nodeIntegration: false,
        partition: 'pm-loginform', spellcheck: false, devTools: !!o.devTools }
    });
    wins.set(token, w);
    w.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
    w.webContents.on('will-navigate', (e) => e.preventDefault());
    w.on('closed', () => { wins.delete(token); try { o.onClosed(token); } catch (e) { /* gone */ } });
    w.once('ready-to-show', () => { if (w.isDestroyed()) return; if (focus) { w.show(); w.focus(); } else w.showInactive(); });
    w.loadFile(path.join(__dirname, '..', 'renderer', 'loginform.html'), { query: { t: token } });
    return {
      win: w,
      show: (f) => { if (w.isDestroyed()) return; if (f) { w.show(); w.focus(); } else w.showInactive(); },
      close: () => { wins.delete(token); if (!w.isDestroyed()) w.destroy(); }
    };
  };
}

module.exports = { formOpener };
