'use strict';
const { contextBridge, ipcRenderer } = require('electron');
const on = (ch) => (cb) => { const f = (e, p) => cb(p); ipcRenderer.on(ch, f); return () => ipcRenderer.removeListener(ch, f); };
contextBridge.exposeInMainWorld('deskPill', {
  act: (name, arg) => ipcRenderer.invoke('pill:act', name, arg),
  onView: on('pill-view')
});
