'use strict';
// What Ben can use Glims for (onboarding step 2) and the Glim each use can start (step 3).
// Pure data + helpers, loaded by the renderer (window.Uses) and by main.js / the unit tests (require).
// Nothing here ever goes into SYSTEM_PROMPT or the tool definitions (the prompt cache must stay byte-constant);
// the picks only reach the model as one line of per-request user context, next to the date (see usesLine).
(function (root) {
  const SAFE = ' Monitoring only: look and report. Never send, reply, post, buy, pay, delete, move or change anything without asking Ben first. If a page needs a sign-in, say so in your report instead of trying to get in.';

  // tpl = the Glim that "Set up recurring Glims" can create now (same fields agent_start takes: name, task, every | at).
  // null = a one-off kind of job, nothing to schedule.
  const USES = [
    { id: 'email', title: 'Email monitoring', example: 'Tell me when something important lands.', chip: 'Check my email',
      tpl: { name: 'Email watch', what: 'Tells you about important mail', every: '30m', label: 'every 30 min',
        task: 'Open my webmail in the browser and look at the newest messages in the inbox since your last report. List only the important ones (real people, deadlines, bills, security alerts, travel), one line each with sender and subject. If nothing important arrived, say "Nothing important."' + SAFE } },
    { id: 'briefing', title: 'Morning briefing', example: 'Weather, calendar and the news, ready at 8.', chip: 'Give me a morning briefing',
      tpl: { name: 'Morning briefing', what: 'Weather, calendar and the top news', at: '08:00', label: 'daily at 08:00',
        task: 'Make my morning briefing: today\'s weather, what is on my calendar today, and the three biggest news headlines. Keep it under 10 short lines.' + SAFE } },
    { id: 'deals', title: 'Price and deal tracking', example: 'Ping me when that thing gets cheaper.', chip: 'Track the price of something for me',
      tpl: { name: 'Deal watch', what: 'Price drops on things you track', every: '6h', label: 'every 6 hours',
        task: 'Check the current price of the items I have asked you to track (search the diary for "track price" if you have it; if you find nothing to track, report "Nothing to track yet. Ask me to track an item." and stop). Report each item with its price now and whether it dropped since the previous report.' + SAFE } },
    { id: 'school', title: 'School and deadline reminders', example: 'What is due soon, so nothing sneaks up on me.', chip: 'What is due this week?',
      tpl: { name: 'Deadline check', what: 'What is due in the next three days', at: '07:30', label: 'daily at 07:30',
        task: 'Find what is due in the next three days: look at my school site or assignments page in the browser (and my calendar if open). List each item with its due date, soonest first. If you cannot get in, say so.' + SAFE } },
    { id: 'research', title: 'Research and summaries', example: 'Dig into a topic and hand me the short version.', chip: 'Research a topic and summarize it', tpl: null },
    { id: 'calendar', title: 'Calendar and planning', example: 'Plan my week around what is already booked.', chip: 'Plan my week', tpl: null },
    { id: 'files', title: 'Tidy files and downloads', example: 'Sort the mess in Downloads, with my OK first.', chip: 'Help me tidy my Downloads folder', tpl: null },
    { id: 'news', title: 'News or topic watch', example: 'Keep an eye on a topic and tell me what is new.', chip: 'Keep an eye on a topic for me',
      tpl: { name: 'Topic watch', what: 'What is new on the topics you follow', at: '12:00', label: 'daily at 12:00',
        task: 'Look for new news on the topics I have asked you to follow (search the diary for "follow" or "watch" if you have it; if there are none, report "No topics yet. Tell me what to watch." and stop). Report only what is new since your previous report, one line each with the source.' + SAFE } }
  ];
  const IDS = USES.map((u) => u.id);
  const DEFAULT_CHIPS = ['Check my email', 'Plan my week', 'Find cheap flights to Boston next month', 'Every morning, brief me on the weather'];

  const byId = (id) => USES.find((u) => u.id === id) || null;
  // The Glim for a use id, as {name, task, every?, at?, label}; null when that use has nothing to schedule.
  const templateFor = (id) => { const u = byId(id); return u && u.tpl ? { ...u.tpl } : null; };
  // Keep only known ids, once each, in menu order.
  const cleanUses = (v) => (Array.isArray(v) ? IDS.filter((id) => v.includes(id)) : []);
  // Welcome-screen chips: the picks first (up to 4), then the defaults to fill the row.
  function chipsFor(uses) {
    const out = cleanUses(uses).map((id) => byId(id).chip);
    for (const d of DEFAULT_CHIPS) if (out.length < 4 && !out.includes(d)) out.push(d);
    return out.slice(0, 4);
  }
  // One line of per-request user context ("" when nothing was picked). Goes beside the date, never in the system prompt.
  function usesLine(uses, other) {
    const names = cleanUses(uses).map((id) => byId(id).title.toLowerCase());
    const o = String(other || '').replace(/\s+/g, ' ').trim().slice(0, 200);
    if (o) names.push(o);
    return names.length ? '[Ben wants Glims for: ' + names.join(', ') + ']' : '';
  }

  const api = { USES, IDS, DEFAULT_CHIPS, templateFor, cleanUses, chipsFor, usesLine };
  root.Uses = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
