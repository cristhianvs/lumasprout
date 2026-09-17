# Laboratorio de Isla Luma

Implementado y probado el 17 de septiembre de 2026.

## Validación completa mediante interfaz: actualización posterior

El laboratorio de este documento reproduce estados sintéticos. Posteriormente se ejecutó una matriz independiente de **36 recorridos completos por Playwright**, sin inyectar estados ni telemetría: cuatro preferencias por nueve comportamientos. Se leen los eventos generados por los controles después de cada respuesta y transición.

Resultado: 36 aprobados; 32 cierres por dominio de las seis habilidades según el motor y cuatro por descanso con ayuda permanente, sin evidencias independientes. La matriz emplea reloj virtual; la suite general también se volvió a ejecutar e incluye un recorrido con reloj real. No participaron niños.

Se corrigieron dos problemas detectados por esta ejecución: la alternativa escrita del audio ausente no marcaba asistencia; una recarga perdía la latencia activa del intento. Pruebas de regresión ejecutadas: 35 Node, 14 generales, 7 modalidades y 5 laboratorio (61 adicionales a la matriz).

Reporte PDF de ocho páginas: `output/pdf/Isla_Luma_Reporte_Simulacion_Playwright.pdf`. Datos, aserciones, capturas y trazas: `output/behavior-matrix/`. Ejecutar `python -X utf8 tests/behavior_matrix.py --profile estructurado`, cambiando el perfil por visual, auditivo y explorador para completar las cuatro series. El script exporta desde Familias e importa cada registro en el tablero, sin usar el simulador de estados descrito abajo.

Las secciones siguientes documentan el laboratorio y su validación original; no deben confundirse con esta matriz de interacción.

## Uso

1. Ejecutar `npm start` si el servidor no está activo.
2. Abrir `http://127.0.0.1:4173/admin.html` en el mismo navegador que la partida que se desea consultar.
3. Pulsar **Ejecutar los 12** para revisar el lote. Elegir un escenario y pulsar **Ejecutar escenario** para recorrer su historial.
4. Usar el deslizador o **Paso siguiente**. **Probar este punto en el juego** carga esa fotografía de telemetría y conocimiento en la aplicación real. A partir de ahí, la persona que prueba responde con los controles del juego; no hay un bot contestando dentro de la vista.
5. Para empezar por un caso informativo, elegir **Dificultad acumulada y recuperación**, avanzar al paso 2 y abrir la vista jugable: aparece apoyo concreto. Comparar con un paso posterior a la recuperación.
6. Cambiar **Ritmo de prueba** y volver a ejecutar para comparar descansos a los 4 minutos activos frente a la política habitual de 8 minutos, reducida a 4 ante señales acumuladas. No hay tiempo límite para responder.
7. Exportar el resultado JSON. Contiene el estado consultado, el recorrido sintético y, si se ejecutó, el lote. La importación admite tanto este formato como las exportaciones de Familias; consulta el estado, sin restaurarlo sobre una partida.

**Partida local · solo lectura** actualiza los indicadores cada 2 segundos. Para observar juego en curso, mantener abierta la isla en otra pestaña del mismo navegador y origen. No hay conexión con otros equipos ni panel central de participantes.

## Escenarios y comprobaciones

| Escenario | Entradas sintéticas | Resultado esperado |
|---|---|---|
| Estructurado | Preferencias de ruta guiada y aciertos independientes | Laboratorio de pasos; progresión por prerrequisitos |
| Visual | Elecciones de apoyo visual y aciertos | Estudio de mosaicos |
| Auditivo | Elecciones de apoyo auditivo y aciertos | Estación de ritmos |
| Explorador | Preferencias de ruta libre y aciertos | Ruta de energía |
| Dificultad y recuperación | Tres retos iniciales con error, ayuda y reintento, luego aciertos | Apoyo concreto temporal; nuevos intentos independientes tras recuperación |
| Lectura lenta | 70 segundos activos por respuesta correcta | No atribuir ansiedad ni activar apoyo concreto solo por lentitud |
| Interrupciones | Inactividad, visibilidad y regreso | Señalar interrupción; no penalizar conocimiento |
| Preferencias mixtas | Evidencia repartida entre modalidades | Dominante desconocido; modalidad inicial estructurada |
| Desacuerdo familiar | Conducta visual y vector familiar auditivo | Empate 45/45; no forzar dominante |
| Elección explícita | Conducta visual y elección exploradora | Respetar elección del jugador |
| Respuestas asistidas | Aciertos con ayuda | Cero evidencias independientes; sin dominio acreditado |
| Sin audio | Preferencia auditiva y disponibilidad de audio desactivada en la vista de prueba | Modalidad auditiva con alternativa visual funcional |

El simulador utiliza el motor compartido para inferencia, clasificación de respuestas, conocimiento, prerrequisitos y política. No asigna directamente `profile.dominant` ni probabilidades finales. Genera un historial de preferencias en contextos sintéticos y calcula conocimiento a partir de intentos. Las fotografías permiten probar cómo consume ese historial la aplicación.

Los guiones son deterministas. La fase previa se resume en un historial artificial de preferencias; no reproduce cada clic ni demuestra que esa secuencia exacta pueda ocurrir en una única aventura previa. Las pausas se representan mediante eventos y las latencias son tiempo activo sintético. Lectura lenta supone actividad durante la lectura; no equivale a 70 segundos sin interacción, que activarían la pausa de inactividad de la aplicación. Los recorridos de navegador existentes sí juegan las misiones mediante controles reales.

## Indicadores y circuito

- Preferencias: puntuaciones provisionales del motor, observaciones y modalidad aplicada. La elección explícita tiene prioridad; no cambia la modalidad a mitad de un reto.
- Conocimiento: probabilidad heurística, número de evidencias independientes y habilidades dominadas. La selección del contenido sigue prerrequisitos; una preferencia no acredita conocimiento.
- Participación: intentos e interrupciones observados. No es una escala validada de enganche.
- Necesidad de apoyo: errores y peticiones de ayuda en los últimos 120 segundos activos de la fase actual, hasta 20 eventos relevantes. Cuatro señales acumuladas activan política de apoyo concreto y descanso más temprano. Se conservan además las ayudas inmediatas existentes por tres fallos y peticiones repetidas.
- Ansiedad: **no inferible**. No se calcula una puntuación clínica ni se etiqueta al niño.
- Cada reto nuevo registra `adaptation_decision` con señales, motivo, habilidad, modalidad y política. El apoyo concreto al inicio marca la respuesta como asistida. Al desaparecer señales recientes, el próximo reto puede volver al apoyo visual; el reto ya abierto conserva su estado.
- `blockMs` continúa siendo un campo de política sugerida; el control efectivo de descanso usa `breakAfterMs`. No hay transición automática cada 60/90 segundos.

## Persistencia y alcance de los controles

Se conserva `CONFIG.version` y `isla-luma-v1`. La vista `/?simulation=1` usa exclusivamente `isla-luma-simulation-v1`; sus eventos llevan `simulation: true`. Ejecutar otro punto reemplaza la partida de simulación. La partida existente se conserva. Usar un solo laboratorio a la vez por navegador: la clave sintética es compartida entre pestañas.

Los controles de ritmo solo afectan simulaciones. No existe control remoto para modificar una sesión infantil en curso. El tablero local no incorpora autenticación, cuentas, sincronización ni agregación de familias. Las importaciones son de solo lectura, con límite de 20 MB y validación básica de estructura.

## Validación ejecutada

El 17 de septiembre de 2026, Windows, Node y Chrome real mediante Python Playwright, en contextos aislados:

- `npm test`: **33 pruebas aprobadas**; incluye los 12 escenarios con ambos ritmos, determinismo, caducidad de señales y separación de fases.
- `npm run simulate`: **12 escenarios aprobados**; JSON por escenario y resumen en `output/simulations/`. Once terminan con seis habilidades dominadas; el de ayuda permanente conserva cero evidencias independientes, como corresponde al guion.
- `python -X utf8 tests/browser_test.py`: **14 pruebas aprobadas**, 69.057 s; incluye recorrido completo con reloj real, errores, ayuda y cierre.
- `python -X utf8 tests/profiles_test.py`: **7 pruebas aprobadas**, 69.418 s; cuatro recorridos completos y regresiones de modalidades.
- `python -X utf8 tests/laboratory_test.py`: **5 pruebas aprobadas**: vista jugable de los 12 escenarios; apoyo, recarga y recuperación; lote, exportación/importación; audio ausente y elección explícita; presentación móvil. Todas comprueban que la clave de la partida existente queda intacta y que no hay excepciones JavaScript.
- Inspección visual de capturas de escritorio y móvil del laboratorio. Se corrigió el desbordamiento del selector en móvil y se ajustaron las tarjetas para pantallas estrechas.

Capturas: `output/simulations/laboratory-desktop.png`, `laboratory-mobile.png`, `laboratory-preview.png`. Exportación probada: `laboratory-export.json`.

Estas pruebas comprueban reglas y funcionamiento técnico. No son observaciones con niños, validación de ansiedad/enganche, ni evidencia de aprendizaje. Queda pendiente calibración con observación real, variabilidad de dispositivos y conductas no contempladas por los guiones.
