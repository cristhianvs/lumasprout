"""One-time preparation of the curated public evidence snapshot and portable links."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
for name in ['admin.js','admin.html']:
    p=ROOT/name;s=p.read_text(encoding='utf8')
    s=s.replace("src='/?simulation=1'","src='./?simulation=1'").replace('href="/"','href="./"')
    p.write_text(s,encoding='utf8')
source=ROOT/'output/pedagogy-matrix/summary.json'
if source.exists():
    s=json.loads(source.read_text(encoding='utf8'))
    out=ROOT/'docs/evidence/validation-summary.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'snapshot':'2026-09-17','scope':s['scope'],'totals':s['totals'],'assertions':s['assertions'],'regressions':s['regressions'],'journeys':[{'profile':r['profile'],'behavior':r['behavior'],'status':r['status'],'mastered':r['mastered'],'attempts':r['attempts']} for r in s['results']],'rawTelemetryPublished':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
