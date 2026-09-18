import type { LumaSerieDia } from '@/lib/lumaApi';
import { formatDiaCorto } from '@/lib/protocolo42Format';
import { LumaBarraApiladaChart, type LumaColumnaApilada } from './LumaBarraApiladaChart';

interface LumaSeriesRespuestaErrorProps {
  serie: LumaSerieDia[];
}

const LEYENDA = [
  { etiqueta: 'Reintento inmediato', colorClase: 'bg-golden' },
  { etiqueta: 'Busca ayuda', colorClase: 'bg-bronze' },
  { etiqueta: 'Inactividad / bloqueo', colorClase: 'bg-midnight' },
  { etiqueta: 'Sin clasificar', colorClase: 'bg-gray-300' },
];

/** Como lo toma el niño ante cada fallo, dia a dia. Las 4 categorias son siempre numeros reales, nunca null. */
export function LumaSeriesRespuestaError({ serie }: LumaSeriesRespuestaErrorProps) {
  const columnas: LumaColumnaApilada[] = serie.map((dia) => {
    const r = dia.respuesta_ante_error;
    const total = r.reintento_inmediato + r.busca_ayuda + r.inactividad_bloqueo + r.sin_clasificar;

    return {
      clave: dia.dia,
      etiquetaEje: formatDiaCorto(dia.dia),
      ariaLabel: `${formatDiaCorto(dia.dia)}: ${total} fallos (reintento ${r.reintento_inmediato}, ayuda ${r.busca_ayuda}, inactividad ${r.inactividad_bloqueo}, sin clasificar ${r.sin_clasificar})`,
      segmentos: [
        { clave: 'reintento', valor: r.reintento_inmediato, colorClase: 'bg-golden' },
        { clave: 'ayuda', valor: r.busca_ayuda, colorClase: 'bg-bronze' },
        { clave: 'inactividad', valor: r.inactividad_bloqueo, colorClase: 'bg-midnight' },
        { clave: 'sin_clasificar', valor: r.sin_clasificar, colorClase: 'bg-gray-300' },
      ],
    };
  });

  return (
    <div className="space-y-1">
      <LumaBarraApiladaChart titulo="Respuesta ante el error por día" columnas={columnas} leyenda={LEYENDA} />
      <p className="text-xs text-gray-500 px-1">{serie[0]?.respuesta_ante_error.limite}</p>
    </div>
  );
}
