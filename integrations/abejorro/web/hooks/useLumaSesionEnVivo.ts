'use client';

import { useEffect, useRef, useState } from 'react';
import { lumaApi, type LumaEvento, type LumaResumen } from '@/lib/lumaApi';
import { LUMA_INTERVALO_SONDEO_DETALLE_MS, LUMA_LIMITE_EVENTOS_POR_SONDEO, LUMA_MAX_EVENTOS_RECIENTES_VISIBLES } from '@/lib/lumaConstantes';
import { useVisiblePolling } from './useVisiblePolling';

interface UseLumaSesionEnVivoResultado {
  resumen: LumaResumen | null;
  eventosRecientes: LumaEvento[];
  /** Fecha ISO del evento mas reciente que realmente llego del juego (no del ultimo sondeo exitoso). */
  ultimoEventoAtIso: string | null;
  /** Marca de tiempo (ms) del ultimo sondeo de /eventos que respondio bien, sin importar si trajo eventos nuevos. */
  ultimaActualizacionEventosMs: number | null;
  /** Marca de tiempo (ms) del ultimo sondeo de /resumen que respondio bien. */
  ultimaActualizacionResumenMs: number | null;
  errorEventos: string | null;
  errorResumen: string | null;
  cargandoInicial: boolean;
}

/**
 * Sondea /eventos (incremental, por secuencia) y /resumen de una sesion de LumaSprout
 * cada LUMA_INTERVALO_SONDEO_DETALLE_MS, pausando cuando la pestaña esta oculta.
 *
 * Los dos endpoints se tratan de forma INDEPENDIENTE en cada ciclo: si uno falla y el
 * otro responde bien, se aplica igual lo que si llego. El objetivo principal de esta
 * vista es mostrar lo que el niño esta haciendo ahora, y el flujo de eventos es lo que
 * mas directamente lo muestra: retrasarlo por un fallo en /resumen seria perder justo
 * eso. Nunca se borra el ultimo estado conocido de un endpoint que esta fallando; el
 * cursor de /eventos (`desde`) solo avanza con los eventos que realmente se aplicaron.
 */
export function useLumaSesionEnVivo(runId: string): UseLumaSesionEnVivoResultado {
  const [resumen, setResumen] = useState<LumaResumen | null>(null);
  const [eventosRecientes, setEventosRecientes] = useState<LumaEvento[]>([]);
  const [ultimoEventoAtIso, setUltimoEventoAtIso] = useState<string | null>(null);
  const [ultimaActualizacionEventosMs, setUltimaActualizacionEventosMs] = useState<number | null>(null);
  const [ultimaActualizacionResumenMs, setUltimaActualizacionResumenMs] = useState<number | null>(null);
  const [errorEventos, setErrorEventos] = useState<string | null>(null);
  const [errorResumen, setErrorResumen] = useState<string | null>(null);
  const [cargandoInicial, setCargandoInicial] = useState(true);

  const ultimaSecuenciaRef = useRef(0);
  const runIdVigenteRef = useRef(runId);
  const ultimoEventoAtMsRef = useRef<number | null>(null);

  useEffect(() => {
    runIdVigenteRef.current = runId;
    ultimaSecuenciaRef.current = 0;
    ultimoEventoAtMsRef.current = null;
    setResumen(null);
    setEventosRecientes([]);
    setUltimoEventoAtIso(null);
    setUltimaActualizacionEventosMs(null);
    setUltimaActualizacionResumenMs(null);
    setErrorEventos(null);
    setErrorResumen(null);
    setCargandoInicial(true);
  }, [runId]);

  useVisiblePolling(() => {
    const runIdDeEstaLlamada = runId;

    void (async () => {
      const [eventosResultado, resumenResultado] = await Promise.all([
        lumaApi.getEventos(runIdDeEstaLlamada, ultimaSecuenciaRef.current, LUMA_LIMITE_EVENTOS_POR_SONDEO),
        lumaApi.getResumen(runIdDeEstaLlamada),
      ]);

      // Si mientras esperabamos la respuesta el investigador cambio de sesion,
      // descartamos el resultado: pertenece a una sesion que ya no se muestra.
      if (runIdVigenteRef.current !== runIdDeEstaLlamada) return;

      // /eventos: se aplica sin importar lo que le haya pasado a /resumen en este mismo ciclo.
      if (eventosResultado.error) {
        setErrorEventos(eventosResultado.error);
      } else {
        setErrorEventos(null);

        const eventosSalida = eventosResultado.data;
        const eventosNuevos = eventosSalida?.eventos ?? [];

        // El cursor solo avanza con lo que realmente se aplico en este ciclo: si este
        // sondeo hubiera fallado, `ultimaSecuenciaRef` se queda donde estaba.
        if (eventosSalida) {
          ultimaSecuenciaRef.current = eventosSalida.ultimo_indice;
        }

        if (eventosNuevos.length > 0) {
          setEventosRecientes((anteriores) =>
            [...anteriores, ...eventosNuevos].slice(-LUMA_MAX_EVENTOS_RECIENTES_VISIBLES)
          );

          // recibido_at es el reloj del SERVIDOR: es el mismo que usa el backend para decidir
          // "heartbeat_reciente", asi que es el criterio correcto de frescura del dato.
          for (const evento of eventosNuevos) {
            const recibidoMs = new Date(evento.recibido_at).getTime();
            if (!Number.isNaN(recibidoMs) && (ultimoEventoAtMsRef.current === null || recibidoMs > ultimoEventoAtMsRef.current)) {
              ultimoEventoAtMsRef.current = recibidoMs;
              setUltimoEventoAtIso(evento.recibido_at);
            }
          }
        }

        setUltimaActualizacionEventosMs(Date.now());
      }

      // /resumen: independiente de /eventos.
      if (resumenResultado.error) {
        setErrorResumen(resumenResultado.error);
      } else {
        setErrorResumen(null);
        setResumen(resumenResultado.data ?? null);
        setUltimaActualizacionResumenMs(Date.now());
      }

      setCargandoInicial(false);
    })();
  }, LUMA_INTERVALO_SONDEO_DETALLE_MS);

  return {
    resumen,
    eventosRecientes,
    ultimoEventoAtIso,
    ultimaActualizacionEventosMs,
    ultimaActualizacionResumenMs,
    errorEventos,
    errorResumen,
    cargandoInicial,
  };
}
