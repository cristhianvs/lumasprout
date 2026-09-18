import { CheckCircle2, CircleDashed } from 'lucide-react';
import type { LumaHabilidadProgreso, LumaProgresion } from '@/lib/lumaApi';
import {
  LUMA_ESTADOS_CASILLA,
  LUMA_ETAPAS_CPA,
  LUMA_ETAPA_ETIQUETAS,
  LUMA_ORDEN_HABILIDADES_RESPALDO,
  type LumaEstadoCasilla,
} from '@/lib/lumaConstantes';

interface LumaRejillaHabilidadesProps {
  /** undefined: el endpoint /resumen todavia no expone `progresion` en este entorno (nunca se inventa la rejilla). */
  progresion: LumaProgresion | undefined;
}

const ESTILO_POR_ESTADO: Record<LumaEstadoCasilla, string> = {
  pendiente: 'bg-gray-50 text-gray-400 border border-gray-200',
  en_curso: 'bg-bronze/10 text-bronze border border-bronze',
  acreditada: 'bg-golden text-midnight border border-golden',
};

const ETIQUETA_ESTADO: Record<LumaEstadoCasilla, string> = {
  pendiente: 'pendiente',
  en_curso: 'en curso',
  acreditada: 'acreditada',
};

function IconoEstado({ estado }: { estado: LumaEstadoCasilla }) {
  if (estado === 'acreditada') return <CheckCircle2 className="h-4 w-4" aria-hidden="true" />;
  return <CircleDashed className="h-4 w-4" aria-hidden="true" />;
}

/** `p`/`n` pueden venir null (evidencia insuficiente para estimar); nunca se fabrica un porcentaje en ese caso. */
function formatBayesiano(p: number | null, n: number | null): string {
  if (p === null || n === null) return 'Sin dato';
  const PORCENTAJE = 100;
  return `${Math.round(p * PORCENTAJE)}% (n=${n})`;
}

function ordenarHabilidades(habilidades: LumaHabilidadProgreso[]): LumaHabilidadProgreso[] {
  const indiceRespaldo = new Map<string, number>(
    LUMA_ORDEN_HABILIDADES_RESPALDO.map((id, indice) => [id, indice])
  );
  return [...habilidades].sort((a, b) => {
    const indiceA = indiceRespaldo.get(a.id) ?? Number.MAX_SAFE_INTEGER;
    const indiceB = indiceRespaldo.get(b.id) ?? Number.MAX_SAFE_INTEGER;
    return indiceA - indiceB;
  });
}

/** La rejilla de 6 habilidades x 4 etapas CPA: la pieza mas valiosa del diagrama. */
export function LumaRejillaHabilidades({ progresion }: LumaRejillaHabilidadesProps) {
  if (!progresion) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-1">
          Taller: dominio por habilidad y etapa
        </h3>
        <p className="text-sm text-gray-500">
          Sin datos: la rejilla de progreso todavía no está disponible en este entorno.
        </p>
      </div>
    );
  }

  const habilidades = ordenarHabilidades(progresion.habilidades);
  const nombrePorId = new Map(habilidades.map((habilidad) => [habilidad.id, habilidad.nombre]));

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-1">
        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">
          Taller: dominio por habilidad y etapa
        </h3>
        <span className="text-sm font-semibold text-midnight">
          {progresion.acreditadas_total}/{progresion.de_24} casillas acreditadas
        </span>
      </div>
      <p className="text-xs text-gray-500 mb-4">
        Acreditada solo con evidencia sin ayuda. El éxito con ayuda no demuestra dominio independiente.
        La estimación bayesiana es una probabilidad, no un recorrido CPA: se muestran por separado.
      </p>

      <div className="overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-1">
          <thead>
            <tr>
              <th scope="col" className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider pr-2">
                Habilidad
              </th>
              {LUMA_ETAPAS_CPA.map((etapa) => (
                <th
                  key={etapa}
                  scope="col"
                  className="text-center text-xs font-medium text-gray-500 uppercase tracking-wider px-1"
                >
                  {LUMA_ETAPA_ETIQUETAS[etapa]}
                  {etapa === 'transfer' && <span aria-hidden="true">*</span>}
                </th>
              ))}
              <th scope="col" className="text-center text-xs font-medium text-gray-500 uppercase tracking-wider px-2">
                Criterio bayesiano
                <br />
                <span className="normal-case font-normal text-gray-400">(no verifica CPA)</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {habilidades.map((habilidad) => (
              <tr key={habilidad.id}>
                <th scope="row" className="text-left pr-2 align-top">
                  <span className="text-sm font-medium text-midnight whitespace-nowrap" title={`id: ${habilidad.id}`}>
                    {habilidad.nombre}
                  </span>
                  {habilidad.prerrequisitos.length > 0 && (
                    <p className="text-[11px] text-gray-400 whitespace-nowrap">
                      Requiere: {habilidad.prerrequisitos.map((id) => nombrePorId.get(id) ?? id).join(', ')}
                    </p>
                  )}
                </th>
                {LUMA_ETAPAS_CPA.map((etapa) => {
                  const estado = habilidad.etapas[etapa];
                  const esTransferAcreditada = etapa === 'transfer' && estado === 'acreditada';
                  const titulo = esTransferAcreditada
                    ? `${ETIQUETA_ESTADO[estado]} (puede estar sobrecontada, ver nota debajo de la tabla)`
                    : ETIQUETA_ESTADO[estado];

                  return (
                    <td key={etapa} className="p-1">
                      <div
                        role="img"
                        aria-label={`${habilidad.nombre}, ${LUMA_ETAPA_ETIQUETAS[etapa]}: ${titulo}`}
                        className={`flex items-center justify-center rounded-md h-10 w-10 mx-auto ${ESTILO_POR_ESTADO[estado]}`}
                        title={titulo}
                      >
                        <IconoEstado estado={estado} />
                      </div>
                    </td>
                  );
                })}
                <td className="px-2 text-center align-middle">
                  <span
                    className={`inline-flex items-center rounded-md px-2 py-1 text-xs whitespace-nowrap ${
                      habilidad.bayesiano.dominada ? 'bg-blue-50 text-blue-700' : 'bg-gray-50 text-gray-500'
                    }`}
                    title="Estimación de probabilidad, no evidencia acreditada por etapa"
                  >
                    {formatBayesiano(habilidad.bayesiano.p, habilidad.bayesiano.n)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-[11px] text-gray-400">
        Estados posibles por etapa: {LUMA_ESTADOS_CASILLA.map((estado) => ETIQUETA_ESTADO[estado]).join(', ')}.
      </p>
      <p className="mt-1 text-[11px] text-gray-400">
        * Transferencia acreditada puede estar sobrecontada: el motor exige además que el ítem sea nuevo para
        el niño, y esa condición no siempre llega a esta vista.
      </p>
    </div>
  );
}
