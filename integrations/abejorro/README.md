# Luma dashboard and telemetry integration

This directory preserves the Luma-specific source developed for the Abejorro host application. It is an **integration source snapshot, not a standalone server or an automatically deployed application**. The game in the repository root remains runnable without this integration.

## Included

- `web/app/admin/components/`: overview, sessions, participant history, game diagnostics, accessible chart details and connection-error presentation.
- `web/lib/`: Luma labels, formatters and the extracted Luma-only API contract (`lumaApi.ts`).
- `web/hooks/`: session polling logic.
- `api/`: Luma SQLAlchemy models, Alembic migration, schemas, ingestion/admin routes, aggregation services and their host-oriented tests.
- `SOURCE_MANIFEST.json`: source commits and file provenance. Working-tree design/error improvements are included.

The public preview uses invented data. Nothing here contains participant exports, database dumps, administrative credentials or the corporate application.

## Integrating with a host

The source targets Next.js 14 / React 18 / TypeScript with Tailwind and CSS modules, and FastAPI / SQLAlchemy / PostgreSQL / Alembic. It uses host interfaces deliberately; copying this directory alone is insufficient.

For the frontend, provide:

1. `lib/hostAdminRequest.ts` exporting the host's authenticated `adminRequest<T>`; validate authorization in the backend as well. No login bypass or embedded credentials.
2. The existing host `lib/http-client.ts` (`ApiResponse`, `API_BASE_URL`), `components/ui/Button`, `hooks/useVisiblePolling`, `lib/protocolo42Format`, and `Protocolo42BarChart` used by the remaining historical/diagnostic widgets. Those shared host components are not copied or modified by this snapshot. The redesigned overview charts use Luma-specific CSS modules.
3. The `@/` source alias and the host Tailwind theme. Mount `LumaPanel` inside the authenticated administrator. Configure the API base at build time. A running frontend does not imply a running API.

For the backend, connect `database.get_db`, the host declarative Base, admin verification, secret/configuration handling, limiter and application/router registration. Inspect imports and existing migration history before integrating: migration `004` follows the host's `003`; do not run it blindly against an unrelated database. The included tests depend on the host's app and fixtures. Run them there with an isolated test database.

The game opens `/api/luma/sesion` and submits batches to `/api/luma/eventos`. Admin endpoints live under `/api/admin/luma/`. Keep the existing admin login and second factor; a player credential must never authorize administrative reads.

## Data interpretation and current limits

- **Overview** aggregates participants and sessions; it is not one child's assessment.
- **Participant** follows a saved `runId`. A saved game is not verified personal identity across devices or shared browsers.
- Missing observations stay distinct from measured zero. Frequency of a modality does not establish its educational effectiveness.
- Behavioral indicators are not clinical measurements of feelings or anxiety.
- Telemetry ingestion/authentication, retention, concurrency and load require host-level review before a child pilot. A token derived from a supplied run ID does not establish participant identity.
- The root client supports an optional `ultimoEventoId` acknowledgement for compatibility with older servers. Missing identity acknowledgements reduce conflict detection; this is not a complete multi-writer reconciliation protocol.
- Existing test results of the host are not a CI certification of this extracted snapshot. The root CI validates the standalone game; deployment and API integration remain separate checks.

## Publication and deployment

Publishing this source to LumaSprout **does not deploy Abejorro or modify Protocolo42**. The public Pages workflow builds the root demo only. An operator must explicitly integrate and validate a versioned game artifact and these modules in the host repository.

Before any host release: preserve unrelated assets and storage keys, restore a database backup in isolation, exercise saved-game compatibility, use additive migrations and pin recoverable images. Do not restore an entire old database as an automatic code rollback: that would discard subsequent progress.

## Contributing

Use focused changes and keep calculations separate from presentation. Test charts with 30 dates, zero-only data, missing data, keyboard focus and narrow viewports. Error screens must distinguish failed requests from empty successful results and label retained data as stale. Document host adapters whenever a new dependency is introduced.
