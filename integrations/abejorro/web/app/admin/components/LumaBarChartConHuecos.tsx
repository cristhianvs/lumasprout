import { LumaChartFrame, LumaDateAxis } from './LumaChartFrame';
import styles from './LumaCharts.module.css';
export interface LumaBarraConHuecoDato {
  clave: string;
  valor: number | null;
  ariaLabel: string;
  etiquetaEje: string;
  notaInferior?: string;
}
interface Props {
  titulo: string;
  datos: LumaBarraConHuecoDato[];
  esPorcentaje?: boolean;
}
export function LumaBarChartConHuecos({ titulo, datos, esPorcentaje }: Props) {
  const max = esPorcentaje ? 1 : Math.max(1, ...datos.map((d) => d.valor ?? 0));
  const format = (n: number) =>
    esPorcentaje ? `${Math.round(n * 100)}%` : n.toLocaleString('es-MX');
  return (
    <LumaChartFrame titulo={titulo}>
      <div className={styles.scale}>
        <span>{esPorcentaje ? 'Proporción' : 'Cantidad'}</span>
        <span>Escala: 0–{format(max)}</span>
      </div>
      <div className={styles.plot}>
        {datos.map((d) => (
          <div
            key={d.clave}
            className={styles.column}
            tabIndex={0}
            role="img"
            aria-label={
              d.valor === null ? `${d.ariaLabel}: sin datos` : d.ariaLabel
            }
          >
            <div className={styles.tooltip}>
              {d.etiquetaEje}
              <br />
              {d.valor === null ? 'Sin datos' : format(d.valor)}
              {d.notaInferior && (
                <>
                  <br />
                  {d.notaInferior}
                </>
              )}
            </div>
            <div
              className={
                d.valor === null
                  ? styles.gap
                  : d.valor === 0
                    ? styles.zero
                    : styles.bar
              }
              style={
                d.valor !== null && d.valor > 0
                  ? {
                      height: `${(100 * d.valor) / max}%`,
                      background: esPorcentaje ? '#0d9488' : '#2563eb',
                    }
                  : undefined
              }
            />
          </div>
        ))}
      </div>
      <LumaDateAxis labels={datos.map((d) => d.etiquetaEje)} />
      <p className={styles.note}>
        Pasa el cursor o enfoca una barra para ver el detalle. Círculo punteado:
        sin datos; marca sólida: cero.
      </p>
      <details className={styles.details}>
        <summary>Ver datos por fecha</summary>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Valor</th>
            </tr>
          </thead>
          <tbody>
            {datos.map((d) => (
              <tr key={d.clave}>
                <td>{d.etiquetaEje}</td>
                <td>
                  {d.valor === null ? 'Sin datos' : format(d.valor)}{' '}
                  {d.notaInferior}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </LumaChartFrame>
  );
}
