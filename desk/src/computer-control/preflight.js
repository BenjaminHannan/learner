'use strict';
// Read-only identity/permission probe. This never creates a tap or posts input.
const { NativeSession } = require('./native');
const { report } = require('./test-status');
NativeSession.start({ preflight:true }).then(session => {
  report({ status:'complete', permissions:session.status });
  process.stdout.write(JSON.stringify(session.status) + '\n');
}).catch(error => { report({ status:'error', error:error.message }); console.error(error.message); process.exitCode = 1; });
