# Complementos posteriores al contraste de investigación

17 de septiembre de 2026. Implementación técnica; ninguna observación con niños.

## Cambios verificables

- Progresión por habilidad: representación concreta con constructor, pictórica sin constructor inicial, abstracta sin paneles y problema contextual. Los apoyos siguen disponibles y se registran como asistencia. La elección de modalidad se conserva aunque se retire su constructor para comprobar autonomía.
- Para las partidas nuevas, el cierre exige el criterio probabilístico anterior y un acierto independiente en cada etapa. Un acierto por etapa es una regla provisional de cobertura, no un umbral de aprendizaje validado. Resolver en un contexto nuevo dentro del juego es transferencia cercana; no sustituye una evaluación externa.
- Se amplían operandos de operaciones y contextos de receta, jardín y ruta. La equivalencia sigue trabajando cuartos/octavos: el banco no representa todo el currículo. Las variantes tienen identificación reproducible, versión y registro de exposición. La novedad se comprueba dentro de cada etapa y contexto, no garantiza operandos nunca vistos.
- Después de ayuda/error se mantiene pendiente una oportunidad independiente. Esta oportunidad evita que las señales antiguas impongan ayuda automática al presentar el siguiente reto. El niño puede pedirla de nuevo. No se atribuye autonomía a reintentos.
- «Todavía no sé» registra incertidumbre declarada y abre piezas; no penaliza conocimiento ni se contabiliza como respuesta incorrecta. El siguiente reto vuelve a comprobar sin ayuda.
- «Sigo leyendo», ante la pausa por inactividad, concede 120 segundos antes de una nueva comprobación. Es una declaración del usuario; no una medición objetiva de lectura o enganche. La espera previa en pausa no se suma al tiempo activo. La concesión termina al recargar.
- Bloques de 60/90 segundos activos se cierran en la siguiente transición tras resolver, registran sus tareas y muestran una invitación a continuar o descansar. No interrumpen una respuesta; pueden exceder la duración objetivo. El descanso de 4/8 minutos continúa siendo independiente de estos bloques.
- El administrador muestra etapas independientes, oportunidades pendientes y decisión enlazada al resultado posterior. Conserva lectura de registros antiguos. La respuesta familiar sobre dificultad aparece como contexto sin peso automático validado.

## Telemetría

Se conserva `CONFIG.version` y las claves de almacenamiento. Los nuevos eventos usan `schemaVersion: 1.3` y `policyVersion: cpa-1`. El conocimiento anterior no se borra: las habilidades ya dominadas se conservan como `legacyMastered`, con CPA no verificada explícitamente en el administrador. Las demás habilidades completan la nueva secuencia. Un reto antiguo en curso conserva sus datos y no recibe retrospectivamente una etapa inventada.

| Registro | Contenido nuevo / uso |
|---|---|
| `task_presented` | Ítem y versión, etapa, contexto, variante, novedad y oportunidad independiente. |
| `adaptation_decision` | ID, señales previas enlazadas, etapa, política, excepción para comprobación independiente, contexto familiar. |
| `attempt` | Decisión, variante, etapa prevista y representación de respuesta, primer intento/asistencia y patrón de error. |
| `decision_response` | Error y decisión que precedió la respuesta; conserva el fallo aun antes de resolver. |
| `decision_evaluated` | Resolución, intentos, independencia, posterior y cobertura pedagógica. No afirma causalidad. |
| `experience_options_offered` | Opciones disponibles y selección vigente; disponibilidad no demuestra que fueron vistas. |
| `uncertainty_reported` | «Todavía no sé»: autoinforme separado del error matemático. |
| `reading_confirmed` | Autoinforme de lectura y duración de la concesión. |
| `learning_block_completed` | Tareas, tiempo activo real, duración objetivo y cierre en transición. |

`support` sigue describiendo la recomendación de la política por señales, mientras `stage`, `independentProbe`, asistencia y eventos de apoyo describen lo aplicado. No interpretar `support` aislado como la representación visible. La latencia es tiempo activo registrado, no tiempo cognitivo observado. El tablero sigue siendo local; no se añadió servidor de seguimiento de múltiples participantes.

## Validación y evidencia

La matriz actual se guarda separada en `output/pedagogy-matrix/`: cuatro modalidades por nueve comportamientos, con reloj virtual y acciones de interfaz desde una partida vacía. Las respuestas se calculan desde información visible; solo se lee localStorage para auditar. Los guiones no introducen eventos o conocimiento. Cada cierre independiente exige las 24 etapas (seis habilidades por cuatro); cada resultado debe enlazar una decisión y sus señales previas. Exportación e importación se prueban con la interfaz.

`tests/pedagogy_test.py` añade comprobaciones específicas de incertidumbre, recuperación independiente, retiro de representaciones, lectura quieta declarada, recarga, tablero y bloques. `tests/pedagogy.test.cjs` prueba migración, prerrequisitos y exactitud del banco (2 304 combinaciones). Los resultados ejecutados y cantidades finales se consignan en el informe PDF y `docs/CONTEXTO_ACTUAL.md`; este apartado describe el contrato de prueba, no anticipa su aprobación.

## Pendientes antes de interpretar resultados humanos

1. Revisión docente de dificultad, consignas y suficiencia del banco; ampliar equivalencias, problemas no isomorfos y diagnóstico inicial entre habilidades. La exploración matemática actual comienza en partes del entero; no es un diagnóstico estandarizado.
2. Revisar el protocolo de `docs/PROTOCOLO_OBSERVACION.md`, preparar las autorizaciones y criterios de interrupción con responsables del estudio. No se ha ejecutado ese protocolo ni aprobado instrumentos.
3. Comparar observación humana con señales del juego y ajustar umbrales usando datos de desarrollo, reservando participantes distintos para evaluación. No se recalibró 60/40, .85, .06 ni ventanas temporales para favorecer estos guiones.
4. Contrabalancear orden de modalidades si se quiere estudiar preferencia; hoy las cuatro están disponibles y su orden es fijo. Disponibilidad equivalente no elimina sesgo de posición.
5. Evaluación externa pre/post y retención, y comparación de adaptación por conocimiento versus sugerencia de modalidad. La puntuación interna no puede ser el resultado principal que valide al propio motor.

Los supuestos rechazados en `docs/CONTRASTE_INVESTIGACION.md` siguen rechazados: modalidad preferida no implica mejor aprendizaje; inactividad no identifica ansiedad; probabilidades internas no son certezas empíricas. La progresión y el circuito son hipótesis instrumentadas, no eficacia demostrada.
