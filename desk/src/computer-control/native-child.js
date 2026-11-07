'use strict';
// Runs in a separate Premonition process. If chat dies, its socket closes and
// the native guard releases held inputs before this child exits.
const [library, bridge, socket, mode] = process.argv.slice(2);
if (![library, bridge, socket].every(v => typeof v === 'string' && require('node:path').isAbsolute(v))) process.exit(2);
require(bridge).start(library, socket, mode === 'preflight', () => process.exit(0));
