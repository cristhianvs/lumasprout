import type { LumaAyuda } from '@/lib/lumaApi';
import { Protocolo42BarChart, type Protocolo42BarraDato } from './Protocolo42BarChart';

interface LumaIndicadorAyudaProps {
  ayuda: LumaAyuda | undefined;
}

/** Ayuda pedida (voluntaria) frente a ayuda impuesta por el sistema: nunca se mezclan en un solo número. */
export function LumaIndicadorAyuda({ ayuda }: LumaIndicadorAyudaProps) {
  if (!ayuda) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-1">Ayuda</h3>
        <p className="text-xs text-gray-500">Sin datos todavía.</p>
      </div>
    );
  }

  const datos: Protocolo42BarraDato[] = [
    {
      clave: 'voluntaria',
      valor: ayuda.apoyo_voluntario,
      etiquetaEje: 'Elegida por el niño',
      ariaLabel: `Ayuda elegida por el niño: ${ayuda.apoyo_voluntario}`,
    },
    {
      clave: 'impuesta',
      valor: ayuda.apoyo_impuesto,
      etiquetaEje: 'Impuesta por el sistema',
      ariaLabel: `Ayuda impuesta por el sistema: ${ayuda.apoyo_impuesto}`,
    },
    {
      clave: 'pistas',
      valor: ayuda.hint_requested,
      etiquetaEje: 'Pistas pedidas',
      ariaLabel: `Pistas pedidas: ${ayuda.hint_requested}`,
    },
  ];

  return <Protocolo42BarChart titulo="Ayuda pedida frente a ayuda impuesta" datos={datos} />;
}
