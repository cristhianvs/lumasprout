import type { LumaSesion } from '@/lib/lumaApi';
import { formatFechaHora } from '@/lib/protocolo42Format';
import { LumaAntiguedadBadge } from './LumaAntiguedadBadge';

interface LumaSesionesTablaProps {
  sesiones: LumaSesion[];
  onSeleccionar: (runId: string) => void;
}

const COLUMNAS_TABLA = 6;

export function LumaSesionesTabla({ sesiones, onSeleccionar }: LumaSesionesTablaProps) {
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider px-6 pt-6 pb-2">
        Sesiones ({sesiones.length})
      </h3>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Participante
              </th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Versión
              </th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Eventos
              </th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Empezó
              </th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Último dato
              </th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <span className="sr-only">Acción</span>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sesiones.length === 0 ? (
              <tr>
                <td colSpan={COLUMNAS_TABLA} className="px-6 py-12 text-center text-gray-500">
                  Todavía no hay sesiones de LumaSprout registradas.
                </td>
              </tr>
            ) : (
              sesiones.map((sesion) => (
                <tr key={sesion.run_id}>
                  <th scope="row" className="px-4 py-4 text-left text-sm font-medium text-midnight">
                    {sesion.participante_codigo ?? (
                      <span className="font-normal text-gray-400">Sin código asignado</span>
                    )}
                  </th>
                  <td className="px-4 py-4 text-left text-sm text-gray-500">{sesion.version}</td>
                  <td className="px-4 py-4 text-right text-sm text-gray-500">{sesion.total_eventos}</td>
                  <td className="px-4 py-4 text-left text-sm text-gray-500">
                    {formatFechaHora(sesion.primer_evento_at)}
                  </td>
                  <td className="px-4 py-4 text-left text-sm">
                    <LumaAntiguedadBadge segundos={sesion.antiguedad_segundos} />
                  </td>
                  <td className="px-4 py-4 text-right text-sm">
                    <button
                      type="button"
                      onClick={() => onSeleccionar(sesion.run_id)}
                      className="font-medium text-bronze hover:text-golden focus:outline-none focus:ring-2 focus:ring-golden rounded"
                    >
                      Ver en vivo
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
