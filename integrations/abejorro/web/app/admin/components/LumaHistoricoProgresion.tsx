import type { LumaProgresionTemporalEntrada } from '@/lib/lumaApi';
import { LUMA_ETAPA_ETIQUETAS, formatHabilidadRespaldo, type LumaEtapaCPA } from '@/lib/lumaConstantes';

interface LumaHistoricoProgresionProps {
  progresionTemporal: LumaProgresionTemporalEntrada[];
}

function esEtapaConocida(valor: string): valor is LumaEtapaCPA {
  return valor in LUMA_ETAPA_ETIQUETAS;
}

/** Cuando se acredito cada casilla CPA, en orden cronologico. Acreditada = evidencia sin ayuda, no un intento superado. */
export function LumaHistoricoProgresion({ progresionTemporal }: LumaHistoricoProgresionProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-4">
        Casillas acreditadas en el tiempo
      </h4>

      {progresionTemporal.length === 0 ? (
        <p className="text-sm text-gray-500">Todavía no acreditó ninguna casilla.</p>
      ) : (
        <ul className="space-y-2">
          {progresionTemporal.map((entrada, indice) => (
            <li
              key={`${entrada.habilidad}-${entrada.etapa}-${indice}`}
              className="flex items-center justify-between text-sm border-b border-gray-100 pb-2 last:border-0"
            >
              <span className="text-midnight">
                <span title={`id: ${entrada.habilidad}`}>{formatHabilidadRespaldo(entrada.habilidad)}</span> ·{' '}
                {esEtapaConocida(entrada.etapa) ? LUMA_ETAPA_ETIQUETAS[entrada.etapa] : entrada.etapa}
              </span>
              <span className="text-gray-500">{entrada.fecha}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
