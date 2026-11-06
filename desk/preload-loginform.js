'use strict';
// SECURE-LOGIN: preload for the app's own sign-in form window (renderer/loginform.html). Not a web page: only main.js opens it.
// It passes what Ben types straight to the main process, which saves it in the keychain (src/loginform.js + src/logins.js).
// Nothing typed here ever goes to the chat, the model, notes, the diary or any log.
const { contextBridge, ipcRenderer } = require('electron');
const token = (() => { try { return new URLSearchParams(location.search).get('t') || ''; } catch (e) { return ''; } })();
contextBridge.exposeInMainWorld('pmLoginForm', {
  info: () => ipcRenderer.invoke('loginform:info', token),
  save: (user, password) => ipcRenderer.invoke('loginform:save', token, String(user || ''), String(password || '')),
  cancel: () => ipcRenderer.invoke('loginform:cancel', token)
});
