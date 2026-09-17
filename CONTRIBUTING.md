# Build the next discovery

Thanks for considering a contribution to LumaSprout. Spanish and English are welcome. Start with a small, reviewable improvement; you do not need to rebuild the whole learning engine.

## Run the workshop

1. Fork and clone the repository. Use Node.js 22+.
2. Run `npm start` and open http://127.0.0.1:4173.
3. Run `npm ci --ignore-scripts`, then `npm run check`. Tooling dependencies are development-only; the application has no runtime dependencies.
4. For browser work, install Python 3.11+, Google Chrome and `python -m pip install -r requirements-dev.txt`.
5. Read [architecture](docs/ARCHITECTURE.md), [current status](docs/PROJECT_STATUS.md) and [starter tasks](docs/ROADMAP.md#starter-tasks).

## Pick a useful slice

Open an issue explaining the problem, the learner/developer impact and the smallest change that addresses it. Include acceptance criteria. Check existing issues before starting overlapping work. An issue discussion is helpful for larger changes; a focused typo or accessibility fix can go straight to a PR.

## Keep these contracts

- Preserve saved games. Do not bump `CONFIG.version` as a routine release action: current loading treats a mismatch as a new save. Prefer additive migration and tests.
- Keep mathematical knowledge separate from interaction preferences. Automatic support must not become a voluntary preference signal.
- Do not certify independent mastery from help, retries or non-math gameplay.
- Telemetry must explain a decision and its response, while distinguishing synthetic events, self-report and direct observation.
- Preserve keyboard access, optional sound and explicit learner choices. Avoid timed answers and public rankings.
- Never publish real participant exports, identifying information, secrets or browser profiles. Use synthetic fixtures. Do not introduce an external telemetry endpoint without a separate design discussion.

## Verify the change

Run `npm run check` and the browser suite relevant to the affected behavior. If changing pedagogy, run `npm run test:pedagogy`; for mode interactions, `npm run test:profiles`; for the dashboard, `npm run test:lab`. A server must be running in another terminal. Tests create isolated browser contexts. `npm run format` applies formatting. Keep prototype policy parameters in `engine.js` / `POLICY`, and keep telemetry payloads independent of mutable state.

For dated evidence usable by reports, run `python -X utf8 scripts/validate.py <suite>` with `node`, `browser`, `profiles`, `pedagogy` or `laboratory`. Reports reject missing or stale evidence. Configure `LUMA_BASE_URL` and `LUMA_BROWSER_CHANNEL` for another browser environment. See [quality corrections and remaining limits](docs/CORRECCIONES_CALIDAD.md).

For the public presentation: `npm run build:site`, then serve `dist/` locally with `python -m http.server 4180 --directory dist --bind 127.0.0.1`. Check both a narrow viewport and desktop. Keep paths relative so the game works beneath `/lumasprout/play/` on Pages. Application tests and landing-page checks are different evidence.

## Send a pull request

Describe the concrete before/after behavior, how it was tested and remaining limitations. Attach synthetic screenshots only where useful. Update the relevant public docs when behavior changes. Changes to learning claims need supporting evidence, not only passing tests.

Original contributions are accepted under the repository’s MIT license. Only contribute material you have the right to contribute. Research references and third-party assets retain their own terms.

## Versioning and releases

Use semantic versions in `package.json`, annotated Git tags (`vX.Y.Z`) and GitHub Releases. Update [CHANGELOG.md](CHANGELOG.md) with reasons, compatibility, executed validation and remaining limits. Keep the product release version separate from the saved-game format guard `CONFIG.version`.
