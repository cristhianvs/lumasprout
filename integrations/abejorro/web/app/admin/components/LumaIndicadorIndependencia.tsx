import type { LumaIntentos } from '@/lib/lumaApi';
import { Protocolo42BarChart, type Protocolo42BarraDato } from './Protocolo42BarChart';

interface LumaIndicadorIndependenciaProps {
  intentos: LumaIntentos | undefined;
}

/** Aciertos en primer intento sin ayuda, separados de los asistidos: nunca se suman en un mismo "aciertos". */
export function LumaIndicadorIndependencia({ intentos }: LumaIndicadorIndependenciaProps) {
  if (!intentos) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-1">Independencia</h3>
        <p className="text-xs text-gray-500">Sin datos todavía.</p>
      </div>
    );
  }

  const datos: Protocolo42BarraDato[] = [
    {
      clave: 'independientes',
      valor: intentos.aciertos_primer_intento_sin_ayuda,
      etiquetaEje: '1er intento, sin ayuda',
      ariaLabel: `Aciertos en primer intento sin ayuda: ${intentos.aciertos_primer_intento_sin_ayuda}`,
    },
    {
      clave: 'resueltos_independientes',
      valor: intentos.resueltos_independientes,
      etiquetaEje: 'Resueltos sin ayuda (con reintentos)',
      ariaLabel: `Resueltos de forma independiente, con o sin reintentos: ${intentos.resueltos_independientes}`,
    },
    {
      clave: 'asistidos',
      valor: intentos.asistidos,
      etiquetaEje: 'Asistidos',
      ariaLabel: `Aciertos asistidos: ${intentos.asistidos}`,
    },
    {
      clave: 'reintentos',
      valor: intentos.reintentos,
      etiquetaEje: 'Reintentos',
      ariaLabel: `Reintentos: ${intentos.reintentos}`,
    },
  ];

  return (
    <div className="space-y-1">
      <Protocolo42BarChart titulo="Independencia" datos={datos} />
      <p className="text-xs text-gray-500 px-1">
        Un acierto asistido no equivale a un acierto independiente: se cuentan por separado a propósito.
      </p>
    </div>
  );
}
