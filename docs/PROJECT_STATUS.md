# Current public status

Snapshot: 18 September 2026. Early prototype; no child participants in the reported tests.

The adventure, fraction workshop, four modalities, local telemetry, synthetic lab, pedagogical stages and independent-response checks are implemented. The original published snapshot reports 36 passing browser journeys plus 67 other checks. See [EVIDENCE](EVIDENCE.md) for that snapshot's scope and reproducibility.

The subsequent local quality correction adds immutable event snapshots, a finite-bank exhaustion outcome, more equivalent-fraction variants, consistent CPA indicators, injected persistence/telemetry adapters and a single persisted attempt state. ESLint, Prettier and browser CI checks enforce conventions. See [quality corrections](CORRECCIONES_CALIDAD.md) for validation commands and remaining architectural limits. These changes do not retroactively repair historical telemetry or validate learning outcomes.

Local validation of that correction passed 75 regression tests and all 36 browser journeys. [Updated aggregate](evidence/quality-validation-summary.json). Version **0.2.0** packages these changes. See the [changelog](../CHANGELOG.md) for reasons, compatibility and version history; the GitHub Release and Actions runs record publication and deployment status.

The marketing site and original GIFs present working software. The standalone game remains browser-local by default. Version 0.3.0 adds optional remote transport and publishes Luma-specific dashboard/API integration source under `integrations/abejorro`; those modules require a host application and are not deployed by the static demo. Production readiness, cross-device identity and a real-child pilot remain unverified. No validated anxiety measure or learning-effectiveness claim is offered.

Before a human pilot: review mathematical content with educators, agree on the observation protocol, review external assessment forms, and design participant data handling. The [protocol draft](PROTOCOLO_OBSERVACION.md) is not an approved or executed study. The [research comparison](CONTRASTE_INVESTIGACION.md) documents assumptions and source limitations.

Preserve saved games, old event compatibility and the distinction between proposed tests, executed technical tests and observed human outcomes. Developer onboarding starts in [CONTRIBUTING](../CONTRIBUTING.md).


## v0.3.0 publication scope

The source release preserves the optional client and its corrections, the redesigned dashboard/API integration snapshot and the blank IL-EXP-0.2 questionnaire. Root lint/format, 83 Node tests and build were checked during preparation. Browser results and CI are recorded against the final commit; the older 36-journey matrix above remains historical evidence. Host visual checks used synthetic responses. No host deployment, database migration or Protocolo42 save operation is part of this publication.
