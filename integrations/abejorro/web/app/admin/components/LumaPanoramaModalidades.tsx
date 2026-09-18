import type { LumaModalidadUso } from '@/lib/lumaApi';
import { formatModalidad } from '@/lib/lumaConstantes';
import { LumaCategoryChart, type LumaCategoryDato } from './LumaCategoryChart';

interface LumaPanoramaModalidadesProps {
  modalidades: LumaModalidadUso[];
}

/** Descriptiva a proposito: una modalidad mas usada NO implica que se aprenda mejor con ella. */
export function LumaPanoramaModalidades({
  modalidades,
}: LumaPanoramaModalidadesProps) {
  if (modalidades.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-1">
          Distribución de modalidades
        </h3>
        <p className="text-sm text-gray-500">
          Sin datos de modalidades todavía.
        </p>
      </div>
    );
  }

  const datos: LumaCategoryDato[] = modalidades.map((modalidad) => ({
    clave: modalidad.experience,
    valor: modalidad.eventos,
    etiquetaEje: formatModalidad(modalidad.experience),
    ariaLabel: `${formatModalidad(modalidad.experience)}: ${modalidad.eventos} eventos`,
  }));

  return (
    <div className="space-y-1">
      <LumaCategoryChart titulo="Distribución de modalidades" datos={datos} />
      <p className="text-xs text-gray-500 px-1">{modalidades[0]?.limite}</p>
    </div>
  );
}
