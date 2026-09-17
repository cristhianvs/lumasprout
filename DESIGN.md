# Isla Luma: diseño del MVP

Estado: prototipo funcional local, versión 0.1. Población: estudiantes de 5.º y 6.º de primaria en México. Uso autónomo en casa. Contenido inicial: comprensión de fracciones, equivalencias, suma y resta. El grado escolar no se usa como evidencia de conocimiento.

## Decisión central

El sistema averigua cómo acompañar al niño mientras juega, y qué sabe de fracciones cuando empieza a interactuar con fracciones. No se pide a la familia decidir dificultad, duración ni ruta de contenidos.

La aventura previa tiene un **límite de 300 segundos activos**, sin operaciones, cantidades, fracciones, puntuaciones ni cuenta regresiva visible. Las misiones tienen objetivos finitos y se puede terminar antes al completarlos. Los cinco minutos no obligan a repetir respuestas correctas. Su resultado es un conjunto de preferencias provisionales y observaciones conductuales. No produce una calificación matemática.

El recorrido completo es:

1. Invitación a explorar la isla.
2. Aventura previa no matemática de cinco minutos.
3. Transición narrativa al taller de energía.
4. Exploración matemática integrada en las primeras actividades del taller.
5. Práctica con dificultad y apoyos adaptativos.
6. Descanso sugerido, persistencia y continuación.

El cuestionario de la familia puede completarse antes o después, sin bloquear el recorrido autónomo. Sin cuestionario completo, el perfil se identifica como provisional y usa exclusivamente la observación disponible.

## Trazabilidad con el PDF

Fuente local: `Investigación Gamificación Matemática Personalizada.pdf`, 13 páginas, revisado en texto y visualmente.

| Elemento del estudio | Página | Decisión de producto |
|---|---|---|
| CPA y reducción de carga cognitiva | 2 | Paneles de piezas, representación visual y escritura de fracciones; ayuda accesible en cualquier momento. |
| Play-test de 5 a 8 minutos | 2–3 | Cinco minutos activos, como solicitó el usuario. Se sustituyen los errores matemáticos de esta fase por obstáculos no matemáticos. |
| Elecciones de modalidad, reacción al error, autonomía | 3 | Ayudas equivalentes, refugios y señales con reintento, elección de ruta y navegación registrada. |
| Observación de la familia | 3 | Canal elegido, intereses y reacción habitual ante una dificultad. Instrumento breve propio, pendiente de validación. |
| Triangulación 60 % / 40 % | 3 | Solo se aplica con observaciones familiares completas. No se inventa el 40 % faltante. |
| Cuatro perfiles dominantes/secundarios | 3–5 | Vector de preferencias editable por nueva evidencia; sin etiquetas visibles para el niño. |
| Seguimiento continuo y árbol de conocimiento | 6 | Registro por actividad y grafo de prerrequisitos del taller. |
| Bayes y selección de siguiente reto | 6–7 | Actualización bayesiana por habilidad y selección voraz restringida por prerrequisitos. Es una simplificación explícita de la red propuesta. |
| Tres errores / 45 segundos sin interacción | 7 | Apoyo manipulativo tras tres fallos. Oferta de pausa y ayuda a los 45 segundos; no se registra como error. |
| Variación de latencia y solicitudes repetidas de pistas | 7 | Se registran y pueden ofrecer apoyo; nunca se declaran equivalentes a ansiedad. |
| Pre-test matemático separado del play-test | 10 | Las respuestas del taller generan el mapa de conocimiento; el juego previo no modifica probabilidades de dominio. |
| Retención y seguimiento longitudinal | 11 | Eventos exportables y progreso conservado. La prueba de retención diferida pertenece al piloto posterior. |

Los tiempos de cada escena, la puntuación de preferencias y los parámetros del modelo son decisiones de este prototipo, no instrumentos validados por el PDF. Tampoco se presenta como realizado el experimento de 300 alumnos descrito en el documento.

## Videojuego previo: «Despierta Isla Luma»

Una tormenta dejó dormida una isla flotante. Luma, una pequeña criatura vegetal, invita al niño a ayudarla. No hay derrota, vidas, comparación pública ni premios por velocidad.

| Tiempo activo | Escena y acción | Evidencia que permite observar |
|---|---|---|
| 0:00–1:00 | **Un lugar por descubrir.** Visitar invernadero, estación y jardín. Elegir «Guíame» o «Quiero explorar»; cambiar de opción libremente. | Elección explícita de autonomía, orden de visitas, cambios de ruta, ayudas elegidas, latencia de exploración. |
| 1:00–2:30 | **El refugio de las hojas.** Seleccionar la criatura objetivo y llevarla a un refugio con su señal. Los símbolos se identifican también por nombre. | Latencia por intento, errores de asociación, reintento, ayuda posterior al error, abandono de la tarea. |
| 2:30–4:00 | **Una señal entre las nubes.** Reconstruir un camino de símbolos, con deshacer y reintentos. La referencia permanece visible. | Revisión de estrategia, ensayo y error, uso de demostración, autonomía y respuesta a una dificultad recuperable. |
| 4:00–5:00 | **Tu rincón de la isla.** Cambiar plantas y ambiente; escuchar una descripción o solicitar una idea de Luma. | Elección entre guía y creación libre, cambios creativos, interés por audio y persistencia exploratoria. |

No se introducen fallos artificiales. Un niño que resuelve todo sin equivocarse termina con «reacción al error no observada», no con una tolerancia supuesta. Tampoco se interpreta una elección de color como capacidad matemática.

La tabla anterior muestra los límites temporales de respaldo. La progresión principal depende de objetivos: explorar los lugares, rescatar a flor/luna/rombo sin repetirlos, completar tres conexiones distintas y terminar el jardín. Cada misión completada ofrece un botón visible para pasar a la siguiente. Los aciertos se conservan al recargar y se recuperan de la telemetría de partidas antiguas. El límite temporal evita retener al niño en una actividad incompleta. Ocultar la pestaña, abrir el panel familiar o pausar detiene el tiempo. Una construcción parcial de símbolos puede reiniciarse al recargar, pero las misiones resueltas no vuelven a pedirse.

## Ayudas comparables

- **Ver una pista:** instrucciones con referencia visual siempre accesible.
- **Escuchar:** la misma información mediante síntesis de voz en español de México; disponibilidad y errores se registran por separado.
- **Probar con Luma:** inicio asistido de la acción, por ejemplo seleccionar la criatura o colocar el primer símbolo. En el taller habilita una mesa de piezas que se puede tocar con ratón, pantalla táctil o teclado.

Las posiciones de estas opciones se rotan entre partidas y permanecen estables dentro de una partida. Se registra si el apoyo fue elegido libremente o mostrado por el sistema. La ayuda automática no se cuenta como una preferencia voluntaria.

La interfaz usa ilustraciones, señales visibles y textos cortos; no necesita cámara ni micrófono. La síntesis de voz depende del navegador. La versión actual ofrece narración, no un minijuego de ritmo. Queda por equilibrar experimentalmente la riqueza y accesibilidad de las tres modalidades.

## Telemetría en segundo plano

Cada evento incluye identificador, sesión, partida, versión de reglas, fecha, tiempo activo del juego, tiempo activo del taller, fase, escena, tarea y datos del evento. Las marcas temporales de pared permiten distinguir días/sesiones; las latencias de tareas usan tiempo activo.

| Familia | Eventos implementados | Uso permitido |
|---|---|---|
| Contexto | `session_started`, `playtest_started`, `scene_entered`, `scene_left`, `task_presented` | Saber qué estímulo estuvo disponible y en qué condiciones. |
| Modalidad | `support_selected`, `support_unavailable`, `sound_changed`, `audio_started`, `audio_completed` | Observar elección voluntaria y disponibilidad real de audio. |
| Autonomía | `route_selected`, `navigation`, `creative_change` | Preferencia por guía, exploración y creación. |
| Acción y estrategia | `object_selected`, `sequence_action`, `strategy_changed`, `manipulation` | Reconstruir decisiones y cambios de estrategia. |
| Desempeño | `attempt`, `input_validation` | Acierto, patrón de error, primera respuesta/reintento, ayuda y latencia. Un formato inválido no cuenta como error de conocimiento. |
| Recuperación | `post_error_action`, `hint_requested` | Tiempo hasta siguiente acción, reintento, solicitud de apoyo o cambio de estrategia. |
| Actividad | `interaction_summary`, `heartbeat` | Resumen de movimiento y tipo de entrada. No almacena trayectorias de puntero ni teclas escritas. |
| Pausa/contexto | `idle_started`, `idle_ended`, `pause_started`, `pause_ended`, `visibility_hidden`, `visibility_visible`, `session_interrupted` | Distinguir tiempo activo, pausa voluntaria, pestaña oculta y cierre de página. Un cierre no demuestra frustración. |
| Adaptación | `adaptation`, `scaffold_shown`, `knowledge_updated`, `break_suggested` | Auditar por qué cambió el apoyo o la recomendación. |
| Familia | `parent_observation_saved`, `family_opened`, `family_closed` | Procedencia y versión de la segunda capa. |
| Cierre | `playtest_completed`, `math_started`, `voluntary_break`, `math_resumed`, `export_requested` | Continuidad y análisis longitudinal. |

Latencia tras un error, velocidad irregular, inactividad y frecuencia de pistas son observaciones ambiguas. Se usan para **ofrecer ayuda**, no para atribuir TDAH, ansiedad, personalidad ni capacidad. No se hacen inferencias por género.

Persistencia actual: `localStorage`, un perfil por navegador, sin cuenta y sin envío de eventos. Exportación completa en JSON desde Familias. Los eventos no se descartan deliberadamente; si el almacenamiento falla se informa en el panel familiar y se puede exportar la memoria disponible. Para un piloto longitudinal deben migrarse a almacenamiento transaccional y un sistema de perfiles; este prototipo no es una plataforma de investigación desplegada.

## Perfil y adaptación

El vector conserva cuatro dimensiones: estructurado, visual, auditivo y explorador. Parte de una distribución uniforme. Las ayudas voluntarias, elecciones de ruta y creación aportan evidencia con pesos explícitos en `engine.js`. No se usa el número de aciertos no matemáticos para estimar dominio de fracciones.

Con cinco observaciones y una separación mínima de 0.06 entre las dos primeras dimensiones se muestra un perfil dominante/secundario únicamente en el panel familiar. Ese umbral es una heurística de producto. Con menos evidencia se informa «evidencia insuficiente».

La familia completa tres observaciones. Canal e interés forman el vector familiar; la reacción habitual queda registrada como contexto, sin convertirla en una puntuación clínica. Cuando está completo:

`preferencia combinada = 0.60 × observación del juego + 0.40 × observación familiar`

Sin cuestionario, se conserva la observación disponible con marca provisional. La isla y el grafo matemático son comunes; el taller ofrece cuatro modalidades jugables. La elección del niño tiene prioridad sobre la inferencia. Sin evidencia suficiente se inicia con pasos ordenados, con todas las modalidades disponibles.

### Reglas operativas

| Señal | Respuesta implementada |
|---|---|
| Tres fallos en una tarea | Demostración inicial / mesa manipulativa. |
| 45 segundos sin acciones discretas | Pausa con opciones de continuar o pedir ayuda. |
| Tres solicitudes de pista en 60 segundos activos | Ofrecer apoyo concreto. |
| Cinco latencias recientes con variación relativa > 1 | Ofrecer apoyo concreto; regla exploratoria con motivo auditable. |
| Cuatro o más errores/pistas/inactividades entre los últimos 20 eventos relevantes | Sugerir descanso al finalizar una tarea después de cuatro minutos activos del bloque. |
| Menor necesidad de apoyo | Sugerir descanso después de ocho minutos activos del bloque. |
| Acierto con ayuda o reintento | Celebrar resolución, sin contarlo como nueva evidencia de dominio independiente. |

La política calcula también un objetivo de microactividad de 60 o 90 segundos. **No corta tareas a ese tiempo**; es un parámetro disponible para ajustar la longitud futura del banco de contenido. El estudiante siempre puede descansar antes o seguir después.

El PDF no proporciona una fórmula validada para deducir toda la duración de estudio a partir de cinco minutos. Por eso los valores iniciales son revisables y la adaptación continúa en el taller.

## Diagnóstico matemático y enseñanza

La transición dice «encendamos el taller», sin presentar una prueba con calificación. Cada habilidad empieza como desconocida (`p = 0.5`). Se pide interpretar y operar paneles de energía.

Grafo actual:

```text
Partes de un entero ──┬── Equivalencia ──────────┬── Suma con distinto denominador
                     ├── Suma con igual denom. ┘
                     └── Resta con igual denom. ─── Resta con distinto denominador
                             Equivalencia ────────┘
```

El selector prioriza habilidades disponibles no dominadas con incertidumbre/necesidad y valor como prerrequisito. La versión actual explora desde los fundamentos; todavía no implementa un diagnóstico abreviado que permita saltar prerrequisitos a partir de ítems compuestos. No asume por ser 5.º o 6.º que ya los domina.

Cada primera respuesta sin ayuda actualiza la probabilidad por Bayes, con probabilidad de acierto dominando = 0.9 y sin dominar = 0.15, más transición de aprendizaje = 0.08. Dominio exige probabilidad ≥ 0.85 y al menos tres respuestas independientes. Es una aproximación por habilidad; no implementa la marginalización conjunta de todos los padres del DAG que describe el estudio.

Se acepta una respuesta equivalente aunque no esté simplificada, excepto cuando la consigna pide expresamente octavos. Se reconocen errores como sumar denominadores, operar unidades de distinto tamaño e invertir numerador y denominador. El formato inválido no reduce dominio.

Representaciones:

1. **Concreta digital:** activar/desactivar piezas de un entero dividido.
2. **Pictórica:** comparar paneles de igual tamaño total.
3. **Abstracta:** escribir y verificar una fracción o entero.

El banco actual es pequeño y sirve para verificar el recorrido y la adaptación. Algunas sumas superan un entero. No se implementa todavía una ruta completa de números mixtos, simplificación explícita, problemas verbales ni retención diferida. Esas extensiones deberán incluir ítems diagnósticos propios antes de atribuir dominio.

## Validación y límites de esta entrega

- Pruebas automáticas del motor: equivalencia, errores, prerrequisitos, falta de evidencia, ponderación y protección contra atribuir dominio por ayudas.
- Pruebas del flujo mediante un entorno DOM simulado: duración activa, pausas, transiciones, persistencia y separación del diagnóstico no matemático.
- La revisión con niños y la calibración pedagógica siguen pendientes. No se afirma eficacia educativa ni validez psicométrica.
- El audio requiere verificación en el navegador/dispositivo final. El juego sigue siendo operable sin audio.
- La navegación visual se revisó posteriormente con Playwright y capturas de Chrome real; ver `docs/VALIDACION.md`. Antes de pilotar siguen pendientes diversidad del banco, calibración de ayudas y almacenamiento para varias familias.

## Criterios para el siguiente piloto

1. El niño puede iniciar y completar la aventura sin instrucciones de un adulto.
2. Todas las elecciones ofrecidas quedan registradas con su contexto y disponibilidad.
3. Se distingue evidencia ausente, respuesta asistida e intento independiente.
4. Las pausas no producen errores ni tiempo de juego artificial.
5. La dificultad matemática responde a ejercicios matemáticos, no a perfiles de preferencia.
6. La familia puede revisar y exportar el registro sin que se muestre telemetría técnica durante el juego.
7. Comparar desempeño independiente al entrar y al salir del taller, además de facilidad de uso; el tiempo de juego por sí solo no constituye aprendizaje.

## Complementos tras la validación con Playwright

La revisión posterior corrigió conservación de borradores/piezas, foco de teclado, alternativa al audio e iconografía. Se agregaron respuesta directa con piezas, `attemptNumber`, `cpaPhase`, `schemaVersion`, `constructed_answer` y `support_exposure` (tiempo activo, origen y causa de cierre). Estas ampliaciones provienen del contraste con la alternativa C y tienen pruebas de navegador real. La mesa «Probar con Luma» produce evidencia asistida. Los constructores normales de las cuatro modalidades permiten evidencia independiente porque no revelan respuestas; pedir pistas o reintentar conserva la marca de asistencia.

El contraste documenta diferencias respecto de los umbrales del PDF y las instrucciones del usuario. No se incorporaron matemáticas en el play-test, fallos inducidos, un mínimo obligatorio de sesión ni una escala clínica. Consultar `docs/VALIDACION.md` para el detalle de decisiones y pendientes.

## Corrección de progresión tras reporte de repetición

La versión inicial confundía tiempo activo con avance: repetía los tres objetivos hasta cambiar de escena por reloj. Se sustituyó por progreso persistente por objetivo y pantalla de misión completada. La antena usa su propio contador de conexiones, independiente del refugio. En matemáticas, completar las seis habilidades lleva a una pantalla final; la repetición queda como práctica elegida por el usuario. Las pruebas 12–14 de Playwright cubren el bucle reportado, migración de partidas antiguas y una partida completa con reloj real desde el mapa hasta la exportación final.

## Cuatro modalidades implementadas

| Preferencia | Modalidad | Interacción y avance |
|---|---|---|
| Estructurada | Laboratorio de pasos | Pasos revisables, elección de denominador y numerador; planos por reto resuelto. |
| Visual | Estudio de mosaicos | Pinceles de tres colores, pintura de casillas en dos enteros; teselas por reto resuelto. |
| Auditiva | Estación de ritmos | Compases editables, reproducción del panel y de la respuesta con Web Audio; notas recuperadas. También funciona sin audio. |
| Exploradora | Ruta de energía | Cargar y devolver piezas de dos baterías, entregar la cantidad construida; entregas acumuladas. |

Las cuatro cubren partes del entero, equivalencias, sumas y restas con denominadores iguales y distintos. Elegir la partición y construir la cantidad son parte de la respuesta: no se proporciona el denominador correcto. Se conserva la entrada escrita como alternativa. Los controles tienen al menos 44 px de altura; las casillas, al menos 44 px por lado. Resultado y botón de continuar aparecen junto al constructor en móvil.

«Cambiar mi forma de jugar» permite elegir o volver a las sugerencias de Luma. Cambiar conserva reto, intentos, condición de ayuda, conocimiento y construcciones de cada modalidad. No concede nuevas recompensas por un reto ya resuelto. La asignación automática se actualiza al empezar un reto, sin alterar una construcción a mitad del trabajo. Las observaciones recientes se limitan a 80 eventos de preferencias y se deduplican por contexto, tipo y elección. Las ayudas automáticas no cuentan como preferencias. Son heurísticas pendientes de calibración; no diagnósticos.

Persistencia compatible con partidas anteriores, sin cambiar la clave ni borrar registros. Los eventos nuevos usan `schemaVersion: 1.2` y el campo `experience`. Se agregan `experience_assigned` (origen y vector), `experience_selected`, `experience_auto_requested`, `experience_action`, `experience_answer`, `experience_reward` y `rhythm_played`. Los eventos antiguos conservan su esquema. El panel familiar y la exportación incluyen modalidad, elección explícita y recompensas.

El sonido se inicia por acción del niño y se detiene al silenciar, pausar, abrir Familias, cambiar de modalidad/reto, descansar u ocultar la pestaña. La falta de Web Audio tiene alternativa visual y queda registrada. La automatización comprueba reproducción sin excepciones; no sustituye escuchar el dispositivo físico.
