# Validación de Isla Luma y contraste con la alternativa C

Fecha: 16 de septiembre de 2026. Revisión técnica y heurística de usabilidad; no es una prueba de comprensión con niños ni una validación de eficacia educativa.

## Resultado

Se probó la aplicación en **Google Chrome 153.0.8010.47 real**, controlado con **Playwright para Python 1.58.0**. Contextos nuevos, separados del perfil personal. Escritorio de 1440 × 1000, móvil de 390 × 844 y pantalla estrecha de 320 × 740.

El reloj de Playwright recorrió los 300 segundos activos ejecutando los temporizadores reales de la página. No se cambiaron los umbrales de la aplicación ni se inyectaron respuestas en su estado. Las respuestas matemáticas se calcularon con aritmética racional de Python a partir de las cantidades representadas en el DOM, de forma independiente al motor JavaScript.

Resultado inicial: 11 pruebas de Playwright y 16 del motor/flujo simulado aprobadas. Esa cobertura verificaba respuestas y transiciones temporales, pero no detectaba la repetición de misiones ya resueltas. El reporte del usuario reveló esa carencia; se añadieron las pruebas 12–14 descritas a continuación.

## Revisión posterior: partida completa y corrección de bucles

La causa del problema reportado era `round % 3`: el objetivo volvía a empezar tras flor, luna y rombo. Solo el reloj cambiaba la escena. La antena repetía del mismo modo. Se corrigieron ambos con objetivos finitos, progreso visible, pantallas de cierre y botones para continuar. El juego previo ahora termina por objetivos o por el límite de cinco minutos; no impone esperar ni repetir para completar tiempo.

También se añadió cierre explícito del taller cuando las seis habilidades alcanzan el criterio de dominio. Antes volvía a seleccionar una habilidad sin avisar que la ruta estaba completa. Ahora la pantalla final conserva el progreso y ofrece práctica adicional voluntaria.

- Prueba 12: rescatar todas las criaturas, terminar las conexiones, crear el jardín y entrar al taller, sin avanzar el reloj; recargas intermedias sin repetir objetivos.
- Prueba 13: cargar una partida del formato anterior con aciertos repetidos, recuperar las criaturas rescatadas y mostrar la salida a la estación.
- Prueba 14: jugar el recorrido completo con reloj real, sin inyectar estado ni usar reloj virtual. Incluye errores en refugio, antena y fracciones; formato inválido; ayuda manipulativa; pausa; descanso; recargas; resolución de las seis habilidades; pantalla final; cuestionario familiar; exportación JSON y verificación del progreso final y de identificadores de evento únicos.

Evidencias: `output/playwright/refuge-completed.png`, `full-game-completed.png`, `full-game-telemetry.json` y las trazas de cada prueba. Los tiempos muy cortos del recorrido automático reflejan la velocidad de Playwright; no son estimaciones de duración ni mediciones con niños.

Resultado de esta revisión: **14 pruebas de navegador aprobadas y 16 pruebas del motor/flujo aprobadas**. La batería completa de navegador terminó en 71.121 segundos, incluyendo la partida completa con reloj real y las regresiones del bucle reportado.

Excepciones controladas: una prueba simula una API de voz no disponible para comprobar su alternativa escrita; las pruebas de visibilidad en DOM simulado se mantienen separadas de las pruebas de Chrome. El navegador usado para las capturas tiene movimiento reducido. No se ha verificado el sonido percibido en altavoces ni el comportamiento en Safari/iOS.

## Problemas encontrados y corregidos

| Problema observado | Consecuencia para el niño | Cambio realizado |
|---|---|---|
| Pedir una pista borraba la respuesta escrita | Pérdida de trabajo y frustración | Borrador por tarea, conservado al cambiar ayudas y recargar. |
| Cambiar representación borraba piezas manipuladas | Impedía explorar y comparar estrategias | Estado de piezas por tarea, conservado entre representaciones y recargas. |
| Elegir criatura con Enter enviaba el foco al cuerpo de la página | Navegación por teclado desorientada | Restauración del foco en el control correspondiente, sin desplazar la pantalla. |
| La comprobación de voz aceptaba una API indefinida | Excepción JavaScript al solicitar audio | Comprobar capacidad real de síntesis y mostrar la misma pista por escrito. |
| «Criaturas» dibujadas solamente como símbolos | El texto no coincidía con lo representado | Personajes vegetales con señal en el cuerpo, y refugios con la misma señal. |
| El icono del rombo parecía cuatro figuras | Ambigüedad de reconocimiento | Un solo rombo SVG, consistente en objetivo, personaje, refugio y antena. |
| Instrucciones principales debajo del juego en móvil | El niño veía controles antes de saber qué hacer | Consigna breve antes del área de juego; feedback móvil cercano y persistente al desplazarse. |
| Antena sin casillas y con un símbolo vacío ambiguo | No quedaba claro qué faltaba ni cómo terminar | Casillas explícitas, dirección de lectura y mensaje para enviar la señal. |
| Portada con lema abstracto y demasiado largo | Ocultaba el propósito de la actividad | «Despierta Isla Luma» y descripción concreta de la misión. |
| Mesa de piezas sin forma de enviar una respuesta | Manipular era accesorio; escribir era obligatorio | «Responder con mis piezas», con comprobación matemática y marca de respuesta asistida. |
| Explorar todos los lugares no permitía continuar | Espera innecesaria en el mapa | Lugares visitados marcados y opción de entrar antes al invernadero; el total sigue siendo 300 segundos activos. |

## Evaluación de comprensión, imágenes e interacción

- **Inicio:** la misión y la acción principal ahora son explícitas. La ilustración muestra los lugares que se visitarán y usa la misma estética que los personajes.
- **Refugios:** el objetivo, las opciones y los destinos comparten una señal reconocible. Los nombres acompañan a las figuras; el color no es el único código. Se distingue selección actual de respuesta correcta.
- **Antena:** la referencia permanece visible. Las flechas señalan el orden; las casillas representan el trabajo del niño. «Deshacer» se desactiva si no hay nada que retirar. La tarea observa interacción con una referencia; no debe presentarse como medición validada de memoria.
- **Jardín:** las plantas son controles con etiquetas accesibles y la ausencia de respuesta correcta se explica. Persisten emojis decorativos de plantas; su apariencia puede variar según el sistema. No se usan como única evidencia diagnóstica.
- **Fracciones:** todas las barras fuente tienen la misma longitud total. Se aclara que una barra completa es un entero; el numerador coloreado y la subdivisión corresponden a las cantidades. El espacio manipulativo permite construir la respuesta sin escribir una barra diagonal.
- **Interacción:** controles de criatura/refugio mayores de 44 × 44 píxeles en pantalla de 320 px; texto de ayudas ampliado. Ese tamaño es un criterio de esta revisión, no una certificación global de accesibilidad. No se hizo una auditoría WCAG completa.
- **Persistencia y salida:** pausar, pedir ayuda y volver al taller conserva la tarea. El área familiar exporta el registro y puede cerrarse con Escape.

## Comparación con `educHiperpersonalizedC/docs/DISENO_MVP.md`

Se revisó íntegramente la alternativa, versión 0.1 del 16/09/2026. Solo se leyó ese archivo; los cambios se hicieron en el proyecto actual.

| Propuesta de la alternativa | Evaluación | Resultado en Isla Luma |
|---|---|---|
| Responder construyendo en fase concreta (§2.2) | Aporta una diferencia funcional respecto de solo ver dibujos | **Implementado:** envío de respuesta desde las piezas. |
| Medir permanencia en cada canal (§4.1) | Distingue un clic accidental de exposición sostenida | **Implementado:** `support_exposure`, duración activa, origen voluntario y causa de cierre. La duración no se transforma automáticamente en una etiqueta de aprendizaje. |
| Intentos numerados, fase CPA y herramienta (§7) | Mejora la interpretación de los registros | **Implementado:** `attemptNumber`, `cpaPhase`, `schemaVersion`, herramienta y pieza manipulada; `constructed_answer`. |
| Ruta real además de elección guiada/libre (§4.1) | Permite comparar preferencia declarada y conducta | **Complementado:** origen y destino de navegación, lugares visitados y avance solicitado por el niño. |
| Contextos cotidianos mexicanos (§3) | Puede dar significado a las operaciones | **Diseño siguiente:** encargos de huerto, cocina o feria dentro de Isla Luma. No se copiaron nombres, barrios ni supuestos de un piloto escolar. |
| Comparación, simplificación, impropias y problemas (§2) | Amplía la cobertura matemática | **Pendiente:** extender el banco y crear evidencia propia por habilidad. No se declara cubierto por tener suma/resta básica. |
| Cuatro barrios con distintas mecánicas (§5) | Aporta autonomía y variedad, pero es un alcance mayor | **Pendiente:** experiencias opcionales sobre habilidades comunes, sin encerrar al niño en un barrio asignado. |
| Motor conjunto sobre DAG (§6) | Es una propuesta de modelado más compleja | **Pendiente:** no se reemplazó un modelo probado por fórmulas sin calibrar. La independencia asumida y la propagación manual no equivalen, por sí solas, a una red bayesiana completa validada. |
| Piloto con códigos, eventos en servidor y panel (§11–12) | Relevante para varias familias y análisis longitudinal | **Pendiente para despliegue:** el prototipo sigue local, con un perfil por navegador. |
| Pre/post y retención (§10) | Permitiría medir aprendizaje además de interacción | **Diseño siguiente:** instrumentos separados del diagnóstico inicial, formas paralelas y análisis por habilidad. |

### Diferencias que no se copiaron

1. **Matemáticas en el play-test:** la alternativa presupone aritmética de 4.º ya dominada. Contradice la instrucción explícita de un juego previo sin matemáticas y el desconocimiento del nivel inicial. Se conservan los obstáculos de asociación y señales.
2. **Falla inducida:** fabricar un fracaso no permite distinguir limpiamente conocimiento, lectura, interfaz o reacción al error. Se registran errores espontáneos; si no aparecen, esa evidencia queda ausente.
3. **Ponderación 70/30:** difiere del 60/40 visible en la página 3 del PDF base. Se mantiene 60/40 cuando existe observación familiar completa, y provisionalidad cuando falta.
4. **Inactividad de 20 segundos:** difiere de los 45 segundos del PDF. Se mantiene el parámetro de referencia, registrado como heurística y no como umbral clínico.
5. **Audio obligatorio por perfil:** una preferencia observada no justifica activar sonido de forma permanente. El audio sigue siendo elegido por el niño y tiene alternativa escrita.
6. **Mínimo de ocho minutos y cierre duro:** son decisiones de la alternativa, no respuestas derivadas del diagnóstico. No se impone una permanencia mínima ni se interrumpe una respuesta por un temporizador.
7. **Nueve nodos:** el resumen de la alternativa dice nueve, pero la tabla enumera F0–F9, es decir, diez; uno se declara opcional. Hay que resolver la cuenta y el alcance antes de convertirla en criterios de aceptación.
8. **Estudiantes agrupados/escuela/fechas:** son supuestos de ese documento. Aquí permanece el uso autónomo en casa.

### Verificación de referencias externas

La propuesta de trabajar equivalencias y operaciones con denominadores distintos coincide con los contenidos de quinto y sexto de la **edición 2024** del Programa Sintético de Fase 5, especialmente su página impresa 49. La comparación/orden y los problemas contextualizados amplían la cobertura que aún falta en el prototipo. [Fuente primaria SEP](https://educacionbasica.sep.gob.mx/wp-content/uploads/2024/06/Programa_Sintetico_Fase_5.pdf).

El estudio original de mAMAS existe y estudió población británica de 8–13 años. Eso no valida automáticamente la traducción mexicana incluida como borrador en la alternativa. No se incorporó como instrumento validado ni se convirtió la telemetría en una escala de ansiedad. [Carey y colaboradores, artículo original](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2017.00011/full).

## Evidencia reproducible

Con `npm start` ejecutándose:

```powershell
npm test
npm run test:browser
```

Las pruebas de navegador cubren aventura completa, errores y ayudas, pausa manual, inactividad, Escape, recarga, cuestionario y descarga JSON, las seis habilidades de fracciones, conservación de borradores/piezas, teclado, pantallas estrechas, falta de voz, respuesta construida, duración de exposición y avance temprano desde el mapa. Se comprueba ausencia de excepciones JavaScript y de solicitudes de la página a servicios externos en los recorridos ensayados.

Capturas y trazas: `output/playwright/`. Las capturas iniciales que mostraban los problemas están en `output/playwright/before/`.

| Captura posterior | Qué revisar |
|---|---|
| `desktop-home.png` | Propósito y jerarquía de la portada |
| `desktop-refugio.png` | Correspondencia entre criatura, señal y refugio |
| `desktop-signal.png` | Casillas y orientación de la antena |
| `mobile-refugio.png` | Consigna antes de actuar en móvil |
| `mobile-math.png` | Piezas, entrada y ayudas |
| `constructed-answer.png` | Respuesta enviada sin escribir |
| `narrow-320.png` | Pantalla estrecha sin desbordamiento horizontal |

## Lo que todavía debe comprobarse con niños

La navegación es operable en los recorridos probados y se corrigieron ambigüedades visibles. **No se puede afirmar solo con Playwright que los niños entienden la actividad o que aprenden.**

Prioridades para una sesión observada:

1. Pedir al niño que empiece sin explicarle controles. Observar si identifica la misión y realiza la primera acción de cada escena por sí solo.
2. Comprobar si distingue la criatura objetivo de las opciones y puede explicar qué significan las casillas de la antena.
3. Detectar aburrimiento o repetición: las tareas del play-test podrían ser demasiado fáciles para algunos niños de 5.º/6.º. La ausencia de errores no debe producir conclusiones sobre tolerancia a la frustración.
4. Comprobar si entiende «entero», las partes iguales y la relación entre las piezas y la fracción escrita. La barra por sí sola no demuestra comprensión conceptual.
5. Ver si descubre y usa las ayudas del panel en móvil. La consigna está arriba, pero las ayudas aún requieren desplazamiento en pantallas cortas.
6. Probar audio en los dispositivos reales, y evaluar el comportamiento con lectura lenta, teclado, pantalla táctil y diferentes necesidades de acceso.
7. Ampliar el diagnóstico matemático para permitir avanzar con menos repeticiones cuando ya exista evidencia suficiente; ampliar el banco antes de sesiones repetidas.

La prioridad siguiente es contrastar las cuatro modalidades con niños y ajustar dificultad, variedad y comprensión con esas observaciones.

## Ampliación: cuatro perfiles jugables

Resultado final: **40 pruebas aprobadas**: 19 de motor/flujo, 14 de navegador general y 7 de perfiles. Últimas ejecuciones: batería general 67.250 s; perfiles 76.204 s. Los cuatro registros finales contienen las seis habilidades con el criterio de dominio alcanzado. Sin excepciones JavaScript ni solicitudes de la página a servicios externos en las pruebas de navegador.

Se implementaron Laboratorio de pasos, Estudio de mosaicos, Estación de ritmos y Ruta de energía. Comparten habilidades y criterio de dominio, con controles, representaciones y recompensas propios. No se presentan al niño como etiquetas de capacidad.

`tests/profiles_test.py` ejecuta siete pruebas adicionales en Chrome:

1. Recorrido estructurado completo mediante pasos, denominador y numerador.
2. Recorrido visual completo mediante pincel y casillas.
3. Recorrido auditivo completo mediante pulsos y reproducción opcional.
4. Recorrido explorador completo mediante cargar/devolver y entregar.
5. Cambio de modalidad con construcciones conservadas, sin reiniciar el reto ni duplicar recompensas.
6. Ausencia de Web Audio, respuesta por teclado y foco conservado.
7. Asignación automática desde elecciones observadas en retos distintos, al retirar la elección manual.

Cada recorrido comienza en una sesión limpia, resuelve refugios, antena y jardín, comete un error matemático, pide ayuda, recarga, pausa y completa las seis habilidades con nuevos intentos independientes. Calcula las respuestas leyendo los paneles visibles, sin consultar respuestas del motor ni inyectar perfiles o conocimiento. El reloj virtual permanece detenido: estas siete pruebas verifican funcionalidad, no duración. La prueba 14 de la batería general conserva su recorrido con reloj real.

Se revisaron capturas de cada modalidad en escritorio y móvil. Los controles se comprueban a 320 px sin desbordamiento horizontal. Resultado y salida se acercaron al constructor. La comprensión y eficacia requieren validación con niños reales.

Los archivos `profile-{estructurado,visual,auditivo,explorador}-telemetry.json` registran los cuatro cierres con `completionReason: mastery`. Capturas con los mismos prefijos y sufijos `desktop.png` y `mobile.png`; trazas ZIP por prueba.
