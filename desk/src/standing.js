'use strict';
// Ben Oct 28: "get stronger at ideas for my model, plan my week with ECs, gym and health stuff with supplements, and make sure everything is organized",
// without him setting anything up. Three standing Motes, added once on the first start after the update (marker file), never again, so
// stopping or deleting one sticks. Each saves what it learns as fact cards (topic "card") for sleep.
const fs = require('fs');
const path = require('path');

const CARDS = ' Save every concrete fact you learn with memory_save, topic "card", written "Subject => relation => Object". Never ask Ben questions: use his saved notes, goals and chats. Work quietly: do not report tips or status; reply exactly NO_UPDATE unless Ben must act.';
const STANDING = [
  { name: 'Model ideas', every: '2h', task: 'Learn by practice: come up with concrete ideas to make Ben\'s Premonition model better at reasoning and at the tasks he gives you: read his recent chats and the saved notes, find where you were slow or wrong, and save each idea as a note with why it should help and how to test it, and try it on a practice task. Dig into something new each run and do not repeat an idea you already saved.' + CARDS },
  { name: 'Week planner', at: '18:00', task: 'Plan Ben\'s week around his extracurriculars, gym days, sleep, meals, health and supplements, using his saved notes, goals and calendar. On Sundays write the whole week; on other days adjust the plan and say what changed. Put the plan in his goals.' + CARDS },
  { name: 'Organizer', at: '06:00', task: 'Check Ben\'s mail, calendar and goals. Save what matters today and what is overdue as notes and goals. Read only; do not send or delete anything.' + CARDS },
];

function seedStanding(helpers, dir) {
  const marker = path.join(dir, 'standing-motes.json');
  try {
    if (fs.existsSync(marker)) {
      const state = JSON.parse(fs.readFileSync(marker, 'utf8'));
      if (!state.organizerSixMigration) {
        const h = helpers.find('Organizer');
        if (Array.isArray(state.added) && state.added.includes('Organizer') && h && h.status !== 'stopped' && h.at === '08:00' && !h.every) helpers.update(h.id, { at: '06:00' });
        state.organizerSixMigration = true;
        fs.writeFileSync(marker, JSON.stringify(state));
      }
      return [];
    }
  } catch (e) { return []; }
  const added = [];
  for (const m of STANDING) {
    try { helpers.add({ name: m.name, task: m.task, every: m.every, at: m.at, deferFirst: true }); added.push(m.name); } catch (e) { /* exists or limit: leave it */ }
  }
  try { fs.mkdirSync(dir, { recursive: true }); fs.writeFileSync(marker, JSON.stringify({ at: new Date().toISOString(), added, organizerSixMigration: true })); } catch (e) { /* retried next start; add() refuses duplicates */ }
  return added;
}

module.exports = { seedStanding, STANDING };
