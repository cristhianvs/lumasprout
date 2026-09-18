import type { LumaSerieDia } from '@/lib/lumaApi';
import { formatDiaCorto } from '@/lib/protocolo42Format';
import { LumaBarChartConHuecos, type LumaBarraConHuecoDato } from './LumaBarChartConHuecos';

interface LumaSeriesIndependenciaProps {
  serie: LumaSerieDia[];
}

/** El indicador de eficacia mas directo: aciertos sin ayuda sobre el total, por dia. Null es un hueco real. */
export function LumaSeriesIndependencia({ serie }: LumaSeriesIndependenciaProps) {
  const datos: LumaBarraConHuecoDato[] = serie.map((dia) => ({
    clave: dia.dia,
    valor: dia.independencia,
    etiquetaEje: formatDiaCorto(dia.dia),
    ariaLabel:
      dia.independencia === null
        ? `${formatDiaCorto(dia.dia)}: sin resoluciones que medir`
        : `${formatDiaCorto(dia.dia)}: independencia ${Math.round(dia.independencia * 100)}%`,
  }));

  return (
    <div className="space-y-1">
      <LumaBarChartConHuecos titulo="Independencia en el tiempo" datos={datos} esPorcentaje />
      <p className="text-xs text-gray-500 px-1">{serie[0]?.limite_independencia}</p>
    </div>
  );
}
