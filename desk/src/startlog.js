'use strict';
// Reading what serve.sh leaves behind: its "not starting" refusal line (--autostart) and the watchdog's WATCHDOG_STOPPED marker.

// "2026-10-27 23:25:19 autostart: not starting (only about 14 GB of memory is free, need about 20)" -> a refusal Ben can act on.
// Returns null when the log has no such line.
function parseRefusal(log) {
  // only the --autostart refusal; "another serve.sh is already running; not starting a second one." means a start is already in progress
  const line = String(log || '').split('\n').reverse().find((l) => /autostart: not starting \(/i.test(l));
  if (!line) return null;
  const m = line.match(/about\s+(\d+(?:\.\d+)?)\s*GB[^,)]*free[^,)]*,\s*need\s+about\s+(\d+(?:\.\d+)?)/i);
  if (m) return { reason: 'memory', error: 'Not enough free memory to start the assistant right now (about ' + m[1] + ' GB free, it needs about ' + m[2] + '). Close some apps and try again.' };
  const why = (line.match(/not starting\s*\(([^)]*)\)/i) || [])[1];
  return { reason: /memory|\bRAM\b|swap|pressure/i.test(why || '') ? 'memory' : 'other', error: 'The assistant was not started to keep your Mac safe' + (why ? ' (' + why.trim() + ')' : '') + '. Close some apps, or wait for other work to finish, and try again.' };
}

// "2026-10-27 22:25:45 stopped by watchdog: pressure 2, swap 3396 MB" -> { at: '22:25', text: <the line> }
function parseWatchdog(content) {
  const text = String(content || '').trim().split('\n')[0].trim();
  const m = text.match(/\b(\d{1,2}:\d{2})(?::\d{2})?\b/);
  return { at: m ? m[1].padStart(5, '0') : '', text };
}

module.exports = { parseRefusal, parseWatchdog };
