import { formatAntiguedad } from '@/lib/lumaFormat';
import { LUMA_UMBRAL_DATO_ENVEJECIDO_SEGUNDOS } from '@/lib/lumaConstantes';

interface LumaAntiguedadBadgeProps {
  segundos: number | null;
  etiqueta?: string;
}

/** Muestra "hace Ns" de forma prominente; cambia a rojo cuando el dato lleva envejeciendo mas de 30 s. */
export function LumaAntiguedadBadge({ segundos, etiqueta }: LumaAntiguedadBadgeProps) {
  const texto = formatAntiguedad(segundos);
  const envejecido = segundos !== null && segundos > LUMA_UMBRAL_DATO_ENVEJECIDO_SEGUNDOS;
  const sinDatos = segundos === null;

  const colorClases = envejecido
    ? 'bg-red-50 text-red-700'
    : sinDatos
      ? 'bg-gray-100 text-gray-500'
      : 'bg-golden/20 text-midnight';

  const puntoClases = envejecido ? 'bg-red-500' : sinDatos ? 'bg-gray-400' : 'bg-golden animate-pulse';

  return (
    <span
      role="status"
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium whitespace-nowrap ${colorClases}`}
    >
      <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${puntoClases}`} />
      {etiqueta ? `${etiqueta}: ${texto}` : texto}
    </span>
  );
}
