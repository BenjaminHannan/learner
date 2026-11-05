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

// aux v2 (MARKS-agent-aux-v2.md): the same two asks at the end of a long chat (~25k chars of earlier turns, like Ben's main thread
// in the live test) because a short fresh chat did not reproduce the stop (aux v1 control 9/10).
const TOPICS = [
  ['what should I make for dinner with chicken, rice and broccoli?', 'A quick stir-fry works: slice the chicken thin, brown it in a hot pan with a little oil, add broccoli florets and a splash of water, cover for 3 minutes, then stir in soy sauce, garlic and a spoon of honey. Serve over rice. '],
  ['explain how a titration curve works', 'A titration curve plots pH against the volume of titrant added. For a strong acid with a strong base, the pH stays low and flat at first, then jumps sharply near the equivalence point, where moles of base equal moles of acid, and levels off high after. The middle of the steep part is the equivalence point; an indicator that changes colour there shows it. '],
  ['what is the weather tomorrow in Dresden Ohio', 'Tomorrow in Dresden, Ohio: partly cloudy, high near 54°F, low around 38°F, light wind from the west, about a 20% chance of a shower in the afternoon. A light jacket should be enough. '],
  ['give me tips for my college essay intro', 'Open with a specific moment rather than a summary: a scene, a line of dialogue or a concrete detail. Keep the first paragraph short, make the reader curious, and tie the moment to what it shows about you by the end of the essay. Avoid quotes from famous people and lists of achievements. '],
  ['how long should I run to train for a 5K', 'For a first 5K, three runs a week for about 6–8 weeks works for most people: two easy runs of 20–30 minutes and one slightly longer run, adding a few minutes each week. Keep the easy runs at a pace where you can talk. '],
  ['what is a good playlist for studying', 'Instrumental music tends to work best: lo-fi beats, film scores, or calm piano. Songs with lyrics in a language you understand compete with reading. Keep the volume low and use the same playlist each time so it becomes a cue to focus. ']
];
function longChat() {
  const out = [];
  for (let i = 0; i < 12; i++) { const [u, a] = TOPICS[i % TOPICS.length]; out.push([u + (i >= TOPICS.length ? ' (again, quick version)' : ''), (a + ' ').repeat(i >= TOPICS.length ? 5 : 10).trim()]); }
  return out;
}
const LONG = longChat();
T.push(
  { ...T[0], id: 'aux_screen_long', preseed: LONG },
  { ...T[1], id: 'aux_cancel_long', preseed: [...LONG, ...T[1].preseed] }
);
module.exports = { TASKS: T };
