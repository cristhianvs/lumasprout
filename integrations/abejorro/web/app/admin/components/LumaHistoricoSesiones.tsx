import type { LumaSesionHistorica } from '@/lib/lumaApi';
import { formatDuracionSegundos } from '@/lib/lumaFormat';
import { formatMotivoCierreAgregado, formatFase } from '@/lib/lumaConstantes';
import { LUMA_MOTIVOS_FINAL, type LumaMotivoFinal } from '@/lib/lumaConstantes';
import { formatPorcentaje } from '@/lib/protocolo42Format';

interface LumaHistoricoSesionesProps {
  sesiones: LumaSesionHistorica[];
}

const MS_POR_SEGUNDO = 1000;
const COLUMNAS_TABLA = 6;

function esMotivoFinalConocido(valor: string): valor is LumaMotivoFinal {
  return (LUMA_MOTIVOS_FINAL as readonly string[]).includes(valor);
}

/** Una fila por cada carga de pagina distinta de este participante, en orden cronologico. */
export function LumaHistoricoSesiones({ sesiones }: LumaHistoricoSesionesProps) {
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wider px-6 pt-6 pb-2">
        Sesiones ({sesiones.length})
      </h4>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Eventos</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Tiempo activo</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Independencia</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Casillas acum.</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cierre</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sesiones.length === 0 ? (
              <tr>
                <td colSpan={COLUMNAS_TABLA} className="px-6 py-12 text-center text-gray-500">
                  Sin sesiones anteriores registradas.
                </td>
              </tr>
            ) : (
              sesiones.map((sesion) => (
                <tr key={sesion.fecha}>
                  <th scope="row" className="px-4 py-4 text-left text-sm font-medium text-midnight">{sesion.fecha}</th>
                  <td className="px-4 py-4 text-right text-sm text-gray-500">{sesion.eventos}</td>
                  <td className="px-4 py-4 text-right text-sm text-gray-500">
                    {sesion.tiempo_activo_ms !== null
                      ? formatDuracionSegundos(sesion.tiempo_activo_ms / MS_POR_SEGUNDO)
                      : 'Sin dato'}
                  </td>
                  <td className="px-4 py-4 text-right text-sm text-gray-500">
                    {sesion.independencia !== null ? formatPorcentaje(sesion.independencia * 100) : 'Sin dato'}
                  </td>
                  <td className="px-4 py-4 text-right text-sm text-gray-500">{sesion.casillas_acreditadas_acumuladas}</td>
                  <td className="px-4 py-4 text-left text-sm text-gray-500">
                    {sesion.fase_final ? formatFase(sesion.fase_final) : 'Sin dato'}
                    {sesion.motivo_final && esMotivoFinalConocido(sesion.motivo_final) && (
                      <span className="text-gray-400"> · {formatMotivoCierreAgregado(sesion.motivo_final)}</span>
                    )}
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
