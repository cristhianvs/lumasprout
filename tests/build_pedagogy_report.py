"""Informe de la matriz CPA ejecutada; rechaza resultados incompletos."""
import json, hashlib
from pathlib import Path
from datetime import datetime, timezone
from xml.sax.saxutils import escape
import fitz
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'output/pedagogy-matrix'
PROFILES=['estructurado','visual','auditivo','explorador']
BEHAVIORS=['baseline','recovery','slow','interruptions','assisted','no_audio','mixed','family','override']
def main():
    rows=[json.loads((DATA/f'{p}-{b}/result.json').read_text(encoding='utf8')) for p in PROFILES for b in BEHAVIORS]
    assert len(rows)==36 and all(r['status']=='passed' for r in rows)
    totals={k:sum(r[k] for r in rows) for k in ['events','attempts','errors','hints','breaks','idle','mathActiveSeconds']}
    checks=sum(len(r['checks']) for r in rows)
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'engine.js',ROOT/'app.js',ROOT/'admin.js',ROOT/'tests/behavior_matrix.py']}
    summary={'generatedAt':datetime.now(timezone.utc).isoformat(),'scope':'36 UI simulations; no child participants','totals':totals,'assertions':checks,'sourceHashes':hashes,'regressions':{'node':38,'browser':14,'profiles':7,'pedagogySpecific':3,'laboratory':5},'results':[{k:v for k,v in r.items() if k!='checks'} for r in rows]}
    (DATA/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    pdfmetrics.registerFont(TTFont('Luma','C:/Windows/Fonts/arial.ttf'))
    pdfmetrics.registerFont(TTFont('LumaBold','C:/Windows/Fonts/arialbd.ttf'))
    pdfmetrics.registerFontFamily('Luma',normal='Luma',bold='LumaBold',italic='Luma',boldItalic='LumaBold')
    green=colors.HexColor('#245744');ink=colors.HexColor('#243c35')
    styles=getSampleStyleSheet()
    for name,size,leading,font in [('BodyL',10.5,15,'Luma'),('TitleL',29,34,'LumaBold'),('HeadL',19,24,'LumaBold'),('SubL',12,17,'LumaBold'),('SmallL',8,11,'Luma')]:
        styles.add(ParagraphStyle(name=name,fontName=font,fontSize=size,leading=leading,textColor=green if name in ['TitleL','HeadL'] else ink,spaceAfter=10))
    story=[]
    def add(text,style='BodyL'):story.append(Paragraph(text,styles[style]))
    def table(data,widths):
        t=Table([[Paragraph(escape(str(c)),styles['SmallL']) for c in row] for row in data],colWidths=widths,repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2eee5')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#cadace'))]))
        story.extend([t,Spacer(1,14)])
    add('ISLA LUMA / VALIDACIÓN TÉCNICA','SmallL')
    add('Complementos antes del piloto infantil','TitleL')
    add('Calibración frente a la investigación y simulaciones de interfaz<br/>17 de septiembre de 2026','SubL')
    add('<b>Resultado:</b> 36 de 36 recorridos completos aprobados, más 67 pruebas de motor, interfaz y laboratorio. Se instrumentó la progresión pedagógica y su circuito de retroalimentación. No participaron niños; no se ha demostrado eficacia educativa ni detección de ansiedad.')
    table([['Evidencia','Resultado'],['Modalidades × comportamientos','4 × 9 recorridos desde partida vacía'],['Cierres independientes','32, con las 24 etapas pedagógicas cubiertas'],['Ayuda permanente','4 cierres por descanso; cero evidencias independientes'],['Telemetría',f"{totals['events']:,} eventos; {totals['attempts']:,} intentos matemáticos"],['Auditoría',f'{checks:,} aserciones internas; no equivalen a participantes']],[170,329])
    add('Qué cambió','HeadL')
    add('Cada habilidad recorre concreto, pictórico, abstracto y un problema contextual. El constructor deja de aparecer inicialmente en la etapa pictórica; después se retiran los paneles. Pedir apoyo sigue siendo posible y no acredita autonomía. Tras ayuda o error, el siguiente reto ofrece una nueva oportunidad independiente.')
    add('Se añadieron «Todavía no sé», autoinforme de lectura quieta y bloques de 60/90 segundos cerrados al terminar un reto. El administrador enlaza señales, decisión y resolución. Las partidas existentes y el conocimiento previo se conservan.')
    story.append(PageBreak())
    add('02 / Hallazgos y trazabilidad','HeadL')
    table([['Hallazgo','Respuesta implementada / límite'],['Tres aciertos podían cerrar una habilidad sin otra representación','Para partidas nuevas, el cierre exige las cuatro etapas además del criterio probabilístico. Un acierto por etapa es una regla provisional.'],['La ayuda podía prolongarse por señales anteriores','La comprobación independiente suspende la ayuda automática al presentar el reto; el niño puede volver a solicitarla.'],['Inactividad confundible con lectura','«Sigo leyendo» concede 120 s y registra autoinforme. No se interpreta como ansiedad ni prueba objetiva de participación.'],['Bloques sugeridos sin cierre efectivo','Cierre e invitación a descansar en la transición tras resolver. Sin cuenta regresiva ni interrupción de respuesta.'],['Desbordamiento nuevo del tablero móvil','Detectado en laboratorio; corregido ajuste de tabla y verificada otra vez la prueba móvil.']],[169,330])
    add('Del evento a la decisión y su resultado','SubL')
    add('Los eventos nuevos usan esquema 1.3 y política cpa-1. La presentación incluye versión del ítem, variante, contexto y etapa. La decisión conserva IDs de señales previas. Intentos y resolución apuntan a esa decisión; los errores registran su patrón. El tablero muestra cobertura y oportunidades pendientes. El enlace permite auditar secuencia, no atribuir causalidad.')
    add('Compatibilidad y límites de interpretación','SubL')
    add('No se cambió CONFIG.version ni se borraron partidas. El dominio antiguo queda preservado y señalado como CPA no verificada. La recomendación de apoyo por señales debe leerse junto con etapa, asistencia y excepción de comprobación independiente. La respuesta familiar sobre dificultad se conserva como contexto; no se inventó un peso validado.')
    add('Los operandos y contextos se ampliaron, pero las equivalencias siguen centradas en cuartos/octavos. La transferencia dentro del juego es cercana y puede reutilizar operaciones; no sustituye un instrumento externo. Las cuatro modalidades permanecen disponibles con orden fijo, todavía susceptible a sesgo de posición.')
    story.append(PageBreak())
    add('03 / Pruebas ejecutadas','HeadL')
    table([['Modalidad','Escenarios aprobados','Cierre con etapas / descanso']]+[[p,'9 / 9','8 / 1'] for p in PROFILES],[150,155,194])
    add('Escenarios: avance independiente, error y recuperación, lectura lenta, interrupciones, ayuda permanente, audio ausente, preferencias mixtas, discrepancia familiar y elección explícita. Se usan clics, teclado, pausa, recarga, exportación e importación. Las respuestas se calculan desde la información visible; no se inyectan conocimiento, perfiles ni eventos.')
    add(f"La matriz acumula {totals['mathActiveSeconds']:,.0f} segundos matemáticos activos con reloj virtual. Las 14 pruebas generales incluyen además una partida completa con reloj real. Ninguno de esos tiempos representa observación humana.")
    table([['Suite','Resultado'],['Node: motor, flujo, migración y banco','38 aprobadas; 2 304 combinaciones del nuevo banco'],['Navegador general','14 aprobadas'],['Modalidades','7 aprobadas'],['Pedagogía específica','3 aprobadas'],['Laboratorio','5 aprobadas; la prueba móvil requirió corrección']],[270,229])
    add('Las pruebas específicas verifican que «no sé» no penaliza, que las ayudas no acreditan etapas, que el siguiente reto permite autonomía, que recargar conserva avance, que el tablero enlaza decisiones, que lectura quieta no genera errores y que el bloque espera a que termine el reto.')
    add('Evidencia reproducible','SubL')
    add('output/pedagogy-matrix/summary.json y carpetas por modalidad/comportamiento: telemetría, exportación, aserciones, capturas y traza Playwright. output/pedagogy-specific/: comprobación de progresión y tablero. Se conservó separada la matriz anterior de 36 recorridos.','SmallL')
    add('Repetición: python -X utf8 tests/behavior_matrix.py --profile estructurado --output output/pedagogy-matrix (y las otras tres modalidades). npm test; python -X utf8 tests/pedagogy_test.py; suites de navegador y laboratorio.','SmallL')
    story.append(PageBreak())
    add('04 / Qué sigue pendiente','HeadL')
    add('Antes de usar el resultado como evidencia educativa','SubL')
    for text in [
        '<b>Revisión docente:</b> comprobar consignas, dificultad y suficiencia de variantes; ampliar equivalencias, problemas menos similares y diagnóstico inicial entre habilidades.',
        '<b>Piloto observado:</b> revisar el borrador operativo, autorizaciones, asentimiento y criterios de interrupción con responsables. La plantilla separa lectura, exploración, ayuda, interrupción externa e indeterminado.',
        '<b>Evaluación externa:</b> preparar formas inicial/final comparables, explicaciones de respuestas y retención. Se entregaron ejemplos pendientes de revisión, no instrumentos ya validados.',
        '<b>Calibración empírica:</b> comparar señales con observaciones; ajustar en una muestra y evaluar en otra. No se cambiaron 60/40, .85, .06 ni las ventanas para aprobar guiones sintéticos.',
        '<b>Diseño del estudio:</b> adecuar población y entorno al uso doméstico en quinto/sexto; separar el efecto de adaptar conocimiento del efecto de sugerir modalidad. El tablero sigue siendo local, sin seguimiento multiusuario.'
    ]:add(text)
    add('Supuestos que siguen sin respaldo','SubL')
    add('Preferir audio o imágenes no demuestra que se aprenda mejor por ese canal. Inactividad, errores y latencia no diagnostican ansiedad. El posterior interno no es certeza empírica de aprendizaje. Un acierto contextual dentro de la aplicación no demuestra transferencia amplia ni retención.')
    add('Fuentes y alcance de la calibración','SubL')
    add('Documento base: Investigación Gamificación Matemática Personalizada.pdf (13 páginas). Contraste previo: docs/CONTRASTE_INVESTIGACION.md. Detalle de esta implementación: docs/COMPLEMENTOS_PREPILOTO.md. Protocolo preparado, no ejecutado: docs/PROTOCOLO_OBSERVACION.md. Esta entrega no repite ni amplía la auditoría bibliográfica anterior.','SmallL')
    pdf=ROOT/'output/pdf/Isla_Luma_Complementos_Validados.pdf';pdf.parent.mkdir(exist_ok=True,parents=True)
    def footer(canvas,doc):
        canvas.setFont('Luma',8);canvas.setFillColor(green);canvas.drawString(48,28,'ISLA LUMA  |  Simulación técnica, sin participantes reales');canvas.drawRightString(A4[0]-48,28,str(doc.page))
    SimpleDocTemplate(str(pdf),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=44,bottomMargin=47).build(story,onFirstPage=footer,onLaterPages=footer)
    render=ROOT/'tmp/pdfs/pedagogy';render.mkdir(parents=True,exist_ok=True)
    doc=fitz.open(pdf)
    for i,page in enumerate(doc):page.get_pixmap(matrix=fitz.Matrix(1.25,1.25)).save(render/f'page-{i+1}.png')
    print(json.dumps({'pdf':str(pdf),'pages':len(doc),'totals':totals,'assertions':checks},ensure_ascii=False))
if __name__=='__main__':main()
