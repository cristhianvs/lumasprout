import type { LumaPuntosDeFuga } from '@/lib/lumaApi';
import { formatFase, LUMA_ESCENAS, formatHabilidadRespaldo } from '@/lib/lumaConstantes';

interface LumaDiagnosticoPuntosFugaProps {
  puntosDeFuga: LumaPuntosDeFuga;
}

function etiquetaEscena(scene: number): string {
  const escena = LUMA_ESCENAS.find((definicion) => definicion.indice === scene);
  return escena ? `${scene} ${escena.etiqueta}` : String(scene);
}

/** Donde abandonan y donde se acaban los ejercicios: decisiones de diseño del juego, no del estudio. */
export function LumaDiagnosticoPuntosFuga({ puntosDeFuga }: LumaDiagnosticoPuntosFugaProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-6">
      <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">Puntos de fuga y banco agotado</h3>

      <div>
        <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Abandono por fase</h4>
        {puntosDeFuga.abandono_por_fase.length === 0 ? (
          <p className="text-sm text-gray-500">Sin abandonos registrados.</p>
        ) : (
          <ul className="flex flex-wrap gap-2 text-xs">
            {puntosDeFuga.abandono_por_fase.map((fila) => (
              <li key={fila.fase} className="bg-gray-100 rounded-full px-3 py-1 text-midnight">
                {formatFase(fila.fase)}: {fila.participantes}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
          Abandono por escena (dentro de la aventura)
        </h4>
        {puntosDeFuga.abandono_por_escena.length === 0 ? (
          <p className="text-sm text-gray-500">Sin abandonos registrados en la aventura.</p>
        ) : (
          <ul className="flex flex-wrap gap-2 text-xs">
            {puntosDeFuga.abandono_por_escena.map((fila) => (
              <li key={fila.scene} className="bg-gray-100 rounded-full px-3 py-1 text-midnight">
                {etiquetaEscena(fila.scene)}: {fila.participantes}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
          Abandono por habilidad y etapa (dentro del taller)
        </h4>
        {puntosDeFuga.abandono_por_habilidad_y_etapa.length === 0 ? (
          <p className="text-sm text-gray-500">Sin abandonos registrados en el taller.</p>
        ) : (
          <ul className="flex flex-wrap gap-2 text-xs">
            {puntosDeFuga.abandono_por_habilidad_y_etapa.map((fila, indice) => (
              <li
                key={`${fila.habilidad}-${fila.etapa}-${indice}`}
                className="bg-gray-100 rounded-full px-3 py-1 text-midnight"
                title={`id: ${fila.habilidad}`}
              >
                {formatHabilidadRespaldo(fila.habilidad)} · {fila.etapa}: {fila.participantes}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Banco de ejercicios agotado</h4>
        {puntosDeFuga.banco_agotado.length === 0 ? (
          <p className="text-sm text-gray-500">El banco de ejercicios no se agotó todavía.</p>
        ) : (
          <ul className="flex flex-wrap gap-2 text-xs">
            {puntosDeFuga.banco_agotado.map((fila, indice) => (
              <li
                key={`${fila.habilidad}-${fila.etapa}-${indice}`}
                className="bg-gray-100 rounded-full px-3 py-1 text-midnight"
                title={fila.habilidad ? `id: ${fila.habilidad}` : undefined}
              >
                {fila.habilidad ? formatHabilidadRespaldo(fila.habilidad) : 'Sin habilidad'}
                {fila.etapa ? ` · ${fila.etapa}` : ''}: {fila.veces}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
