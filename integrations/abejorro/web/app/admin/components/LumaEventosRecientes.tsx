import type { LumaEvento } from '@/lib/lumaApi';
import { formatFechaHora } from '@/lib/protocolo42Format';

interface LumaEventosRecientesProps {
  eventos: LumaEvento[];
}

/** Los ultimos eventos crudos recibidos, para que el investigador pueda ver el pulso real del sondeo. */
export function LumaEventosRecientes({ eventos }: LumaEventosRecientesProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-1">Eventos recientes</h3>
      <p className="text-xs text-gray-500 mb-4">
        Los últimos eventos crudos recibidos en este sondeo (más reciente al final).
      </p>

      {eventos.length === 0 ? (
        <p className="text-sm text-gray-500">Todavía no ha llegado ningún evento nuevo.</p>
      ) : (
        <ul className="max-h-64 overflow-y-auto divide-y divide-gray-100 text-sm">
          {eventos.map((evento) => (
            <li key={evento.secuencia} className="flex justify-between gap-2 py-1.5">
              <span className="text-gray-500">#{evento.secuencia}</span>
              <span className="font-medium text-midnight">{evento.tipo}</span>
              <span className="text-gray-500">{formatFechaHora(evento.recibido_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
