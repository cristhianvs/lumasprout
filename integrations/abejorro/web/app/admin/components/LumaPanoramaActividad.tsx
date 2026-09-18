import type { LumaSesionesPorDia } from '@/lib/lumaApi';
import { formatDiaCorto } from '@/lib/protocolo42Format';
import {
  LumaBarChartConHuecos,
  type LumaBarraConHuecoDato,
} from './LumaBarChartConHuecos';

interface LumaPanoramaActividadProps {
  sesionesPorDia: LumaSesionesPorDia[];
}

/**
 * Actividad por día segun la reporta /panorama: solo trae los días con al menos una sesión
 * (a diferencia de /series, que si rellena todo el rango). No se inventan días intermedios
 * en cero: se muestran los días tal como los devuelve la API, en su orden.
 */
export function LumaPanoramaActividad({
  sesionesPorDia,
}: LumaPanoramaActividadProps) {
  if (sesionesPorDia.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-1">
          Actividad por día
        </h3>
        <p className="text-sm text-gray-500">
          Sin actividad registrada todavía.
        </p>
      </div>
    );
  }

  const datos: LumaBarraConHuecoDato[] = sesionesPorDia.map((dia) => ({
    clave: dia.dia,
    valor: dia.sesiones,
    etiquetaEje: formatDiaCorto(dia.dia),
    ariaLabel: `${formatDiaCorto(dia.dia)}: ${dia.sesiones} sesiones, ${dia.eventos} eventos`,
    notaInferior: `${dia.eventos} ev.`,
  }));

  return <LumaBarChartConHuecos titulo="Actividad por día" datos={datos} />;
}
