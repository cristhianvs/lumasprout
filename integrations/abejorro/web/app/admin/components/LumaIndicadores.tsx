import type { LumaResumen } from '@/lib/lumaApi';
import { LumaIndicadorRespuestaError } from './LumaIndicadorRespuestaError';
import { LumaIndicadorAyuda } from './LumaIndicadorAyuda';
import { LumaIndicadorIndependencia } from './LumaIndicadorIndependencia';
import { LumaIndicadorAutonomia } from './LumaIndicadorAutonomia';
import { LumaIndicadorRitmo } from './LumaIndicadorRitmo';

interface LumaIndicadoresProps {
  resumen: LumaResumen | null;
}

/** Los indicadores del marco de investigacion del proyecto: nunca se inventan, solo se muestran los que llegan. */
export function LumaIndicadores({ resumen }: LumaIndicadoresProps) {
  return (
    <div className="space-y-6">
      <LumaIndicadorRespuestaError respuesta={resumen?.respuesta_ante_error} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LumaIndicadorAyuda ayuda={resumen?.ayuda} />
        <LumaIndicadorIndependencia intentos={resumen?.intentos} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LumaIndicadorAutonomia autonomia={resumen?.autonomia} modalidad={resumen?.estado_actual.experience} />
        <LumaIndicadorRitmo intentos={resumen?.intentos} inactividad={resumen?.inactividad} />
      </div>
    </div>
  );
}
