import type { ReactNode } from 'react';
import styles from './LumaCharts.module.css';
export const LUMA_COLORS = [
  '#0d9488',
  '#2563eb',
  '#8b5cf6',
  '#d97706',
  '#64748b',
];
export function LumaChartFrame({
  titulo,
  children,
}: {
  titulo: string;
  children: ReactNode;
}) {
  return (
    <section className={styles.card} aria-label={titulo}>
      <h3 className={styles.title}>{titulo}</h3>
      {children}
    </section>
  );
}
export function LumaDateAxis({ labels }: { labels: string[] }) {
  const indices = Array.from(
    new Set([
      0,
      Math.round((labels.length - 1) / 3),
      Math.round((2 * (labels.length - 1)) / 3),
      labels.length - 1,
    ])
  ).filter((i) => i >= 0);
  return (
    <div className={styles.axis} aria-hidden="true">
      {indices.map((i) => (
        <span key={i}>
          {labels[i].replace(
            /(\d+) de (\S+)/,
            (_, day: string, month: string) => `${day} ${month.slice(0, 3)}`
          )}
        </span>
      ))}
    </div>
  );
}
