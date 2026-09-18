import type { LumaEfectoAndamiaje, LumaOportunidadesIndependientes } from '@/lib/lumaApi';

interface LumaDiagnosticoAndamiajeProps {
  efecto: LumaEfectoAndamiaje;
  oportunidades: LumaOportunidadesIndependientes;
}

const PORCENTAJE = 100;

function formatTasa(tasa: number | null): string {
  return tasa !== null ? `${Math.round(tasa * PORCENTAJE)}%` : 'Sin dato';
}

/**
 * La señal mas importante de esta vista si aparece: si el acierto tras un apoyo concreto
 * NO es mejor que sin apoyo (con muestra suficiente en ambos grupos), el andamiaje esta
 * estorbando en vez de ayudar. Se destaca visualmente cuando ocurre.
 */
export function LumaDiagnosticoAndamiaje({ efecto, oportunidades }: LumaDiagnosticoAndamiajeProps) {
  const andamiajeEstorbando =
    efecto.muestra_suficiente &&
    efecto.tasa_acierto_con_andamiaje !== null &&
    efecto.tasa_acierto_sin_andamiaje !== null &&
    efecto.tasa_acierto_con_andamiaje <= efecto.tasa_acierto_sin_andamiaje;

  return (
    <div
      className={`rounded-lg shadow p-6 space-y-4 ${
        andamiajeEstorbando ? 'bg-amber-50 border-2 border-amber-300' : 'bg-white'
      }`}
    >
      <div>
        <h3
          className={`text-sm font-medium uppercase tracking-wider mb-1 ${
            andamiajeEstorbando ? 'text-amber-800' : 'text-gray-500'
          }`}
        >
          Efecto del andamiaje
        </h3>
        {andamiajeEstorbando && (
          <p className="text-sm text-amber-700 mb-2">
            El acierto tras un apoyo concreto no es mejor que sin apoyo: el andamiaje parece estar
            estorbando en vez de ayudar.
          </p>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-gray-500 uppercase">Con andamiaje</div>
            <div className="text-lg font-semibold text-midnight">
              {formatTasa(efecto.tasa_acierto_con_andamiaje)}
            </div>
            <div className="text-xs text-gray-400">{efecto.presentaciones_con_andamiaje} presentaciones</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase">Sin andamiaje</div>
            <div className="text-lg font-semibold text-midnight">
              {formatTasa(efecto.tasa_acierto_sin_andamiaje)}
            </div>
            <div className="text-xs text-gray-400">{efecto.presentaciones_sin_andamiaje} presentaciones</div>
          </div>
        </div>

        {!efecto.muestra_suficiente && (
          <p className="mt-2 text-xs text-gray-400">
            Muestra insuficiente en al menos uno de los dos grupos: esta comparación todavía no es
            confiable.
          </p>
        )}
        <p className="mt-2 text-xs text-gray-500">{efecto.limite}</p>
      </div>

      <div className="border-t border-gray-100 pt-4">
        <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
          Oportunidades independientes
        </h4>
        <p className="text-sm text-midnight">
          {oportunidades.resueltas_independientemente} de {oportunidades.total} resueltas de forma
          independiente
          {!oportunidades.muestra_suficiente && (
            <span className="ml-1 text-xs text-gray-400">(muestra insuficiente)</span>
          )}
        </p>
      </div>
    </div>
  );
}
