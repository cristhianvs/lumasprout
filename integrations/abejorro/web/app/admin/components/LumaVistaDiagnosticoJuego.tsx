'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { lumaApi, type LumaAdaptacion, type LumaItems, type LumaPuntosDeFuga } from '@/lib/lumaApi';
import { LumaDiagnosticoErroresFormato } from './LumaDiagnosticoErroresFormato';
import { LumaDiagnosticoTablaItems } from './LumaDiagnosticoTablaItems';
import { LumaDiagnosticoAndamiaje } from './LumaDiagnosticoAndamiaje';
import { LumaDiagnosticoAdaptacionTablas } from './LumaDiagnosticoAdaptacionTablas';
import { LumaDiagnosticoPuntosFuga } from './LumaDiagnosticoPuntosFuga';

const ERROR_ITEMS_GENERICO = 'Error al cargar el análisis por ítem';
const ERROR_ADAPTACION_GENERICO = 'Error al cargar la evaluación del motor adaptativo';
const ERROR_PUNTOS_FUGA_GENERICO = 'Error al cargar los puntos de fuga';

/**
 * A diferencia de Panorama/Sesiones/Participante (que leen a las PERSONAS), esta vista lee
 * al PRODUCTO: que parte del juego hay que arreglar. Es el core del proyecto segun el
 * usuario, asi que tiene su propia pestaña en vez de ser un bloque mas al final de otra
 * vista.
 *
 * Los nombres de evento que usa el backend (input_validation, adaptation, scaffold_shown)
 * fueron verificados por team-lead contra el motor real el 2026-09-18: un 0 en estos
 * indicadores es un 0 real, no un desajuste de nombre (ver nota en lib/adminApi.ts). La
 * forma de /items y /adaptacion tambien se verifico contra la API real, aunque con muy
 * pocos items de prueba, asi que el calculo en si se sigue mostrando tal cual llega, con
 * su `limite`, sin intentar adivinar ni corregir nada del lado del cliente.
 */
export function LumaVistaDiagnosticoJuego() {
  const [items, setItems] = useState<LumaItems | null>(null);
  const [errorItems, setErrorItems] = useState<string | null>(null);
  const [cargandoItems, setCargandoItems] = useState(true);

  const [adaptacion, setAdaptacion] = useState<LumaAdaptacion | null>(null);
  const [errorAdaptacion, setErrorAdaptacion] = useState<string | null>(null);
  const [cargandoAdaptacion, setCargandoAdaptacion] = useState(true);

  const [puntosDeFuga, setPuntosDeFuga] = useState<LumaPuntosDeFuga | null>(null);
  const [errorPuntosFuga, setErrorPuntosFuga] = useState<string | null>(null);
  const [cargandoPuntosFuga, setCargandoPuntosFuga] = useState(true);

  const cargarItems = async () => {
    setCargandoItems(true);
    const resultado = await lumaApi.getItems();
    if (resultado.data) {
      setItems(resultado.data);
      setErrorItems(null);
    } else {
      setErrorItems(resultado.error || ERROR_ITEMS_GENERICO);
    }
    setCargandoItems(false);
  };

  const cargarAdaptacion = async () => {
    setCargandoAdaptacion(true);
    const resultado = await lumaApi.getAdaptacion();
    if (resultado.data) {
      setAdaptacion(resultado.data);
      setErrorAdaptacion(null);
    } else {
      setErrorAdaptacion(resultado.error || ERROR_ADAPTACION_GENERICO);
    }
    setCargandoAdaptacion(false);
  };

  // Los puntos de fuga viven dentro de /panorama (decision de team-lead), no de /items ni
  // /adaptacion: se piden por separado para que un fallo ahi no tumbe el resto de esta vista.
  const cargarPuntosFuga = async () => {
    setCargandoPuntosFuga(true);
    const resultado = await lumaApi.getPanorama();
    if (resultado.data) {
      setPuntosDeFuga(resultado.data.puntos_de_fuga);
      setErrorPuntosFuga(null);
    } else {
      setErrorPuntosFuga(resultado.error || ERROR_PUNTOS_FUGA_GENERICO);
    }
    setCargandoPuntosFuga(false);
  };

  useEffect(() => {
    void cargarItems();
    void cargarAdaptacion();
    void cargarPuntosFuga();
  }, []);

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-500">
        Qué parte del juego hay que arreglar: análisis por ítem, errores de formato, y si el motor
        adaptativo está ayudando o estorbando.
      </p>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-600">
        Regla de esta vista: toda tasa se muestra siempre junto a su número de presentaciones. Lo que
        no tenga muestra suficiente se ve claramente atenuado o marcado: con 5 presentaciones, un 40%
        de aciertos no significa nada, y esta es la vista donde alguien va a decidir reescribir un
        ejercicio a partir de lo que ve aquí. Estos indicadores describen el comportamiento observado
        con el ítem, no su calidad pedagógica: un ítem difícil puede ser justo el que hace falta.
      </div>

      {cargandoItems && !items && !errorItems && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="animate-pulse text-gray-500">Cargando análisis por ítem...</div>
        </div>
      )}

      {errorItems && (
        <div className="bg-white rounded-lg shadow p-12 text-center space-y-4">
          <p className="text-red-600">{errorItems}</p>
          <Button variant="outline" size="sm" onClick={cargarItems}>
            Reintentar
          </Button>
        </div>
      )}

      {items && (
        <>
          <LumaDiagnosticoErroresFormato items={items.items} />
          <LumaDiagnosticoTablaItems items={items.items} umbralMuestraSuficiente={items.umbral_muestra_suficiente} />
        </>
      )}

      {cargandoAdaptacion && !adaptacion && !errorAdaptacion && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="animate-pulse text-gray-500">Cargando evaluación del motor adaptativo...</div>
        </div>
      )}

      {errorAdaptacion && (
        <div className="bg-white rounded-lg shadow p-12 text-center space-y-4">
          <p className="text-red-600">{errorAdaptacion}</p>
          <Button variant="outline" size="sm" onClick={cargarAdaptacion}>
            Reintentar
          </Button>
        </div>
      )}

      {adaptacion && (
        <>
          <LumaDiagnosticoAndamiaje
            efecto={adaptacion.efecto_del_andamiaje}
            oportunidades={adaptacion.oportunidades_independientes}
          />
          <LumaDiagnosticoAdaptacionTablas
            porRazonDecision={adaptacion.por_razon_decision}
            porReglaMidReto={adaptacion.por_regla_mid_reto}
          />
          <p className="text-xs text-gray-500">{adaptacion.limite}</p>
        </>
      )}

      {cargandoPuntosFuga && !puntosDeFuga && !errorPuntosFuga && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="animate-pulse text-gray-500">Cargando puntos de fuga...</div>
        </div>
      )}

      {errorPuntosFuga && (
        <div className="bg-white rounded-lg shadow p-12 text-center space-y-4">
          <p className="text-red-600">{errorPuntosFuga}</p>
          <Button variant="outline" size="sm" onClick={cargarPuntosFuga}>
            Reintentar
          </Button>
        </div>
      )}

      {puntosDeFuga && <LumaDiagnosticoPuntosFuga puntosDeFuga={puntosDeFuga} />}
    </div>
  );
}
