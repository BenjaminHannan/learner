'use strict';
const { execFile } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const NOT_INSTALLED = 'screen control helper not installed';

function candidates(settings, resourcesPath) {
  const list = [];
  if (settings && settings.helperPath) list.push(settings.helperPath);
  if (resourcesPath) list.push(path.join(resourcesPath, 'deskhelper'));
  list.push(path.join(__dirname, '..', '..', 'helper', 'deskhelper'));
  list.push(path.join(__dirname, '..', '..', 'build', 'deskhelper'));
  return list;
}

function findHelper(settings, resourcesPath) {
  for (const c of candidates(settings, resourcesPath)) {
    try { if (fs.statSync(c).isFile()) return c; } catch (e) { /* next */ }
  }
  return null;
}

function callHelper(bin, args, signal) {
  return new Promise((resolve) => {
    execFile(bin, args, { timeout: 30000, maxBuffer: 8 * 1024 * 1024, signal }, (err, stdout) => {
      let j = null;
      try { j = JSON.parse(String(stdout || '').trim()); } catch (e) { /* not json */ }
      if (j) return resolve(j);
      resolve({ error: err ? String(err.message).split('\n')[0] : 'helper returned no JSON' });
    });
  });
}

function formatLook(j) {
  if (j.error) return 'Error: ' + j.error;
  const lines = [];
  lines.push('App: ' + (j.app || '?') + (j.pid ? ' (pid ' + j.pid + ')' : ''));
  for (const w of j.windows || []) lines.push('Window: ' + (w.title || '(untitled)') + (w.frame ? ' ' + JSON.stringify(w.frame) : ''));
  for (const e of j.elements || []) {
    const f = e.frame ? ' @' + e.frame.map((n) => Math.round(n)).join(',') : '';
    lines.push('[' + e.id + '] ' + (e.role || '') + (e.title ? ' "' + String(e.title).slice(0, 60) + '"' : '') + (e.value ? ' value="' + String(e.value).slice(0, 60) + '"' : '') + f);
  }
  let s = lines.join('\n');
  if (s.length > 3500) s = s.slice(0, 3500) + '\n[truncated]';
  return s;
}

// factory: returns tool functions + helpers used by main.js for the Screen tab
function createScreen(getSettings, resourcesPath, onLook) {
  const bin = () => findHelper(getSettings(), resourcesPath);
  const run = async (args, signal) => {
    const b = bin();
    if (!b) return { error: NOT_INSTALLED };
    return callHelper(b, args, signal);
  };
  const res = (j, okText) => (j.error ? { text: 'Error: ' + j.error, error: true } : okText || JSON.stringify(j));

  async function screenshot(max) {
    const b = bin();
    if (!b) return null;
    const p = path.join(os.tmpdir(), 'premonition-desk-shot-' + process.pid + '.jpg');
    const j = await callHelper(b, ['screenshot', p, '--max', String(max || 1280)]);
    if (j.error) return null;
    try { return 'data:image/jpeg;base64,' + fs.readFileSync(p).toString('base64'); } catch (e) { return null; }
  }

  const vis = () => { const v = getSettings().vision; return v === 'on' || v === true; };

  return {
    findHelper: () => bin(),
    check: async () => run(['check']),
    askPermissions: async () => run(['ask-permissions']),
    screenshot,
    tools: {
      screen_look: async (a, ctx) => {
        const args = ['look'];
        if (a.app) args.push('--app', String(a.app));
        const j = await run(args, ctx && ctx.signal);
        if (j.error) return { text: 'Error: ' + j.error, error: true };
        const text = formatLook(j);
        const shot = await screenshot(1280);
        if (onLook) onLook({ text, image: shot, data: j });
        return vis() && shot ? { text, image: shot } : text;
      },
      screen_click: async (a, ctx) => {
        let j;
        if (a.id !== undefined && a.id !== null) j = await run(['press', String(a.id)], ctx && ctx.signal);
        else if (a.x !== undefined && a.y !== undefined) j = await run(['click', String(a.x), String(a.y)].concat(a.double ? ['--double'] : []), ctx && ctx.signal);
        else return { text: 'Error: give id, or x and y', error: true };
        return res(j, 'Clicked.');
      },
      screen_type: async (a, ctx) => res(await run(['type', String(a.text || '')], ctx && ctx.signal), 'Typed.'),
      screen_key: async (a, ctx) => res(await run(['key', String(a.keys || '')], ctx && ctx.signal), 'Pressed ' + a.keys + '.'),
      open_app: async (a, ctx) => res(await run(['open-app', String(a.name || '')], ctx && ctx.signal), 'Opened ' + a.name + '.')
    }
  };
}

module.exports = { createScreen, findHelper, formatLook, NOT_INSTALLED };
