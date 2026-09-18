import type { LumaResumen } from '@/lib/lumaApi';
import { formatDuracionSegundos } from '@/lib/lumaFormat';
import { Protocolo42BarChart, type Protocolo42BarraDato } from './Protocolo42BarChart';

interface LumaIndicadorRespuestaErrorProps {
  respuesta: LumaResumen['respuesta_ante_error'] | undefined;
}

const MS_POR_SEGUNDO = 1000;

function notaLatencia(medianaMs: number | null): string | undefined {
  if (medianaMs === null) return undefined;
  return `mediana ${formatDuracionSegundos(medianaMs / MS_POR_SEGUNDO)}`;
}

/** La señal más importante del panel: qué hace el niño justo después de cada fallo matemático. */
export function LumaIndicadorRespuestaError({ respuesta }: LumaIndicadorRespuestaErrorProps) {
  if (!respuesta) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-1">
          Respuesta ante el error
        </h3>
        <p className="text-sm text-gray-500">Sin datos todavía.</p>
      </div>
    );
  }

  const datos: Protocolo42BarraDato[] = [
    {
      clave: 'reintento',
      valor: respuesta.reintento_inmediato,
      etiquetaEje: 'Reintento inmediato',
      ariaLabel: `Reintento inmediato: ${respuesta.reintento_inmediato}`,
      notaInferior: notaLatencia(respuesta.latencia_mediana_ms.reintento_inmediato),
    },
    {
      clave: 'ayuda',
      valor: respuesta.busca_ayuda,
      etiquetaEje: 'Busca ayuda',
      ariaLabel: `Busca ayuda: ${respuesta.busca_ayuda}`,
      notaInferior: notaLatencia(respuesta.latencia_mediana_ms.busca_ayuda),
    },
    {
      clave: 'inactividad',
      valor: respuesta.inactividad_bloqueo,
      etiquetaEje: 'Inactividad / bloqueo',
      ariaLabel: `Inactividad o bloqueo: ${respuesta.inactividad_bloqueo}`,
      notaInferior: notaLatencia(respuesta.latencia_mediana_ms.inactividad_bloqueo),
    },
    {
      clave: 'sin_clasificar',
      valor: respuesta.sin_clasificar,
      etiquetaEje: 'Sesión cortada tras el error',
      ariaLabel: `Sin clasificar (sesión cortada justo después del error): ${respuesta.sin_clasificar}`,
    },
  ];

  return (
    <div className="space-y-1">
      <Protocolo42BarChart titulo="Respuesta ante el error (la señal más importante)" datos={datos} />
      <p className="text-xs text-gray-500 px-1">{respuesta.limite}</p>
    </div>
  );
}
