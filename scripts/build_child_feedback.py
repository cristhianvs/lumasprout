"""Create the review questionnaire; the questionnaire is not a validated scale."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/Isla_Luma_Cuestionario_10_a_12_v0.2.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
W, H = letter
GREEN = colors.HexColor('#245744')
INK = colors.HexColor('#273E38')
MUTED = colors.HexColor('#52675F')
PALE = colors.HexColor('#EFF5EE')
GOLD = colors.HexColor('#F6E9B9')
LINE = colors.HexColor('#A5B8AD')
c = canvas.Canvas(str(OUT), pagesize=letter)
c.setTitle('Tu voz en Isla Luma | Cuestionario de experiencia | 10 a 12 años')
c.setAuthor('LumaSprout')
c.setSubject('Borrador v0.2 para revisión. Autoinforme después del juego; no validado.')
form = c.acroForm
fields = {}

def para(text, x, top, width, size=12, leading=16, bold=False, color=INK):
    style = ParagraphStyle('text', fontName='Helvetica-Bold' if bold else 'Helvetica',
                           fontSize=size, leading=leading, textColor=color)
    p = Paragraph(text, style)
    _, height = p.wrap(width, H)
    p.drawOn(c, x, top-height)
    return top-height

def textfield(name, x, y, width, height=20, multiline=False, label=None):
    form.textfield(name=name, tooltip=label or name, x=x, y=y, width=width, height=height,
                   fontName='Helvetica', fontSize=12, textColor=INK,
                   fillColor=colors.white, borderColor=LINE, borderWidth=.7,
                   fieldFlags='multiline' if multiline else '', forceBorder=True,
                   maxlen=800 if multiline else 100)
    fields[name] = 'text'

def leaf(x, y):
    c.setFillColor(GOLD); c.circle(x,y,22,stroke=0,fill=1)
    c.setStrokeColor(GREEN); c.setLineWidth(2)
    c.line(x,y-9,x,y+9)
    path=c.beginPath();path.moveTo(x,y+1);path.curveTo(x-16,y+3,x-14,y+18,x,y+9)
    path.curveTo(x+14,y+20,x+17,y+5,x,y+3)
    c.drawPath(path,stroke=1,fill=0)

def header(k, title, subtitle, adult=False):
    c.setFillColor(PALE); c.rect(0,H-110,W,110,stroke=0,fill=1)
    para('LUMASPROUT / ISLA LUMA',40,H-24,480,9,12,True,GREEN)
    para(title,40,H-44,480,25 if not adult else 22,29,True,GREEN)
    para(subtitle,40,H-80,490,11,15,color=MUTED)
    leaf(W-60,H-52)
    c.setStrokeColor(LINE);c.setLineWidth(.5);c.line(40,38,W-40,38)
    para('Borrador para revisión · Cuestionario v0.2 · 17/09/2026',40,29,470,8,10,color=MUTED)
    para(f'{k} / 4',W-69,29,40,9,10,color=MUTED)

def radio(name, options, top, columns=5):
    fields[name] = [value for value,_ in options]
    width=(W-80)/columns
    for i,(value,label) in enumerate(options):
        row,col=divmod(i,columns)
        x=40+col*width; y=top-row*32
        form.radio(name=name, tooltip=f'{name}: {label}', value=value, selected=False,
                   x=x,y=y-13,size=12,buttonStyle='circle',shape='circle',
                   fillColor=colors.white,borderColor=GREEN,textColor=GREEN,
                   borderWidth=1,fieldFlags='radio',forceBorder=False)
        para(label,x+18,y, width-22,10.5,13)

def question(number,title,top,options,columns=5):
    para(f'{number}. {title}',40,top,W-80,13,17,True)
    radio(f'Q{number:02}',options,top-27,columns)

def note(text, top, height=48):
    c.setFillColor(PALE);c.roundRect(40,top-height,W-80,height,9,stroke=0,fill=1)
    para(text,51,top-10,W-102,11,15)

header(1,'Primero, la aventura','Tu voz en Isla Luma · Para niños y niñas de 10 a 12 años')
para('Esto no es un examen. Queremos mejorar el juego.',40,669,532,13,17,True)
para('Piensa en la partida que acabas de jugar. Marca una opción por pregunta. Puedes elegir «No sé», dejar algo en blanco o parar cuando quieras. Si necesitas ayuda para leer, puedes pedirla.',40,642,532,11.5,16)
para('Código (lo pone quien te acompaña):',40,580,260,10,14,color=MUTED)
textfield('participantCode',263,562,115,21,label='Código del participante, sin nombre')
para('Edad (opcional):',394,580,140,10,14,color=MUTED)
textfield('age',487,562,45,21,label='Edad en años, opcional')
note('Estas preguntas son sobre el inicio: explorar la isla, ayudar a las criaturas, ordenar las señales y cambiar el jardín. Todavía no hablamos de fracciones.',543,53)
ease=[('0','Muy difícil'),('1','Algo difícil'),('2','Algo fácil'),('3','Muy fácil'),('NA','No jugué esta parte'),('NS','No sé')]
para('A. Entender qué hacer al empezar la aventura fue...',40,471,532,13,17,True)
radio('I01',ease,444)
para('B. Entender cómo ayudar a las criaturas fue...',40,369,532,13,17,True)
radio('I02',ease,342)
para('C. Entender cómo ordenar las señales fue...',40,267,532,13,17,True)
radio('I03',ease,240)
para('D. Entender qué podía hacer en el jardín fue...',40,165,532,13,17,True)
radio('I04',ease,138)
para('No escribas tu nombre. Sigue en la otra página cuando quieras.',40,61,532,10,14,color=MUTED)
c.showPage()

header(2,'Los retos y el juego','Después de jugar, cuéntanos cómo te fue.')
para('Esto no es un examen y no tiene calificación. Queremos mejorar el juego.',40,668,532,12,16,True)
para('Piensa en la partida que acabas de jugar. Marca una opción en cada pregunta.\nPuedes elegir «No sé», dejar una pregunta sin responder o parar cuando quieras.',40,645,532,11.5,16)
para('No escribas tu nombre. Si necesitas ayuda para leer, puedes pedirla.',40,608,532,11,15)
para('Ahora piensa en los retos de fracciones y en el juego completo.',40,581,532,11,15,True)

question(1,'¿Cuánto te gustó jugar?',543,[('0','Nada'),('1','Poco'),('2','Bastante'),('3','Mucho'),('NS','No sé')])
question(2,'Entender qué hacer en los retos de fracciones fue...',484,[('0','Muy difícil'),('1','Algo difícil'),('2','Algo fácil'),('3','Muy fácil'),('NA','No llegué'),('NS','No sé')])
question(3,'¿Qué tan fácil fue usar los botones del juego?',386,[('0','Muy difícil'),('1','Algo difícil'),('2','Algo fácil'),('3','Muy fácil'),('NS','No sé')])
question(4,'Los retos de fracciones me parecieron...',330,[('1','Muy fáciles'),('2','Algo fáciles'),('3','A mi medida'),('4','Algo difíciles'),('5','Muy difíciles'),('NA','No llegué a esos retos'),('NS','No sé')])
question(5,'El juego iba...',229,[('fast','Muy rápido'),('right','A buen ritmo'),('slow','Muy lento'),('NS','No sé')],4)
question(6,'Si usaste pistas, ¿cuánto te ayudaron?',158,[('0','Nada'),('1','Poco'),('2','Bastante'),('3','Mucho'),('NA','No usé pistas'),('NS','No sé')])
para('Sigue en la otra página. También puedes descansar.',40,59,520,10,14,color=MUTED)
c.showPage()

header(3,'Así se sintió jugar','Puedes decir lo bueno, lo difícil y lo que cambiarías.')
para('Marca una opción por pregunta. Si algo no te pasó, puedes decirlo.',40,665,532,11.5,16)
frequency=[('0','Nunca'),('1','Pocas veces'),('2','Muchas veces'),('3','Todo el tiempo'),('NS','No sé')]
question(7,'¿Cuántas veces te molestó que algo no te saliera?',629,frequency)
question(8,'¿Cuántas veces te preocupó equivocarte en el juego?',556,frequency)
question(9,'¿Te gustaría jugar otra vez?',483,[('no','No'),('maybe','Tal vez'),('yes','Sí'),('NS','No sé')],4)
question(10,'¿Qué forma de jugar te gustó más?',410,[
    ('estructurado','Resolver por pasos'),('visual','Pintar mosaicos'),
    ('auditivo','Crear ritmos'),('explorador','Llevar energía'),
    ('tie','Varias por igual'),('none','Ninguna'),
    ('one','Solo probé una'),('NS','No sé')],4)
para('Para terminar: escribe unas palabras. Puedes dejarlo en blanco.',40,302,532,11,15,color=MUTED)
para('11. ¿Qué fue lo que más te gustó, si hubo algo?',40,277,532,13,17,True)
textfield('Q11',40,190,532,60,True,'11. Lo que más me gustó, si hubo algo')
para('12. ¿Qué cambiarías para que el juego fuera mejor para ti?',40,169,532,13,17,True)
textfield('Q12',40,79,532,64,True,'12. Lo que cambiaría del juego')
para('¡Gracias por contarnos tu experiencia!',40,60,532,11,15,True,GREEN)
c.showPage()

header(4,'Guía para quien acompaña','Esta página es para la persona adulta. Entrega al participante las páginas 1 a 3.',True)
top=668
top=para('Aplicación igual para todas las sesiones',40,top,532,14,18,True,GREEN)-7
top=para('Aplicar al terminar o interrumpir la partida, antes de dar opiniones sobre su desempeño. Reservar unos 7 a 10 minutos (estimación por comprobar). No es obligatorio acabar. Usar siempre el mismo texto, orden y opciones; registrar la versión del cuestionario.',40,top,532,10.5,14)-10
top=para('<b>Leer al inicio:</b> «Queremos saber cómo te fue para mejorar el juego. No hay respuestas correctas o incorrectas. Puedes decir que algo no te gustó. No pasa nada si dejas una pregunta en blanco o prefieres terminar. Si quieres, puedo leerte las preguntas».',40,top,532,10.5,14)-11
top=para('Leer sin sugerir respuestas ni explicar lo que “debería” haber sentido. Si pide aclaración, registrar qué se dijo. Si dicta las respuestas abiertas, escribir sus palabras. No pedir que provoque errores ni que siga jugando para poder contestar.',40,top,532,10.5,14)-15

top=para('Ficha de sesión (sin nombres)',40,top,532,14,18,True,GREEN)-7
para('Fecha y hora local:',40,top,135,10,13);textfield('sessionDateTime',171,top-19,159,21,label='Fecha y hora local de aplicación')
para('Observador (código):',349,top,145,10,13);textfield('observerCode',485,top-19,87,21,label='Código del observador')
top-=34
para('runId del JSON:',40,top,119,10,13);textfield('runId',171,top-19,401,21,label='runId de la sesión exportada, no el id de un evento')
top-=34
para('App / dispositivo:',40,top,126,10,13);textfield('appDevice',171,top-19,401,21,label='Versión del producto y dispositivo')
top-=34
para('Ayuda / incidencias:',40,top,130,10,13);textfield('administrationNotes',171,top-29,401,32,True,'Lectura o dictado, aclaraciones, interrupciones y motivo del cierre')
top-=48

top=para('Registro y comparación con la telemetría',40,top,532,14,18,True,GREEN)-7
top=para('Vincular el código de la página 1, el <b>runId</b> del JSON exportado y la hora de aplicación. Conservar el JSON y las respuestas por separado: este PDF no las envía a la aplicación ni a una base de datos. Usar questionnaireVersion = IL-EXP-0.2 y guardar cada respuesta como I01 a I04 (aventura) y Q01 a Q12.',40,top,532,10.5,14)-8
top=para('<b>Codificación:</b> I01 a I04 y Q01, Q02, Q03, Q06, Q07 y Q08: categorías ordenadas de 0 a 3, en el orden impreso. Q04: 1 a 5; Q05, Q09 y Q10: conservar la categoría elegida. Q11 y Q12: texto literal. «No sé» = NS; «No llegué» / «No usé» = NA; sin respuesta = OM; varias marcas donde se pide una = AM. No convertir faltantes en cero. En el PDF digital, un campo sin selección también se registra como OM.',40,top,532,10,13.5)-8
top=para('<b>Lectura de resultados:</b> revisar aventura y fracciones por separado, sin sumar una nota general. Q07 y Q08 no diagnostican ansiedad; Q10 no identifica cómo aprende mejor. El formulario recoge lo que expresa el participante; la telemetría registra acciones, tiempos y ayudas, no sentimientos directos. Contrastar coincidencias y discrepancias con la observación, sin asumir que una fuente tiene siempre la razón ni atribuir una emoción a un evento solo por coincidir en la sesión.',40,top,532,10,13.5)-9
para('<b>Antes de usarlo como instrumento estable:</b> revisar comprensión con niños y niñas de 10 a 12 años y registrar qué palabras necesitan explicación. Este borrador estandariza la aplicación; su comprensión, duración y propiedades de medición todavía no están validadas.',40,top,532,10,13.5,color=MUTED)
c.save()
print(OUT)
print('Expected form fields:',len(fields))
