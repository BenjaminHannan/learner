'use strict';
// Ben Oct 28: "make it proactive". Once a day, when Ben opens the chat, Glim checks on what he left open. Pure decision, no Electron.
const FOLLOWUP_ASK = '[Daily follow-up: check "Keeping track of" and the last chats. If something Ben left open is due soon, blocked or waiting on him, follow up in one or two short sentences and end with 2-4 choices (lines starting with "→ "). If nothing needs him, reply exactly NO_UPDATE.]';
const dayKey = (d) => { const p = (n) => String(n).padStart(2, '0'); return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()); };
// now: Date; lastDay: 'YYYY-MM-DD' of the last follow-up; hour: 0-23 local; lastActivity: ms of the latest main thread (0/undefined = no thread)
function shouldFollowUp({ now, lastDay, hour, front, busy, asleep, lastActivity, enabled }) {
  if (enabled === false || !front || busy || asleep || !lastActivity) return false;
  if (!(hour >= 7 && hour < 22)) return false;
  const d = now instanceof Date ? now : new Date(now);
  const today = dayKey(d);
  if (lastDay === today) return false;
  return dayKey(new Date(lastActivity)) < today;
}
module.exports = { shouldFollowUp, FOLLOWUP_ASK, dayKey };
