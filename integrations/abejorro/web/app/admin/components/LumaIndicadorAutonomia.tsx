import type { LumaAutonomia } from '@/lib/lumaApi';
import { LUMA_DESTINOS_AUTONOMIA, LUMA_DESTINO_ETIQUETAS, LUMA_RUTA_ETIQUETAS, formatModalidad } from '@/lib/lumaConstantes';

interface LumaIndicadorAutonomiaProps {
  autonomia: LumaAutonomia | undefined;
  modalidad: string | null | undefined;
}

/** Autonomía (ruta guiada o libre, navegación por el mapa) y modalidad elegida. */
export function LumaIndicadorAutonomia({ autonomia, modalidad }: LumaIndicadorAutonomiaProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-4">
      <div>
        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">Autonomía</h3>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-midnight">
            {autonomia?.ruta_actual ? LUMA_RUTA_ETIQUETAS[autonomia.ruta_actual] : 'Sin dato'}
          </span>
          {autonomia && (
            <span className="text-xs text-gray-500">
              {autonomia.cambios_de_ruta} {autonomia.cambios_de_ruta === 1 ? 'cambio de ruta' : 'cambios de ruta'}
            </span>
          )}
        </div>
      </div>

      {autonomia && (
        <div className="border-t border-gray-100 pt-4">
          <div className="flex items-baseline justify-between mb-2">
            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Navegación libre</h4>
            <span className="text-xs text-gray-500">{autonomia.navegaciones} navegaciones</span>
          </div>
          <ul className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            {LUMA_DESTINOS_AUTONOMIA.map((destino) => (
              <li key={destino} className="bg-gray-50 rounded-md px-2 py-1.5 text-center">
                <div className="text-midnight font-semibold">{autonomia.destinos[destino]}</div>
                <div className="text-gray-500">{LUMA_DESTINO_ETIQUETAS[destino]}</div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="border-t border-gray-100 pt-4">
        <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Modalidad</h4>
        <span className="inline-flex rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-midnight">
          {formatModalidad(modalidad ?? null)}
        </span>
        <p className="mt-2 text-xs text-gray-500">
          Es una preferencia elegida o asignada, no una prueba de que el niño aprende mejor así.
        </p>
      </div>
    </div>
  );
}
