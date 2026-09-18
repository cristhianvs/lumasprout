export type LumaVista =
  | 'panorama'
  | 'sesiones'
  | 'participante'
  | 'diagnostico';

interface LumaSubTabsProps {
  vistaActiva: LumaVista;
  onCambiarVista: (vista: LumaVista) => void;
  /** El tab "Participante" solo tiene sentido una vez que se eligio una sesion. */
  participanteDisponible: boolean;
}

interface LumaSubTabDefinicion {
  id: LumaVista;
  label: string;
}

const LUMA_SUB_TABS: LumaSubTabDefinicion[] = [
  { id: 'panorama', label: 'Panorama' },
  { id: 'sesiones', label: 'Sesiones' },
  { id: 'participante', label: 'Participante' },
  { id: 'diagnostico', label: 'Diagnóstico del juego' },
];

/**
 * Sub-navegacion de la pestaña Luma. Las primeras tres vistas leen a las PERSONAS (como
 * va el estudio, que sesiones hay, como le va a un nino); "Diagnostico del juego" lee al
 * PRODUCTO (que parte del juego hay que arreglar). Son dos preguntas distintas a
 * proposito: por eso Diagnostico es su propia pestaña, no un bloque mas al final de
 * Panorama donde nadie bajaria a mirarlo.
 */
export function LumaSubTabs({
  vistaActiva,
  onCambiarVista,
  participanteDisponible,
}: LumaSubTabsProps) {
  return (
    <div className="inline-flex flex-wrap gap-1 rounded-lg border border-gray-200 bg-white p-1">
      {LUMA_SUB_TABS.map((tab) => {
        const deshabilitado =
          tab.id === 'participante' && !participanteDisponible;
        const activo = vistaActiva === tab.id;

        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onCambiarVista(tab.id)}
            disabled={deshabilitado}
            aria-current={activo ? 'page' : undefined}
            title={
              deshabilitado
                ? 'Elegí una sesión en "Sesiones" primero'
                : undefined
            }
            className={`rounded-md px-3 py-2.5 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-teal-600 ${
              activo
                ? 'bg-teal-700 text-white'
                : deshabilitado
                  ? 'text-gray-300 cursor-not-allowed'
                  : 'text-gray-500 hover:text-midnight hover:bg-gray-50'
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
