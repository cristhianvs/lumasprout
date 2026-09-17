"""Build the report from executed browser artifacts; refuse incomplete matrices."""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

import fitz
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.graphics.shapes import Drawing, Line, String, Rect, PolyLine

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'output/behavior-matrix'
PDF=ROOT/'output/pdf/Isla_Luma_Reporte_Simulacion_Playwright.pdf'
PROFILES=['estructurado','visual','auditivo','explorador']
BEHAVIORS=['baseline','recovery','slow','interruptions','assisted','no_audio','mixed','family','override']
LABELS={'baseline':'Avance independiente','recovery':'Error y recuperación','slow':'Lectura lenta','interruptions':'Interrupciones','assisted':'Ayuda permanente','no_audio':'Audio no disponible','mixed':'Preferencias mixtas','family':'Discrepancia familiar','override':'Elección explícita'}
GREEN=colors.HexColor('#245744');INK=colors.HexColor('#243c35');MUTED=colors.HexColor('#61736b');PALE=colors.HexColor('#edf3ed');GOLD=colors.HexColor('#b8802c')

def load(path):return json.loads(path.read_text(encoding='utf8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    rows=[load(DATA/f'{p}-{b}'/'result.json') for p in PROFILES for b in BEHAVIORS]
    if len(rows)!=36 or any(r['status']!='passed' for r in rows):
        raise RuntimeError('La matriz no tiene 36 recorridos aprobados; no emitir un informe de éxito.')
    records={(r['profile'],r['behavior']):load(ROOT/r['artifacts']/'telemetry.json') for r in rows}
    post_checks=[]
    for (profile,behavior),record in records.items():
        assignments=[e for e in record['events'] if e['type']=='experience_assigned']
        last=assignments[-1]['data']
        expected=PROFILES[(PROFILES.index(profile)+1)%4] if behavior=='override' else 'estructurado' if behavior=='mixed' else profile
        assert last['profile']==expected,(profile,behavior,last)
        if behavior=='mixed':assert last['inference']['dominant'] is None
        if behavior=='family':assert last['inference']['provisional'] is False
        if behavior=='override':assert last['source']=='child_choice'
        assert sum(e['type']=='learning_path_completed' for e in record['events'])==(0 if behavior=='assisted' else 1)
        post_checks.append({'profile':profile,'behavior':behavior,'finalAssignment':last['profile'],'source':last['source'],'dominant':last['inference']['dominant'],'pass':True})
    totals={key:sum(r[key] for r in rows) for key in ['events','attempts','errors','hints','breaks','idle','mathActiveSeconds','wallSeconds']}
    checks=sum(len(r['checks']) for r in rows)
    inventory={str(path.relative_to(ROOT)):sha(path) for path in [ROOT/'app.js',ROOT/'engine.js',ROOT/'tests/behavior_matrix.py']}
    summary={'generatedAt':datetime.now(timezone.utc).isoformat(),'scope':'36 UI-driven runs, 4 preferences x 9 behaviors; virtual clock; no seeded state','totals':totals,'assertions':checks,'sourceHashes':inventory,'postChecks':post_checks,'results':[{k:v for k,v in r.items() if k!='checks'} for r in rows]}
    (DATA/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    regression=load(DATA/'regression-results.json')
    pdfmetrics.registerFont(TTFont('Luma','C:/Windows/Fonts/arial.ttf'))
    pdfmetrics.registerFont(TTFont('Luma-Bold','C:/Windows/Fonts/arialbd.ttf'))
    pdfmetrics.registerFontFamily('Luma',normal='Luma',bold='Luma-Bold',italic='Luma',boldItalic='Luma-Bold')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyL',fontName='Luma',fontSize=10,leading=14.7,textColor=INK,spaceAfter=9))
    styles.add(ParagraphStyle(name='SmallL',fontName='Luma',fontSize=8,leading=11,textColor=MUTED,spaceAfter=7))
    styles.add(ParagraphStyle(name='TitleL',fontName='Luma-Bold',fontSize=31,leading=35,textColor=GREEN,spaceAfter=18))
    styles.add(ParagraphStyle(name='H1L',fontName='Luma-Bold',fontSize=21,leading=25,textColor=GREEN,spaceAfter=13))
    styles.add(ParagraphStyle(name='H2L',fontName='Luma-Bold',fontSize=13,leading=17,textColor=GREEN,spaceAfter=9,spaceBefore=8))
    styles.add(ParagraphStyle(name='CellL',fontName='Luma',fontSize=8,leading=10.5,textColor=INK))
    story=[]
    def p(text,style='BodyL'):return Paragraph(text,styles[style])
    def add(text,style='BodyL'):story.append(p(text,style))
    def title(number,text):add(f'{number:02d} / {text}','H1L')
    def table(data,widths,small=False):
        cells=[[p(escape(str(c)),'CellL') for c in row] for row in data]
        t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),1,GREEN),('LINEBELOW',(0,1),(-1,-1),.35,colors.HexColor('#dce5dd')),('TOPPADDING',(0,0),(-1,-1),7 if not small else 5),('BOTTOMPADDING',(0,0),(-1,-1),7 if not small else 5),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7)]))
        story.append(t);story.append(Spacer(1,12))
    def newpage():story.append(PageBreak())

    add('ISLA LUMA / VALIDACIÓN TÉCNICA','SmallL')
    story.append(Spacer(1,24))
    add('Simulación completa<br/>desde la interfaz','TitleL')
    add('Hallazgos de Playwright y lectura del circuito de telemetría','H2L')
    add('17 de septiembre de 2026 | Prototipo local | Quinto y sexto de primaria','SmallL')
    story.append(Spacer(1,18))
    table([['Recorridos ejecutados','Cierre por dominio','Cierre por descanso'],['36 de 36 aprobados','32 con seis habilidades','4 con ayuda permanente']],[165,165,165])
    add('Se ejecutó la matriz completa de cuatro preferencias por nueve comportamientos. Cada partida comenzó vacía y recorrió mapa, refugios, antena, jardín y taller mediante controles de la aplicación. La telemetría se leyó durante las respuestas y transiciones; no se cargaron historias ni probabilidades prefabricadas.')
    add('<b>Se encontraron y corrigieron dos defectos:</b> la pista escrita de respaldo ante audio ausente no marcaba asistencia; la recarga podía borrar el tiempo activo acumulado del intento. Los recorridos finales y las regresiones verifican ambas correcciones.')
    add(f'La matriz produjo <b>{totals["events"]:,} eventos</b>, <b>{totals["attempts"]:,} intentos matemáticos</b> y {checks:,} comprobaciones automáticas. Esos conteos describen ejecución de software, no tamaño de una muestra de niños.')
    add('Alcance de la conclusión','H2L')
    add('El circuito probado responde de forma coherente a los guiones ejecutados: respeta prerrequisitos, distingue intentos independientes de asistidos, modifica apoyo y descanso, y conserva el progreso. No demuestra aprendizaje, comprensión infantil, una medición validada del enganche ni capacidad para reconocer ansiedad.')
    add('La matriz usa reloj virtual para esperas y pausas. Se ejecutó además la suite general que incluye un recorrido completo con reloj real. Las pruebas se realizaron en contextos de navegador aislados; no se utilizó el perfil personal ni se modificaron partidas existentes.','SmallL')

    newpage();title(2,'Cómo se produjo la evidencia')
    add('Interacciones y lectura independiente','H2L')
    add('Playwright pulsa botones, construye fracciones con las cuatro modalidades, solicita ayudas, completa el cuestionario familiar, pausa, recarga y exporta desde Familias. Las respuestas correctas se calculan en Python con fracciones a partir de los paneles y operaciones visibles; no se lee la respuesta interna del motor para contestar.')
    add('Después de cada intento se leen los eventos y el estado guardado. Un cálculo independiente comprueba qué habilidad puede actualizarse, si hubo asistencia, la transición de probabilidad y los prerrequisitos. En cada decisión se reconstruye la ventana de señales con los eventos anteriores y se verifica el apoyo y el descanso elegidos.')
    add('Preferencias y comportamientos','H2L')
    add('En los recorridos habituales se elige una modalidad en cinco retos distintos y después se devuelve el control a Luma: esto comprueba inferencia desde elecciones reales de interfaz. En preferencias mixtas se alternan ocho elecciones. El desacuerdo familiar se introduce con el formulario real. La elección explícita se cambia después de observar una sugerencia automática.')
    add('Tiempo y dispositivos','H2L')
    add(f'Chrome {rows[0]["browser"]}, Windows, Python Playwright, modo headless. Los 36 recorridos acumulan {totals["mathActiveSeconds"]/3600:.2f} horas de tiempo matemático <b>virtual activo</b>. La suma de duración de los procesos por recorrido es {totals["wallSeconds"]/60:.1f} minutos; se ejecutaron procesos concurrentes, por lo que no equivale al tiempo de pared del lote.')
    add('Lectura lenta: 70 segundos activos por reto, con una tecla neutra periódica para representar actividad. Interrupciones: ausencia de interacción hasta la pausa y otros 90 segundos de espera. Se verifica que esa espera no consume tiempo activo. Audio ausente: se desactivan las capacidades del navegador, sin modificar respuestas ni datos del juego.')
    add('Artefactos por recorrido','H2L')
    add('telemetry.json: registro final; checkpoints.json: lecturas durante el recorrido; export.json: descarga real desde Familias; trace.zip: traza Playwright; result.json: comprobaciones y resultado; final.png: cierre. Los casos de apoyo, lectura lenta y ayuda permanente también incluyen captura del tablero al importar el registro.')
    add('El estado persistido se lee solo para verificar. Las únicas alteraciones del entorno son el reloj virtual y, en los cuatro casos correspondientes, las capacidades de audio. La partida de simulación usa una clave separada y todos sus eventos quedan identificados.','SmallL')

    newpage();title(3,'Cobertura de la matriz')
    matrix=[['Comportamiento','Estruct.','Visual','Auditivo','Explor.']]
    for b in BEHAVIORS:
        matrix.append([LABELS[b]]+['Descanso / 0' if b=='assisted' else 'Dominio / 6' for _ in PROFILES])
    table(matrix,[171,81,81,81,81])
    add('Cada celda representa un recorrido completo desde bienvenida hasta un cierre explícito. “6” significa seis habilidades que cumplen las reglas del motor; “0” significa ninguna evidencia independiente acreditada en el guion de ayuda permanente.','SmallL')
    add('Qué debía ocurrir','H2L')
    table([['Guion','Expectativa verificada'],['Avance independiente','Modalidad inferida; progresión de las seis habilidades.'],['Error y recuperación','Errores y ayudas activan apoyo; luego vuelve la oportunidad independiente.'],['Lectura lenta','Latencia alta no activa por sí sola apoyo concreto; se ofrecen descansos.'],['Interrupciones','La pausa no altera conocimiento ni consume tiempo de espera.'],['Ayuda permanente','Los aciertos asistidos no acreditan dominio; cierre por descanso adaptativo.'],['Audio no disponible','Pista escrita asistida y continuidad de la interacción visual.'],['Preferencias mixtas','No forzar una preferencia dominante con evidencia repartida.'],['Discrepancia familiar','Combinar el formulario real con las elecciones; conservar progreso.'],['Elección explícita','Respetar el cambio sin reiniciar reto o conocimiento.']],[139,356],small=True)

    newpage();title(4,'Defectos encontrados y corregidos')
    add('01. Una pista podía contabilizarse como respuesta independiente','H2L')
    add('<b>Reproducción:</b> entrar al taller sin síntesis de voz y pulsar “Escuchar”. Se mostraba el texto de la pista, pero el flujo salía antes de marcar asistencia. La prueba falló en <b>written_fallback_is_assistance</b>.')
    add('<b>Impacto:</b> un acierto posterior podía elevar el conocimiento estimado aun después de recibir una pista. También faltaba registrar la exposición al apoyo escrito.')
    add('<b>Corrección:</b> la alternativa escrita recorre el flujo de apoyo visual y marca asistencia. Se conserva el canal solicitado y el motivo de indisponibilidad; la alternativa automática no cuenta como preferencia visual voluntaria.')
    add('<b>Comprobación:</b> cuatro recorridos finales sin audio, una prueba Node específica y regresiones generales. Se verifica el estado de asistencia y que la respuesta ayudada no incremente la evidencia independiente.')
    add('Evidencia inicial: output/behavior-diagnostics/estructurado-no_audio/result.json.','SmallL')
    add('02. Recargar podía convertir 70 segundos activos en cero','H2L')
    add('<b>Reproducción:</b> dedicar 70 segundos activos a un reto, pausar, volver y recargar antes de responder. La telemetría del intento registró latencia 0. La prueba falló en <b>active_latency_survives_reload</b>.')
    add('<b>Impacto:</b> el tablero podía mostrar respuestas artificialmente rápidas y el análisis de variabilidad quedaba distorsionado. La partida conservaba conocimiento, pero perdía el origen temporal del intento.')
    add('<b>Corrección:</b> se persiste el inicio del intento en tiempo activo. Los guardados antiguos lo recuperan del último intento o de la presentación del reto, sin cambiar versión ni borrar progreso.')
    add('<b>Comprobación:</b> los 36 recorridos incluyen pausa y recarga antes de responder; se comprueba la latencia contra el intervalo activo esperado. Una prueba Node cubre además el guardado antiguo sin el nuevo campo.')
    add('Evidencia inicial: output/behavior-diagnostics-latency/estructurado-slow/result.json.','SmallL')
    add('También se corrigió una aserción de la prueba: la pausa se mide desde su activación, no desde un guardado anterior. Ese desfase del comprobador no se contabiliza como defecto del producto.','SmallL')
    add('Incidencia de automatización: el caso visual con interrupciones detectó un botón inestable bajo reloj congelado y cursor inmóvil. Se reprodujo por separado. Mover el cursor fuera de los controles antes de reconstruir y pulsar permitió repetir el recorrido sin forzar clics, alterar el DOM ni cambiar reglas. Se conservó la primera traza en output/behavior-first-pass-visual-interruptions.','SmallL')

    newpage();title(5,'El circuito observado en los registros')
    checkpoints=load(DATA/'estructurado-recovery/checkpoints.json')
    points=[c for c in checkpoints if c['label']=='next_boundary']
    max_time=max(c['mathMs'] for c in points)/1000
    drawing=Drawing(495,175)
    drawing.add(Rect(0,0,495,175,fillColor=PALE,strokeColor=None))
    x0,y0,w,h=43,35,425,105
    for level in range(7):
        y=y0+level*h/6
        drawing.add(Line(x0,y,x0+w,y,strokeColor=colors.HexColor('#d1ded3'),strokeWidth=.4))
        drawing.add(String(25,y-3,str(level),fontName='Luma',fontSize=8,fillColor=MUTED))
    coords=[]
    for c in points:
        x=x0+c['mathMs']/1000/max_time*w
        n=sum(k['n']>=3 and k['p']>=.85 for k in c['knowledge'].values())
        coords.extend([x,y0+n*h/6])
        if c['current'].get('supportMode')=='hands':
            drawing.add(Rect(x-2,17,4,8,fillColor=GOLD,strokeColor=None))
    drawing.add(PolyLine(coords,strokeColor=GREEN,strokeWidth=2))
    drawing.add(String(x0,155,'Habilidades con dominio según el motor',fontName='Luma-Bold',fontSize=10,fillColor=GREEN))
    drawing.add(String(x0,4,'0 s',fontName='Luma',fontSize=8,fillColor=MUTED))
    drawing.add(String(385,4,f'{max_time:.0f} s activos virtuales',fontName='Luma',fontSize=8,fillColor=MUTED))
    story.append(drawing);story.append(Spacer(1,8))
    add('Ejemplo: estructurado + error y recuperación. Línea verde: habilidades dominadas. Marcas doradas: siguiente reto con apoyo concreto. La curva representa un guion de respuestas programadas, no una curva de aprendizaje observada en un niño.','SmallL')
    for label,b in [('Recuperación','recovery'),('Lectura lenta','slow'),('Ayuda permanente','assisted')]:
        subset=[r for r in rows if r['behavior']==b]
        add(label,'H2L')
        add(f'Los cuatro recorridos acumularon {sum(r["attempts"] for r in subset)} intentos, {sum(r["hints"] for r in subset)} peticiones de ayuda y {sum(r["breaks"] for r in subset)} descansos sugeridos. '+('Todos recuperaron apoyo visual en retos posteriores y terminaron las seis habilidades.' if b=='recovery' else 'La lentitud por sí sola no activó apoyo concreto; los recorridos sí alcanzaron los descansos por duración.' if b=='slow' else 'El cierre conservó cero evidencias independientes. Acertar con ayuda permanente no se convirtió en dominio.'))
    add('Cómo se verificó el tablero','H2L')
    add('Cada uno de los 36 registros exportados desde Familias se importó en el tablero real. Se comprobó el total de habilidades mostrado. Durante el juego, la lectura y las comprobaciones del circuito se hicieron desde la telemetría persistida después de cada intento y transición; no mediante una vigilancia visual continua del tablero.')

    newpage();title(6,'Resultados por recorrido - primera mitad')
    add('Intentos, errores y ayudas corresponden al taller. “Desc.” cuenta descansos sugeridos automáticamente; las pausas manuales no se incluyen.','SmallL')
    def detailed(selected):
        data=[['Preferencia / comportamiento','Intentos','Errores','Ayudas','Desc.','Dominio']]
        for r in selected:
            data.append([f'{r["profile"]} / {LABELS[r["behavior"]]}',r['attempts'],r['errors'],r['hints'],r['breaks'],f'{r["mastered"]}/6'])
        table(data,[240,51,51,51,51,51],small=True)
    detailed(rows[:18])
    add('Todos los resultados de esta tabla aprobaron las comprobaciones del recorrido. Los archivos result.json incluyen el detalle de cada aserción y la huella SHA-256 de su telemetría.','SmallL')

    newpage();title(7,'Resultados por recorrido - segunda mitad')
    detailed(rows[18:])
    add('Regresiones adicionales ejecutadas','H2L')
    table([['Suite','Resultado','Duración'],*[ [r['name'],f'{r["passed"]} aprobadas',r['duration']] for r in regression['suites']]],[287,110,98],small=True)
    add('Las regresiones incluyen el recorrido general con reloj real y los cuatro recorridos de modalidades. No se suman las aserciones internas a los recorridos para inflar el número de escenarios.','SmallL')

    newpage();title(8,'Límites, seguimiento y reproducción')
    add('Lo que todavía no demuestra esta validación','H2L')
    add('No participaron niños. Los guiones no modelan toda la variabilidad humana, lectura, comprensión, cansancio o estrategias espontáneas. La prueba de lentitud usa actividad periódica explícita; no permite concluir cómo interpretar a alguien que lee quieto durante más de 45 segundos, cuando la aplicación propone pausa.')
    add('Los perfiles se infieren aquí a partir de elecciones explícitas repetidas. No se verificó una identificación automática del “tipo de niño” desde movimientos pasivos. Las cuatro modalidades comparten el mismo banco matemático; la preferencia modifica presentación e interacción, mientras el contenido se decide por evidencia y prerrequisitos.')
    add('Enganche se representa mediante participación e interrupciones observables. Ansiedad permanece “no inferible”. La política de cuatro señales y los parámetros de conocimiento siguen siendo heurísticos. La calidad audible en dispositivos físicos, aprendizaje y retención requieren evaluación adicional.')
    add('El tablero sigue siendo local y no agrega sesiones de distintas familias. El ritmo editable del laboratorio solo afecta sus simulaciones. La matriz de este informe usa la política normal de la aplicación, sin sobreescribir sus parámetros.')
    add('Siguientes comprobaciones propuestas - no ejecutadas aquí','H2L')
    add('1. Piloto observado para contrastar comprensión de instrucciones, lectura quieta y elección de ayudas.<br/>2. Ampliación del banco para comprobar transferencia y evitar que la repetición aparente sea interpretada como aprendizaje.<br/>3. Calibración con registros consentidos y pruebas físicas de audio, accesibilidad y conectividad local.')
    add('Reproducir y auditar','H2L')
    add('Iniciar con <b>npm start</b>. Ejecutar <b>python -X utf8 tests/behavior_matrix.py --profile estructurado</b> y repetir con visual, auditivo y explorador. El comando crea partidas nuevas en contextos aislados. No importa registros ni reutiliza la partida del navegador personal.')
    add('Resumen auditable: output/behavior-matrix/summary.json. Evidencias por celda: output/behavior-matrix/&lt;preferencia&gt;-&lt;comportamiento&gt;/. Fuentes del comportamiento: app.js y engine.js. Comprobador: tests/behavior_matrix.py. Generador del informe: tests/build_behavior_report.py.','SmallL')
    add('Huellas de las fuentes verificadas','H2L')
    for name,digest in inventory.items():
        add(f'{escape(name)}<br/>{digest[:32]}<br/>{digest[32:]}','SmallL')

    PDF.parent.mkdir(parents=True,exist_ok=True)
    def page(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#d1ded3'));canvas.line(50,42,545,42)
        canvas.setFont('Luma',8);canvas.setFillColor(MUTED)
        canvas.drawString(50,28,'ISLA LUMA | Simulación técnica | 17 septiembre 2026')
        canvas.drawRightString(545,28,f'{doc.page}')
    doc=SimpleDocTemplate(str(PDF),pagesize=A4,rightMargin=50,leftMargin=50,topMargin=43,bottomMargin=57,title='Isla Luma - Reporte de simulación completa con Playwright',author='Isla Luma - Validación técnica')
    doc.build(story,onFirstPage=page,onLaterPages=page)
    rendered=ROOT/'tmp/pdfs/behavior-report';rendered.mkdir(parents=True,exist_ok=True)
    with fitz.open(PDF) as pdf:
        for index,page_obj in enumerate(pdf):
            page_obj.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(rendered/f'page-{index+1:02d}.png')
        text='\n'.join(page_obj.get_text() for page_obj in pdf)
        (rendered/'extracted.txt').write_text(text,encoding='utf8')
        print(json.dumps({'pdf':str(PDF),'pages':len(pdf),'matrix':len(rows),'checks':checks,'totals':totals},ensure_ascii=False))

if __name__=='__main__':main()
