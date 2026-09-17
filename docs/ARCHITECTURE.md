# Architecture

LumaSprout is the public project identity. **Isla Luma** is the learner-facing world. Branding changes do not rename storage keys or reset existing progress.

## Runtime

- `engine.js`: pure mathematical and adaptation functions, exported to both Node tests and the browser.
- `app.js`: state machine, UI, clocks, local saves and telemetry events.
- `simulation.js`: deterministic synthetic histories for laboratory scenarios.
- `admin.js`: read-only live-local/import views, synthetic scenario controls and linked outcomes. This is not a central multi-user service.
- `server.cjs`: loopback-only development server with an explicit runtime-file allowlist.

The runtime has no third-party JavaScript dependencies and does not call an LLM. Adaptation is a readable heuristic/Bayesian model by skill, not a validated clinical or learning-style classifier.

## Persistence and events

`isla-luma-v1` stores the ordinary game; `isla-luma-simulation-v1` stores the explicitly marked simulation game. Both are browser-local. JSON export is initiated by the user. Current events use schema 1.3 and policy cpa-1; old events remain readable.

`CONFIG.version` is a save-format guard, not a release number. Do not change it without designing a migration. Existing completed knowledge is preserved as legacy coverage; missing CPA evidence is not invented.

## Public site

`site/` contains the developer-facing landing page. `scripts/build-site.cjs` assembles only the landing page, original media and nine runtime files under `dist/play/`. It never publishes working telemetry, local context or source research PDFs. GitHub Actions deploys that curated artifact to Pages.

The public game is Spanish. The English landing/README are for international contributors; an English game is a proposed contribution, not an implemented feature.

## Testing boundaries

Node tests check engine contracts and state-machine behavior. Playwright controls Chrome in isolated contexts and inspects exported telemetry. The full matrix has 4 modalities × 9 scripted behaviors; it does not model real child behavior scientifically. See [EVIDENCE](EVIDENCE.md).
