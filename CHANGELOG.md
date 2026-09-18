# Historial de versiones

Se usa versionamiento semántico: MAJOR para incompatibilidades, MINOR para capacidades compatibles y PATCH para correcciones compatibles. Mientras el proyecto esté en 0.x es un prototipo en evolución. Cada entrega publicada debe tener una etiqueta Git `vX.Y.Z` y una GitHub Release con motivos, validación y límites.

La versión del producto en `package.json` es independiente de `CONFIG.version`, que controla compatibilidad de partidas. No modificar esa clave para publicar una entrega: requiere una migración explícita.

## [0.3.0] — 2026-09-18

### Motivo

Preparar colaboración sobre telemetría remota y hacer público el trabajo reciente de observación, manteniendo el juego local y las partidas existentes. Es una versión de desarrollo; no declara listo el piloto infantil ni despliega el administrador de Abejorro.

### Cambios

- Transporte opcional desactivado por defecto, exclusión de simulaciones, destinos autorizados, timeout/reintentos, límites UTF-8 y confirmaciones de recepción con `ultimoEventoId` cuando está disponible.
- Familias refleja el estado de envío. Compatibilidad con las claves de guardado y `CONFIG.version` intactas.
- Snapshot público de los módulos Luma de API PostgreSQL y panel integrado: tarjetas, paleta diferenciada, fechas legibles, detalle accesible, manejo de errores y distinción entre panorama agregado y partida individual.
- Cuestionario infantil rellenable IL-EXP-0.2, con comprensión de la aventura introductoria y guía de aplicación; generador reproducible.
- Portada y documentación pública actualizadas con captura sintética y guías de integración, alcance y límites.

### Validación y límites

Lint, formato, 83 pruebas Node y build local aprobados durante la preparación; las comprobaciones de navegador y CI del commit publicado se registran en GitHub Actions. El rediseño del host pasó TypeScript/lint y comprobaciones Playwright con respuestas ficticias en escritorio y móvil; no equivale a probar APIs reales. Los módulos extraídos requieren adaptadores y pruebas en su host. Sin migración de producción ni modificación de Protocolo42. La evidencia histórica de 36 recorridos corresponde a v0.2.0 y no se presenta como repetida en esta entrega.

## [0.2.0] — 2026-09-17

### Motivo

La revisión de calidad detectó dos defectos críticos: los eventos históricos podían cambiar al modificarse el aprendizaje y el agotamiento de variantes de transferencia podía bloquear el avance. Esta entrega corrige ambos, amplía el banco y facilita mantener reglas y evidencia coherentes. Se incrementa MINOR por incorporar variantes, una salida de agotamiento y capacidades de validación compatibles con las partidas existentes.

### Correcciones

- Fotografías inmutables de telemetría: las etapas obtenidas después ya no alteran eventos anteriores.
- Selección de variantes no vistas, 90 variantes contextuales de equivalencias y salida explícita al agotar el banco, sin acreditar transferencia ficticia.
- Presentación basada en `targetDen`, eliminando la dependencia de octavos en barras, ecuaciones y mensajes.
- Tablero con indicadores separados de estimación bayesiana y CPA verificada; simulador histórico identificado por su política.

### Mantenimiento y reproducibilidad

- Adaptadores inyectables de telemetría y persistencia, estado único por intento y guardados agrupados.
- Parámetros centralizados en `POLICY` y evidencia enlazada desde la misma evaluación que genera la decisión.
- ESLint, Prettier, dependencias fijadas, lista común de archivos públicos y pruebas de navegador en CI.
- Configuración de URL, puerto y navegador; informes basados en resultados fechados y vinculados al código, sin recuentos históricos incrustados.

### Compatibilidad y validación

- Se mantienen las claves de guardado y `CONFIG.version`. No se borran partidas ni registros.
- Nuevos eventos: esquema `1.4`, política `cpa-2`, ítems `fractions-3`. Simulador anterior: `legacy-bayesian-1`.
- Validación local: **75 pruebas aprobadas y 36 recorridos Playwright aprobados**, con 15 530 eventos y 856 intentos. Lint, formato y build aprobados.
- [Evidencia agregada](docs/evidence/quality-validation-summary.json) y [detalle de correcciones](docs/CORRECCIONES_CALIDAD.md).

### Límites

No se reparan retrospectivamente eventos históricos ya alterados. La interfaz/audio sigue admitiendo separación adicional; el guardado completo por lote todavía crece con el historial. El banco necesita revisión docente. No participaron niños ni se validó eficacia educativa o detección de ansiedad.

## [0.1.0] — 2026-09-17

Publicación inicial, commit `9d837c7`: aventura Isla Luma, cuatro modalidades, seis habilidades, progresión CPA, telemetría local, laboratorio, presentación LumaSprout, GIFs y documentación para colaboradores. Validación de aquella entrega: 36 recorridos y 67 comprobaciones adicionales. Se conserva como antecedente, separado de la evidencia de 0.2.0.

[0.2.0]: https://github.com/cristhianvs/lumasprout/compare/9d837c7...v0.2.0
[0.1.0]: https://github.com/cristhianvs/lumasprout/tree/9d837c7
