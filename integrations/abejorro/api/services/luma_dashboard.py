"""Agregados de telemetria de LumaSprout: panorama del estudio, series en el tiempo
y evolucion de un participante.

Distinto de `luma_service.py` (estado de UNA partida en vivo): aqui la pregunta es
"esta funcionando el juego" viendo la evolucion en el tiempo de todo el estudio o de
un participante. La tabla `luma_eventos` crece con cada evento (a diferencia de
`luma_sesiones`, que crece solo con cada participante nuevo), asi que las
agregaciones caras se hacen en SQL (GROUP BY, date_trunc, DISTINCT ON) en vez de
traer eventos a Python; ver cada funcion para el detalle de que se agrega donde.

DECISIONES DE DISENO que conviene que el equipo revise (no estan completamente
fijadas por el encargo):
1. "sesiones" (panorama.sesiones_total, series) se cuenta como `session_carga`
   distintos (la carga de pagina, ver models/luma.py), NO como filas de
   `luma_sesiones` (que son "partidas"/run_id, ya contadas aparte en
   `participantes_total`). CONFIRMADO por el equipo probando contra Postgres
   real: es la unica lectura que da dos numeros distintos con el esquema actual.
   `embudo_fases` cuenta run_id (participantes) por fase, no session_carga.
2. "independencia" reutiliza EXACTAMENTE la misma fuente que
   `LumaIntentos.resueltos_independientes` del resumen por partida
   (decision_evaluated.data.independent), no el desglose secundario sobre
   attempt.data.correct. CONFIRMADO por el equipo: una sola definicion de
   "independencia" en todo el sistema.
3. `respuesta_ante_error` en /series solo mira eventos DENTRO de la ventana de
   dias pedida al clasificar cada fallo (no la sesion completa como en el resumen
   por partida): un fallo muy cerca del limite de la ventana cuya respuesta llega
   justo despues del corte se reporta como sin_clasificar. CONFIRMADO por el
   equipo como aceptable; el aviso vive en LumaRespuestaAnteErrorDia.limite
   (LIMITE_RESPUESTA_ANTE_ERROR_SERIE) para que el panel lo muestre.
4. `tiempo_activo_mediana_ms`: la primera version de este archivo asumia que
   play_ms se reinicia en cada carga de pagina. ES INCORRECTO, confirmado por el
   equipo contra datos reales: play_ms (y math_ms) son ACUMULATIVOS a lo largo de
   TODA la partida (persisten en localStorage entre recargas, con tope de 300000
   ms cada uno). El tiempo de UNA carga es el delta MAX-MIN de cada reloj DENTRO
   de esa carga, no su valor bruto; se exponen sumados (play + math, aventura +
   taller). Ver LIMITE_TIEMPO_ACTIVO.
5. Si estas consultas se vuelven lentas en produccion, el primer indice a pedirle
   a db-specialist es sobre `luma_eventos.at_cliente` (hoy no hay ninguno; los
   tres indices existentes son todos (sesion_id, ...)), ya que /series y el
   embudo filtran y agrupan por esa columna sin apoyo de indice.
6. TRAMPA DE SQLALCHEMY VERIFICADA CONTRA POSTGRES REAL: `LumaEvento.data["clave"]`
   crea un bind parameter NUEVO cada vez que se llama. Si la misma clave JSONB se
   usa en el SELECT y tambien en el GROUP BY como dos llamadas separadas, Postgres
   las trata como expresiones DISTINTAS (parametros distintos en la sentencia
   preparada) y rechaza la consulta con GroupingError, aunque el SQL se vea
   identico en texto y aunque compile sin error en SQLAlchemy. La correccion es
   construir la expresion UNA sola vez en una variable de Python y reutilizar ESE
   MISMO objeto en select() y group_by() (ver `_casillas_acreditadas_por_dia`).
"""

from __future__ import annotations

import logging
import statistics
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from itertools import groupby
from types import SimpleNamespace

from sqlalchemy import Boolean, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.luma import LumaEvento, LumaSesion
from schemas.luma_dashboard import (
    LumaAyudaDia,
    LumaBancoAgotado,
    LumaBayesianoTemporalEntrada,
    LumaConteoEscena,
    LumaConteoFase,
    LumaConteoHabilidadEtapa,
    LumaConteoModalidad,
    LumaConteoMotivoCierre,
    LumaConteoSesionesPorDia,
    LumaHistoricoSalida,
    LumaPanoramaSalida,
    LumaProgresionTemporalEntrada,
    LumaPuntosDeFuga,
    LumaRespuestaAnteErrorDia,
    LumaRetencion,
    LumaSerieDia,
    LumaSeriesSalida,
    LumaSesionHistorica,
)
from services.luma_service import (
    CATEGORIA_BUSCA_AYUDA,
    CATEGORIA_INACTIVIDAD_BLOQUEO,
    CATEGORIA_REINTENTO_INMEDIATO,
    CATEGORIA_SIN_CLASIFICAR,
    FASE_COMPLETA,
    MOTIVO_FINAL_BANK_EXHAUSTED,
    MOTIVO_FINAL_BREAK,
    MOTIVO_FINAL_MASTERY,
    OUTCOME_SOLVED,
    TIPO_BREAK_SUGGESTED,
    TIPO_DECISION_EVALUATED,
    TIPO_IDLE_STARTED,
    TIPO_ITEM_BANK_EXHAUSTED,
    TIPO_KNOWLEDGE_UPDATED,
    TIPO_LEARNING_PATH_COMPLETED,
    TIPO_SUPPORT_SELECTED,
    TIPO_TASK_PRESENTED,
    TIPO_VOLUNTARY_BREAK,
    _campo,
    _clasificar_fallos,
    _motivo_final,
    _skill_y_stage_de_task_presented,
)

logger = logging.getLogger(__name__)

MOTIVO_SIN_DATO = "sin_dato"
FASES_EMBUDO = ("welcome", "play", "bridge", "math", "complete")

_TIPOS_MOTIVO_FINAL = (
    TIPO_LEARNING_PATH_COMPLETED,
    TIPO_VOLUNTARY_BREAK,
    TIPO_BREAK_SUGGESTED,
    TIPO_ITEM_BANK_EXHAUSTED,
)


def _motivo_desde_tipo_relevante(ultima_fase: str | None, tipo_relevante: str | None) -> str:
    if ultima_fase != FASE_COMPLETA:
        return MOTIVO_SIN_DATO
    if tipo_relevante == TIPO_LEARNING_PATH_COMPLETED:
        return MOTIVO_FINAL_MASTERY
    if tipo_relevante in (TIPO_VOLUNTARY_BREAK, TIPO_BREAK_SUGGESTED):
        return MOTIVO_FINAL_BREAK
    if tipo_relevante == TIPO_ITEM_BANK_EXHAUSTED:
        return MOTIVO_FINAL_BANK_EXHAUSTED
    return MOTIVO_SIN_DATO


# ---------------------------------------------------------------------------
# GET /panorama
# ---------------------------------------------------------------------------


async def _totales(db: AsyncSession) -> tuple[int, int, int]:
    sesiones_y_eventos = (
        await db.execute(
            select(
                func.count(func.distinct(LumaEvento.session_carga)),
                func.count(),
            )
            .select_from(LumaEvento)
            .join(LumaSesion, LumaSesion.id == LumaEvento.sesion_id)
            .where(LumaSesion.simulation.is_(False))
        )
    ).one_or_none()
    sesiones_total, eventos_total = sesiones_y_eventos if sesiones_y_eventos else (0, 0)

    participantes_total = (
        await db.execute(select(func.count()).select_from(LumaSesion).where(LumaSesion.simulation.is_(False)))
    ).scalar_one()

    return sesiones_total, participantes_total, eventos_total


async def _sesiones_por_dia(db: AsyncSession) -> list[LumaConteoSesionesPorDia]:
    dia_col = func.date_trunc("day", LumaEvento.at_cliente).label("dia")
    resultado = await db.execute(
        select(dia_col, func.count(func.distinct(LumaEvento.session_carga)), func.count())
        .select_from(LumaEvento)
        .join(LumaSesion, LumaSesion.id == LumaEvento.sesion_id)
        .where(LumaSesion.simulation.is_(False))
        .group_by(dia_col)
        .order_by(dia_col)
    )
    return [
        LumaConteoSesionesPorDia(dia=dia.date().isoformat(), sesiones=sesiones, eventos=eventos)
        for dia, sesiones, eventos in resultado.all()
    ]


async def _embudo_fases(db: AsyncSession) -> list[LumaConteoFase]:
    """ACUMULATIVO: cada fase cuenta a quien llego AL MENOS hasta ahi, no a quien
    tuvo algun evento puntual en esa fase (eso daria un embudo que puede crecer,
    como se vio contra datos reales: no tiene sentido leerlo como embudo).

    Se mapea cada `phase` a su posicion en FASES_EMBUDO con un CASE, se toma el
    MAX de esa posicion por participante (la fase mas avanzada que alcanzo) y
    luego, para cada fase, se cuentan los participantes cuyo maximo es >= esa
    posicion. Solo se trae a Python un entero por participante (bounded), no
    eventos completos.
    """
    posicion_de_fase = case(
        *[(LumaEvento.phase == fase, indice) for indice, fase in enumerate(FASES_EMBUDO)],
        else_=None,
    )
    maximo_por_sesion = (
        select(func.max(posicion_de_fase).label("posicion_maxima"))
        .select_from(LumaEvento)
        .join(LumaSesion, LumaSesion.id == LumaEvento.sesion_id)
        .where(LumaSesion.simulation.is_(False))
        .group_by(LumaEvento.sesion_id)
    ).subquery()

    resultado = await db.execute(select(maximo_por_sesion.c.posicion_maxima))
    posiciones_maximas = [posicion for (posicion,) in resultado.all() if posicion is not None]

    return [
        LumaConteoFase(fase=fase, participantes=sum(1 for posicion in posiciones_maximas if posicion >= indice))
        for indice, fase in enumerate(FASES_EMBUDO)
    ]


async def _motivos_cierre(db: AsyncSession) -> list[LumaConteoMotivoCierre]:
    """Determina, por SQL, la ultima fase y el ultimo evento relevante de cada
    participante (DISTINCT ON sobre el indice (sesion_id, secuencia): no trae
    eventos completos, solo dos columnas angostas por sesion) y clasifica el
    motivo en Python sobre ese resultado ya reducido a una fila por partida."""
    ultima_fase = (
        select(LumaEvento.sesion_id, LumaEvento.phase.label("ultima_fase"))
        .distinct(LumaEvento.sesion_id)
        .order_by(LumaEvento.sesion_id, LumaEvento.secuencia.desc())
    ).subquery()

    ultimo_relevante = (
        select(LumaEvento.sesion_id, LumaEvento.tipo.label("tipo_relevante"))
        .where(LumaEvento.tipo.in_(_TIPOS_MOTIVO_FINAL))
        .distinct(LumaEvento.sesion_id)
        .order_by(LumaEvento.sesion_id, LumaEvento.secuencia.desc())
    ).subquery()

    resultado = await db.execute(
        select(ultima_fase.c.ultima_fase, ultimo_relevante.c.tipo_relevante)
        .select_from(LumaSesion)
        .outerjoin(ultima_fase, ultima_fase.c.sesion_id == LumaSesion.id)
        .outerjoin(ultimo_relevante, ultimo_relevante.c.sesion_id == LumaSesion.id)
        .where(LumaSesion.simulation.is_(False))
    )

    conteo: Counter[str] = Counter(
        _motivo_desde_tipo_relevante(ultima_fase_valor, tipo_relevante) for ultima_fase_valor, tipo_relevante in resultado.all()
    )
    motivos_orden = (MOTIVO_FINAL_MASTERY, MOTIVO_FINAL_BREAK, MOTIVO_FINAL_BANK_EXHAUSTED, MOTIVO_SIN_DATO)
    return [LumaConteoMotivoCierre(motivo=motivo, participantes=conteo.get(motivo, 0)) for motivo in motivos_orden]


async def _modalidades(db: AsyncSession) -> list[LumaConteoModalidad]:
    resultado = await db.execute(
        select(LumaEvento.experience, func.count())
        .select_from(LumaEvento)
        .join(LumaSesion, LumaSesion.id == LumaEvento.sesion_id)
        .where(LumaSesion.simulation.is_(False), LumaEvento.experience.is_not(None))
        .group_by(LumaEvento.experience)
        .order_by(func.count().desc())
    )
    return [LumaConteoModalidad(experience=experience, eventos=eventos) for experience, eventos in resultado.all()]


async def _retencion(db: AsyncSession) -> LumaRetencion:
    """GROUP BY (run_id, session_carga) reduce toda la tabla de eventos a una fila
    por sesion de juego (no por evento); el conteo de sesiones por participante y
    la mediana de dias entre ellas se calculan en Python sobre esa lista ya
    reducida, tipicamente ordenes de magnitud mas chica que `luma_eventos`."""
    inicios_por_sesion = (
        select(
            LumaSesion.run_id,
            LumaEvento.session_carga,
            func.min(LumaEvento.at_cliente).label("inicio"),
        )
        .select_from(LumaEvento)
        .join(LumaSesion, LumaSesion.id == LumaEvento.sesion_id)
        .where(LumaSesion.simulation.is_(False))
        .group_by(LumaSesion.run_id, LumaEvento.session_carga)
    ).subquery()

    resultado = await db.execute(
        select(inicios_por_sesion.c.run_id, inicios_por_sesion.c.inicio).order_by(
            inicios_por_sesion.c.run_id, inicios_por_sesion.c.inicio
        )
    )
    filas = resultado.all()

    con_una = con_dos = con_tres_mas = 0
    gaps_dias: list[float] = []
    for _run_id, grupo in groupby(filas, key=lambda fila: fila[0]):
        inicios = sorted(inicio for _run_id_fila, inicio in grupo)
        cantidad = len(inicios)
        if cantidad == 1:
            con_una += 1
        elif cantidad == 2:
            con_dos += 1
        else:
            con_tres_mas += 1
        for anterior, siguiente in zip(inicios, inicios[1:], strict=False):
            gaps_dias.append((siguiente - anterior).total_seconds() / 86400)

    return LumaRetencion(
        con_una_sesion=con_una,
        con_dos_sesiones=con_dos,
        con_tres_o_mas_sesiones=con_tres_mas,
        mediana_dias_entre_sesiones=statistics.median(gaps_dias) if gaps_dias else None,
    )


async def _banco_agotado(db: AsyncSession) -> list[LumaBancoAgotado]:
    """item_bank_exhausted es raro (uno por banco agotado, no por evento comun),
    asi que traer su `data` completo a Python es barato: no es un escaneo de la
    tabla completa, solo de las filas de ese tipo."""
    resultado = await db.execute(
        select(LumaEvento.data)
        .select_from(LumaEvento)
        .join(LumaSesion, LumaSesion.id == LumaEvento.sesion_id)
        .where(LumaSesion.simulation.is_(False), LumaEvento.tipo == TIPO_ITEM_BANK_EXHAUSTED)
    )
    conteo: Counter[tuple[str | None, str | None]] = Counter()
    for (data,) in resultado.all():
        evento_data = data if isinstance(data, dict) else {}
        skill = evento_data.get("skill")
        stage = evento_data.get("stage")
        conteo[(skill if isinstance(skill, str) else None, stage if isinstance(stage, str) else None)] += 1
    return [
        LumaBancoAgotado(habilidad=habilidad, etapa=etapa, veces=veces)
        for (habilidad, etapa), veces in conteo.items()
    ]


async def _puntos_de_fuga(db: AsyncSession) -> LumaPuntosDeFuga:
    """Ultima fase, ultimo scene y ultimo task_presented por sesion, via
    DISTINCT ON sobre el indice (sesion_id, secuencia): trae, como mucho, una fila
    (con su JSONB) por PARTICIPANTE, no por evento."""
    ultima_fase_y_escena = (
        select(LumaEvento.sesion_id, LumaEvento.phase.label("ultima_fase"), LumaEvento.scene.label("ultimo_scene"))
        .distinct(LumaEvento.sesion_id)
        .order_by(LumaEvento.sesion_id, LumaEvento.secuencia.desc())
    ).subquery()

    ultimo_task_presented = (
        select(LumaEvento.sesion_id, LumaEvento.data.label("data_ultimo_task"))
        .where(LumaEvento.tipo == TIPO_TASK_PRESENTED)
        .distinct(LumaEvento.sesion_id)
        .order_by(LumaEvento.sesion_id, LumaEvento.secuencia.desc())
    ).subquery()

    resultado = await db.execute(
        select(
            ultima_fase_y_escena.c.ultima_fase,
            ultima_fase_y_escena.c.ultimo_scene,
            ultimo_task_presented.c.data_ultimo_task,
        )
        .select_from(LumaSesion)
        .outerjoin(ultima_fase_y_escena, ultima_fase_y_escena.c.sesion_id == LumaSesion.id)
        .outerjoin(ultimo_task_presented, ultimo_task_presented.c.sesion_id == LumaSesion.id)
        .where(LumaSesion.simulation.is_(False))
    )

    conteo_fase: Counter[str] = Counter()
    conteo_escena: Counter[int] = Counter()
    conteo_habilidad_etapa: Counter[tuple[str, str]] = Counter()

    for ultima_fase, ultimo_scene, data_ultimo_task in resultado.all():
        if ultima_fase == FASE_COMPLETA:
            continue
        conteo_fase[ultima_fase or MOTIVO_SIN_DATO] += 1
        if ultima_fase == "play" and ultimo_scene is not None:
            conteo_escena[ultimo_scene] += 1
        if ultima_fase == "math" and isinstance(data_ultimo_task, dict):
            skill, stage = _skill_y_stage_de_task_presented(SimpleNamespace(data=data_ultimo_task))
            if isinstance(skill, str) and isinstance(stage, str):
                conteo_habilidad_etapa[(skill, stage)] += 1

    return LumaPuntosDeFuga(
        abandono_por_fase=[LumaConteoFase(fase=fase, participantes=cantidad) for fase, cantidad in conteo_fase.items()],
        abandono_por_escena=[
            LumaConteoEscena(scene=scene, participantes=cantidad) for scene, cantidad in sorted(conteo_escena.items())
        ],
        abandono_por_habilidad_y_etapa=[
            LumaConteoHabilidadEtapa(habilidad=habilidad, etapa=etapa, participantes=cantidad)
            for (habilidad, etapa), cantidad in conteo_habilidad_etapa.items()
        ],
        banco_agotado=await _banco_agotado(db),
    )


async def obtener_panorama(db: AsyncSession) -> LumaPanoramaSalida:
    sesiones_total, participantes_total, eventos_total = await _totales(db)
    return LumaPanoramaSalida(
        generado=datetime.now(UTC),
        sesiones_total=sesiones_total,
        participantes_total=participantes_total,
        eventos_total=eventos_total,
        sesiones_por_dia=await _sesiones_por_dia(db),
        embudo_fases=await _embudo_fases(db),
        motivos_cierre=await _motivos_cierre(db),
        modalidades=await _modalidades(db),
        retencion=await _retencion(db),
        puntos_de_fuga=await _puntos_de_fuga(db),
    )


# ---------------------------------------------------------------------------
# GET /series
# ---------------------------------------------------------------------------


async def _independencia_por_dia(db: AsyncSession, desde: datetime, hasta: datetime) -> dict[date, float | None]:
    dia_col = func.date_trunc("day", LumaEvento.at_cliente).label("dia")
    independiente_col = LumaEvento.data["independent"].astext.cast(Boolean)
    resultado = await db.execute(
        select(
            dia_col,
            func.count().filter(independiente_col.is_(True)),
            func.count(),
        )
        .select_from(LumaEvento)
        .join(LumaSesion, LumaSesion.id == LumaEvento.sesion_id)
        .where(
            LumaSesion.simulation.is_(False),
            LumaEvento.tipo == TIPO_DECISION_EVALUATED,
            LumaEvento.at_cliente >= desde,
            LumaEvento.at_cliente < hasta,
        )
        .group_by(dia_col)
    )
    salida: dict[date, float | None] = {}
    for dia, independientes, total in resultado.all():
        salida[dia.date()] = (independientes / total) if total > 0 else None
    return salida


async def _ayuda_por_dia(db: AsyncSession, desde: datetime, hasta: datetime) -> dict[date, LumaAyudaDia]:
    dia_col = func.date_trunc("day", LumaEvento.at_cliente).label("dia")
    voluntary_col = LumaEvento.data["voluntary"].astext.cast(Boolean)
    resultado = await db.execute(
        select(
            dia_col,
            func.count().filter(voluntary_col.is_(True)),
            func.count().filter(voluntary_col.is_(False)),
        )
        .select_from(LumaEvento)
        .join(LumaSesion, LumaSesion.id == LumaEvento.sesion_id)
        .where(
            LumaSesion.simulation.is_(False),
            LumaEvento.tipo == TIPO_SUPPORT_SELECTED,
            LumaEvento.at_cliente >= desde,
            LumaEvento.at_cliente < hasta,
        )
        .group_by(dia_col)
    )
    return {
        dia.date(): LumaAyudaDia(voluntaria=voluntaria, impuesta=impuesta) for dia, voluntaria, impuesta in resultado.all()
    }


async def _casillas_acreditadas_por_dia(db: AsyncSession, desde: datetime, hasta: datetime) -> dict[date, int]:
    """Primera vez que se acredito cada (sesion, skill, stage): MIN(at_cliente)
    agrupado por casilla en una subconsulta, y esa fecha minima es la que se
    agrupa por dia en la consulta exterior. Evita contar de nuevo una casilla que
    ya estaba acreditada si el motor emite mas de un decision_evaluated calificado
    para la misma (sesion, skill, stage)."""
    # OJO: cada `LumaEvento.data["skill"]` crea un bind parameter NUEVO para la
    # clave 'skill'. Si el SELECT y el GROUP BY llaman a `LumaEvento.data["skill"]`
    # por separado, Postgres los ve como dos expresiones DISTINTAS (parametros
    # distintos en la sentencia preparada, aunque el valor sea el mismo) y rechaza
    # la consulta con GroupingError: "column luma_eventos.data must appear in the
    # GROUP BY clause". Verificado contra Postgres real. La correccion es
    # construir la expresion UNA sola vez y reutilizar el mismo objeto en select()
    # y group_by(), para que comparta el mismo bind parameter.
    independiente_col = LumaEvento.data["independent"].astext.cast(Boolean)
    skill_col = LumaEvento.data["skill"].astext.label("skill")
    stage_col = LumaEvento.data["stage"].astext.label("stage")
    primera_acreditacion = (
        select(
            LumaEvento.sesion_id,
            skill_col,
            stage_col,
            func.min(LumaEvento.at_cliente).label("primera_vez"),
        )
        .select_from(LumaEvento)
        .join(LumaSesion, LumaSesion.id == LumaEvento.sesion_id)
        .where(
            LumaSesion.simulation.is_(False),
            LumaEvento.tipo == TIPO_DECISION_EVALUATED,
            independiente_col.is_(True),
            LumaEvento.data["outcome"].astext == OUTCOME_SOLVED,
        )
        .group_by(LumaEvento.sesion_id, skill_col, stage_col)
    ).subquery()

    dia_col = func.date_trunc("day", primera_acreditacion.c.primera_vez).label("dia")
    resultado = await db.execute(
        select(dia_col, func.count())
        .select_from(primera_acreditacion)
        .where(primera_acreditacion.c.primera_vez >= desde, primera_acreditacion.c.primera_vez < hasta)
        .group_by(dia_col)
    )
    return {dia.date(): cantidad for dia, cantidad in resultado.all()}


async def _tiempo_activo_mediana_por_dia(db: AsyncSession, desde: datetime, hasta: datetime) -> dict[date, float | None]:
    """play_ms y math_ms son ACUMULATIVOS a lo largo de TODA la partida (no se
    reinician en cada carga de pagina: persisten en localStorage), verificado por
    el equipo contra datos reales. El tiempo activo de UNA carga de pagina
    (session_carga) es entonces MAX-MIN de cada reloj dentro de esa carga, no su
    valor bruto (que seguiria subiendo entre cargas). Se exponen sumados
    (play + math): son dos relojes distintos (aventura / taller), pero el campo es
    uno solo; ver LIMITE_TIEMPO_ACTIVO."""
    tiempo_por_sesion_carga = (
        select(
            LumaEvento.session_carga,
            func.date_trunc("day", func.min(LumaEvento.at_cliente)).label("dia"),
            (func.max(LumaEvento.play_ms) - func.min(LumaEvento.play_ms)).label("delta_play_ms"),
            (func.max(LumaEvento.math_ms) - func.min(LumaEvento.math_ms)).label("delta_math_ms"),
        )
        .select_from(LumaEvento)
        .join(LumaSesion, LumaSesion.id == LumaEvento.sesion_id)
        .where(
            LumaSesion.simulation.is_(False),
            LumaEvento.at_cliente >= desde,
            LumaEvento.at_cliente < hasta,
        )
        .group_by(LumaEvento.session_carga)
    ).subquery()

    resultado = await db.execute(
        select(
            tiempo_por_sesion_carga.c.dia,
            tiempo_por_sesion_carga.c.delta_play_ms,
            tiempo_por_sesion_carga.c.delta_math_ms,
        )
    )
    valores_por_dia: dict[date, list[float]] = {}
    for dia, delta_play_ms, delta_math_ms in resultado.all():
        if delta_play_ms is None and delta_math_ms is None:
            continue
        tiempo_activo_ms = (delta_play_ms or 0) + (delta_math_ms or 0)
        valores_por_dia.setdefault(dia.date(), []).append(tiempo_activo_ms)

    return {dia: statistics.median(valores) for dia, valores in valores_por_dia.items()}


async def _inactividad_por_dia(db: AsyncSession, desde: datetime, hasta: datetime) -> dict[date, int]:
    dia_col = func.date_trunc("day", LumaEvento.at_cliente).label("dia")
    resultado = await db.execute(
        select(dia_col, func.count())
        .select_from(LumaEvento)
        .join(LumaSesion, LumaSesion.id == LumaEvento.sesion_id)
        .where(
            LumaSesion.simulation.is_(False),
            LumaEvento.tipo == TIPO_IDLE_STARTED,
            LumaEvento.at_cliente >= desde,
            LumaEvento.at_cliente < hasta,
        )
        .group_by(dia_col)
    )
    return {dia.date(): cantidad for dia, cantidad in resultado.all()}


async def _respuesta_ante_error_por_dia(
    db: AsyncSession, desde: datetime, hasta: datetime
) -> dict[date, LumaRespuestaAnteErrorDia]:
    """Ver limitacion (3) en el docstring del modulo: solo se traen eventos DENTRO
    de la ventana pedida, agrupados por sesion, y se reutiliza `_clasificar_fallos`
    (el mismo algoritmo del resumen por partida) sesion por sesion."""
    filas = (
        await db.execute(
            select(LumaEvento)
            .join(LumaSesion, LumaSesion.id == LumaEvento.sesion_id)
            .where(LumaSesion.simulation.is_(False), LumaEvento.at_cliente >= desde, LumaEvento.at_cliente < hasta)
            .order_by(LumaEvento.sesion_id, LumaEvento.secuencia)
        )
    ).scalars().all()

    conteos_por_dia: dict[date, Counter[str]] = {}
    for _sesion_id, eventos_de_sesion in groupby(filas, key=lambda e: e.sesion_id):
        for fallo, categoria, _posteriores in _clasificar_fallos(list(eventos_de_sesion)):
            dia = fallo.at_cliente.date()
            conteos_por_dia.setdefault(dia, Counter()).update([categoria])

    return {
        dia: LumaRespuestaAnteErrorDia(
            reintento_inmediato=conteo.get(CATEGORIA_REINTENTO_INMEDIATO, 0),
            busca_ayuda=conteo.get(CATEGORIA_BUSCA_AYUDA, 0),
            inactividad_bloqueo=conteo.get(CATEGORIA_INACTIVIDAD_BLOQUEO, 0),
            sin_clasificar=conteo.get(CATEGORIA_SIN_CLASIFICAR, 0),
        )
        for dia, conteo in conteos_por_dia.items()
    }


async def obtener_series(db: AsyncSession, dias: int) -> LumaSeriesSalida:
    hoy = datetime.now(UTC).date()
    primer_dia = hoy - timedelta(days=dias - 1)
    desde = datetime(primer_dia.year, primer_dia.month, primer_dia.day, tzinfo=UTC)
    hasta = datetime(hoy.year, hoy.month, hoy.day, tzinfo=UTC) + timedelta(days=1)

    independencia = await _independencia_por_dia(db, desde, hasta)
    ayuda = await _ayuda_por_dia(db, desde, hasta)
    casillas = await _casillas_acreditadas_por_dia(db, desde, hasta)
    tiempo_activo = await _tiempo_activo_mediana_por_dia(db, desde, hasta)
    inactividad = await _inactividad_por_dia(db, desde, hasta)
    respuesta_ante_error = await _respuesta_ante_error_por_dia(db, desde, hasta)

    dias_vacios_respuesta = LumaRespuestaAnteErrorDia(
        reintento_inmediato=0, busca_ayuda=0, inactividad_bloqueo=0, sin_clasificar=0
    )
    dias_vacios_ayuda = LumaAyudaDia(voluntaria=0, impuesta=0)

    serie = [
        LumaSerieDia(
            dia=dia.isoformat(),
            independencia=independencia.get(dia),
            respuesta_ante_error=respuesta_ante_error.get(dia, dias_vacios_respuesta),
            ayuda=ayuda.get(dia, dias_vacios_ayuda),
            casillas_acreditadas=casillas.get(dia, 0),
            tiempo_activo_mediana_ms=tiempo_activo.get(dia),
            inactividad_idle_started=inactividad.get(dia, 0),
        )
        for dia in (primer_dia + timedelta(days=offset) for offset in range(dias))
    ]

    return LumaSeriesSalida(generado=datetime.now(UTC), dias=dias, serie=serie)


# ---------------------------------------------------------------------------
# GET /sesiones/{run_id}/historico
# ---------------------------------------------------------------------------


async def obtener_historico(db: AsyncSession, sesion: LumaSesion) -> LumaHistoricoSalida:
    """A diferencia de panorama/series, esto es sobre UN participante: el volumen
    de eventos esta acotado a su historial de juego (mismo orden de magnitud que
    /resumen), asi que se trae completo y se procesa en Python, reutilizando la
    misma logica de clasificacion que el resumen en vivo."""
    eventos = list(
        (
            await db.execute(
                select(LumaEvento).where(LumaEvento.sesion_id == sesion.id).order_by(LumaEvento.secuencia)
            )
        )
        .scalars()
        .all()
    )

    sesiones_historicas: list[LumaSesionHistorica] = []
    progresion_temporal: list[LumaProgresionTemporalEntrada] = []
    bayesiano_temporal: list[LumaBayesianoTemporalEntrada] = []
    acreditadas_vistas: set[tuple[str, str]] = set()

    for _session_carga, grupo in groupby(eventos, key=lambda e: e.session_carga):
        eventos_de_sesion = list(grupo)
        sesiones_historicas.append(_sesion_historica_de(eventos_de_sesion, acreditadas_vistas))

    # progresion_temporal y bayesiano_temporal se recorren sobre TODOS los
    # eventos en orden cronologico (no por session_carga), porque una casilla se
    # acredita una sola vez en la vida de la partida, sin importar en que carga
    # de pagina ocurrio.
    acreditadas_ya_registradas: set[tuple[str, str]] = set()
    for evento in eventos:
        if evento.tipo == TIPO_DECISION_EVALUATED:
            skill = _campo(evento, "skill")
            stage = _campo(evento, "stage")
            if (
                isinstance(skill, str)
                and isinstance(stage, str)
                and _campo(evento, "independent") is True
                and _campo(evento, "outcome") == OUTCOME_SOLVED
                and (skill, stage) not in acreditadas_ya_registradas
            ):
                acreditadas_ya_registradas.add((skill, stage))
                progresion_temporal.append(
                    LumaProgresionTemporalEntrada(habilidad=skill, etapa=stage, fecha=evento.at_cliente)
                )
        elif evento.tipo == TIPO_KNOWLEDGE_UPDATED:
            skill = _campo(evento, "skill")
            posterior = _campo(evento, "posterior")
            if isinstance(skill, str) and isinstance(posterior, dict):
                bayesiano_temporal.append(
                    LumaBayesianoTemporalEntrada(
                        habilidad=skill,
                        fecha=evento.at_cliente,
                        p=posterior.get("p"),
                        n=posterior.get("n"),
                    )
                )

    return LumaHistoricoSalida(
        run_id=sesion.run_id,
        sesiones=sesiones_historicas,
        progresion_temporal=progresion_temporal,
        bayesiano_temporal=bayesiano_temporal,
    )


def _sesion_historica_de(
    eventos_de_sesion: list[LumaEvento], acreditadas_acumuladas: set[tuple[str, str]]
) -> LumaSesionHistorica:
    """Un session_carga = una fila de `sesiones` en el historico. Muta
    `acreditadas_acumuladas` (compartido entre llamadas) para que
    casillas_acreditadas_acumuladas refleje el total hasta el FINAL de esta
    sesion, inclusive, en el orden cronologico real de las sesiones."""
    ultimo = eventos_de_sesion[-1]

    for evento in eventos_de_sesion:
        if evento.tipo != TIPO_DECISION_EVALUATED:
            continue
        skill = _campo(evento, "skill")
        stage = _campo(evento, "stage")
        if (
            isinstance(skill, str)
            and isinstance(stage, str)
            and _campo(evento, "independent") is True
            and _campo(evento, "outcome") == OUTCOME_SOLVED
        ):
            acreditadas_acumuladas.add((skill, stage))

    # play_ms/math_ms son ACUMULATIVOS a lo largo de TODA la partida (no se
    # reinician en cada carga de pagina): el tiempo de ESTA carga es el delta
    # MAX-MIN dentro de ella, no el valor bruto. Se suman ambos relojes (aventura +
    # taller); ver LIMITE_TIEMPO_ACTIVO.
    tiempos_play = [e.play_ms for e in eventos_de_sesion if e.play_ms is not None]
    tiempos_math = [e.math_ms for e in eventos_de_sesion if e.math_ms is not None]
    delta_play_ms = (max(tiempos_play) - min(tiempos_play)) if tiempos_play else 0
    delta_math_ms = (max(tiempos_math) - min(tiempos_math)) if tiempos_math else 0
    tiempo_activo_ms = (delta_play_ms + delta_math_ms) if (tiempos_play or tiempos_math) else None

    decisiones = [e for e in eventos_de_sesion if e.tipo == TIPO_DECISION_EVALUATED]
    independientes = sum(1 for e in decisiones if _campo(e, "independent") is True)
    independencia = (independientes / len(decisiones)) if decisiones else None

    return LumaSesionHistorica(
        fecha=eventos_de_sesion[0].at_cliente.date(),
        eventos=len(eventos_de_sesion),
        tiempo_activo_ms=tiempo_activo_ms,
        independencia=independencia,
        casillas_acreditadas_acumuladas=len(acreditadas_acumuladas),
        fase_final=ultimo.phase,
        motivo_final=_motivo_final(eventos_de_sesion, ultimo.phase),
    )
