'use strict';
const fs = require('node:fs');
function report(value) {
  const file = process.env.GLIM_HANDS_STATUS;
  if (!file) return;
  fs.writeFileSync(file + '.tmp', JSON.stringify(value), { mode:0o600 });
  fs.renameSync(file + '.tmp', file);
}
module.exports = { report };
