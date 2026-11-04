'use strict';
// AGENT1 bench report: node report.js DIR [DIR ...] (one dir per run of a version) -> per-task pass counts + means (markdown)
const fs = require('fs'), path = require('path');
const dirs = process.argv.slice(2);
const rows = [];
for (const d of dirs) { const f = path.join(d, 'summary.jsonl'); if (fs.existsSync(f)) for (const l of fs.readFileSync(f, 'utf8').split('\n')) if (l.trim()) rows.push({ ...JSON.parse(l), dir: d }); }
const tasks = [...new Set(rows.map((r) => r.task))];
const mean = (a) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
const f1 = (x) => (Math.round(x * 10) / 10).toString();
console.log('| task | pass | secs | model calls | replans | leaks | repeats | max req tok |');
console.log('|---|---|---|---|---|---|---|---|');
for (const t of tasks) { const R = rows.filter((r) => r.task === t);
  console.log('| ' + t + ' | ' + R.filter((r) => r.ok).length + '/' + R.length + ' | ' + f1(mean(R.map((r) => r.secs))) + ' | ' + f1(mean(R.map((r) => r.modelCalls))) + ' | ' + f1(mean(R.map((r) => r.replans))) + ' | ' + f1(mean(R.map((r) => r.leaks))) + ' | ' + f1(mean(R.map((r) => r.repeats))) + ' | ' + Math.max(...R.map((r) => r.maxReqTokens)) + ' |'); }
const perRun = dirs.map((d) => rows.filter((r) => r.dir === d));
console.log('\nper run (passed of tasks): ' + perRun.map((R) => R.filter((r) => r.ok).length + '/' + R.length).join(', ') + '; mean ' + f1(mean(perRun.map((R) => R.filter((r) => r.ok).length))));
console.log('totals per task-run: secs ' + f1(mean(rows.map((r) => r.secs))) + ', model calls ' + f1(mean(rows.map((r) => r.modelCalls))) + ', replans ' + f1(mean(rows.map((r) => r.replans))) + ', leaks ' + f1(mean(rows.map((r) => r.leaks))) + ', repeats ' + f1(mean(rows.map((r) => r.repeats))) +
  ', timeouts ' + rows.filter((r) => r.timedOut).length + ', requests over 8192 est. tokens ' + rows.reduce((n, r) => n + r.over8192, 0) + ', max req tokens ' + Math.max(0, ...rows.map((r) => r.maxReqTokens)) + ', first-request tools chars ' + Math.max(0, ...rows.map((r) => r.toolChars)) + ', system chars ' + Math.max(0, ...rows.map((r) => r.sysChars)));
