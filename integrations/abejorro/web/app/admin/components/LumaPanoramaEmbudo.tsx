import type { LumaEmbudoFase } from '@/lib/lumaApi';
import { formatFase } from '@/lib/lumaConstantes';
import { LumaCategoryChart, type LumaCategoryDato } from './LumaCategoryChart';

interface LumaPanoramaEmbudoProps {
  embudoFases: LumaEmbudoFase[];
}

/** Cuantos participantes llegan de welcome a math: resumen aqui, el detalle de fuga vive en Diagnóstico del juego. */
export function LumaPanoramaEmbudo({ embudoFases }: LumaPanoramaEmbudoProps) {
  const datos: LumaCategoryDato[] = embudoFases.map((fase) => ({
    clave: fase.fase,
    valor: fase.participantes,
    etiquetaEje: formatFase(fase.fase),
    ariaLabel: `${formatFase(fase.fase)}: ${fase.participantes} participantes`,
  }));

  return <LumaCategoryChart titulo="Embudo de fases" datos={datos} />;
}
