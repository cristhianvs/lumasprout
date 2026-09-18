import type { LumaDecisionAdaptacion } from '@/lib/lumaApi';
import { LumaDecisionAdaptacionFila } from './LumaDecisionAdaptacionFila';

interface LumaCircuitoAdaptacionProps {
  decisiones: LumaDecisionAdaptacion[] | undefined;
}

/** Por cada decision del motor de adaptacion: su motivo, lo aplicado, y que paso despues. */
export function LumaCircuitoAdaptacion({ decisiones }: LumaCircuitoAdaptacionProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-1">Circuito de adaptación</h3>
      <p className="text-xs text-gray-500 mb-4">
        Cada decisión enlazada con la evidencia en la que se apoyó y con lo que pasó después.
      </p>

      {!decisiones || decisiones.length === 0 ? (
        <p className="text-sm text-gray-500">Sin decisiones de adaptación todavía.</p>
      ) : (
        <ul className="space-y-2">
          {decisiones.map((decision, indice) => (
            <LumaDecisionAdaptacionFila key={decision.decision_id ?? `sin-id-${indice}`} decision={decision} indice={indice} />
          ))}
        </ul>
      )}
    </div>
  );
}
