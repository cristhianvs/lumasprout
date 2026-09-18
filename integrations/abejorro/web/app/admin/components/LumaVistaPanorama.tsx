'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { lumaApi, type LumaPanorama, type LumaSeries } from '@/lib/lumaApi';
import { formatFechaHora } from '@/lib/protocolo42Format';
import { LumaPanoramaResumenCards } from './LumaPanoramaResumenCards';
import { LumaPanoramaActividad } from './LumaPanoramaActividad';
import { LumaPanoramaEmbudo } from './LumaPanoramaEmbudo';
import { LumaPanoramaMotivosCierre } from './LumaPanoramaMotivosCierre';
import { LumaPanoramaModalidades } from './LumaPanoramaModalidades';
import { LumaSeriesIndependencia } from './LumaSeriesIndependencia';
import { LumaSeriesRespuestaError } from './LumaSeriesRespuestaError';
import { LumaSeriesCasillasAcumuladas } from './LumaSeriesCasillasAcumuladas';
import { LumaSeriesAyuda } from './LumaSeriesAyuda';

const ERROR_PANORAMA_GENERICO = 'Error al cargar el panorama de LumaSprout';
const ERROR_SERIES_GENERICO = 'Error al cargar las series temporales';
const DIAS_SERIE = 30;

/**
 * El estado del estudio completo, no solo de una sesion en vivo. /panorama y /historico
 * fueron verificados contra Postgres real; /series todavia responde 500 en ese mismo
 * entorno (ver nota en lib/adminApi.ts), asi que su seccion se trata por separado: un
 * fallo ahi nunca debe impedir ver el resto del panorama, ya confirmado.
 */
export function LumaVistaPanorama() {
  const [panorama, setPanorama] = useState<LumaPanorama | null>(null);
  const [errorPanorama, setErrorPanorama] = useState<string | null>(null);
  const [cargandoPanorama, setCargandoPanorama] = useState(true);

  const [series, setSeries] = useState<LumaSeries | null>(null);
  const [errorSeries, setErrorSeries] = useState<string | null>(null);
  const [cargandoSeries, setCargandoSeries] = useState(true);

  const cargarPanorama = async () => {
    setCargandoPanorama(true);
    const resultado = await lumaApi.getPanorama();

    if (resultado.data) {
      setPanorama(resultado.data);
      setErrorPanorama(null);
    } else {
      setErrorPanorama(resultado.error || ERROR_PANORAMA_GENERICO);
    }

    setCargandoPanorama(false);
  };

  const cargarSeries = async () => {
    setCargandoSeries(true);
    const resultado = await lumaApi.getSeries(DIAS_SERIE);

    if (resultado.data) {
      setSeries(resultado.data);
      setErrorSeries(null);
    } else {
      setErrorSeries(resultado.error || ERROR_SERIES_GENERICO);
    }

    setCargandoSeries(false);
  };

  useEffect(() => {
    void cargarPanorama();
    void cargarSeries();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-gray-500">
          Vista general · Todos los participantes. Actividad, participación y
          evolución de las sesiones. Selecciona una sesión para explorar su
          recorrido.
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            void cargarPanorama();
            void cargarSeries();
          }}
          disabled={cargandoPanorama && cargandoSeries}
        >
          Actualizar
        </Button>
      </div>

      {cargandoPanorama && !panorama && !errorPanorama && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="animate-pulse text-gray-500">
            Cargando panorama...
          </div>
        </div>
      )}

      {errorPanorama && (
        <div className="bg-white rounded-lg shadow p-12 text-center space-y-4">
          <p className="text-red-600">{errorPanorama}</p>
          <Button variant="outline" size="sm" onClick={cargarPanorama}>
            Reintentar
          </Button>
        </div>
      )}

      {panorama && (
        <>
          <p className="text-xs text-gray-500">
            Generado el {formatFechaHora(panorama.generado)}
          </p>

          <LumaPanoramaResumenCards panorama={panorama} />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <LumaPanoramaMotivosCierre
              motivosCierre={panorama.motivos_cierre}
            />
            <LumaPanoramaModalidades modalidades={panorama.modalidades} />
          </div>

          <LumaPanoramaEmbudo embudoFases={panorama.embudo_fases} />

          <LumaPanoramaActividad sesionesPorDia={panorama.sesiones_por_dia} />
        </>
      )}

      <div className="border-t border-gray-200 pt-6 space-y-6">
        <h3 className="text-lg font-bold text-midnight">
          Series de los últimos {DIAS_SERIE} días
        </h3>

        {cargandoSeries && !series && !errorSeries && (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <div className="animate-pulse text-gray-500">
              Cargando series...
            </div>
          </div>
        )}

        {errorSeries && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700 space-y-2">
            <p>
              No se pudieron cargar las series temporales: {errorSeries}. Los
              gráficos de independencia, respuesta ante el error, casillas
              acreditadas y ayuda en el tiempo no están disponibles por ahora;
              el resto del panorama de arriba no depende de esto.
            </p>
            <Button variant="outline" size="sm" onClick={cargarSeries}>
              Reintentar
            </Button>
          </div>
        )}

        {series && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <LumaSeriesIndependencia serie={series.serie} />
            <LumaSeriesRespuestaError serie={series.serie} />
            <LumaSeriesCasillasAcumuladas serie={series.serie} />
            <LumaSeriesAyuda serie={series.serie} />
          </div>
        )}
      </div>
    </div>
  );
}
