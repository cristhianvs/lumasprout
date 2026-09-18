import type { LumaBayesianoTemporalEntrada } from '@/lib/lumaApi';
import { formatHabilidadRespaldo } from '@/lib/lumaConstantes';

interface LumaHistoricoBayesianoProps {
  bayesianoTemporal: LumaBayesianoTemporalEntrada[];
}

const PORCENTAJE = 100;

/** Evolucion del criterio bayesiano por habilidad: una probabilidad estimada, no un recorrido CPA acreditado. */
export function LumaHistoricoBayesiano({ bayesianoTemporal }: LumaHistoricoBayesianoProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-1">
        Evolución del criterio bayesiano
      </h4>
      <p className="text-xs text-gray-500 mb-4">
        Estimación de probabilidad por habilidad, no evidencia acreditada por etapa: se muestra por separado
        del recorrido CPA.
      </p>

      {bayesianoTemporal.length === 0 ? (
        <p className="text-sm text-gray-500">Sin actualizaciones registradas todavía.</p>
      ) : (
        <ul className="space-y-2">
          {bayesianoTemporal.map((entrada, indice) => (
            <li
              key={`${entrada.habilidad}-${entrada.fecha}-${indice}`}
              className="flex items-center justify-between text-sm border-b border-gray-100 pb-2 last:border-0"
            >
              <span className="text-midnight" title={`id: ${entrada.habilidad}`}>
                {formatHabilidadRespaldo(entrada.habilidad)}
              </span>
              <span className="text-gray-500">{entrada.fecha}</span>
              <span className="text-midnight font-medium">
                {entrada.p !== null && entrada.n !== null
                  ? `${Math.round(entrada.p * PORCENTAJE)}% (n=${entrada.n})`
                  : 'Sin dato'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
