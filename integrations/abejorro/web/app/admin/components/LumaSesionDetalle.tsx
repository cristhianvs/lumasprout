'use client';

import { Button } from '@/components/ui/Button';
import type { LumaSesion } from '@/lib/lumaApi';
import { calcularAntiguedadSegundos, calcularAntiguedadSegundosDesdeMs, formatAntiguedad } from '@/lib/lumaFormat';
import {
  LUMA_UMBRAL_JUGANDO_SEGUNDOS,
  LUMA_UMBRAL_SIN_CONEXION_SEGUNDOS,
  LUMA_UMBRAL_ZONA_DESACTUALIZADA_SEGUNDOS,
} from '@/lib/lumaConstantes';
import { useLumaSesionEnVivo } from '@/hooks/useLumaSesionEnVivo';
import { useRelojTicker } from '@/hooks/useRelojTicker';
import { LumaAntiguedadBadge } from './LumaAntiguedadBadge';
import { LumaDiagramaFases } from './LumaDiagramaFases';
import { LumaRejillaHabilidades } from './LumaRejillaHabilidades';
import { LumaIndicadores } from './LumaIndicadores';
import { LumaCircuitoAdaptacion } from './LumaCircuitoAdaptacion';
import { LumaEventosRecientes } from './LumaEventosRecientes';

interface LumaSesionDetalleProps {
  runId: string;
  /** Fila de la lista, si ya se cargo; solo se usa como respaldo inicial mientras llega el primer sondeo. */
  sesion: LumaSesion | null;
  onVolver: () => void;
}

type LumaSituacionEnVivo = 'cargando' | 'sin_conexion' | 'jugando' | 'inactivo_o_pausa';

export function LumaSesionDetalle({ runId, sesion, onVolver }: LumaSesionDetalleProps) {
  const ahoraMs = useRelojTicker();
  const {
    resumen,
    eventosRecientes,
    ultimoEventoAtIso,
    ultimaActualizacionEventosMs,
    ultimaActualizacionResumenMs,
    errorEventos,
    errorResumen,
    cargandoInicial,
  } = useLumaSesionEnVivo(runId);

  const ultimoDatoIso = ultimoEventoAtIso ?? sesion?.ultimo_evento_at ?? null;
  const antiguedadUltimoDatoSegundos = calcularAntiguedadSegundos(ultimoDatoIso, ahoraMs);

  // /eventos y /resumen se evaluan por separado: uno puede estar fallando mientras el otro
  // sigue en vivo, y eso NO es lo mismo que la sesion entera incomunicada.
  const antiguedadEventosSegundos = calcularAntiguedadSegundosDesdeMs(ultimaActualizacionEventosMs, ahoraMs);
  const antiguedadResumenSegundos = calcularAntiguedadSegundosDesdeMs(ultimaActualizacionResumenMs, ahoraMs);

  const eventosIncomunicados =
    !cargandoInicial &&
    (ultimaActualizacionEventosMs === null ||
      (antiguedadEventosSegundos !== null && antiguedadEventosSegundos > LUMA_UMBRAL_SIN_CONEXION_SEGUNDOS));
  const resumenIncomunicado =
    !cargandoInicial &&
    (ultimaActualizacionResumenMs === null ||
      (antiguedadResumenSegundos !== null && antiguedadResumenSegundos > LUMA_UMBRAL_SIN_CONEXION_SEGUNDOS));

  // El banner grande de "sin conexion" solo aparece cuando LOS DOS estan incomunicados:
  // si uno de los dos responde, la sesion no esta incomunicada.
  const sinConexionTotal = eventosIncomunicados && resumenIncomunicado;

  // Zona de indicadores/rejilla (todo lo que sale de /resumen) desactualizada, aunque
  // /eventos siga fluyendo con normalidad. No hace falta decir cual endpoint fallo: basta
  // con marcar que esta zona en particular no se actualiza desde hace un rato.
  const resumenDesactualizado =
    !cargandoInicial &&
    (ultimaActualizacionResumenMs === null ||
      (antiguedadResumenSegundos !== null && antiguedadResumenSegundos > LUMA_UMBRAL_ZONA_DESACTUALIZADA_SEGUNDOS));

  const jugandoAhora =
    !sinConexionTotal &&
    resumen !== null &&
    (resumen?.estado_actual.heartbeat_reciente ??
      (antiguedadUltimoDatoSegundos !== null && antiguedadUltimoDatoSegundos <= LUMA_UMBRAL_JUGANDO_SEGUNDOS));

  const situacion: LumaSituacionEnVivo = cargandoInicial
    ? 'cargando'
    : sinConexionTotal
      ? 'sin_conexion'
      : jugandoAhora
        ? 'jugando'
        : 'inactivo_o_pausa';

  const BANNER_POR_SITUACION: Record<LumaSituacionEnVivo, { texto: string; clase: string }> = {
    cargando: { texto: 'Conectando con la sesión en vivo...', clase: 'bg-gray-50 text-gray-500' },
    sin_conexion: {
      texto: 'No llegan datos nuevos: puede ser un corte de red, no falta de interés del niño.',
      clase: 'bg-red-50 text-red-700',
    },
    jugando: { texto: 'El niño está jugando ahora mismo.', clase: 'bg-golden/20 text-midnight' },
    inactivo_o_pausa: {
      texto: 'Sin actividad reciente: puede estar en pausa o inactivo, la sesión sigue viva.',
      clase: 'bg-gray-100 text-gray-600',
    },
  };

  const banner = BANNER_POR_SITUACION[situacion];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Button variant="outline" size="sm" onClick={onVolver}>
            Volver a la lista
          </Button>
        </div>
        <div className="text-right">
          <h2 className="text-2xl font-bold text-midnight">
            {sesion?.participante_codigo ?? 'Sesión'}
          </h2>
          <p className="text-xs text-gray-500 font-mono">{runId}</p>
        </div>
      </div>

      <div className={`rounded-lg p-4 flex flex-wrap items-center justify-between gap-3 ${banner.clase}`}>
        <p className="text-sm font-medium">{banner.texto}</p>
        <LumaAntiguedadBadge segundos={antiguedadUltimoDatoSegundos} etiqueta="Último dato" />
      </div>

      {resumen?.estado_actual.limite_heartbeat && (
        <p className="text-xs text-gray-500">{resumen.estado_actual.limite_heartbeat}</p>
      )}

      {errorEventos && (
        <p className="text-xs text-red-600">
          Último error en el flujo de eventos: {errorEventos}. Mostrando los últimos eventos conocidos.
        </p>
      )}
      {errorResumen && (
        <p className="text-xs text-red-600">
          Último error en el resumen: {errorResumen}. Mostrando el último resumen conocido.
        </p>
      )}

      <p className="text-xs text-gray-400">
        Este panel nunca infiere estados emocionales (ansiedad, desmotivación, etc.): el motor marca esos campos
        explícitamente como no inferibles y aquí no se muestran.
      </p>

      {!sinConexionTotal && resumenDesactualizado && (
        <p className="text-xs bg-amber-50 text-amber-700 rounded-md px-3 py-2">
          Indicadores y rejilla sin actualizar desde {formatAntiguedad(antiguedadResumenSegundos)}: el resto de la
          pantalla sigue en vivo.
        </p>
      )}

      <LumaDiagramaFases estadoActual={resumen?.estado_actual ?? null} />

      <LumaRejillaHabilidades progresion={resumen?.progresion} />

      <LumaIndicadores resumen={resumen} />

      <LumaCircuitoAdaptacion decisiones={resumen?.decisiones_adaptacion} />

      <LumaEventosRecientes eventos={eventosRecientes} />
    </div>
  );
}
