import type { LumaInactividad, LumaIntentos } from '@/lib/lumaApi';
import { formatDuracionSegundos } from '@/lib/lumaFormat';
import { formatFechaHora, pluralizar } from '@/lib/protocolo42Format';

interface LumaIndicadorRitmoProps {
  intentos: LumaIntentos | undefined;
  inactividad: LumaInactividad | undefined;
}

const MS_POR_SEGUNDO = 1000;

/** Pausas e inactividad. El backend no calcula un promedio de latencia: solo advierte, para no fabricar un numero enganoso. */
export function LumaIndicadorRitmo({ intentos, inactividad }: LumaIndicadorRitmoProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-4">
      <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">Ritmo</h3>

      <div>
        <div className="text-xs text-gray-500 uppercase">Tiempo entre intentos</div>
        <p className="mt-1 text-sm text-gray-600">
          {intentos?.limite_latencia ?? 'Sin datos todavía.'}
        </p>
        <p className="mt-1 text-[11px] text-gray-400">El contador se reinicia tras cada intento.</p>
      </div>

      <div className="border-t border-gray-100 pt-4">
        <div className="flex items-baseline justify-between mb-2">
          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Pausas e inactividad</h4>
          <span className="text-xs text-gray-500">
            {inactividad
              ? `${inactividad.idle_started} ${pluralizar(inactividad.idle_started, 'aviso', 'avisos')} de inactividad`
              : 'Sin datos'}
          </span>
        </div>

        {inactividad && inactividad.pausas.length > 0 ? (
          <ul className="space-y-1">
            {inactividad.pausas.map((pausa, indice) => (
              <li key={`${pausa.inicio_at ?? 'sin-inicio'}-${indice}`} className="flex justify-between text-sm text-gray-500">
                <span>{pausa.inicio_at ? formatFechaHora(pausa.inicio_at) : 'Inicio sin registrar'}</span>
                <span className="text-midnight">
                  {pausa.duracion_ms !== null ? formatDuracionSegundos(pausa.duracion_ms / MS_POR_SEGUNDO) : 'En curso'}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500">Sin pausas registradas.</p>
        )}

        <p className="mt-2 text-xs text-gray-500">
          {inactividad?.limite ?? 'Una pausa larga no demuestra por sí sola ansiedad ni desinterés.'}
        </p>
      </div>
    </div>
  );
}
