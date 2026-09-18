import type { LumaMotivoCierreConteo } from '@/lib/lumaApi';
import { formatMotivoCierreAgregado } from '@/lib/lumaConstantes';
import { LumaCategoryChart, type LumaCategoryDato } from './LumaCategoryChart';

interface LumaPanoramaMotivosCierreProps {
  motivosCierre: LumaMotivoCierreConteo[];
}

/** "bank_exhausted" nunca se agrupa visualmente con "mastery": el juego se quedo sin preguntas, no es exito. */
export function LumaPanoramaMotivosCierre({
  motivosCierre,
}: LumaPanoramaMotivosCierreProps) {
  const datos: LumaCategoryDato[] = motivosCierre.map((motivo) => ({
    clave: motivo.motivo,
    valor: motivo.participantes,
    etiquetaEje: formatMotivoCierreAgregado(motivo.motivo),
    ariaLabel: `${formatMotivoCierreAgregado(motivo.motivo)}: ${motivo.participantes} participantes`,
  }));

  return <LumaCategoryChart titulo="Motivos de cierre" datos={datos} />;
}
