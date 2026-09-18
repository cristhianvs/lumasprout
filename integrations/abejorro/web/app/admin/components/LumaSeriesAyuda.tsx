import type { LumaSerieDia } from '@/lib/lumaApi';
import { formatDiaCorto } from '@/lib/protocolo42Format';
import { LumaBarraApiladaChart, type LumaColumnaApilada } from './LumaBarraApiladaChart';

interface LumaSeriesAyudaProps {
  serie: LumaSerieDia[];
}

const LEYENDA = [
  { etiqueta: 'Elegida por el niño', colorClase: 'bg-golden' },
  { etiqueta: 'Impuesta por el sistema', colorClase: 'bg-bronze' },
];

/** Ayuda voluntaria frente a impuesta, dia a dia: nunca se mezclan en un solo numero. */
export function LumaSeriesAyuda({ serie }: LumaSeriesAyudaProps) {
  const columnas: LumaColumnaApilada[] = serie.map((dia) => ({
    clave: dia.dia,
    etiquetaEje: formatDiaCorto(dia.dia),
    ariaLabel: `${formatDiaCorto(dia.dia)}: ${dia.ayuda.voluntaria} voluntaria, ${dia.ayuda.impuesta} impuesta`,
    segmentos: [
      { clave: 'voluntaria', valor: dia.ayuda.voluntaria, colorClase: 'bg-golden' },
      { clave: 'impuesta', valor: dia.ayuda.impuesta, colorClase: 'bg-bronze' },
    ],
  }));

  return (
    <LumaBarraApiladaChart titulo="Ayuda voluntaria frente a impuesta en el tiempo" columnas={columnas} leyenda={LEYENDA} />
  );
}
