# Evidence, without inflated claims

## Subsequent local quality correction: 17 September 2026

The corrected source passed **75 regression tests** (44 Node, 14 general browser, seven modality, five pedagogy and five laboratory), plus **36 Playwright journeys**. The new matrix contains 15,530 events and 856 mathematical attempts; 32 independent completions and four help-only breaks. Lint, formatting and the public build also passed locally. [Current aggregate](evidence/quality-validation-summary.json) and [corrections and limits](CORRECCIONES_CALIDAD.md) are separate from the original published snapshot below. No new deployment or remote CI run is claimed.

## Original published technical snapshot: 17 September 2026

| Check | Result |
|---|---|
| Complete Playwright journeys | 36 passed: 4 modalities × 9 behaviors |
| Independent completion | 32 journeys covered 6 skills × 4 pedagogical stages |
| Help-only behavior | 4 journeys ended with a break and zero independent evidence |
| Telemetry generated | 15,467 events; 856 mathematical attempts |
| Assertions within the journeys | 12,764; these are not participants |
| Additional checks | 38 Node + 14 browser + 7 modality + 3 pedagogy + 5 laboratory |

Scenarios: independent progress, error/recovery, slow reading, interruptions, persistent help, unavailable audio, mixed preferences, family disagreement and explicit choice. They begin with empty isolated browser contexts, drive the actual UI and read telemetry for verification. The matrix uses virtual active time. The general suite also includes a complete real-clock journey.

One new mobile dashboard overflow was found and corrected; its failing check was rerun successfully. [Machine-readable aggregate](evidence/validation-summary.json) records the snapshot without publishing raw telemetry.

## Reproduce

Use Node.js 22+, Python 3.11+, Google Chrome and `requirements-dev.txt`. Start `npm start` in another terminal.

```sh
npm test
npm run test:browser
npm run test:profiles
npm run test:pedagogy
npm run test:lab
python tests/behavior_matrix.py --profile estructurado --output output/pedagogy-matrix
python tests/behavior_matrix.py --profile visual --output output/pedagogy-matrix
python tests/behavior_matrix.py --profile auditivo --output output/pedagogy-matrix
python tests/behavior_matrix.py --profile explorador --output output/pedagogy-matrix
```

The matrix writes telemetry, exports, assertions, screenshots and traces under ignored `output/` folders. This repository distributes tests and aggregate results; generated raw records are not part of the public source bundle. Report-building helpers require their generated input artifacts and extra PDF tooling; they are not application dependencies.

## What this does not establish

- That real children understand the instructions or improve learning outcomes.
- That presentation preferences are stable learner types or improve learning when matched.
- That inactivity, latency or errors diagnose anxiety or engagement.
- That internal knowledge probabilities are empirically calibrated.
- That nearby contextual problems demonstrate broad transfer or retention.

The research comparison and pre-pilot complement documents are historical technical notes. The source research PDF and local working records are not redistributed. A reviewed human study is still required. See [roadmap](ROADMAP.md) and [pilot draft](PROTOCOLO_OBSERVACION.md).
