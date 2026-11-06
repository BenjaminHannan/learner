'use strict';
const fs = require('node:fs');
const path = require('node:path');
const [mark, raw, expression] = process.argv.slice(2);
try {
  const value = JSON.parse(raw);
  if (Function('value', '"use strict"; return (' + expression + ');')(value) !== true) throw Error('mark did not pass');
  fs.appendFileSync(path.join(__dirname, 'marks.jsonl'), JSON.stringify({ mark, pass: true, at: new Date().toISOString() }) + '\n');
  console.log('PASS: ' + mark);
} catch (error) { console.error('FAIL: ' + mark + ': ' + error.message); process.exitCode = 1; }
