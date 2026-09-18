import type { LumaPorRazonDecision, LumaPorReglaMidReto, LumaResultadoConteo } from '@/lib/lumaApi';
import { formatMotivoDecision } from '@/lib/lumaConstantes';

interface LumaDiagnosticoAdaptacionTablasProps {
  porRazonDecision: LumaPorRazonDecision[];
  porReglaMidReto: LumaPorReglaMidReto[];
}

const COLUMNAS_TABLA = 5;

function FilaResultado({ etiqueta, veces, resultado }: { etiqueta: string; veces: number; resultado: LumaResultadoConteo }) {
  return (
    <tr className={resultado.muestra_suficiente ? undefined : 'opacity-50'}>
      <th scope="row" className="px-3 py-3 text-left text-sm font-medium text-midnight">
        {etiqueta}
        {!resultado.muestra_suficiente && (
          <span className="ml-1 text-[10px] font-normal text-gray-400">(muestra insuficiente)</span>
        )}
      </th>
      <td className="px-3 py-3 text-right text-sm text-gray-500">{veces}</td>
      <td className="px-3 py-3 text-right text-sm text-gray-500">{resultado.resuelto_independiente}</td>
      <td className="px-3 py-3 text-right text-sm text-gray-500">{resultado.resuelto_con_ayuda}</td>
      <td className="px-3 py-3 text-right text-sm text-gray-500">{resultado.no_resuelto}</td>
    </tr>
  );
}

function TablaAdaptacion({ titulo, filas }: { titulo: string; filas: { etiqueta: string; veces: number; resultado: LumaResultadoConteo }[] }) {
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider px-6 pt-6 pb-2">{titulo}</h3>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Motivo</th>
              <th scope="col" className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Veces</th>
              <th scope="col" className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Independiente</th>
              <th scope="col" className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Con ayuda</th>
              <th scope="col" className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">No resuelto</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filas.length === 0 ? (
              <tr>
                <td colSpan={COLUMNAS_TABLA} className="px-6 py-12 text-center text-gray-500">
                  Sin decisiones registradas todavía.
                </td>
              </tr>
            ) : (
              filas.map((fila) => <FilaResultado key={fila.etiqueta} {...fila} />)
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Por cada motivo y por cada regla del motor de adaptacion, que paso despues: resuelto solo, con ayuda, o no resuelto. */
export function LumaDiagnosticoAdaptacionTablas({ porRazonDecision, porReglaMidReto }: LumaDiagnosticoAdaptacionTablasProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <TablaAdaptacion
        titulo="Por motivo de decisión"
        filas={porRazonDecision.map((fila) => ({ etiqueta: formatMotivoDecision(fila.razon), veces: fila.veces, resultado: fila.resultado }))}
      />
      <TablaAdaptacion
        titulo="Por regla en medio del reto"
        filas={porReglaMidReto.map((fila) => ({ etiqueta: fila.regla, veces: fila.veces, resultado: fila.resultado }))}
      />
    </div>
  );
}
