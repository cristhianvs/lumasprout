import type { LumaItemAnalisis } from '@/lib/lumaApi';
import { formatHabilidadRespaldo } from '@/lib/lumaConstantes';

interface LumaDiagnosticoErroresFormatoProps {
  items: LumaItemAnalisis[];
}

/**
 * El hallazgo mas accionable del panel, destacado aparte: un item con muchos errores de
 * formato no tiene un problema de matematicas, el niño sabe la respuesta y no consigue
 * introducirla. Es un problema de interfaz del juego, no del contenido.
 */
export function LumaDiagnosticoErroresFormato({ items }: LumaDiagnosticoErroresFormatoProps) {
  const conErrores = items
    .filter((item) => item.errores_de_formato > 0)
    .sort((a, b) => b.errores_de_formato - a.errores_de_formato);

  return (
    <div className="border-2 border-dashed border-amber-300 bg-amber-50 rounded-lg p-6">
      <h3 className="text-sm font-medium text-amber-800 uppercase tracking-wider mb-1">
        Errores de formato (input_validation)
      </h3>
      <p className="text-sm text-amber-700 mb-4">
        Un ítem con muchos errores de formato no tiene un problema de matemáticas: el niño sabe la
        respuesta y no consigue introducirla. Es un problema de interfaz del juego, no del contenido.
      </p>

      {conErrores.length === 0 ? (
        <p className="text-sm text-amber-600">Sin errores de formato detectados en los ítems actuales.</p>
      ) : (
        <ul className="space-y-1">
          {conErrores.map((item) => (
            <li key={item.variant_id} className="flex items-center justify-between text-sm">
              <span className="text-amber-900">
                {item.variant_id}
                {item.habilidad && (
                  <>
                    {' · '}
                    <span title={`id: ${item.habilidad}`}>{formatHabilidadRespaldo(item.habilidad)}</span>
                  </>
                )}
                {item.etapa && ` · ${item.etapa}`}
              </span>
              <span className="font-semibold text-amber-800">{item.errores_de_formato}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
