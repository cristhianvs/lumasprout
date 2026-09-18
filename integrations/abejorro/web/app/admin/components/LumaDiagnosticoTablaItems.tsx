'use client';

import { useState } from 'react';
import type { LumaItemAnalisis } from '@/lib/lumaApi';
import { formatHabilidadRespaldo } from '@/lib/lumaConstantes';

interface LumaDiagnosticoTablaItemsProps {
  items: LumaItemAnalisis[];
  umbralMuestraSuficiente: number;
}

type LumaColumnaOrdenable = 'habilidad' | 'etapa' | 'variant_id' | 'presentaciones' | 'acierto';

const COLUMNAS_TABLA = 8;
const PORCENTAJE = 100;

function valorOrden(item: LumaItemAnalisis, columna: LumaColumnaOrdenable): string | number {
  switch (columna) {
    case 'habilidad':
      return item.habilidad ?? '';
    case 'etapa':
      return item.etapa ?? '';
    case 'variant_id':
      return item.variant_id;
    case 'presentaciones':
      return item.presentaciones;
    case 'acierto':
      return item.acierto_primer_intento_sin_ayuda ?? -1;
  }
}

function formatPatronesError(patrones: Record<string, number>): string {
  const entradas = Object.entries(patrones);
  if (entradas.length === 0) return 'Ninguno';
  return entradas.map(([patron, cantidad]) => `${patron} (${cantidad})`).join(', ');
}

/** Tabla ordenable por habilidad, etapa CPA y variante. Toda tasa se muestra con sus presentaciones. */
export function LumaDiagnosticoTablaItems({ items, umbralMuestraSuficiente }: LumaDiagnosticoTablaItemsProps) {
  const [columnaOrden, setColumnaOrden] = useState<LumaColumnaOrdenable>('habilidad');
  const [ascendente, setAscendente] = useState(true);

  const itemsOrdenados = [...items].sort((a, b) => {
    const valorA = valorOrden(a, columnaOrden);
    const valorB = valorOrden(b, columnaOrden);
    const comparacion = valorA < valorB ? -1 : valorA > valorB ? 1 : 0;
    return ascendente ? comparacion : -comparacion;
  });

  const alternarOrden = (columna: LumaColumnaOrdenable) => {
    if (columna === columnaOrden) {
      setAscendente((valor) => !valor);
    } else {
      setColumnaOrden(columna);
      setAscendente(true);
    }
  };

  const encabezado = (columna: LumaColumnaOrdenable, etiqueta: string, alineacion: 'left' | 'right' = 'left') => (
    <th scope="col" className={`px-3 py-3 text-${alineacion} text-xs font-medium text-gray-500 uppercase tracking-wider`}>
      <button type="button" onClick={() => alternarOrden(columna)} className="hover:text-midnight focus:outline-none focus:ring-2 focus:ring-golden rounded">
        {etiqueta}
        {columnaOrden === columna && (ascendente ? ' ▲' : ' ▼')}
      </button>
    </th>
  );

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider px-6 pt-6 pb-2">
        Análisis por ítem ({items.length})
      </h3>
      <p className="text-xs text-gray-500 px-6 pb-2">
        Ítems con menos de {umbralMuestraSuficiente} presentaciones aparecen atenuados: con pocas
        presentaciones una tasa no significa nada.
      </p>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {encabezado('variant_id', 'Ítem')}
              {encabezado('habilidad', 'Habilidad')}
              {encabezado('etapa', 'Etapa')}
              {encabezado('presentaciones', 'Presentaciones', 'right')}
              {encabezado('acierto', 'Acierto 1er intento sin ayuda', 'right')}
              <th scope="col" className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Intentos mediana</th>
              <th scope="col" className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Pidió ayuda</th>
              <th scope="col" className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Abandonos</th>
              <th scope="col" className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Patrones de error</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {itemsOrdenados.length === 0 ? (
              <tr>
                <td colSpan={COLUMNAS_TABLA} className="px-6 py-12 text-center text-gray-500">
                  Sin ítems analizados todavía.
                </td>
              </tr>
            ) : (
              itemsOrdenados.map((item) => (
                <tr key={item.variant_id} className={item.muestra_suficiente ? undefined : 'opacity-50'}>
                  <th scope="row" className="px-3 py-3 text-left text-sm font-medium text-midnight whitespace-nowrap">
                    {item.variant_id}
                    {!item.muestra_suficiente && (
                      <span className="ml-1 text-[10px] font-normal text-gray-400">(muestra insuficiente)</span>
                    )}
                  </th>
                  <td className="px-3 py-3 text-left text-sm text-gray-500" title={item.habilidad ? `id: ${item.habilidad}` : undefined}>
                    {item.habilidad ? formatHabilidadRespaldo(item.habilidad) : 'Sin dato'}
                  </td>
                  <td className="px-3 py-3 text-left text-sm text-gray-500">{item.etapa ?? 'Sin dato'}</td>
                  <td className="px-3 py-3 text-right text-sm text-gray-500">{item.presentaciones}</td>
                  <td className="px-3 py-3 text-right text-sm text-gray-500">
                    {item.acierto_primer_intento_sin_ayuda !== null
                      ? `${Math.round(item.acierto_primer_intento_sin_ayuda * PORCENTAJE)}%`
                      : 'Sin dato'}
                  </td>
                  <td className="px-3 py-3 text-right text-sm text-gray-500">{item.intentos_mediana ?? 'Sin dato'}</td>
                  <td className="px-3 py-3 text-right text-sm text-gray-500">
                    {item.pidio_ayuda !== null ? `${Math.round(item.pidio_ayuda * PORCENTAJE)}%` : 'Sin dato'}
                  </td>
                  <td className="px-3 py-3 text-right text-sm text-gray-500">{item.abandonos}</td>
                  <td className="px-3 py-3 text-left text-sm text-gray-500">{formatPatronesError(item.patrones_error)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <p className="px-6 py-4 text-xs text-gray-400 border-t border-gray-100">{items[0]?.limite}</p>
    </div>
  );
}
