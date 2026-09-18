import styles from './LumaCharts.module.css';
import type { LumaPanorama } from '@/lib/lumaApi';
import { formatNumero } from '@/lib/protocolo42Format';

interface LumaPanoramaResumenCardsProps {
  panorama: LumaPanorama;
}

interface ResumenCard {
  label: string;
  value: string;
}

/** Totales del estudio y retención, en el mismo formato de tarjeta que usa Protocolo42ResumenCards. */
export function LumaPanoramaResumenCards({
  panorama,
}: LumaPanoramaResumenCardsProps) {
  const cards: ResumenCard[] = [
    { label: 'Sesiones totales', value: String(panorama.sesiones_total) },
    { label: 'Participantes', value: String(panorama.participantes_total) },
    { label: 'Eventos totales', value: String(panorama.eventos_total) },
    {
      label: 'Con una sesión',
      value: String(panorama.retencion.con_una_sesion),
    },
    {
      label: 'Con dos sesiones',
      value: String(panorama.retencion.con_dos_sesiones),
    },
    {
      label: 'Con tres o más sesiones',
      value: String(panorama.retencion.con_tres_o_mas_sesiones),
    },
    {
      label: 'Mediana de días entre sesiones',
      value: formatNumero(panorama.retencion.mediana_dias_entre_sesiones),
    },
  ];

  return (
    <div className={styles.metrics}>
      {cards.map((card) => (
        <div key={card.label} className={styles.metric}>
          <div className={styles.metricLabel}>{card.label}</div>
          <div className={styles.metricValue}>{card.value}</div>
        </div>
      ))}
    </div>
  );
}
