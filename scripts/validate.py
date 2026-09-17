"""Run a suite and record dated, source-bound evidence for report consumers."""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITES = {
    'node': ['node', '--test', *map(str, sorted((ROOT / 'tests').glob('*.test.cjs')))],
    **{name: [sys.executable, '-X', 'utf8', str(ROOT / 'tests' / file)] for name, file in {
        'browser': 'browser_test.py', 'profiles': 'profiles_test.py',
        'pedagogy': 'pedagogy_test.py', 'laboratory': 'laboratory_test.py',
    }.items()},
}

def source_hash():
    files = sorted([*ROOT.glob('*.js'), *ROOT.glob('*.html'), *ROOT.glob('*.css'),
                    *(ROOT / 'tests').glob('*.py'), *(ROOT / 'tests').glob('*.cjs')])
    digest = hashlib.sha256()
    for file in files:
        digest.update(str(file.relative_to(ROOT)).encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()

def main():
    suite = sys.argv[1]
    command = SUITES[suite]
    before = source_hash()
    started = datetime.now(timezone.utc).isoformat()
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf8')
    output = run.stdout + run.stderr
    print(output, end='')
    matches = re.search(r'# tests (\d+)' if suite == 'node' else r'Ran (\d+) tests?', output)
    count = int(matches.group(1)) if matches else 0
    valid = run.returncode == 0 and count > 0 and before == source_hash()
    folder = ROOT / 'output' / 'validation'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f'{suite}.log').write_text(output, encoding='utf8')
    (folder / f'{suite}.json').write_text(json.dumps({
        'suite': suite, 'startedAt': started, 'finishedAt': datetime.now(timezone.utc).isoformat(),
        'sourceHash': before, 'status': 'passed' if valid else 'failed',
        'tests': count, 'exitCode': run.returncode, 'command': command,
    }, indent=2), encoding='utf8')
    raise SystemExit(0 if valid else 1)

if __name__ == '__main__':
    main()
