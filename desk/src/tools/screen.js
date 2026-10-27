'use strict';
const { execFile } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const { screenAfter, lookSummary } = require('./after');
const Platform = require('../../renderer/platform');

const NOT_INSTALLED = 'screen control helper not installed';

// open_app is for Mac apps, never for browsing: the web goes through the built-in browser (browser_go).
const BROWSER_APPS = /^(safari( technology preview)?|google chrome( canary)?|chrome|chromium|firefox|mozilla firefox|arc|microsoft edge|msedge|edge|iexplore|internet explorer|brave( browser)?|opera( gx)?|vivaldi|orion|duckduckgo)(\.app|\.exe)?$/i;
const isBrowserApp = (name) => BROWSER_APPS.test(String(name || '').trim());
const BROWSER_REFUSAL = 'Error: do not open a web browser app. Use browser_go (the built-in browser) for anything on the web. open_app is only for non-browser apps.';

function candidates(settings, resourcesPath, platform) {
  return Platform.helperCandidates(platform || process.platform, path.join, settings, resourcesPath, path.join(__dirname, '..', '..'));
}

function findHelper(settings, resourcesPath, platform) {
  for (const c of candidates(settings, resourcesPath, platform)) {
    try { if (fs.statSync(c).isFile()) return c; } catch (e) { /* next */ }
  }
  return null;
}

// What to execute for a helper file: the Swift binary itself on a Mac, powershell.exe -File deskhelper.ps1 on Windows.
function helperInvocation(bin, args, platform) {
  const h = Platform.helperCommand(platform || process.platform, bin);
  return { cmd: h.cmd, args: h.prefix.concat(args) };
}

function callHelper(bin, args, signal) {
  return new Promise((resolve) => {
    const inv = helperInvocation(bin, args);
    execFile(inv.cmd, inv.args, { windowsHide: true, timeout: 30000, maxBuffer: 8 * 1024 * 1024, signal }, (err, stdout) => {
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

  // After a state-changing action: look again (cheap, no screenshot) and say what changed since the last look.
  let lastLook = null;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function after(kind, signal, extra) {
    try {
      await sleep(300);
      const j = await run(['look', '--max', '80'], signal);
      if (j.error) return '';
      const note = screenAfter(lastLook, j, kind, extra && extra(j));
      lastLook = lookSummary(j);
      return '\n' + note;
    } catch (e) { return ''; }
  }
  const withAfter = async (r, kind, signal, extra) => (typeof r === 'string' ? r + await after(kind, signal, extra) : r);

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
        lastLook = lookSummary(j);
        const shot = await screenshot(1280);
        if (onLook) onLook({ text, image: shot, data: j }, ctx);
        return vis() && shot ? { text, image: shot } : text;
      },
      screen_click: async (a, ctx) => {
        let j;
        if (a.id !== undefined && a.id !== null) j = await run(['press', String(a.id)], ctx && ctx.signal);
        else if (a.x !== undefined && a.y !== undefined) j = await run(['click', String(a.x), String(a.y)].concat(a.double ? ['--double'] : []), ctx && ctx.signal);
        else return { text: 'Error: give id, or x and y', error: true };
        return withAfter(res(j, 'Clicked.'), 'click', ctx && ctx.signal);
      },
      screen_type: async (a, ctx) => withAfter(res(await run(['type', String(a.text || '')], ctx && ctx.signal), 'Typed.'), 'type', ctx && ctx.signal),
      screen_key: async (a, ctx) => withAfter(res(await run(['key', Platform.mapKeys(process.platform, String(a.keys || ''))], ctx && ctx.signal), 'Pressed ' + a.keys + '.'), 'key', ctx && ctx.signal),
      open_app: async (a, ctx) => {
        if (isBrowserApp(a.name)) return { text: BROWSER_REFUSAL, error: true };
        const r = res(await run(['open-app', String(a.name || '')], ctx && ctx.signal), 'Opened ' + a.name + '.');
        const want = String(a.name || '').toLowerCase().replace(/\.app$/, '');
        return withAfter(r, 'open', ctx && ctx.signal, (j) => (want && j.app && !String(j.app).toLowerCase().includes(want) ? 'WARNING: front app is "' + j.app + '", not "' + a.name + '"; it may not have opened' : ''));
      }
    }
  };
}

module.exports = { createScreen, findHelper, helperInvocation, candidates, formatLook, NOT_INSTALLED, isBrowserApp, BROWSER_REFUSAL };
