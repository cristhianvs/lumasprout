'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { lumaApi, type LumaSesion, type LumaHistorico } from '@/lib/lumaApi';
import { LumaSesionDetalle } from './LumaSesionDetalle';
import { LumaHistoricoSesiones } from './LumaHistoricoSesiones';
import { LumaHistoricoProgresion } from './LumaHistoricoProgresion';
import { LumaHistoricoBayesiano } from './LumaHistoricoBayesiano';

const ERROR_GENERICO = 'Error al cargar el histórico del participante';

interface LumaVistaParticipanteProps {
  runId: string | null;
  sesion: LumaSesion | null;
  onVolverASesiones: () => void;
}

/** La vista en vivo de una sesion mas, debajo, su historico como participante (verificado contra Postgres real). */
export function LumaVistaParticipante({
  runId,
  sesion,
  onVolverASesiones,
}: LumaVistaParticipanteProps) {
  const [historico, setHistorico] = useState<LumaHistorico | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    if (runId === null) {
      setHistorico(null);
      setError(null);
      return;
    }

    let cancelado = false;
    setCargando(true);

    void (async () => {
      const resultado = await lumaApi.getHistorico(runId);
      if (cancelado) return;

      if (resultado.data) {
        setHistorico(resultado.data);
        setError(null);
      } else {
        setError(resultado.error || ERROR_GENERICO);
      }
      setCargando(false);
    })();

    return () => {
      cancelado = true;
    };
  }, [runId]);

  if (runId === null) {
    return (
      <div className="bg-white rounded-lg shadow p-12 text-center space-y-2">
        <p className="text-gray-500">Todavía no elegiste una sesión.</p>
        <p className="text-sm text-gray-400">
          Andá a la pestaña &quot;Sesiones&quot; y elegí &quot;Ver en vivo&quot;
          en una fila.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <LumaSesionDetalle
        runId={runId}
        sesion={sesion}
        onVolver={onVolverASesiones}
      />

      <div className="border-t border-gray-200 pt-6 space-y-6">
        <h3 className="text-lg font-bold text-midnight">
          Histórico del participante
        </h3>
        <p className="text-sm text-gray-500">
          Datos de la partida seleccionada, agrupados por su identificador. No
          identifican por sí solos a un niño en distintos dispositivos. Aquí
          puedes revisar cuándo acreditó cada casilla y cómo cambió el criterio
          bayesiano por habilidad.
        </p>

        {cargando && !historico && !error && (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <div className="animate-pulse text-gray-500">
              Cargando histórico...
            </div>
          </div>
        )}

        {error && (
          <div className="bg-white rounded-lg shadow p-12 text-center space-y-4">
            <p className="text-red-600">{error}</p>
            <Button variant="outline" size="sm" onClick={() => setError(null)}>
              Cerrar
            </Button>
          </div>
        )}

        {historico && (
          <>
            <LumaHistoricoSesiones sesiones={historico.sesiones} />
            <LumaHistoricoProgresion
              progresionTemporal={historico.progresion_temporal}
            />
            <LumaHistoricoBayesiano
              bayesianoTemporal={historico.bayesiano_temporal}
            />
          </>
        )}
      </div>
    </div>
  );
}
