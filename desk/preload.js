'use strict';
const { contextBridge, ipcRenderer } = require('electron');
const inv = (c) => (...a) => ipcRenderer.invoke(c, ...a);
const on = (ch) => (cb) => { const f = (e, p) => cb(p); ipcRenderer.on(ch, f); return () => ipcRenderer.removeListener(ch, f); };

contextBridge.exposeInMainWorld('desk', {
  info: inv('info'),
  settings: { get: inv('settings:get'), set: inv('settings:set') },
  threads: { list: inv('threads:list'), create: inv('threads:new'), load: inv('threads:load'), remove: inv('threads:delete'), rename: inv('threads:rename') },
  agent: { send: inv('agent:send'), stop: inv('agent:stop'), respond: inv('respond') },
  browser: { go: inv('browser:go'), back: inv('browser:back'), forward: inv('browser:forward'), reload: inv('browser:reload'), bounds: inv('browser:bounds'), visible: inv('browser:visible'), state: inv('browser:state') },
  screen: { check: inv('screen:check'), ask: inv('screen:ask'), shot: inv('screen:shot') },
  helpers: { list: inv('helpers:list'), run: inv('helpers:run'), pause: inv('helpers:pause'), remove: inv('helpers:delete') },
  openExternal: inv('open:external'),
  ping: inv('gateway:ping'),
  onAgent: on('agent'),
  onBrowser: on('browser-state'),
  onScreen: on('screen'),
  onThreads: on('threads:changed'),
  onHelpers: on('helpers:changed'),
  onOpenThread: on('open-thread')
});
