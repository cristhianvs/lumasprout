# Correcciones de calidad de código

Fecha: 17 de septiembre de 2026. Seguimiento de [la revisión inicial](REVISION_CALIDAD_CODIGO.md).

## Cambios implementados

| Hallazgo | Corrección |
|---|---|
| Eventos que cambiaban después de emitirse | `runtime.js` captura y congela profundamente el registro JSON. El simulador también captura sus payloads. Los registros antiguos se conservan; no se puede reconstruir evidencia histórica que ya hubiera sido modificada. |
| Transferencia bloqueada por variantes repetidas | Selección determinista de variantes no vistas, equivalencias ampliadas y agotamiento explícito. Agotar el banco registra `item_bank_exhausted`, conserva el progreso y pide revisión con un adulto; no certifica transferencia ni vuelve a presentar el mismo reto indefinidamente. |
| Indicadores de dominio incompatibles | `progressSummary` separa criterio bayesiano, etapas, transferencia, compatibilidad anterior y cierre. El tablero distingue CPA verificada y estimación. El simulador anterior se identifica como `legacy-bayesian-1`. |
| Dependencias y estado duplicado | Telemetría y repositorio de partidas tienen adaptadores inyectables de contexto, reloj, almacenamiento y planificación. El intento vive directamente en `state.current`; se eliminó su copia sincronizada al guardar. |
| Parámetros dispersos | `POLICY` reúne parámetros de conocimiento, preferencias, señales, apoyo, ritmo y contenido. La decisión devuelve los mismos IDs de evidencia que utilizó. No se recalibraron umbrales a partir de simulaciones. |
| Octavos fijos en la interfaz | Consignas, barras, ecuación y mensajes usan `targetDen`. El constructor admite los denominadores del catálogo, incluido 18. |
| Guardado repetido por evento | El repositorio agrupa cambios síncronos en una escritura por microtarea y fuerza el guardado al ocultar/cerrar la página. Los errores conservan los datos en memoria, se anuncian y permiten reintentar/exportar. |
| Calidad y reproducibilidad | ESLint, Prettier, lockfile, CI con pruebas de navegador, configuración de URL/canal/puerto y lista común de archivos públicos. Los generadores de informes consumen evidencia fechada y rechazan resultados fallidos, ausentes o de otro código. |

## Compatibilidad y contratos

- `CONFIG.version` y las claves de almacenamiento permanecen iguales. No se borran partidas ni eventos.
- Los eventos nuevos del juego usan esquema `1.4`, política `cpa-2` e ítems `fractions-3`. El simulador histórico conserva una política identificada por separado.
- Las variantes no son nuevas por cambiarles un ID: se distinguen por operandos, representación solicitada y contexto. Las huellas antiguas de cuartos/octavos siguen reconociéndose.
- La ampliación y selección del banco es un cambio de comportamiento explícito. La calidad pedagógica y suficiencia de la transferencia cercana requieren revisión docente.
- El formato JSON de guardado/exportación sigue siendo compatible. No se truncó el historial.

## Validación y reproducción

**Ejecutado sobre esta corrección:** 75/75 pruebas aprobadas (44 Node, 14 navegador general, siete modalidades, cinco pedagógicas y cinco de laboratorio), más 36/36 recorridos Playwright. La matriz produjo 15 530 eventos y 856 intentos; 32 cierres independientes y cuatro descansos en los escenarios de ayuda permanente, con cero evidencias independientes en esos cuatro casos. Pasaron lint, formato, build y comprobación sintáctica Python. [Agregado de resultados](evidence/quality-validation-summary.json).

Se verificó que el generador de reportes rechaza la matriz histórica como evidencia actual. No se regeneraron PDFs ni se ejecutó un despliegue o CI remoto. La comparación local de reglas que debían permanecer iguales realizó otras 4 676 comprobaciones contra `9d837c7`, conservadas en `output/validation/policy-compatibility.json`; no se mezclan con el número de pruebas de las suites.

```sh
npm ci --ignore-scripts
npm run check
npm run build:site
npm start
# En otra terminal, con Playwright instalado:
python -X utf8 scripts/validate.py node
python -X utf8 scripts/validate.py browser
python -X utf8 scripts/validate.py profiles
python -X utf8 scripts/validate.py pedagogy
python -X utf8 scripts/validate.py laboratory
python -X utf8 tests/behavior_matrix.py --profile estructurado --output output/quality-matrix
# Repetir la matriz para visual, auditivo y explorador.
```

Las suites escriben `output/validation/<suite>.json` y su log, con fechas, comando, recuento, resultado y hash de fuentes. La matriz guarda la misma vinculación, telemetría, capturas y trazas. `LUMA_BASE_URL` cambia el servidor y `LUMA_BROWSER_CHANNEL` vacío selecciona Chromium de Playwright; por defecto se usa Chrome. `PORT` y `HOST` configuran el servidor local.

Las regresiones nuevas comprueban inmutabilidad anidada, recuperación tras error de cuota, agotamiento de cada banco, compatibilidad de huellas, separación de criterios de progreso y exactitud de IDs de señales. Las pruebas de navegador añaden equivalencias con denominadores distintos de ocho y salida de banco agotado. Esta última usa una partida preparada explícitamente; la matriz de comportamientos sigue usando interacción de UI sin inyectar estado.

## Límites que no deben ocultarse

Esto mejora Clean Code, responsabilidad única, inversión de dependencias, DRY y KISS; no constituye una certificación de SOLID. La interfaz y el audio aún comparten `app.js`; se puede seguir extrayendo presentadores por modalidad cuando se amplíen sus comportamientos. No hay jerarquías de clases que requieran demostrar Liskov.

La persistencia sigue serializando la partida completa una vez por lote. Un diario por segmentos o IndexedDB sería una migración adicional para sesiones extensas; no se ha medido rendimiento a esa escala. No se declara solucionado ese límite por haber reducido escrituras. Las constantes matemáticas, los catálogos, las versiones y los valores gráficos siguen siendo literales legítimos; el objetivo no es eliminar todos los números.

Estas comprobaciones son técnicas. No se realizaron observaciones con niños, calibración clínica ni validación de eficacia educativa.
