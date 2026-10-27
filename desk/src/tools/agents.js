'use strict';
// agent_start / agent_list / agent_stop. Helpers get the same tool list as the primary (shared prompt cache),
// so for them these just refuse.
const { fmtWhen, short } = require('../helpers');

const NO = "Error: helpers can't start helpers";

function agentTools(mgr, opts) {
  if (opts && opts.isHelper) {
    const no = () => ({ text: NO, error: true });
    return { agent_start: no, agent_list: no, agent_stop: no };
  }
  const err = (e) => ({ text: 'Error: ' + (e && e.message || e), error: true });
  return {
    agent_start: (a, ctx) => {
      try {
        const h = mgr.add({ name: a.name, task: a.task, every: a.every, at: a.at, parent: ctx && ctx.thread && ctx.thread.id });
        const when = h.schedule === 'once' ? 'running now (one time)' : h.schedule.startsWith('daily') ? h.schedule + ', next run ' + fmtWhen(h.next) : 'running now, then ' + h.schedule + ', next run ' + fmtWhen(h.next);
        return { text: "Started helper '" + h.name + "' (id " + h.id + '): ' + when + '. Its report will arrive as a [helper updates] note.', summary: 'Started helper ' + h.name };
      } catch (e) { return err(e); }
    },
    agent_list: () => {
      const l = mgr.list();
      if (!l.length) return 'No helpers.';
      return l.map((h) => h.id + ' ' + h.name + ' | ' + h.status + (h.paused ? ' (paused)' : '') + ' | ' + h.schedule + ' | next ' + fmtWhen(h.next) + ' | last: ' + (short(h.lastSummary, 120) || 'none yet')).join('\n');
    },
    agent_stop: (a) => {
      const h = mgr.stop(a.name_or_id);
      return h ? { text: "Stopped helper '" + h.name + "' and removed its schedule.", summary: 'Stopped helper ' + h.name } : { text: "Error: no helper '" + a.name_or_id + "'", error: true };
    }
  };
}

module.exports = { agentTools, NO };
