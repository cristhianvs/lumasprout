import type { LumaSerieDia } from '@/lib/lumaApi';
import { formatDiaCorto } from '@/lib/protocolo42Format';
import {
  LumaBarChartConHuecos,
  type LumaBarraConHuecoDato,
} from './LumaBarChartConHuecos';

interface LumaSeriesCasillasAcumuladasProps {
  serie: LumaSerieDia[];
}

/** La curva de aprendizaje real del estudio: `casillas_acreditadas` es un delta diario, se acumula aqui. */
export function LumaSeriesCasillasAcumuladas({
  serie,
}: LumaSeriesCasillasAcumuladasProps) {
  let acumulado = 0;
  const datos: LumaBarraConHuecoDato[] = serie.map((dia) => {
    acumulado += dia.casillas_acreditadas;
    return {
      clave: dia.dia,
      valor: acumulado,
      etiquetaEje: formatDiaCorto(dia.dia),
      ariaLabel: `${formatDiaCorto(dia.dia)}: ${acumulado} casillas acreditadas acumuladas (+${dia.casillas_acreditadas} ese día)`,
      notaInferior:
        dia.casillas_acreditadas > 0
          ? `+${dia.casillas_acreditadas}`
          : undefined,
    };
  });

  return (
    <LumaBarChartConHuecos
      titulo="Casillas CPA acreditadas (acumulado)"
      datos={datos}
    />
  );
}
