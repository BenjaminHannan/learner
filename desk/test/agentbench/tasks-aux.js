'use strict';
// AGENT1 aux bench (MARKS-agent-aux-v1.md): the two live prompts from the lead's M1 UX test 2026-11-04 (build 166fed5b4) where Glim said
// what it would do, then wrote only blank lines and stopped with no tool call. Kept apart from the registered 20 tasks (tasks.js).
// Fake screen and Motes stand in for the Mac; a pass = the right tool was called (and, for the reminder, the right one cancelled).
const SCREEN = 'Front app: Safari. Windows: Safari - "Khan Academy: Titration practice"; Notes - "Chem lab notes"; Spotify - "Lo-fi beats". ' +
  'Screen text (front window): Titration practice. Question 3 of 10: 25.0 mL of 0.100 M HCl is titrated with 0.125 M NaOH. What volume of NaOH reaches the equivalence point?';
const MOTES = 'Motes:\n- "Gym clothes reminder" (id h5jq2b8w): every weekday at 7:00 AM, says "Pack your gym clothes". Running.\n- "Chem study nudge" (id k2m9c4xz): Sundays at 4:00 PM. Running.';
const GYM = /h5jq2b8w|gym/i;
const T = [
  { id: 'aux_screen', kind: 'stopped',
    text: 'what am I looking at on my screen right now?',
    tools: (s, tr) => ({ screen_look: () => { tr.screenLooks = (tr.screenLooks || 0) + 1; return SCREEN; } }),
    score: (s, a, tr) => (tr.screenLooks || 0) > 0 && /titration|khan/i.test(a) },
  { id: 'aux_cancel', kind: 'stopped',
    preseed: [['remind me every weekday at 7 to pack my gym clothes', 'Done: a Mote called "Gym clothes reminder" will tell you at 7:00 AM every weekday.']],
    text: 'cancel that gym clothes reminder please',
    tools: (s, tr) => ({ agent_list: () => MOTES,
      agent_update: (x) => { (tr.updates = tr.updates || []).push(x); return GYM.test(String(x.name_or_id)) ? (x.stop ? 'Stopped "Gym clothes reminder".' : 'Updated "Gym clothes reminder".') : 'No Mote called ' + x.name_or_id + '.'; } }),
    score: (s, a, tr) => (tr.updates || []).some((x) => GYM.test(String(x.name_or_id)) && (x.stop === true || x.paused === true)) && !(tr.updates || []).some((x) => /k2m9c4xz|chem/i.test(String(x.name_or_id))) }
];
module.exports = { TASKS: T };
