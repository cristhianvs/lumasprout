'use client';

import { useState } from 'react';
import { lumaApi, type LumaSesion } from '@/lib/lumaApi';
import { LUMA_INTERVALO_SONDEO_LISTA_MS } from '@/lib/lumaConstantes';
import { useVisiblePolling } from '@/hooks/useVisiblePolling';
import { LumaSubTabs, type LumaVista } from './LumaSubTabs';
import { LumaVistaPanorama } from './LumaVistaPanorama';
import { LumaVistaSesiones } from './LumaVistaSesiones';
import { LumaVistaParticipante } from './LumaVistaParticipante';
import { LumaVistaDiagnosticoJuego } from './LumaVistaDiagnosticoJuego';

const ERROR_GENERICO = 'Error al cargar las sesiones de LumaSprout';

export function LumaPanel() {
  const [vista, setVista] = useState<LumaVista>('panorama');

  const [sesiones, setSesiones] = useState<LumaSesion[] | null>(null);
  const [formaReconocida, setFormaReconocida] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runIdSeleccionado, setRunIdSeleccionado] = useState<string | null>(
    null
  );

  const loadSesiones = async () => {
    setIsLoading(true);
    const resultado = await lumaApi.getSesiones();

    if (resultado.data) {
      setSesiones(resultado.data.sesiones);
      setFormaReconocida(resultado.data.formaReconocida);
      setError(null);
    } else {
      setError(resultado.error || ERROR_GENERICO);
    }

    setIsLoading(false);
  };

  // La lista se refresca sola salvo cuando se esta viendo el detalle en vivo de una sesion
  // (esa vista tiene su propio sondeo, mas frecuente, sobre una sola sesion).
  useVisiblePolling(() => {
    if (vista !== 'participante') {
      void loadSesiones();
    }
  }, LUMA_INTERVALO_SONDEO_LISTA_MS);

  const handleSeleccionarSesion = (runId: string) => {
    setRunIdSeleccionado(runId);
    setVista('participante');
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-2xl font-bold text-midnight">Luma</h2>
        <LumaSubTabs
          vistaActiva={vista}
          onCambiarVista={setVista}
          participanteDisponible={runIdSeleccionado !== null}
        />
      </div>

      {vista === 'panorama' && <LumaVistaPanorama />}

      {vista === 'sesiones' && (
        <LumaVistaSesiones
          sesiones={sesiones}
          formaReconocida={formaReconocida}
          isLoading={isLoading}
          error={error}
          onActualizar={loadSesiones}
          onSeleccionar={handleSeleccionarSesion}
        />
      )}

      {vista === 'participante' && (
        <LumaVistaParticipante
          runId={runIdSeleccionado}
          sesion={
            sesiones?.find((sesion) => sesion.run_id === runIdSeleccionado) ??
            null
          }
          onVolverASesiones={() => setVista('sesiones')}
        />
      )}

      {vista === 'diagnostico' && <LumaVistaDiagnosticoJuego />}
    </div>
  );
}
