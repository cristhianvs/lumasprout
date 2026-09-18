import { LumaChartFrame, LumaDateAxis } from './LumaChartFrame';
import styles from './LumaCharts.module.css';
export interface LumaSegmentoApilado {
  clave: string;
  valor: number;
  colorClase: string;
}
export interface LumaColumnaApilada {
  clave: string;
  etiquetaEje: string;
  ariaLabel: string;
  segmentos: LumaSegmentoApilado[];
}
export interface LumaLeyendaEntrada {
  etiqueta: string;
  colorClase: string;
}
const COLORS: Record<string, string> = {
  'bg-golden': '#0d9488',
  'bg-bronze': '#8b5cf6',
  'bg-midnight': '#d97706',
  'bg-gray-300': '#94a3b8',
};
export function LumaBarraApiladaChart({
  titulo,
  columnas,
  leyenda,
}: {
  titulo: string;
  columnas: LumaColumnaApilada[];
  leyenda: LumaLeyendaEntrada[];
}) {
  const total = (c: LumaColumnaApilada) =>
    c.segmentos.reduce((s, d) => s + d.valor, 0);
  const max = Math.max(1, ...columnas.map(total));
  return (
    <LumaChartFrame titulo={titulo}>
      <ul className={styles.legend}>
        {leyenda.map((l) => (
          <li key={l.etiqueta}>
            <span
              className={styles.dot}
              style={{ background: COLORS[l.colorClase] || '#64748b' }}
            />
            {l.etiqueta}
          </li>
        ))}
      </ul>
      <div className={styles.scale}>
        <span>Eventos por día</span>
        <span>Escala: 0–{max}</span>
      </div>
      <div className={styles.plot}>
        {columnas.map((c) => (
          <div
            key={c.clave}
            className={styles.column}
            tabIndex={0}
            role="img"
            aria-label={c.ariaLabel}
          >
            <div className={styles.tooltip}>{c.ariaLabel}</div>
            <div
              className={total(c) === 0 ? styles.zero : styles.bar}
              style={
                total(c) > 0
                  ? {
                      height: `${(100 * total(c)) / max}%`,
                      display: 'flex',
                      flexDirection: 'column-reverse',
                      overflow: 'hidden',
                      background: 'transparent',
                    }
                  : undefined
              }
            >
              {c.segmentos.map((s) => (
                <div
                  key={s.clave}
                  style={{
                    height: total(c) ? `${(100 * s.valor) / total(c)}%` : 0,
                    background: COLORS[s.colorClase] || '#64748b',
                  }}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
      <LumaDateAxis labels={columnas.map((c) => c.etiquetaEje)} />
      <details className={styles.details}>
        <summary>Ver datos por fecha</summary>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Detalle</th>
            </tr>
          </thead>
          <tbody>
            {columnas.map((c) => (
              <tr key={c.clave}>
                <td>{c.etiquetaEje}</td>
                <td>{c.ariaLabel}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </LumaChartFrame>
  );
}
