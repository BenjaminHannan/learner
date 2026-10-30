'use strict';
// Everything that differs between macOS, Windows and Linux, as pure functions of a platform string, so it can be unit-tested
// by passing 'win32' / 'darwin' / 'linux' (no need to stub process.platform). Loaded by the renderer (window.Platform) and by
// main.js / src/* / the tests (require). No Electron, no fs.
(function (root) {
  const isWin = (p) => p === 'win32';
  const isMac = (p) => p === 'darwin';

  // ---- screen helper -------------------------------------------------------------------------------
  // Mac: the compiled Swift binary `deskhelper`. Windows: `deskhelper.exe`, a small C# program (.NET Framework 4.8, built by helper/win/build.sh; a PowerShell script was flagged by Defender).
  // Linux has no helper (dev machine only).
  const helperFileName = (p) => (isWin(p) ? 'deskhelper.exe' : 'deskhelper');
  // {cmd, prefix}: the command to execute and the args that come before the helper's own args.
  function helperCommand(p, helperPath) {
    return { cmd: helperPath, prefix: [] };
  }
  // Where to look, in order. join is path.join (or the win32/posix variant under test).
  function helperCandidates(p, join, settings, resourcesPath, baseDir) {
    const f = helperFileName(p);
    const list = [];
    if (settings && settings.helperPath) list.push(settings.helperPath);
    if (resourcesPath) list.push(join(resourcesPath, f));
    list.push(join(baseDir, 'helper', f));
    if (isWin(p)) list.push(join(baseDir, 'vendor', 'helper', f)); // dev checkout: the exe built by helper/win/build.sh
    list.push(join(baseDir, 'build', f));
    return list;
  }

  // ---- keys ---------------------------------------------------------------------------------------
  // The model writes Mac-style combos ("cmd+t", "option+left"). On Windows: cmd -> ctrl, option -> alt, and a few Mac-only
  // combos become their Windows twin. Returns the combo string for the helper (lowercase, '+' separated).
  const WIN_COMBOS = { 'ctrl+q': 'alt+f4', 'ctrl+w': 'ctrl+w', 'ctrl+,': 'ctrl+,' };
  function mapKeys(p, combo) {
    const raw = String(combo == null ? '' : combo).trim();
    if (!isWin(p) || !raw) return raw;
    let parts = raw.split('+').map((s) => s.trim().toLowerCase());
    if (raw.endsWith('++')) parts = raw.slice(0, -2).split('+').map((s) => s.trim().toLowerCase()).concat('plus');
    parts = parts.filter((s) => s !== '');
    const MODS = { cmd: 'ctrl', command: 'ctrl', meta: 'ctrl', super: 'ctrl', control: 'ctrl', ctrl: 'ctrl', option: 'alt', opt: 'alt', alt: 'alt', shift: 'shift' };
    const KEYS = { return: 'enter', esc: 'escape', delete: 'backspace', del: 'delete', forwarddelete: 'delete', pageup: 'pageup', pagedown: 'pagedown' };
    const mods = []; let key = null;
    for (const s of parts) {
      if (s === 'fn') continue;
      if (MODS[s]) { if (!mods.includes(MODS[s])) mods.push(MODS[s]); } else key = KEYS[s] || s;
    }
    if (!key) return mods.join('+');
    const order = ['ctrl', 'alt', 'shift'];
    mods.sort((a, b) => order.indexOf(a) - order.indexOf(b));
    const out = mods.concat(key).join('+');
    return WIN_COMBOS[out] || out;
  }

  // ---- hotkey -------------------------------------------------------------------------------------
  // Alt+Space opens the window menu on Windows, so Windows defaults to Ctrl+Space.
  const defaultHotkey = (p) => (isWin(p) ? 'Ctrl+Space' : 'Alt+Space');
  function hotkeyLabel(p, acc) {
    if (!acc) return 'Off';
    if (isMac(p)) return acc.replace(/\bAlt\b/g, 'Option').replace(/\bCommand\b/g, 'Cmd').replace(/\bControl\b/g, 'Ctrl');
    return acc.replace(/\bControl\b/g, 'Ctrl').replace(/\bCommand\b/g, 'Win');
  }
  const modifierHint = (p) => (isMac(p) ? 'Option, Cmd, Ctrl' : 'Ctrl, Alt, Shift');

  // ---- feature gating -----------------------------------------------------------------------------
  // perms: the macOS Privacy card (Windows needs no permission to click or look). sleep: the Sleep group and top-bar button.
  // sleepBuiltin: sleep runs through the app's own runner (src/sleepwin.js) on the built-in model; else through the sleepmode app. tray: hide-to-tray instead of the Mac "see-through window".
  // o.hasLocalAssistant: true when this is one of Ben's Macs (~/learner-ops/assistant/serve.sh exists). main.js looks at the disk and
  // passes it in, so this file stays pure. The built-in model runs on Windows, and on any Mac that is known to have no such assistant
  // (an unknown value keeps the old behaviour: the assistant gateway).
  const builtinOn = (p, o) => isWin(p) || (isMac(p) && !!o && o.hasLocalAssistant === false);
  // Every platform sleeps: Windows and the built-in Mac through the app's own runner (the trainer's base is the built-in model's
  // base, so the night's adapter is loaded into the daytime model), Ben's Macs through the sleepmode app.
  function features(p, o) {
    return { perms: isMac(p), sleep: true, sleepSoon: false, sleepBuiltin: builtinOn(p, o), builtin: builtinOn(p, o), tray: isWin(p), dock: isMac(p), call: isMac(p), dictate: isMac(p), menuBarAutoHide: isWin(p) };
  }
  const PERMS_NOTE_WIN = "Windows doesn't need extra permissions.";
  // What Settings shows for the gated rows. With the built-in runner (Windows, built-in Mac) the sleepmode-app rows (its folder and
  // Python) are replaced by the plain-language rows (sleepWindows: the name is historical).
  function settingsGating(p, o) {
    const f = features(p, o);
    return { showSleepGroup: true, sleepUnavailable: false, sleepNote: '', sleepWindows: f.sleepBuiltin, showPermRow: f.perms, permsNote: f.perms ? '' : (isWin(p) ? PERMS_NOTE_WIN : 'Nothing to set up on this system.'), showSleepButton: f.sleep };
  }
  // Onboarding: the Permissions step exists only on a Mac (and in the Linux e2e, which fakes macOS).
  const needsPermsStep = (p, e2e) => isMac(p) || !!e2e;

  // ---- pill window --------------------------------------------------------------------------------
  // Mac: an NSPanel on all Spaces. Windows: a frameless always-on-top window at the 'screen-saver' level (no 'panel' type).
  function pillOptions(p, width, height) {
    const base = {
      width, height, show: false, transparent: true, frame: false, hasShadow: false, resizable: false, movable: false,
      focusable: false, skipTaskbar: true, alwaysOnTop: true, fullscreenable: false, backgroundColor: '#00000000'
    };
    // enableLargerThanScreen: otherwise macOS pushes the window below the menu bar (y=44 on a 16") and the idle icon can't reach the notch
    if (isMac(p)) return { options: { ...base, type: 'panel', enableLargerThanScreen: true }, level: 'screen-saver', allWorkspaces: true, hideInMissionControl: true };
    return { options: base, level: 'screen-saver', allWorkspaces: false, hideInMissionControl: false };
  }
  // top-center of the primary display's work area (below the menu bar on a Mac, clear of the taskbar on Windows)
  // minTop: the biggest menu-bar/notch height seen on this display (workArea.y - bounds.y). In a full-screen app the menu bar hides and
// workArea.y drops to 0, which would put the pill behind the camera notch, so it never rides higher than that.
const pillPosition = (workArea, width, minTop) => ({ x: Math.round(workArea.x + (workArea.width - width) / 2), y: Math.round(Math.max(workArea.y, minTop || 0) + 6) });

  // ---- window / startup ---------------------------------------------------------------------------
  // What closing the window does. 'quit' (keep-running off), 'tray' (Windows), 'conceal' (Mac with browser views alive), 'hide'.
  function closeBehavior(p, keepRunning, hasBrowsers) {
    if (!keepRunning) return 'quit';
    if (isWin(p)) return 'tray';
    if (isMac(p) && hasBrowsers) return 'conceal';
    return 'hide';
  }
  const quitHint = (p) => (isMac(p) ? 'Cmd+Q' : 'the tray icon\'s Quit (or File > Quit)');
  // setLoginItemSettings argument. Windows has no openAsHidden: it starts us with --hidden instead.
  function loginItemOptions(p, on) {
    return isWin(p) ? { openAtLogin: !!on, args: ['--hidden'] } : { openAtLogin: !!on, openAsHidden: true };
  }
  function startedHidden(p, argv, loginSettings) {
    if ((argv || []).includes('--night')) return true;   // opened by the night-start agent at the start of the sleep window (src/nightstart.js)
    if (isWin(p)) return (argv || []).includes('--hidden');
    return !!(loginSettings && loginSettings.wasOpenedAsHidden);
  }
  // BrowserWindow options that differ by platform
  function windowOptions(p, icon) {
    const mac = isMac(p);
    return { icon: mac ? undefined : icon, titleBarStyle: mac ? 'hiddenInset' : 'default', trafficLightPosition: mac ? { x: 16, y: 18 } : undefined, autoHideMenuBar: isWin(p) };
  }

  // ---- text swaps for the model's constant prompt --------------------------------------------------
  const osWords = (p) => (isWin(p) ? { computer: 'PC', apps: 'Windows', shell: 'PowerShell', keyEx: 'ctrl+t', browsers: 'Chrome, Firefox, Brave or Edge' } : { computer: 'Mac', apps: 'Mac', shell: 'zsh', keyEx: 'cmd+t', browsers: 'Safari, Chrome, Firefox, Arc or Edge' });

  // ---- model presets (Settings > Model) --------------------------------------------------------------
  // gatewayUrl includes /v1 (the app appends /chat/completions). llama-server ignores the model name, so all three are "default".
  const PRESETS = [
    { id: 'premonition', label: 'Premonition gateway', gatewayUrl: 'http://127.0.0.1:8090/v1', modelAuto: 'qwen36-auto', modelMain: 'qwen36', modelFast: 'qwen36-fast', model: 'qwen36-auto', compactTokens: 24000, contextTokens: 12000, maxToolChars: 8000 },
    { id: 'llamacpp', label: 'llama.cpp server', gatewayUrl: 'http://127.0.0.1:8080/v1', modelAuto: 'default', modelMain: 'default', modelFast: 'default', model: 'default', compactTokens: 12000, contextTokens: 24000, maxToolChars: 6000 },
    // The model the app runs itself (Windows, and Macs without Ben's assistant): LFM3 1.7B through llama-server behind the built-in gateway. ctx 8192, of which the
    // system prompt + tools take ~2k tokens, so history is compacted early and tool results are kept short.
    { id: 'builtin', label: 'Built-in (LFM3)', gatewayUrl: 'http://127.0.0.1:18091/v1', modelAuto: 'auto', modelMain: 'main', modelFast: 'fast', model: 'auto', compactTokens: 4500, contextTokens: 4500, maxToolChars: 3000, builtin: true }
  ];
  const presetsFor = (p, o) => PRESETS.filter((x) => !x.builtin || builtinOn(p, o));
  const defaultPreset = (p, o) => (builtinOn(p, o) ? PRESETS.find((x) => x.id === 'builtin') : PRESETS[0]);
  // sleep window default: never before 11 pm, until 8 am, on every platform (the app then fits it to Ben's routine, src/rhythm.js)
  const defaultSleepWindow = (p) => ['23:00', '08:00'];
  const presetFor = (gatewayUrl) => { const u = String(gatewayUrl || '').replace(/\/+$/, ''); return PRESETS.find((x) => x.gatewayUrl === u) || null; };

  const api = { isWin, isMac, helperFileName, helperCommand, helperCandidates, mapKeys, defaultHotkey, hotkeyLabel, modifierHint, features, builtinOn, settingsGating, needsPermsStep, pillOptions, pillPosition, closeBehavior, quitHint, loginItemOptions, startedHidden, windowOptions, osWords, PRESETS, presetsFor, defaultPreset, defaultSleepWindow, presetFor, PERMS_NOTE_WIN };
  root.Platform = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
