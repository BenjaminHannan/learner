'use strict';
// agent_start / agent_list / agent_update / agent_stop. Helpers get the same tool list as the primary (shared prompt cache) and the
// same abilities: a Glim may start, list, change and stop other Glims (the Glim count cap and the duplicate check still apply).
const { fmtWhen, short } = require('../helpers');

const NO = "Error: Glims can't start Glims"; // kept for old callers; helpers can now start Glims

function agentTools(mgr, opts) {
  const err = (e) => ({ text: 'Error: ' + (e && e.message || e), error: true });
  const stopTool = (a) => {
    const h = mgr.stop(a.name_or_id);
    return h ? { text: "Stopped Glim '" + h.name + "' and removed its schedule.", summary: 'Stopped Glim ' + h.name } : { text: "Error: no Glim '" + a.name_or_id + "'", error: true };
  };
  return {
    agent_start: (a, ctx) => {
      try {
        const h = mgr.add({ name: a.name, task: a.task, every: a.every, at: a.at, parent: ctx && ctx.thread && ctx.thread.id });
        const when = h.schedule === 'once' ? 'running now (one time)' : h.schedule.startsWith('daily') ? h.schedule + ', next run ' + fmtWhen(h.next) : 'running now, then ' + h.schedule + ', next run ' + fmtWhen(h.next);
        return { text: "Started Glim '" + h.name + "' (id " + h.id + '): ' + when + '. Its report will arrive as a [helper updates] note.', summary: 'Started Glim ' + h.name };
      } catch (e) { return err(e); }
    },
    agent_list: () => {
      const l = mgr.list();
      if (!l.length) return 'No Glims.';
      return l.map((h) => h.id + ' ' + h.name + ' | ' + h.status + (h.paused ? ' (paused)' : '') + ' | ' + h.schedule + ' | next ' + fmtWhen(h.next) + ' | last: ' + (short(h.lastSummary, 120) || 'none yet')).join('\n');
    },
    agent_update: (a) => {
      try {
        if (a.stop) return stopTool(a);
        const patch = {};
        for (const k of ['task', 'every', 'at']) if (a[k] !== undefined && a[k] !== null) patch[k] = a[k];
        if (a.new_name !== undefined && a.new_name !== null) patch.name = a.new_name;
        const h = mgr.update(a.name_or_id, patch);
        if (!h) return { text: "Error: no Glim '" + a.name_or_id + "'", error: true };
        if (a.paused !== undefined) mgr.pause(h.id, !!a.paused);
        const v = mgr.find(h.id) ? mgr.view(mgr.find(h.id)) : h;
        return { text: "Updated Glim '" + v.name + "': " + v.schedule + (v.paused ? ' (paused)' : '') + (v.next ? ', next run ' + fmtWhen(v.next) : ''), summary: 'Updated Glim ' + v.name };
      } catch (e) { return err(e); }
    },
    agent_stop: stopTool // still callable by name (older chats); the tool list offers it through agent_update
  };
}

module.exports = { agentTools, NO };
