'use strict';
const { contextBridge, ipcRenderer } = require('electron');
const inv = (c) => (...a) => ipcRenderer.invoke(c, ...a);
const on = (ch) => (cb) => { const f = (e, p) => cb(p); ipcRenderer.on(ch, f); return () => ipcRenderer.removeListener(ch, f); };

contextBridge.exposeInMainWorld('desk', {
  info: inv('info'),
  settings: { get: inv('settings:get'), set: inv('settings:set') },
  threads: { list: inv('threads:list'), create: inv('threads:new'), load: inv('threads:load'), remove: inv('threads:delete'), rename: inv('threads:rename') },
  agent: { send: inv('agent:send'), stop: inv('agent:stop'), respond: inv('respond') },
  browser: { open: inv('browser:open'), exists: inv('browser:exists'), layout: inv('browser:layout'), cmd: inv('browser:cmd') },
  perms: { status: inv('perms:status'), open: inv('perms:open'), reveal: inv('perms:reveal'), drag: (which) => ipcRenderer.send('perms:drag', which) },
  screen: { check: inv('screen:check'), ask: inv('screen:ask') },
  helpers: { list: inv('helpers:list'), run: inv('helpers:run'), pause: inv('helpers:pause'), remove: inv('helpers:delete') },
  openSystem: inv('system:open'),
  openExternal: inv('open:external'),
  gateway: { state: inv('gateway:state'), test: inv('gateway:test') },
  onAgent: on('agent'),
  onGateway: on('gateway'),
  onGlim: on('glim-state'),
  onThreads: on('threads:changed'),
  onHelpers: on('helpers:changed'),
  onOpenThread: on('open-thread'),
  onOpenSettings: on('open-settings'),
  onNewThread: on('new-thread'),
  onPermsShow: on('perms-show'),
  onPermsRecheck: on('perms-recheck'),
  onBrowserShow: on('browser-show'),
  onBrowserHide: on('browser-hide'),
  onBrowserState: on('browser-state'),
  onBrowserGone: on('browser-gone'),
  onFocusComposer: on('focus-composer')
});
