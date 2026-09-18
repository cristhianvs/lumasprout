import type { LumaEstadoActual } from '@/lib/lumaApi';
import { LUMA_ESCENAS, LUMA_FASES, LUMA_FASE_ETIQUETAS, LUMA_MOTIVO_FINAL_ETIQUETAS } from '@/lib/lumaConstantes';

/** "bank_exhausted" no es un exito (el juego se quedo sin preguntas): se estiliza distinto de "mastery". */
const CLASE_MOTIVO_FINAL: Record<'mastery' | 'break' | 'bank_exhausted', string> = {
  mastery: 'text-midnight font-medium',
  break: 'text-midnight font-medium',
  bank_exhausted: 'text-bronze font-medium',
};

interface LumaDiagramaFasesProps {
  estadoActual: LumaEstadoActual | null;
}

/** Fases del recorrido (welcome -> play -> bridge -> math -> complete) y, si esta en "play", la escena actual. */
export function LumaDiagramaFases({ estadoActual }: LumaDiagramaFasesProps) {
  const faseActual = estadoActual?.phase ?? null;
  const indiceFaseActual = faseActual ? LUMA_FASES.findIndex((fase) => fase === faseActual) : -1;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-4">Recorrido</h3>

      <ol className="flex flex-wrap items-center gap-2">
        {LUMA_FASES.map((fase, indice) => {
          const esActual = fase === faseActual;
          const yaPasada = indiceFaseActual >= 0 && indice < indiceFaseActual;

          return (
            <li key={fase} className="flex items-center gap-2">
              <span
                aria-current={esActual ? 'step' : undefined}
                className={`rounded-full px-3 py-1.5 text-xs font-medium whitespace-nowrap ${
                  esActual
                    ? 'bg-golden text-midnight'
                    : yaPasada
                      ? 'bg-bronze/20 text-bronze'
                      : 'bg-gray-100 text-gray-500'
                }`}
              >
                {LUMA_FASE_ETIQUETAS[fase]}
              </span>
              {indice < LUMA_FASES.length - 1 && (
                <span aria-hidden="true" className="text-gray-300">
                  &rarr;
                </span>
              )}
            </li>
          );
        })}
      </ol>

      {faseActual === 'complete' && (
        <p className="mt-3 text-sm text-gray-500">
          Motivo del cierre:{' '}
          {estadoActual?.motivo_final ? (
            <span className={CLASE_MOTIVO_FINAL[estadoActual.motivo_final]}>
              {LUMA_MOTIVO_FINAL_ETIQUETAS[estadoActual.motivo_final]}
            </span>
          ) : (
            <span className="text-gray-400">terminó sin evidencia clara de motivo</span>
          )}
        </p>
      )}

      {faseActual === 'play' && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Escena de la aventura</h4>
          <ol className="flex flex-wrap gap-2">
            {LUMA_ESCENAS.map((escena) => {
              const esEscenaActual = estadoActual?.scene === escena.indice;

              return (
                <li
                  key={escena.indice}
                  aria-current={esEscenaActual ? 'step' : undefined}
                  className={`rounded-md px-3 py-1.5 text-xs font-medium whitespace-nowrap ${
                    esEscenaActual ? 'bg-golden text-midnight' : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {escena.indice} {escena.etiqueta}
                </li>
              );
            })}
          </ol>
        </div>
      )}

      {estadoActual === null && <p className="mt-3 text-sm text-gray-500">Sin dato del estado actual todavía.</p>}
    </div>
  );
}
