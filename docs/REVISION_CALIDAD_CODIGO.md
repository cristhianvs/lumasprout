# Revisión de calidad de código — LumaSprout

> Revisión inicial conservada como historial. Las correcciones posteriores y sus límites se documentan en [CORRECCIONES_CALIDAD.md](CORRECCIONES_CALIDAD.md); los P1 descritos aquí ya tienen correcciones y regresiones permanentes.

Fecha: 17 de septiembre de 2026. Base revisada: commit `9d837c7`, más documentación local de continuidad. Revisión de implementación, no certificación de cumplimiento ni auditoría exhaustiva de seguridad. No se modificó código de ejecución ni se desplegaron cambios.

## Dictamen

**Cumplimiento parcial.** El motor separado, las pruebas y la ausencia de dependencias de ejecución son buenas bases. No se puede afirmar que el proyecto cumple completamente Clean Code/SOLID/DRY ni que esté libre de hardcoding. Se encontraron dos defectos funcionales reproducibles y deuda de diseño que debe corregirse antes de seguir ampliando reglas.

| Criterio | Evaluación razonada |
|---|---|
| Clean Code | Parcial: nombres útiles en el motor, pero fuentes comprimidas, funciones con responsabilidades mixtas y estado compartido. |
| S — Responsabilidad única | Débil en app y administrador: presentación, eventos, decisiones, persistencia y audio comparten módulos y estado. |
| O — Abierto/cerrado | Parcial: añadir modalidades exige modificar varios condicionales y catálogos dispersos; no hay contrato de extensión. |
| L — Sustitución de Liskov | Sin jerarquías de subtipos relevantes que permitan una evaluación directa. No usar ausencia de clases como incumplimiento ni como prueba de cumplimiento. |
| I — Segregación de interfaces | No hay interfaces formales que permitan concluir una violación concreta. Conviene limitar las dependencias de cada consumidor al separar módulos. |
| D — Inversión de dependencias | El motor reduce dependencia del DOM; la aplicación depende directamente de window, localStorage, relojes y audio, sin adaptadores inyectables. |
| KISS | Buena sencillez de despliegue; complejidad interna innecesaria por mezcla de responsabilidades y estado duplicado. |
| DRY | Parcial: reglas de finalización, selección y ventanas están dispersas, con diferencias ya visibles entre componentes. |
| Configuración/hardcoding | Existe CONFIG, pero parámetros de adaptación, denominadores de UI, rutas de herramientas y cifras de reportes siguen embebidos. |

## Hallazgos, en orden de prioridad

### 1. P1 — Los eventos históricos no son fotografías inmutables

**Ubicaciones:** `app.js:23`, `app.js:151`, `engine.js:128`.

`log()` conserva `data` por referencia. `decision_evaluated` recibe `learning: state.learning.skills[t.id]`; luego `recordLearning()` modifica ese mismo objeto y sus listas. Un resultado anterior puede mostrar etapas obtenidas después de su emisión. La serialización de cada guardado no elimina la referencia compartida que sigue en memoria; una recarga puede además cambiar cómo se manifiesta el problema al reconstruir objetos independientes.

**Reproducción ejecutada:** se ejecutó la función `log()` real de app.js en una VM aislada, con persistencia sustituida por una función vacía. Un evento emitido con `passed: ['concrete']` pasó a contener `['concrete', 'pictorial']` después de actualizar el aprendizaje, sin volver a emitir ese evento.

**Impacto:** compromete la interpretación temporal de la telemetría, base del circuito de retroalimentación.

**Corrección propuesta:** crear un snapshot independiente del payload al emitir; definir el contrato de evento y validar los tipos serializables. Prueba de regresión: modificar el estado tras emitir y verificar que el evento anterior, tanto en memoria como exportado, permanece idéntico. Congelar superficialmente el objeto exterior no basta para proteger listas anidadas.

### 2. P1 — Agotar variantes de transferencia puede bloquear el avance

**Ubicaciones:** `engine.js:95`, `engine.js:115`, `engine.js:125`, `engine.js:128`.

Equivalencias usa numerador `1 + serial % 3`, denominadores 4/8 y contexto según `serial % 3`. Solo produce tres combinaciones de transferencia distintas. Cada variante queda marcada como vista incluso con asistencia; para acreditar transferencia se exige `novel` y no existe una política de agotamiento.

**Reproducción ejecutada:** con las tres etapas anteriores cubiertas, se resolvieron las tres variantes de transferencia con ayuda. Después se simularon 30 respuestas correctas independientes: cero tareas nuevas y transferencia sin completar, aunque el criterio bayesiano sí se cumplía. La periodicidad de tres explica por qué esperar más rondas no introduce una variante diferente.

**Impacto:** un usuario que necesitó ayuda en esas tres oportunidades puede quedar bloqueado en esa habilidad. Es una reproducción del motor, no una sesión observada con niños ni una nueva prueba de interfaz.

**Corrección propuesta:** separar generación, historial y selección de evidencia; disponer de alternativas suficientes y una política explícita de banco agotado. No resolverlo fingiendo novedad ni cambiando solo el ID de una tarea idéntica. La salida pedagógica debe preservar la distinción entre repetición, independencia y transferencia.

### 3. P2 — Definiciones distintas de «dominio» entre juego y tablero

**Ubicaciones:** `app.js:292`, `admin.js:13`, `admin.js:15`, `admin.js:18`, `simulation.js:29`, `simulation.js:35`.

El juego actual cierra mediante `learningComplete`, que exige cobertura pedagógica. Los indicadores principales del administrador y el simulador histórico siguen usando `mastered`, basado en probabilidad y número de observaciones. Por ejemplo, tres aciertos pueden satisfacer el indicador bayesiano mientras la transferencia todavía está pendiente. El tablero sí añade una tabla CPA separada, pero sus etiquetas principales no distinguen con suficiente precisión esos dos criterios.

El simulador anterior está conservado por compatibilidad; eso no convierte sus cierres en validación de la política actual. **Recomendación:** exponer un resumen de progreso común con campos separados para estimación bayesiana, cobertura CPA, transferencia y cierre; etiquetar explícitamente la versión de cada simulador. No eliminar compatibilidad de registros.

### 4. P2 — La aplicación concentra responsabilidades y duplica estado

**Ubicaciones:** `app.js:13`, `app.js:22`, `app.js:87`, `app.js:144`, `app.js:157`, `app.js:209`, `app.js:260`.

El mismo módulo gestiona DOM/HTML, audio, tiempos, persistencia, telemetría, apoyo adaptativo, respuestas y recompensas. `submitMath()` evalúa, modifica conocimiento, registra eventos, cambia progreso, recompensa y renderiza. Variables como `assisted`, `solved` y `firstAttempt` existen además dentro de `state.current` y se sincronizan en `save()`/restauración.

**Impacto:** añadir una modalidad o tocar una transición requiere conocer efectos de otras responsabilidades; aumenta el riesgo de desincronizar guardado, UI y eventos. El motor separado es una base útil, pero no resuelve esa concentración.

**Recomendación:** extraer por responsabilidad y por etapas: estado/transiciones, registro de eventos, repositorio de partidas, adaptación y renderizado por modalidad. Inyectar almacenamiento, reloj y audio mediante funciones pequeñas; no introducir un framework de inyección o jerarquías de clases innecesarias.

### 5. P2 — Configuración parcial y reglas de señales dispersas

**Ubicaciones:** `engine.js:3`, `engine.js:29`, `engine.js:67`, `engine.js:69`, `engine.js:72`, `engine.js:87`, `app.js:32`, `app.js:117`, `app.js:136`, `app.js:246`.

Hay constantes con nombre en CONFIG, pero pesos 60/40, umbral .06, tamaño de historial, ventanas de señales, probabilidades y duraciones se escriben dentro de funciones. El motor calcula su ventana y la aplicación vuelve a reconstruirla para registrar IDs de evidencia. Otra política de apoyo usa su propia ventana y umbrales en la UI. Además `renderMath()` utiliza `failures >= 3` aunque existe `CONFIG.failures`.

**Impacto:** cambiar una regla puede dejar incoherentes la decisión, su explicación y los eventos usados para justificarla.

**Recomendación:** política versionada con parámetros semánticos e identificadores de regla; que la evaluación devuelva tanto la decisión como sus señales. Mantener diferenciadas reglas distintas: dos valores iguales de 120 s no necesariamente representan el mismo concepto. Esta revisión no propone recalibrar sus valores sin evidencia humana.

### 6. P2 — La UI fija octavos aunque el modelo declara targetDen

**Ubicaciones:** `app.js:129`, `app.js:135`, `app.js:152`, `app.js:164`, `engine.js:95`.

El dibujo vacío usa `[0,8]`, la ecuación muestra `?/8`, la etiqueta exige denominador 8 y el mensaje habla de octavos. `targetDen` ya existe en la tarea, pero no dirige esos textos y dibujos. El selector de denominadores tiene además una lista fija independiente del banco.

**Impacto:** ampliar equivalencias en el motor no basta; podría generarse un reto válido con interfaz contradictoria. El banco actual todavía usa 8, por lo que esta es una restricción de extensión comprobada por lectura, no un fallo de una tarea actual con otro denominador.

**Recomendación:** renderizar a partir de los datos de la tarea y un catálogo de textos/unidades, con pruebas de un denominador diferente. Separar contenido de presentación facilitaría también traducciones.

### 7. P2 — Persistencia completa y síncrona en cada evento

**Ubicaciones:** `app.js:22`, `app.js:23`, `app.js:308`.

Cada `log()` vuelve a serializar y guardar toda la partida, incluido un historial que crece. También existen guardados periódicos. `localStorage` es síncrono. Un fallo se captura en `storageError`, cuyo aviso aparece en el panel Familias.

**Impacto potencial:** el coste por evento crece con el historial y pueden producirse fallos de cuota. No se midió latencia ni se reprodujo agotamiento de almacenamiento en esta auditoría; no se afirma que ya ocurra en las sesiones habituales.

**Recomendación:** separar eventos de snapshots de partida, definir lotes y puntos de persistencia, y probar recuperación ante cuota/error. Diseñar retención/exportación antes de descartar datos; no truncar telemetría silenciosamente.

### 8. P2/P3 — Legibilidad, portabilidad y evidencia automática mejorables

**Ubicaciones:** `app.js`, `admin.js`, `styles.css:1`, `site/site.css:1`, `tests/build_pedagogy_report.py:24`, `tests/build_pedagogy_report.py:26`, `tests/browser_test.py:17`, `.github/workflows/ci.yml:16`.

- `app.js`: 58 032 caracteres, 48 líneas de más de 300 caracteres; línea máxima de 2 829. `admin.js`: línea máxima de 1 143. `styles.css` concentra 9 335 caracteres en una línea. Estas medidas no son complejidad ciclomática, pero evidencian una fuente difícil de revisar y comparar.
- No hay comandos de lint/formato en package.json; CI ejecuta pruebas Node, construcción y comprobación sintáctica. No ejecuta los recorridos de navegador ni comprueba convenciones de estilo.
- Los generadores PDF fijan rutas de fuentes `C:/Windows/Fonts/...`; las herramientas de navegador fijan Chrome y frecuentemente localhost:4173. Son dependencias de entorno documentadas, pero limitan portabilidad y ejecución paralela.
- `build_pedagogy_report.py` comprueba que las 36 filas de la matriz pasaron, pero incrusta los recuentos 38/14/7/3/5 de otras suites y textos de «67 pruebas». Esas cifras corresponden a una ejecución previa real; volver a generar un informe no verifica automáticamente que las regresiones se ejecutaron otra vez.

**Recomendación:** formatear en un cambio separado, añadir lint/formato verificables, configurar entorno de herramientas con defaults y consumir resultados fechados de cada suite para generar informes. P2 para integridad de reportes; P3 para formato y conveniencia de portabilidad.

## Qué conviene conservar

- Motor matemático independiente de la vista, comprobable desde Node.
- Pocas dependencias y arranque sencillo: KISS no exige un framework nuevo.
- Separación de ayudas e independencia, compatibilidad y registro explícito de simulaciones.
- Oráculos independientes en pruebas de matemáticas y telemetría: repetir una fórmula para verificarla por otra vía no es necesariamente duplicación que deba eliminarse. Importar la misma implementación como resultado esperado puede debilitar las pruebas.
- Catálogos, identificadores estables, valores matemáticos, colores, puertos predeterminados y versiones fijadas son constantes legítimas cuando están bien ubicadas. «Cero literales» no es un objetivo de calidad.

## Validación realizada en esta revisión

- Lectura de motor, aplicación, administrador, simulador, servidor, build, workflows y herramientas/pruebas relevantes.
- `npm test`: **38/38 aprobadas**. No garantiza cobertura de todos los comportamientos ni cumplimiento arquitectónico.
- `node tmp/review-audit.cjs`: reproducciones aisladas de mutación histórica y agotamiento de variantes; resultados en `output/code-review/reproduction.json`.
- No se reejecutó la matriz Playwright ni se observaron participantes. No se ejecutaron analizadores de complejidad, una auditoría de seguridad exhaustiva ni pruebas de rendimiento.
- No se aplicaron refactorizaciones, correcciones de runtime, commit o publicación en esta tarea. Los dos P1 siguen pendientes.

## Secuencia recomendada de corrección

1. Agregar regresiones permanentes y corregir los dos P1, con eventos inmutables y política de agotamiento revisable.
2. Unificar el resumen de progreso y la evaluación de señales, preservando compatibilidad y significado de los eventos.
3. Separar persistencia/telemetría/transiciones de la UI; introducir adaptadores pequeños y una fuente única de estado.
4. Hacer que la presentación use los datos de la tarea y concentrar configuración por responsabilidad.
5. Formatear, añadir lint y ampliar CI con pruebas seleccionadas de navegador; hacer que los reportes lean resultados de ejecución.

Aplicar cambios pequeños con pruebas de equivalencia y migración. No reescribir todo el proyecto ni cambiar reglas pedagógicas bajo la etiqueta de «refactorización».
