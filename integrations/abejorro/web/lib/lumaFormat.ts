const SIN_DATOS_TEXTO = 'Sin datos';
const SEGUNDOS_POR_MINUTO = 60;
const MINUTOS_POR_HORA = 60;
const HORAS_POR_DIA = 24;

/** Convierte una antiguedad en segundos a "hace Ns" / "hace Nmin" para mostrarla de forma prominente. */
export function formatAntiguedad(segundos: number | null): string {
  if (segundos === null || Number.isNaN(segundos)) return SIN_DATOS_TEXTO;
  if (segundos < 1) return 'hace instantes';
  if (segundos < SEGUNDOS_POR_MINUTO) return `hace ${Math.floor(segundos)} s`;

  const minutos = Math.floor(segundos / SEGUNDOS_POR_MINUTO);
  if (minutos < MINUTOS_POR_HORA) return `hace ${minutos} min`;

  const horas = Math.floor(minutos / MINUTOS_POR_HORA);
  if (horas < HORAS_POR_DIA) return `hace ${horas} h`;

  const dias = Math.floor(horas / HORAS_POR_DIA);
  return `hace ${dias} d`;
}

/** Antiguedad en segundos entre una fecha ISO y "ahora" (en ms), o null si la fecha no existe o es invalida. */
export function calcularAntiguedadSegundos(fechaIso: string | null | undefined, ahoraMs: number): number | null {
  if (!fechaIso) return null;

  const fechaMs = new Date(fechaIso).getTime();
  if (Number.isNaN(fechaMs)) return null;

  return Math.max(0, Math.round((ahoraMs - fechaMs) / 1000));
}

/** Antiguedad en segundos entre una marca de tiempo en ms y "ahora" (en ms), o null si no hay marca. */
export function calcularAntiguedadSegundosDesdeMs(marcaMs: number | null, ahoraMs: number): number | null {
  if (marcaMs === null) return null;
  return Math.max(0, Math.round((ahoraMs - marcaMs) / 1000));
}

/** Duracion en segundos a "Nmin Ss" legible, para pausas y tiempo activo. */
export function formatDuracionSegundos(segundos: number | null): string {
  if (segundos === null || Number.isNaN(segundos)) return SIN_DATOS_TEXTO;

  const totalSegundos = Math.max(0, Math.round(segundos));
  const minutos = Math.floor(totalSegundos / SEGUNDOS_POR_MINUTO);
  const resto = totalSegundos % SEGUNDOS_POR_MINUTO;

  if (minutos === 0) return `${resto} s`;
  return `${minutos} min ${resto} s`;
}
