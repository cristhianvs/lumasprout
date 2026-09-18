<p align="center"><img src="../assets/media/hero.png" alt="LumaSprout: cada siguiente paso tiene una razón" width="100%"></p>

# LumaSprout

**Una aventura de aprendizaje con adaptación explicable.** Explora Isla Luma, juega con fracciones y observa cómo las interacciones cambian el siguiente reto. Buscamos desarrolladores, diseñadores, docentes e investigadores que quieran construirla con nosotros.

[Probar la demo](https://cristhianvs.github.io/lumasprout/) · [Contribuir](../CONTRIBUTING.md) · [English](../README.md)

![Interacciones reales del juego](../assets/media/gameplay.gif)

## Qué puedes explorar

- Cuatro formas de jugar: pasos ordenados, mosaicos, ritmos y exploración.
- Seis habilidades de fracciones, con progresión concreto → pictórico → abstracto → problema contextual.
- Ayudas que no acreditan autonomía y una nueva oportunidad independiente después del apoyo.
- Telemetría local que enlaza señales, decisiones y respuestas; tablero de simulación e importación/exportación.
- JavaScript, HTML y CSS, sin dependencias de ejecución ni claves de API.

## Empezar

Con Node.js 22.13 o posterior:

```sh
git clone https://github.com/cristhianvs/lumasprout.git
cd lumasprout
npm start
```

Abre http://127.0.0.1:4173. El tablero está en http://127.0.0.1:4173/admin.html. No necesitas `npm install` para ejecutar la aplicación. Usa `npm test` para comprobar el motor y el flujo.

La demo pública usa una partida de simulación separada. El juego conserva los eventos en tu navegador y no los envía a un servidor. El sitio público está alojado en GitHub Pages. **Familias → Registro y adaptación** permite exportar explícitamente. Usa perfiles de navegador separados para diferentes jugadores.

## Lo comprobado y lo pendiente

La validación del 17 de septiembre de 2026 incluye **36 recorridos Playwright y 67 comprobaciones adicionales**: 15 467 eventos y 856 intentos matemáticos sintéticos. No participaron niños. La preferencia de modalidad no es un diagnóstico ni una garantía de aprendizaje; la telemetría no permite inferir ansiedad. [Detalle de evidencia](EVIDENCE.md).

Faltan revisión docente, evaluación externa y piloto observado. Precisamente por eso abrimos el proyecto: queremos mejorar el contenido, la accesibilidad y la calidad de las decisiones antes de afirmar resultados educativos.

## Únete al taller

Revisa las [tareas iniciales](ROADMAP.md#starter-tasks) y la [guía para contribuir](../CONTRIBUTING.md). Hay espacio para mejoras pequeñas: accesibilidad, traducción, tareas matemáticas, contratos de telemetría o documentación reproducible. Se aceptan aportaciones en español e inglés.

Licencia [MIT](../LICENSE) para el código y los recursos originales. Creado por [Cristhian Velazco](https://github.com/cristhianvs).

[Version history / Historial de versiones — v0.3.0](../CHANGELOG.md)

## Novedades de v0.3.0

- Telemetría remota opcional, desactivada por defecto; simulaciones excluidas, destinos autorizados, reintentos y confirmación de recepción.
- [Código del panel y la API de Luma](../integrations/abejorro/README.md), como módulos de integración con un host. No es un backend autónomo ni una publicación automática en Hetzner.
- Panel rediseñado con fechas legibles, colores diferenciados y errores de conexión explicados. [Vista previa con datos sintéticos](../assets/media/remote-dashboard-preview.png).
- [Cuestionario infantil IL-EXP-0.2](questionnaires/README.md), rellenable y con preguntas sobre la aventura inicial.

Panorama reúne las partidas. Participante sigue un runId; eso no garantiza identificar al mismo niño entre dispositivos. La telemetría no mide directamente emociones. [Contrato y límites](TELEMETRY.md).
