import { LumaChartFrame, LUMA_COLORS } from './LumaChartFrame';
import styles from './LumaCharts.module.css';
export interface LumaCategoryDato {
  clave: string;
  valor: number;
  ariaLabel: string;
  etiquetaEje: string;
  notaInferior?: string;
}
const COLORS: Record<string, string> = {
  mastery: '#0d9488',
  break: '#2563eb',
  bank_exhausted: '#d97706',
  sin_dato: '#94a3b8',
  estructurado: '#2563eb',
  visual: '#8b5cf6',
  auditivo: '#0d9488',
  explorador: '#d97706',
};
export function LumaCategoryChart({
  titulo,
  datos,
}: {
  titulo: string;
  datos: LumaCategoryDato[];
}) {
  const max = Math.max(1, ...datos.map((d) => d.valor));
  return (
    <LumaChartFrame titulo={titulo}>
      <div className={styles.rows}>
        {datos.map((d, i) => (
          <div key={d.clave} role="img" aria-label={d.ariaLabel}>
            <div className={styles.rowHeading}>
              <span>{d.etiquetaEje}</span>
              <span className={styles.value}>
                {d.valor.toLocaleString('es-MX')}
                {d.notaInferior && <small> · {d.notaInferior}</small>}
              </span>
            </div>
            <div className={styles.track}>
              <div
                className={styles.fill}
                style={{
                  width: `${(100 * d.valor) / max}%`,
                  background:
                    COLORS[d.clave] || LUMA_COLORS[i % LUMA_COLORS.length],
                }}
              />
            </div>
          </div>
        ))}
      </div>
      {!datos.length && (
        <p className={styles.note}>Todavía no hay datos registrados.</p>
      )}
    </LumaChartFrame>
  );
}
