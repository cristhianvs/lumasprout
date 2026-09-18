'use client';

import { useState } from 'react';
import type { LumaDecisionAdaptacion } from '@/lib/lumaApi';
import { formatMotivoDecision } from '@/lib/lumaConstantes';

interface LumaDecisionAdaptacionFilaProps {
  decision: LumaDecisionAdaptacion;
  indice: number;
}

/** Una decision del circuito de adaptacion: su motivo, lo aplicado, en cuanta evidencia se apoyo y su resultado. */
export function LumaDecisionAdaptacionFila({ decision, indice }: LumaDecisionAdaptacionFilaProps) {
  const [expandido, setExpandido] = useState(false);
  const idDetalle = `luma-decision-resultado-${indice}`;
  const hayResultado = decision.resultado !== null && Object.keys(decision.resultado).length > 0;

  return (
    <li className="border border-gray-100 rounded-md p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-midnight">{formatMotivoDecision(decision.reason)}</p>
        <span className="text-xs text-gray-500">
          Basada en {decision.evidencia_cantidad} {decision.evidencia_cantidad === 1 ? 'observación' : 'observaciones'}
        </span>
      </div>

      <p className="mt-1 text-sm text-gray-500">
        Aplicado: <span className="text-midnight font-medium">{decision.effective_support ?? 'Sin dato'}</span>
      </p>

      <p className="mt-2 text-xs">
        {decision.resuelta ? (
          <span className="text-midnight">Resultado evaluado</span>
        ) : (
          <span className="text-gray-500">Todavía sin evaluar</span>
        )}
      </p>

      {hayResultado && decision.resultado && (
        <>
          <button
            type="button"
            onClick={() => setExpandido((valor) => !valor)}
            aria-expanded={expandido}
            aria-controls={idDetalle}
            className="mt-2 text-xs font-medium text-bronze hover:text-golden focus:outline-none focus:ring-2 focus:ring-golden rounded"
          >
            {expandido ? 'Ocultar resultado' : 'Ver resultado'}
          </button>

          {expandido && (
            <dl id={idDetalle} className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-1 text-xs bg-gray-50 rounded-md p-2">
              {Object.entries(decision.resultado).map(([clave, valor]) => (
                <div key={clave} className="flex justify-between gap-2">
                  <dt className="text-gray-500">{clave}</dt>
                  <dd className="text-midnight font-medium truncate">{String(valor)}</dd>
                </div>
              ))}
            </dl>
          )}
        </>
      )}
    </li>
  );
}
