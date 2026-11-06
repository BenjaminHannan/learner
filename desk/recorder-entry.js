'use strict';
// Choose the recorder role before loading chat, model startup, or its singleton.
if (process.argv.includes('--glim-recorder-native')) {
  const path = require('node:path');
  try {
    if (process.argv.includes('--capture')) {
      const fs = require('node:fs'), os = require('node:os');
      const approval = path.join(os.homedir(), 'learner-ops/hands-recorder/LEAD-RELEASE.json');
      if (JSON.parse(fs.readFileSync(approval)).approved !== true) throw Error('Ben recording is OFF');
    }
    require(path.join(process.resourcesPath, 'glim-recorder/native-bridge.node'))
      .run(process.argv.includes('--glim-canary') ? 'canary' : 'capture');
  } catch (error) { console.error(error.stack); process.exit(1); }
} else if (process.argv.includes('--glim-recorder-host')) {
  require('./src/hands-toy/premonition-host').run();
} else {
  require('./main');
}
