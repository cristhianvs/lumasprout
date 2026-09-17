# Contraste entre investigación base, implementación y simulaciones

Fecha: 17 de septiembre de 2026. Revisión documental y de código, con verificación selectiva de fuentes primarias. No constituye calibración estadística con datos de niños ni una nueva prueba de navegador.

## Conclusión

Las 36 simulaciones verifican consistencia operativa de reglas y recorridos. No validan la taxonomía cognitiva, la precisión del diagnóstico inicial, una medida de ansiedad, ni la superioridad pedagógica de asignar modalidades por preferencias. La propuesta base contiene hipótesis que presenta con demasiada certeza, errores concretos de atribución y componentes todavía no implementados.

Se conservaron el documento base y el informe técnico anterior. No se cambiaron pesos ni umbrales a partir de respuestas programadas: ajustar esos parámetros a los mismos guiones no aportaría validez externa.

Fuentes locales: `Investigación Gamificación Matemática Personalizada.pdf` (13 páginas, texto íntegro; inspección visual adicional de páginas 3, 7, 10 y 11), `engine.js`, `app.js`, `tests/behavior_matrix.py`, `output/behavior-matrix/summary.json` e informe técnico en `output/pdf/Isla_Luma_Reporte_Simulacion_Playwright.pdf`.

## Matriz de contraste

| Proposición del PDF | Evidencia actual | Clasificación y decisión |
|---|---|---|
| El juego previo permite caracterizar perfil cognitivo y motivacional (pp. 2–3) | Los recorridos incorporan cinco elecciones explícitas de modalidad y después comprueban sugerencia automática. No validan clasificación espontánea desde el juego previo. | Pendiente de validación: observar preferencias sin imponerlas desde el guion y contrastarlas entre sesiones. No afirmar que reconoce tipos de niño. |
| Un canal preferido determina cómo aprende mejor (pp. 3–5, 12) | La matriz no compara aprendizaje entre modalidades equivalentes; los aciertos son programados. | Supuesto no justificado como regla educativa. Conservar elección y accesibilidad, separar preferencia de eficacia y de competencia matemática. |
| Triangulación 60/40 y cuestionario estandarizado (p. 3) | Ponderación implementada; formulario de tres preguntas marcado como no validado. `response` se registra pero no interviene en puntuaciones ni política. | Implementación parcial y pesos sin calibrar. Validar preguntas, constructos y ponderaciones; decidir expresamente el uso de la respuesta familiar sobre dificultad. |
| La triangulación elimina sesgos y no genera estrés evaluativo (p. 11) | Ninguna observación humana en la matriz. | Garantía no respaldada. Dos fuentes pueden aportar contexto sin eliminar sus respectivos sesgos. |
| Telemetría indica ansiedad o crisis (pp. 6–7) | Registra errores, ayudas, latencias e interrupciones; el tablero informa ansiedad no inferible. | No válido como inferencia automática actual. Diferenciar lectura, dificultad conceptual, interfaz, ayuda exploratoria y posible malestar. |
| Tres fallos y 45 s indican bloqueo; sprints 60–90 s (pp. 4–7) | Tres fallos activan ayuda; 45 s pausa; `blockMs` 60/90 s no organiza bloques efectivos. Descanso efectivo por `breakAfterMs`. La prueba lenta introduce actividad neutra. | Umbrales heurísticos; falta probar lectura quieta, graduar apoyos y completar bloques. No tratar inactividad como desinterés. |
| CPA progresivo hasta autonomía y abstracción (pp. 2, 7, 11) | Hay representaciones y ayuda manipulativa; las barras siguen presentes y no existe retirada gradual validada hacia transferencia abstracta. | Pendiente pedagógico. Probar concreto, pictórico, simbólico y problema nuevo con evidencia independiente por etapa. |
| Red bayesiana de dependencias y selección informativa óptima (pp. 6–7) | Probabilidades separadas por habilidad y prerrequisitos para habilitar tareas; puntuación heurística local de selección. | Simplificación explícita, no equivalencia. Faltan calibración, predicción externa e inferencia conjunta si demuestra beneficio. |
| Umbral 0.85 acredita dominio (p. 7) | Umbral y tres evidencias independientes disparan cierre; probabilidades usan parámetros fijos .5, .9, .15 y .08. | Criterio interno sin validación psicométrica. No interpretar 0.85 como 85 % de certeza real sin evaluar calibración. |
| Mejora aprendizaje, motivación y retención (pp. 8–11) | 32 guiones alcanzan criterio interno; cuatro con ayuda permanente no aportan evidencia independiente. | No demostrado por automatización. Tampoco cero evidencias implica cero aprendizaje. Faltan pre/post independiente, transferencia, retención y contraste experimental. |
| Validación por expertos y piloto longitudinal (pp. 10–11) | Verificación técnica y tablero local. | Pendientes: juicio experto, observación infantil, instrumentos adecuados, gestión longitudinal, comparación y análisis. |

## Supuestos y errores del documento base

### 1. Preferencia, motivación y capacidad se mezclan

El PDF combina Hexad, Felder–Silverman, VARK e inteligencias múltiples como si produjeran una clasificación cognitiva común. No presenta un instrumento validado que justifique esa correspondencia para esta población. El caso más delicado es asociar exploración con TDAH leve (p. 4): el prototipo no mide ni debe inferir esa condición.

La revisión de Pashler y colaboradores distingue preferencias declaradas de evidencia de que adaptar la enseñanza a un supuesto estilo mejore el aprendizaje. No encontró respaldo adecuado para generalizar esa práctica. Esto no demuestra que toda adaptación sea inútil ni invalida ofrecer opciones; sí impide asumir «prefiere audio, por tanto aprende mejor con audio».

Fuente: [Pashler et al., Learning Styles: Concepts and Evidence](https://journals.sagepub.com/doi/10.1111/j.1539-6053.2009.01038.x).

### 2. Hay un error verificable en Hexad

La p. 1 enumera Explorer como uno de los seis componentes de Hexad, omitiendo Disruptor. El marco del autor enumera Philanthropist, Achiever, Socialiser, Free Spirit, Player y Disruptor. La exploración puede ser una orientación de diseño, pero esa lista no es una transcripción correcta de Hexad.

Fuente primaria: [Marczewski, Gamification User Types 2.0](https://www.gamified.uk/2013/11/18/gamification-user-types-2-0/).

### 3. Mayor rendimiento no garantiza menor ansiedad

El propio documento reseña ConectaIdeas. La publicación original informa mejora matemática y aumento de ansiedad. Por tanto, la reducción de ansiedad de la propuesta es una hipótesis separada, no una consecuencia garantizada del acierto, del juego o de la personalización. La comparación observada no permite atribuir aisladamente el daño a un único elemento competitivo.

Fuente: [Araya et al., BID, 2019](https://publications.iadb.org/en/does-gamification-education-work-experimental-evidence-chile-0).

### 4. La cadena de referencias necesita depuración

Gran parte de la taxonomía y las reglas remite a la referencia 1, otro PDF identificado solo por título, que no está disponible en este repositorio. No se verificó su respaldo primario.

La referencia 17, usada para justificar el motor, describe un contexto de universidad virtual. Además, su bibliografía atribuye a Kirschmer y Voight un trabajo de IA educativa con DOI `10.1137/080734467`; la editorial identifica ese DOI como un artículo sobre clases de ideales en órdenes de cuaterniones. Es una discordancia documental concreta, no prueba por sí sola de falsedad de todas las ideas del artículo. Impide usar esa cadena como aval suficiente sin revisar las fuentes.

Fuentes: [artículo CEUR, referencia 17 del PDF](https://ceur-ws.org/Vol-4014/Short8.pdf), [registro original de SIAM](https://epubs.siam.org/doi/10.1137/080734467).

No se auditaron exhaustivamente las 25 referencias. Los porcentajes y resultados de los restantes estudios no se adoptan como metas ni efectos esperados de Isla Luma.

### 5. El plan experimental requiere reformulación

El PDF propone 300 alumnos de tercero a quinto, asignación por aulas, intervención de 12 semanas y tres grupos. El producto acordado es uso autónomo en casa, quinto/sexto de primaria, con foco en fracciones. La muestra, contexto e instrumentos no se pueden trasladar sin rediseñar el estudio.

Existe una inconsistencia temporal: la intervención termina en la semana 22, la fase final abarca semanas 23–26, pero incluye retención ocho semanas después del postest. Esa retención requiere extender el calendario más allá de la semana 26. El tamaño de 300 alumnos tampoco está acompañado en el documento por un cálculo de potencia; si se asigna por aulas, el análisis debe contemplar esa agrupación.

## Desviaciones deliberadas que deben conservarse como decisiones, no fallos

- Juego previo no matemático de hasta cinco minutos y salida por objetivos: acuerdo del usuario, frente a 5–8 minutos del PDF y su mención de errores matemáticos.
- Sin clasificaciones competitivas ni cronómetros de respuesta desde el inicio: no hace falta detectar una crisis para retirarlos.
- Audio opcional y alternativa visual: preferencia no equivale a obligación ni a disponibilidad del dispositivo.
- Banco común de fracciones para todos: no limitar a un niño a geometría o ritmo por una etiqueta.
- Cambios automáticos al iniciar un reto, preservando trabajo actual, con elección explícita prioritaria.
- Preferencias provisionales y posibilidad de evidencia insuficiente: no forzar un dominante.

## Prioridades y criterios propuestos

1. **Depurar especificación y fuentes antes de ampliar inferencias.** Separar conocimiento, preferencias y necesidad de apoyo; documentar cada regla como hipótesis o requisito, y corregir errores bibliográficos. Criterio: ninguna regla de producción depende de una etiqueta clínica o de una garantía no demostrada.
2. **Completar la evidencia pedagógica.** Añadir problemas nuevos, retirada gradual de ayuda y comprobaciones independientes después del andamiaje. Criterio: resolver otra representación y un contexto nuevo, no únicamente repetir el constructor conocido.
3. **Preparar calibración observacional.** Distinguir lectura quieta, exploración y dificultad con observación humana; revisar ayudas, 45 s, 60/40, 120 s/20 eventos, separación .06 y conocimiento. Criterio: evaluar errores de decisión y rendimiento predictivo en datos distintos de los utilizados para ajustar.
4. **Evaluar la contribución de cada adaptación.** Comparar con tareas y tiempos equivalentes: elección libre, sugerencia por preferencia y adaptación basada en conocimiento. Criterio: resultados externos de aprendizaje y bienestar; no usar la puntuación del propio motor como resultado principal.
5. **Diseñar investigación longitudinal adecuada al contexto.** Expertos, piloto observado, instrumentos pertinentes, pre/post, retención y persistencia por participante. Estas actividades son propuestas; no se ejecutaron en esta revisión.

Los dos defectos corregidos en Playwright refuerzan una lección transversal: registrar un evento no garantiza que mida el constructo pretendido. Primero se valida integridad de medición; después se calibra y finalmente se evalúa eficacia.
