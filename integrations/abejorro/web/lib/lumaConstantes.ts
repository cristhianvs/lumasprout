/**
 * Identificadores exactos que emite el motor de LumaSprout.
 *
 * Estos valores son literales del motor de juego, no texto libre: nunca se
 * escriben "a mano" en un componente (regla del proyecto: no magic strings).
 */

export const LUMA_FASES = ['welcome', 'play', 'bridge', 'math', 'complete'] as const;
export type LumaFase = (typeof LUMA_FASES)[number];

export const LUMA_FASE_ETIQUETAS: Record<LumaFase, string> = {
  welcome: 'Bienvenida',
  play: 'Aventura',
  bridge: 'Puente',
  math: 'Taller de matemáticas',
  complete: 'Sesión terminada',
};

function esFaseConocida(valor: string): valor is LumaFase {
  return (LUMA_FASES as readonly string[]).includes(valor);
}

/** `fase` llega como texto libre en agregados (embudo_fases): se traduce si se reconoce, si no tal cual. */
export function formatFase(fase: string): string {
  return esFaseConocida(fase) ? LUMA_FASE_ETIQUETAS[fase] : fase;
}

export const LUMA_MOTIVOS_FINAL = ['mastery', 'break', 'bank_exhausted'] as const;
export type LumaMotivoFinal = (typeof LUMA_MOTIVOS_FINAL)[number];

export const LUMA_MOTIVO_FINAL_ETIQUETAS: Record<LumaMotivoFinal, string> = {
  mastery: 'Dominio alcanzado',
  break: 'Pausa',
  // "bank_exhausted" es un motivo distinto de "mastery" a proposito (api-luma): el juego se
  // quedo sin preguntas, NO implica que el nino domino el tema. No agrupar como "exito".
  bank_exhausted: 'Banco de preguntas agotado',
};

/** Igual que LUMA_MOTIVO_FINAL_ETIQUETAS, mas "sin_dato": la fase agregada de /panorama admite ese cuarto valor. */
export function formatMotivoCierreAgregado(motivo: LumaMotivoFinal | 'sin_dato'): string {
  return motivo === 'sin_dato' ? 'Sin dato' : LUMA_MOTIVO_FINAL_ETIQUETAS[motivo];
}

interface LumaEscenaDefinicion {
  indice: 0 | 1 | 2 | 3;
  etiqueta: string;
}

export const LUMA_ESCENAS: LumaEscenaDefinicion[] = [
  { indice: 0, etiqueta: 'EL DESPERTAR' },
  { indice: 1, etiqueta: 'EL INVERNADERO' },
  { indice: 2, etiqueta: 'LA ESTACION' },
  { indice: 3, etiqueta: 'EL JARDIN' },
];

/**
 * El id, nombre y prerrequisitos de cada habilidad ahora los da `progresion.habilidades`
 * del propio /resumen (confirmado por api-luma / team-lead): no se hardcodean aqui para
 * no arriesgar que la etiqueta local quede desincronizada de la que use el backend.
 * Este orden se usa solo como respaldo de ordenamiento si hiciera falta.
 */
export const LUMA_ORDEN_HABILIDADES_RESPALDO = [
  'meaning',
  'equivalent',
  'add_same',
  'sub_same',
  'add_diff',
  'sub_diff',
] as const;

/**
 * Nombres de respaldo, SOLO para vistas donde la API no manda `nombre` junto al id (por
 * ejemplo /historico: progresion_temporal y bayesiano_temporal solo traen `habilidad` como
 * id crudo). En la rejilla en vivo se sigue prefiriendo el `nombre` que da /resumen.
 */
const LUMA_HABILIDAD_ETIQUETAS_RESPALDO: Record<string, string> = {
  meaning: 'Partes de un entero',
  equivalent: 'Fracciones equivalentes',
  add_same: 'Sumar partes del mismo tamaño',
  sub_same: 'Restar partes del mismo tamaño',
  add_diff: 'Sumar con distintos denominadores',
  sub_diff: 'Restar con distintos denominadores',
};

/** Traduce un id de habilidad crudo cuando la API no acompaña su `nombre`; si no se reconoce, se muestra tal cual. */
export function formatHabilidadRespaldo(id: string): string {
  return LUMA_HABILIDAD_ETIQUETAS_RESPALDO[id] ?? id;
}

export const LUMA_ETAPAS_CPA = ['concrete', 'pictorial', 'abstract', 'transfer'] as const;
export type LumaEtapaCPA = (typeof LUMA_ETAPAS_CPA)[number];

export const LUMA_ETAPA_ETIQUETAS: Record<LumaEtapaCPA, string> = {
  concrete: 'Concreto',
  pictorial: 'Pictórico',
  abstract: 'Abstracto',
  transfer: 'Transferencia',
};

export const LUMA_ESTADOS_CASILLA = ['pendiente', 'en_curso', 'acreditada'] as const;
export type LumaEstadoCasilla = (typeof LUMA_ESTADOS_CASILLA)[number];

/** Estado visual usado solo cuando la API todavia no informa una casilla (nunca se inventa un "pendiente"). */
export const LUMA_ESTADO_CASILLA_SIN_DATO = 'sin_dato' as const;
export type LumaEstadoCasillaVisual = LumaEstadoCasilla | typeof LUMA_ESTADO_CASILLA_SIN_DATO;

export const LUMA_MODALIDADES = ['estructurado', 'visual', 'auditivo', 'explorador'] as const;
export type LumaModalidad = (typeof LUMA_MODALIDADES)[number];

export const LUMA_MODALIDAD_ETIQUETAS: Record<LumaModalidad, string> = {
  estructurado: 'Laboratorio de pasos',
  visual: 'Estudio de mosaicos',
  auditivo: 'Estación de ritmos',
  explorador: 'Ruta de energía',
};

function esModalidadConocida(valor: string): valor is LumaModalidad {
  return (LUMA_MODALIDADES as readonly string[]).includes(valor);
}

/** `experience` llega como texto libre (`string | null`) del backend: se traduce si se reconoce, si no se muestra tal cual. */
export function formatModalidad(experience: string | null): string {
  if (!experience) return 'Sin datos';
  return esModalidadConocida(experience) ? LUMA_MODALIDAD_ETIQUETAS[experience] : experience;
}

export const LUMA_RUTAS = ['guided', 'free'] as const;
export type LumaRuta = (typeof LUMA_RUTAS)[number];

export const LUMA_RUTA_ETIQUETAS: Record<LumaRuta, string> = {
  guided: 'Guiada',
  free: 'Libre',
};

/** Los 4 destinos que reporta `autonomia.destinos` (navegacion libre por el mapa). */
export const LUMA_DESTINOS_AUTONOMIA = ['map', 'greenhouse', 'station', 'garden'] as const;
export type LumaDestinoAutonomia = (typeof LUMA_DESTINOS_AUTONOMIA)[number];

export const LUMA_DESTINO_ETIQUETAS: Record<LumaDestinoAutonomia, string> = {
  map: 'Mapa',
  greenhouse: 'Invernadero',
  station: 'Estación',
  garden: 'Jardín',
};

/**
 * Valores de `reason` conocidos del motor de adaptacion. api-luma confirmo que el
 * campo es texto libre (no hay un enum en el backend), asi que un valor que no
 * aparezca aqui se muestra tal cual llega en lugar de fallar.
 */
export const LUMA_MOTIVOS_DECISION_CONOCIDOS = [
  'recent_errors_and_help',
  'simulation_gentle_pace',
  'standard_pace',
] as const;
export type LumaMotivoDecisionConocido = (typeof LUMA_MOTIVOS_DECISION_CONOCIDOS)[number];

export const LUMA_MOTIVO_DECISION_ETIQUETAS: Record<LumaMotivoDecisionConocido, string> = {
  recent_errors_and_help: 'Errores recientes y ayuda pedida',
  simulation_gentle_pace: 'Ritmo suave de simulación',
  standard_pace: 'Ritmo estándar',
};

function esMotivoDecisionConocido(valor: string): valor is LumaMotivoDecisionConocido {
  return (LUMA_MOTIVOS_DECISION_CONOCIDOS as readonly string[]).includes(valor);
}

/** Etiqueta legible de `reason` si es un motivo conocido; si no, el texto tal cual llego del backend. */
export function formatMotivoDecision(reason: string | null): string {
  if (!reason) return 'Sin motivo registrado';
  return esMotivoDecisionConocido(reason) ? LUMA_MOTIVO_DECISION_ETIQUETAS[reason] : reason;
}

/** Umbrales de la vista en vivo. No son datos clínicos, solo cadencia de refresco y avisos de frescura. */
export const LUMA_INTERVALO_SONDEO_DETALLE_MS = 3000;
export const LUMA_INTERVALO_SONDEO_LISTA_MS = 15000;
export const LUMA_LIMITE_EVENTOS_POR_SONDEO = 200;
export const LUMA_MAX_EVENTOS_RECIENTES_VISIBLES = 20;

/** El motor considera "jugando ahora" cuando hubo un latido en los ultimos 15 s (dato del propio backend). */
export const LUMA_UMBRAL_JUGANDO_SEGUNDOS = 15;
/** A partir de 30 s sin dato nuevo, la interfaz debe avisar visualmente que el dato envejece. */
export const LUMA_UMBRAL_DATO_ENVEJECIDO_SEGUNDOS = 30;
/**
 * Sin una respuesta exitosa de un endpoint en 4 ciclos de sondeo, esa mitad de la pantalla se
 * trata como incomunicada. El banner grande de "sin conexion" solo aparece cuando /eventos Y
 * /resumen llevan mas de esto sin responder: si uno de los dos sigue vivo, la sesion no esta
 * incomunicada, solo una zona de la pantalla esta desactualizada (ver umbral siguiente).
 */
export const LUMA_UMBRAL_SIN_CONEXION_SEGUNDOS = (LUMA_INTERVALO_SONDEO_DETALLE_MS / 1000) * 4;
/**
 * A partir de 2 ciclos de sondeo sin una respuesta exitosa de /resumen, se marca la zona de
 * indicadores/rejilla como "sin actualizar desde hace N s", aunque /eventos siga fluyendo con
 * normalidad. Mas corto que LUMA_UMBRAL_SIN_CONEXION_SEGUNDOS porque el objetivo aqui es avisar
 * rapido de que esa zona en particular quedo congelada, no declarar la sesion incomunicada.
 */
export const LUMA_UMBRAL_ZONA_DESACTUALIZADA_SEGUNDOS = (LUMA_INTERVALO_SONDEO_DETALLE_MS / 1000) * 2;
