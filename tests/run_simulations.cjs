const fs = require('node:fs');
const path = require('node:path');
const S = require('../simulation');
const dir = path.join(__dirname, '../output/simulations');
fs.mkdirSync(dir, { recursive: true });
const reports = S.scenarios.map((s) => S.run(s.id));
for (const report of reports)
  fs.writeFileSync(path.join(dir, report.scenario.id + '.json'), JSON.stringify(report, null, 2));
const summary = reports.map((r) => ({
  scenario: r.scenario.id,
  checks: r.checks,
  steps: r.timeline.length,
  mastered: r.timeline.at(-1).mastered,
}));
fs.writeFileSync(path.join(dir, 'summary.json'), JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary, null, 2));
if (reports.some((r) => r.checks.some((c) => !c.pass))) process.exitCode = 1;
