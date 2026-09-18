import { adminRequest } from './hostAdminRequest';
import type { ApiResponse } from './http-client';

interface LumaSesion {
  run_id: string;
  /** Verificado contra la API real: viene null cuando el jugador todavia no tiene codigo asignado. */
  participante_codigo: string | null;
  version: string;
  total_eventos: number;
  primer_evento_at: string;
  ultimo_evento_at: string;
  ultima_recepcion_at: string;
  antiguedad_segundos: number;
}

interface LumaEvento {
  id: string;
  evento_id: string;
  secuencia: number;
  /** El "type" del envoltorio tal cual llega, sin whitelist: hay ademas de los conocidos otros ~50 tipos sin catalogar. */
  tipo: string;
  /** Reloj del cliente (el juego). */
  at_cliente: string;
  /** Reloj del servidor (cuando el lote llego a la API); es el que usa el backend para "heartbeat_reciente". */
  recibido_at: string;
  phase: string | null;
  scene: number | null;
  task: string | null;
  experience: string | null;
  play_ms: number | null;
  math_ms: number | null;
  /** El envoltorio completo tal cual lo mando el juego, por si hace falta un campo no desnormalizado arriba. */
  data: Record<string, unknown>;
}

interface LumaEventosSalida {
  eventos: LumaEvento[];
  /** El `secuencia` mas alto devuelto, o el `desde` enviado si no vino ningun evento nuevo. */
  ultimo_indice: number;
}

interface LumaEstadoActual {
  phase: string | null;
  scene: number | null;
  task: string | null;
  experience: string | null;
  heartbeat_reciente: boolean;
  /** Texto de advertencia fijo del backend: el juego solo late cada 5 s cuando esta activo, asi que su ausencia no implica inactividad del nino. */
  limite_heartbeat: string;
  /**
   * Solo trae valor cuando `phase` es "complete"; en cualquier otro momento es null y eso
   * es normal ("todavia no termino"), no un hueco. Si phase SI es "complete" y aun asi es
   * null, significa "termino sin evidencia clara de motivo" (tampoco es un error).
   * `bank_exhausted` es un motivo distinto de `mastery` a proposito: no implica dominio.
   */
  motivo_final: 'mastery' | 'break' | 'bank_exhausted' | null;
}

interface LumaConteoPorTipo {
  tipo: string;
  cantidad: number;
}

interface LumaIntentos {
  total: number;
  aciertos_primer_intento_sin_ayuda: number;
  reintentos: number;
  asistidos: number;
  /** Verificado contra la API real: resuelto sin ayuda, con o sin reintentos (distinto de "1er intento"). */
  resueltos_independientes: number;
  /** Texto de advertencia fijo del backend (no un numero): no se debe fabricar una latencia promedio. */
  limite_latencia: string;
}

interface LumaAyuda {
  hint_requested: number;
  apoyo_voluntario: number;
  apoyo_impuesto: number;
}

interface LumaPausa {
  inicio_at: string | null;
  fin_at: string | null;
  duracion_ms: number | null;
}

interface LumaInactividad {
  idle_started: number;
  pausas: LumaPausa[];
  /** Texto de advertencia fijo del backend. */
  limite: string;
}

/**
 * Clasifica CADA fallo matematico por separado (no es una suma de contadores de toda la
 * sesion): las tres primeras categorias son excluyentes entre si por fallo. `sin_clasificar`
 * es legitimo (la sesion se corto justo despues de un error) y se muestra como una cuarta
 * categoria real, nunca como "sin datos".
 */
interface LumaRespuestaAnteError {
  reintento_inmediato: number;
  busca_ayuda: number;
  inactividad_bloqueo: number;
  sin_clasificar: number;
  latencia_mediana_ms: {
    reintento_inmediato: number | null;
    busca_ayuda: number | null;
    inactividad_bloqueo: number | null;
  };
  /** Texto de advertencia fijo del backend: es clasificacion conductual, no inferencia de estado emocional. */
  limite: string;
}

interface LumaAutonomiaDestinos {
  greenhouse: number;
  station: number;
  garden: number;
  map: number;
}

interface LumaAutonomia {
  ruta_actual: 'guided' | 'free' | null;
  /** No cuenta la eleccion inicial, solo transiciones reales entre rutas. */
  cambios_de_ruta: number;
  navegaciones: number;
  destinos: LumaAutonomiaDestinos;
}

interface LumaDecisionAdaptacion {
  decision_id: string | null;
  reason: string | null;
  effective_support: string | null;
  evidencia_cantidad: number;
  resuelta: boolean;
  resultado: Record<string, unknown> | null;
}

type LumaEstadoEtapaCasilla = 'pendiente' | 'en_curso' | 'acreditada';

interface LumaBayesiano {
  p: number | null;
  n: number | null;
  dominada: boolean;
}

interface LumaHabilidadProgreso {
  id: string;
  nombre: string;
  prerrequisitos: string[];
  bayesiano: LumaBayesiano;
  etapas: {
    concrete: LumaEstadoEtapaCasilla;
    pictorial: LumaEstadoEtapaCasilla;
    abstract: LumaEstadoEtapaCasilla;
    transfer: LumaEstadoEtapaCasilla;
  };
}

interface LumaProgresion {
  habilidades: LumaHabilidadProgreso[];
  acreditadas_total: number;
  de_24: number;
}

interface LumaResumen {
  run_id: string;
  estado_actual: LumaEstadoActual;
  conteos_por_tipo: LumaConteoPorTipo[];
  intentos: LumaIntentos;
  ayuda: LumaAyuda;
  inactividad: LumaInactividad;
  decisiones_adaptacion: LumaDecisionAdaptacion[];
  respuesta_ante_error: LumaRespuestaAnteError;
  autonomia: LumaAutonomia;
  /** Se sigue leyendo como opcional por si este entorno en particular no lo tiene desplegado. */
  progresion?: LumaProgresion;
}

interface LumaListaNormalizada<T> {
  /**
   * false significa "la respuesta llego bien (200) pero no reconocimos su forma": NUNCA se
   * debe tratar igual que una lista vacia de verdad, o un desajuste de nombre en el backend
   * se ve en pantalla identico a "no hay datos" (asi paso con /sesiones: la API envolvia en
   * `sesiones`, el cliente buscaba `items`, y la interfaz mostro "no hay sesiones" con datos
   * reales en la base).
   */
  formaReconocida: boolean;
  items: T[];
}

/** Acepta un arreglo plano o un sobre con cualquiera de `clavesCandidatas` (probadas en orden). */
function normalizarListaOSobre<T>(valor: unknown, clavesCandidatas: string[]): LumaListaNormalizada<T> {
  if (Array.isArray(valor)) return { formaReconocida: true, items: valor as T[] };

  if (valor && typeof valor === 'object') {
    for (const clave of clavesCandidatas) {
      const campo = (valor as Record<string, unknown>)[clave];
      if (Array.isArray(campo)) return { formaReconocida: true, items: campo as T[] };
    }
  }

  return { formaReconocida: false, items: [] };
}

/** GET /sesiones no envuelve en `items`: la API real usa `{ sesiones, total, pagina, tamano_pagina }`. */
const CLAVES_SOBRE_SESIONES = ['sesiones', 'items', 'data'];

interface LumaSesionesResultado {
  sesiones: LumaSesion[];
  formaReconocida: boolean;
}

function esRegistroConCampo(valor: unknown, campo: string): valor is Record<string, unknown> {
  return !!valor && typeof valor === 'object' && campo in (valor as Record<string, unknown>);
}

/** Validacion minima: alcanza para no reventar la pantalla con un objeto a medias, no revalida cada campo. */
function esResumenReconocible(valor: unknown): valor is LumaResumen {
  return esRegistroConCampo(valor, 'estado_actual') && esRegistroConCampo(valor, 'intentos');
}

function esEventosSalidaReconocible(valor: unknown): valor is LumaEventosSalida {
  return esRegistroConCampo(valor, 'eventos') && Array.isArray((valor as Record<string, unknown>).eventos);
}

const ERROR_FORMATO_INESPERADO = 'La API respondió, pero con un formato de datos inesperado';

// ---------------------------------------------------------------------------
// Luma: panorama del estudio, series temporales e historico por participante.
//
// Confirmado por api-luma (2026-09-18) con una advertencia explicita: "borrador
// confirmado en su logica, no confirmado en su SQL" para los tres, porque no tenia una
// base Postgres real para probarlos. Se verifico contra la API real en 127.0.0.1:8010:
//   - /panorama: 200, forma exacta a la dada. Confirmado de verdad.
//   - /sesiones/{id}/historico: 200, forma exacta. Confirmado de verdad.
//   - /series (con o sin ?dias): 500 "An error occurred while accessing the database",
//     reproducible. AUN NO FUNCIONA contra Postgres real. Se tipa y se blinda igual,
//     pero los graficos que dependen de esto no se pueden dar por verificados hasta que
//     el endpoint deje de fallar.
// ---------------------------------------------------------------------------

interface LumaSesionesPorDia {
  dia: string;
  sesiones: number;
  eventos: number;
}

interface LumaEmbudoFase {
  fase: string;
  participantes: number;
}

type LumaMotivoCierreConSinDato = 'mastery' | 'break' | 'bank_exhausted' | 'sin_dato';

interface LumaMotivoCierreConteo {
  motivo: LumaMotivoCierreConSinDato;
  participantes: number;
}

interface LumaModalidadUso {
  experience: string;
  eventos: number;
  /** Texto de advertencia fijo del backend: distribucion de uso, no medida de eficacia. */
  limite: string;
}

interface LumaRetencion {
  con_una_sesion: number;
  con_dos_sesiones: number;
  con_tres_o_mas_sesiones: number;
  mediana_dias_entre_sesiones: number | null;
}

interface LumaAbandonoPorFase {
  fase: string;
  participantes: number;
}

interface LumaAbandonoPorEscena {
  scene: number;
  participantes: number;
}

interface LumaAbandonoPorHabilidadEtapa {
  habilidad: string;
  etapa: string;
  participantes: number;
}

interface LumaBancoAgotado {
  habilidad: string | null;
  etapa: string | null;
  veces: number;
}

interface LumaPuntosDeFuga {
  abandono_por_fase: LumaAbandonoPorFase[];
  abandono_por_escena: LumaAbandonoPorEscena[];
  abandono_por_habilidad_y_etapa: LumaAbandonoPorHabilidadEtapa[];
  banco_agotado: LumaBancoAgotado[];
}

interface LumaPanorama {
  generado: string;
  sesiones_total: number;
  participantes_total: number;
  eventos_total: number;
  sesiones_por_dia: LumaSesionesPorDia[];
  embudo_fases: LumaEmbudoFase[];
  motivos_cierre: LumaMotivoCierreConteo[];
  modalidades: LumaModalidadUso[];
  retencion: LumaRetencion;
  /** Decisiones de diseño del juego, no del estudio: el detalle se muestra en Diagnóstico del juego. */
  puntos_de_fuga: LumaPuntosDeFuga;
}

interface LumaSerieRespuestaAnteError {
  reintento_inmediato: number;
  busca_ayuda: number;
  inactividad_bloqueo: number;
  sin_clasificar: number;
  limite: string;
}

interface LumaSerieAyuda {
  voluntaria: number;
  impuesta: number;
}

interface LumaSerieDia {
  dia: string;
  /** null (no 0) el dia que no hubo ninguna resolucion que medir: un hueco real, no un cero. */
  independencia: number | null;
  limite_independencia: string;
  respuesta_ante_error: LumaSerieRespuestaAnteError;
  ayuda: LumaSerieAyuda;
  /** Delta del dia, no acumulado: sumar la serie para obtener el acumulado. */
  casillas_acreditadas: number;
  tiempo_activo_mediana_ms: number | null;
  limite_tiempo_activo: string;
  inactividad_idle_started: number;
  limite_inactividad: string;
}

interface LumaSeries {
  generado: string;
  dias: number;
  /** Siempre `dias` entradas, una por cada dia del rango, sin huecos omitidos (los rellena la API). */
  serie: LumaSerieDia[];
}

interface LumaSesionHistorica {
  fecha: string;
  eventos: number;
  tiempo_activo_ms: number | null;
  independencia: number | null;
  /** Acumulado hasta el final de ESTA sesion, inclusive (no un delta). */
  casillas_acreditadas_acumuladas: number;
  fase_final: string | null;
  motivo_final: string | null;
}

interface LumaProgresionTemporalEntrada {
  habilidad: string;
  etapa: string;
  fecha: string;
}

interface LumaBayesianoTemporalEntrada {
  habilidad: string;
  fecha: string;
  p: number | null;
  n: number | null;
}

interface LumaHistorico {
  run_id: string;
  sesiones: LumaSesionHistorica[];
  progresion_temporal: LumaProgresionTemporalEntrada[];
  bayesiano_temporal: LumaBayesianoTemporalEntrada[];
}

function esPanoramaReconocible(valor: unknown): valor is LumaPanorama {
  return (
    esRegistroConCampo(valor, 'sesiones_total') &&
    esRegistroConCampo(valor, 'embudo_fases') &&
    Array.isArray((valor as Record<string, unknown>).embudo_fases)
  );
}

function esSeriesReconocible(valor: unknown): valor is LumaSeries {
  return esRegistroConCampo(valor, 'serie') && Array.isArray((valor as Record<string, unknown>).serie);
}

function esHistoricoReconocible(valor: unknown): valor is LumaHistorico {
  return esRegistroConCampo(valor, 'sesiones') && Array.isArray((valor as Record<string, unknown>).sesiones);
}

// ---------------------------------------------------------------------------
// Luma: diagnostico del juego (/items y /adaptacion).
//
// El usuario cambio la prioridad: "el core radica en los indicadores mas que en el
// juego", asi que estos dos endpoints son mas importantes que panorama/series/historico.
// Verificado que la FORMA responde 200 contra la API real en 127.0.0.1:8010 (con muy
// pocos items de prueba, no se pudo verificar el CALCULO desde este lado).
//
// NOMBRES DE EVENTO VERIFICADOS (team-lead, 2026-09-18): input_validation, adaptation
// (rule: three_failures | repeated_help_requests | variable_response_latency) y
// scaffold_shown (reason: student_choice | adaptive) existen con esos nombres literales
// en el motor real, confirmados contra el mapa del motor y con una ingesta de prueba que
// devolvio errores_de_formato = 1 para un input_validation real (no dio 0 en silencio).
// Un 0 en estos indicadores es un 0 real, no un desajuste de nombre. Si en el futuro
// alguien duda de esto de nuevo: ya se verifico, la fecha de arriba es la referencia.
// ---------------------------------------------------------------------------

interface LumaItemAnalisis {
  variant_id: string;
  habilidad: string | null;
  etapa: string | null;
  presentaciones: number;
  muestra_suficiente: boolean;
  acierto_primer_intento_sin_ayuda: number | null;
  intentos_mediana: number | null;
  pidio_ayuda: number | null;
  abandonos: number;
  patrones_error: Record<string, number>;
  /** NO es dificultad matematica: es un problema de interfaz (el niño sabe la respuesta y no puede introducirla). */
  errores_de_formato: number;
  limite: string;
}

interface LumaItems {
  generado: string;
  umbral_muestra_suficiente: number;
  items: LumaItemAnalisis[];
}

interface LumaResultadoConteo {
  resuelto_independiente: number;
  resuelto_con_ayuda: number;
  no_resuelto: number;
  muestra_suficiente: boolean;
}

interface LumaPorRazonDecision {
  razon: string;
  veces: number;
  resultado: LumaResultadoConteo;
}

interface LumaPorReglaMidReto {
  regla: string;
  veces: number;
  resultado: LumaResultadoConteo;
}

interface LumaEfectoAndamiaje {
  tasa_acierto_con_andamiaje: number | null;
  presentaciones_con_andamiaje: number;
  tasa_acierto_sin_andamiaje: number | null;
  presentaciones_sin_andamiaje: number;
  /** Exige AMBOS grupos con presentaciones >= umbral_muestra_suficiente. */
  muestra_suficiente: boolean;
  limite: string;
}

interface LumaOportunidadesIndependientes {
  total: number;
  resueltas_independientemente: number;
  muestra_suficiente: boolean;
}

interface LumaAdaptacion {
  generado: string;
  umbral_muestra_suficiente: number;
  por_razon_decision: LumaPorRazonDecision[];
  por_regla_mid_reto: LumaPorReglaMidReto[];
  efecto_del_andamiaje: LumaEfectoAndamiaje;
  oportunidades_independientes: LumaOportunidadesIndependientes;
  limite: string;
}

function esItemsReconocible(valor: unknown): valor is LumaItems {
  return esRegistroConCampo(valor, 'items') && Array.isArray((valor as Record<string, unknown>).items);
}

function esAdaptacionReconocible(valor: unknown): valor is LumaAdaptacion {
  return esRegistroConCampo(valor, 'efecto_del_andamiaje') && esRegistroConCampo(valor, 'oportunidades_independientes');
}

export const lumaApi = {
  getSesiones: async (): Promise<ApiResponse<LumaSesionesResultado>> => {
    const resultado = await adminRequest<unknown>('/api/admin/luma/sesiones');
    if (resultado.error) return { error: resultado.error };

    const normalizado = normalizarListaOSobre<LumaSesion>(resultado.data, CLAVES_SOBRE_SESIONES);
    return { data: { sesiones: normalizado.items, formaReconocida: normalizado.formaReconocida } };
  },

  getEventos: async (runId: string, desdeSecuencia: number, limite: number): Promise<ApiResponse<LumaEventosSalida>> => {
    const parametros = new URLSearchParams({
      desde: String(desdeSecuencia),
      limite: String(limite),
    });
    const resultado = await adminRequest<unknown>(
      `/api/admin/luma/sesiones/${encodeURIComponent(runId)}/eventos?${parametros.toString()}`
    );
    if (resultado.error) return { error: resultado.error };
    if (!esEventosSalidaReconocible(resultado.data)) return { error: ERROR_FORMATO_INESPERADO };

    return { data: resultado.data };
  },

  getResumen: async (runId: string): Promise<ApiResponse<LumaResumen>> => {
    const resultado = await adminRequest<unknown>(`/api/admin/luma/sesiones/${encodeURIComponent(runId)}/resumen`);
    if (resultado.error) return { error: resultado.error };
    if (!esResumenReconocible(resultado.data)) return { error: ERROR_FORMATO_INESPERADO };

    return { data: resultado.data };
  },

  getPanorama: async (): Promise<ApiResponse<LumaPanorama>> => {
    const resultado = await adminRequest<unknown>('/api/admin/luma/panorama');
    if (resultado.error) return { error: resultado.error };
    if (!esPanoramaReconocible(resultado.data)) return { error: ERROR_FORMATO_INESPERADO };

    return { data: resultado.data };
  },

  /** dias: 1-365, la API usa 30 por defecto. GET /series todavia falla contra Postgres real (ver nota arriba). */
  getSeries: async (dias?: number): Promise<ApiResponse<LumaSeries>> => {
    const parametros = dias !== undefined ? `?${new URLSearchParams({ dias: String(dias) }).toString()}` : '';
    const resultado = await adminRequest<unknown>(`/api/admin/luma/series${parametros}`);
    if (resultado.error) return { error: resultado.error };
    if (!esSeriesReconocible(resultado.data)) return { error: ERROR_FORMATO_INESPERADO };

    return { data: resultado.data };
  },

  getHistorico: async (runId: string): Promise<ApiResponse<LumaHistorico>> => {
    const resultado = await adminRequest<unknown>(`/api/admin/luma/sesiones/${encodeURIComponent(runId)}/historico`);
    if (resultado.error) return { error: resultado.error };
    if (!esHistoricoReconocible(resultado.data)) return { error: ERROR_FORMATO_INESPERADO };

    return { data: resultado.data };
  },

  getItems: async (): Promise<ApiResponse<LumaItems>> => {
    const resultado = await adminRequest<unknown>('/api/admin/luma/items');
    if (resultado.error) return { error: resultado.error };
    if (!esItemsReconocible(resultado.data)) return { error: ERROR_FORMATO_INESPERADO };

    return { data: resultado.data };
  },

  getAdaptacion: async (): Promise<ApiResponse<LumaAdaptacion>> => {
    const resultado = await adminRequest<unknown>('/api/admin/luma/adaptacion');
    if (resultado.error) return { error: resultado.error };
    if (!esAdaptacionReconocible(resultado.data)) return { error: ERROR_FORMATO_INESPERADO };

    return { data: resultado.data };
  },
};

export type {
  LumaSesion,
  LumaSesionesResultado,
  LumaEvento,
  LumaEventosSalida,
  LumaEstadoActual,
  LumaConteoPorTipo,
  LumaIntentos,
  LumaAyuda,
  LumaPausa,
  LumaInactividad,
  LumaDecisionAdaptacion,
  LumaRespuestaAnteError,
  LumaAutonomia,
  LumaAutonomiaDestinos,
  LumaBayesiano,
  LumaHabilidadProgreso,
  LumaProgresion,
  LumaResumen,
  LumaSesionesPorDia,
  LumaEmbudoFase,
  LumaMotivoCierreConSinDato,
  LumaMotivoCierreConteo,
  LumaModalidadUso,
  LumaRetencion,
  LumaPanorama,
  LumaSerieRespuestaAnteError,
  LumaSerieAyuda,
  LumaSerieDia,
  LumaSeries,
  LumaSesionHistorica,
  LumaProgresionTemporalEntrada,
  LumaBayesianoTemporalEntrada,
  LumaHistorico,
  LumaAbandonoPorFase,
  LumaAbandonoPorEscena,
  LumaAbandonoPorHabilidadEtapa,
  LumaBancoAgotado,
  LumaPuntosDeFuga,
  LumaItemAnalisis,
  LumaItems,
  LumaResultadoConteo,
  LumaPorRazonDecision,
  LumaPorReglaMidReto,
  LumaEfectoAndamiaje,
  LumaOportunidadesIndependientes,
  LumaAdaptacion,
};
