'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

// The real Mac takeover and task marks must pass before this path is enabled
// for ordinary chat. A separate test process may opt in explicitly.
function enabled() {
  if (process.env.GLIM_HANDS_TEST === '1') return true;
  try {
    const file = path.join(os.homedir(), 'learner-ops', 'hands-attempts', 'CONTROL-ENABLED.json');
    const row = JSON.parse(fs.readFileSync(file, 'utf8'));
    return row.schema === 'hands-control/v1' && row.enabled === true;
  } catch (_) { return false; }
}
module.exports = { enabled };
