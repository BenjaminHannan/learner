'use strict';
// Read-only identity/permission probe. This never creates a tap or posts input.
const { NativeSession } = require('./native');
NativeSession.start({ preflight:true }).then(session => {
  process.stdout.write(JSON.stringify(session.status) + '\n');
}).catch(error => { console.error(error.message); process.exitCode = 1; });
