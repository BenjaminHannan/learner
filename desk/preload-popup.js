'use strict';
const { contextBridge, ipcRenderer } = require('electron');
const on = (ch) => (cb) => { const f = (e, p) => cb(p); ipcRenderer.on(ch, f); return () => ipcRenderer.removeListener(ch, f); };
contextBridge.exposeInMainWorld('deskPopup', {
  cmd: (name, arg) => ipcRenderer.invoke('popup:cmd', name, arg),
  onState: on('popup-state'), onBanner: on('popup-banner'), onActive: on('popup-active')
});
