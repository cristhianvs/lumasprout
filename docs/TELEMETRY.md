# Optional remote telemetry / Telemetría remota opcional

Version 0.3.0 adds a transport client without requiring a backend to play. It is **off by default**, and simulation mode never sends events. The hosted demo starts in simulation mode.

The normal save remains `isla-luma-v1`; simulation uses `isla-luma-simulation-v1`. `CONFIG.version` remains unchanged. Events and the last acknowledged cursor share the existing save; no participant history is uploaded to GitHub.

`?telemetria=1` enables the configured transport. Production URL overrides accept only the serving origin or explicit code-defined authorized origins. Local development allows another HTTP(S) origin for testing; use only synthetic records and a trusted development backend.

The client retries with backoff, bounds requests with a timeout, measures UTF-8 batch bytes and advances its cursor from valid server acknowledgements. The server contract is:

| Request | Purpose | Acknowledgement |
| --- | --- | --- |
| `POST /api/luma/sesion` | Open/resume a run | `token`, `ultimoIndice`, optionally `ultimoEventoId` |
| `POST /api/luma/eventos` | Submit `{runId, eventos}` with player token | `ultimoIndice`, optionally `ultimoEventoId` |

Page-hide delivery is best effort; it does not advance the cursor because no server acknowledgement is read. The next visit can retry. Deduplication and immutable-event validation are server responsibilities.

Limitations: the queue is the full local history, not an independently bounded journal. Multiple tabs can still compete for the save. Identity checking is strongest when the server returns `ultimoEventoId`; older acknowledgements are accepted for compatibility. A byte limit and passing unit tests do not certify reliability on every browser/network. Review storage quotas, concurrency, credential handling, body-read timeouts and retention before real participants.

The family view describes whether transport is enabled. The questionnaire captures expressed experience; events record behavior. Neither is an infallible measurement of feelings. A `runId` is a saved-game identifier, not a verified child identity.

The dashboard/API source is preserved under [integrations/abejorro](../integrations/abejorro/README.md). Its source availability is separate from production deployment and from the browser-local simulation lab at `admin.html`.
