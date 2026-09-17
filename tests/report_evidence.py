"""Reject missing, failed or stale evidence instead of printing historical pass counts."""
import json
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import Font

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate import source_hash

def regressions():
    current = source_hash()
    evidence = {}
    for suite in ('node', 'browser', 'profiles', 'pedagogy', 'laboratory'):
        result = json.loads((ROOT / 'output' / 'validation' / f'{suite}.json').read_text(encoding='utf8'))
        if result['status'] != 'passed' or result['sourceHash'] != current:
            raise ValueError(f'Failed or stale evidence: {suite}; rerun scripts/validate.py {suite}')
        evidence[suite] = result['tests']
    return evidence

def register_fonts(bold_name='LumaBold'):
    pdfmetrics.registerFont(Font('Luma', 'Helvetica', 'WinAnsiEncoding'))
    pdfmetrics.registerFont(Font(bold_name, 'Helvetica-Bold', 'WinAnsiEncoding'))
    pdfmetrics.registerFontFamily('Luma', normal='Luma', bold=bold_name, italic='Luma', boldItalic=bold_name)

def matrix_records(folder):
    profiles = ('estructurado', 'visual', 'auditivo', 'explorador')
    behaviors = ('baseline', 'recovery', 'slow', 'interruptions', 'assisted', 'no_audio', 'mixed', 'family', 'override')
    current = source_hash()
    rows = []
    for profile in profiles:
        for behavior in behaviors:
            record = folder / f'{profile}-{behavior}'
            row = json.loads((record / 'result.json').read_text(encoding='utf8'))
            if row['status'] != 'passed' or row.get('sourceHash') != current or not row.get('sourceUnchanged'):
                raise ValueError(f'Missing current passing matrix evidence: {record}')
            digest = hashlib.sha256((record / 'telemetry.json').read_bytes()).hexdigest()
            if digest != row['telemetrySha256']:
                raise ValueError(f'Telemetry integrity mismatch: {record}')
            rows.append(row)
    return rows

def build(default_folder, filename):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    folder = ROOT / os.environ.get('LUMA_MATRIX_DIR', f'output/{default_folder}')
    rows, suites = matrix_records(folder), regressions()
    now = datetime.now(timezone.utc).isoformat()
    totals = {key: sum(row[key] for row in rows) for key in ('events', 'attempts', 'errors', 'hints', 'breaks', 'mathActiveSeconds')}
    summary = {'generatedAt': now, 'sourceHash': source_hash(), 'scope': 'Technical simulation; no child participants', 'regressions': suites, 'totals': totals, 'runs': len(rows)}
    (folder / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf8')
    styles = getSampleStyleSheet()
    story = [Paragraph('LumaSprout: validación técnica', styles['Title']),
             Paragraph(escape(now), styles['Normal']), Spacer(1, 16),
             Paragraph(f'{len(rows)} recorridos de interfaz aprobados y {sum(suites.values())} pruebas de regresión. Resultados vinculados al código mediante SHA-256. No participaron niños; no se ha demostrado eficacia educativa ni detección de ansiedad.', styles['BodyText']), Spacer(1, 12)]
    data = [['Suite ejecutada', 'Pruebas aprobadas'], *[[name, str(count)] for name, count in suites.items()], *[[name, str(count)] for name, count in totals.items()]]
    table = Table(data, colWidths=[300, 180], repeatRows=1)
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2eee5')), ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]))
    story.extend([table, Spacer(1, 16)])
    for text in [
        'La telemetría nueva conserva fotografías independientes del estado. La política selecciona variantes no vistas; el agotamiento requiere revisión y no concede transferencia. El tablero separa el criterio bayesiano de la cobertura CPA.',
        'Se conservan las partidas y los registros anteriores. El simulador histórico bayesiano está identificado por su versión; no verifica la secuencia CPA actual. Los eventos históricos no se reconstruyen retrospectivamente.',
        'Pendiente: revisión docente del banco ampliado, calibración con observaciones humanas, evaluación externa de transferencia y retención. Estas simulaciones comprueban funcionamiento técnico, no resultados educativos.',
        'Fuentes: output/validation/*.json, logs de suites y result.json/telemetry.json por recorrido. Las cifras se calculan desde esas evidencias; se rechazan resultados incompletos o de otro código.',
    ]:
        story.extend([Paragraph(text, styles['BodyText']), Spacer(1, 10)])
    destination = ROOT / 'output' / 'pdf' / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(destination), pagesize=A4, leftMargin=48, rightMargin=48).build(story)
    print(destination)
