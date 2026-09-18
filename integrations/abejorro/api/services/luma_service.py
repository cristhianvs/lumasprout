"""Logica de negocio de la telemetria de LumaSprout.

Decision de diseno importante: LumaSesion (models/luma.py) NO tiene una columna
`token`. En vez de agregar una (fuera del alcance de este agente: modelos y
migraciones son responsabilidad de db-specialist), el token opaco por partida se
DERIVA con HMAC-SHA256 del propio `run_id` y el SECRET_KEY del servidor:

    token = HMAC(SECRET_KEY, "luma-telemetria-token-v1:" + run_id)

Ventajas: no hace falta almacenarlo ni consultarlo (abrir/reanudar y verificar son
operaciones sin estado adicional), es estable entre reinicios del servidor, y sigue
siendo opaco e imposible de forjar para quien no conoce SECRET_KEY.

Limitaciones reales de este esquema, aceptadas por el equipo para el piloto:
(a) No es revocable individualmente: para invalidar el token de UNA partida haria
    falta rotar SECRET_KEY, lo que invalidaria de paso todos los JWT de admin
    (verify_admin usa el mismo SECRET_KEY). Si mas adelante hace falta poder
    revocar una partida sin afectar al resto, hace falta una columna `token`
    dedicada en LumaSesion, y ese cambio le corresponde a db-specialist.
(b) `run_id` lo genera el CLIENTE, no el servidor: cualquiera puede llamar a
    POST /sesion con runIds inventados y obtener un token valido para cada uno
    (el HMAC no impide crear partidas, solo impide escribir en la de otro). El
    rate limit de RATE_LIMIT_SESION en routers/luma.py es la unica defensa
    contra la creacion masiva de sesiones basura; no hay una capa adicional.

Siete trampas del motor que este servicio respeta (ver encargo del equipo):
1. attempt.data.latencyMs es tiempo ENTRE intentos, no tiempo en el reto.
2. support (recomendado) != effectiveSupport (aplicado) != attempt.data.representation
   (lo que el nino realmente vio). El resumen no expone "lo que vio el nino": no hay
   ninguna consulta pedida sobre representation todavia.
3. adaptation_decision (frontera de reto) y los eventos "adaptation" con `rule` dentro
   del reto son fuentes distintas; este resumen solo agrega adaptation_decision, tal
   como se pidio.
4. decision_evaluated.data.learning tiene un bug conocido (referencia mutable): se
   descarta explicitamente de `resultado` en _resultado_decision_evaluated, y nunca
   se lee para calcular "resueltos_independientes" (se usa `independent`, no `learning`).
5. run_id + version identifican la partida; si el juego cambia de version aparece un
   run_id nuevo, y este servicio simplemente lo trata como una partida distinta.
6. La clave de idempotencia es (sesion_id, evento_id), nunca el id de evento suelto.
7. Solo los intentos SIN ayuda cuentan como dominio demostrado. La fuente principal
   es decision_evaluated.data.independent (ya calculado por el motor como
   `!wasAssisted`, donde wasAssisted = assisted || !firstAttempt); el conteo sobre
   attempt.data.correct/attemptNumber/assisted es un desglose secundario, no la
   fuente de verdad (ver LumaIntentos).

Ademas: la ausencia de heartbeat NO se interpreta como inactividad del nino. El
heartbeat solo se emite cada 5000 ms cuando el juego esta activo, asi que su ausencia
puede deberse a una pausa, a inactividad real o a una caida de red; el panel no debe
asumir cual de las tres. Ver LIMITE_HEARTBEAT.

LIMITACION CONOCIDA de la rejilla CPA (progresion): el motor exige ademas
`novel || stage !== 'transfer'` para acreditar una casilla de la etapa 'transfer'
(no acredita un transfer ya visto/repetido). Esa condicion no se puede verificar
desde aqui porque `novel` no forma parte del contrato de eventos que recibimos, asi
que _casillas_acreditadas puede SOBRECONTAR alguna casilla de 'transfer' como
acreditada cuando en realidad el motor no la acredito. No se intenta replicar esa
regla: se documenta como limitacion conocida, tal como pidio el equipo.
"""

import hashlib
import hmac
import logging
import statistics
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from models.luma import LumaEvento, LumaSesion
from schemas.luma import (
    LumaAutonomia,
    LumaAyuda,
    LumaBayesiano,
    LumaConteoTipo,
    LumaDecisionAdaptacion,
    LumaDestinos,
    LumaEstadoActual,
    LumaEtapasCPA,
    LumaEventoRechazado,
    LumaEventosSalida,
    LumaHabilidadProgresion,
    LumaInactividad,
    LumaIntentos,
    LumaLatenciaMedianaPorCategoria,
    LumaPausa,
    LumaProgresion,
    LumaRespuestaAnteError,
    LumaResumenSalida,
    LumaSesionEntrada,
    LumaSesionSalida,
)

logger = logging.getLogger(__name__)

TOKEN_ESPACIO_DE_NOMBRES = b"luma-telemetria-token-v1:"

SEGUNDOS_HEARTBEAT_RECIENTE = 15
LIMITE_EVENTOS_RESUMEN = 50_000

LIMITE_HEARTBEAT = (
    "La ausencia de heartbeat NO es evidencia de inactividad del nino: el heartbeat "
    "solo se emite cada 5000 ms cuando el juego esta activo, asi que su ausencia puede "
    "deberse a una pausa, a inactividad real o a una caida de red. No asumir cual de "
    "las tres sin mas contexto."
)

TIPO_ATTEMPT = "attempt"
TIPO_HINT_REQUESTED = "hint_requested"
TIPO_SUPPORT_SELECTED = "support_selected"
TIPO_IDLE_STARTED = "idle_started"
TIPO_PAUSE_STARTED = "pause_started"
TIPO_PAUSE_ENDED = "pause_ended"
TIPO_ADAPTATION_DECISION = "adaptation_decision"
TIPO_DECISION_EVALUATED = "decision_evaluated"
TIPO_DECISION_RESPONSE = "decision_response"
TIPO_HEARTBEAT = "heartbeat"
TIPO_TASK_PRESENTED = "task_presented"
TIPO_KNOWLEDGE_UPDATED = "knowledge_updated"
TIPO_UNCERTAINTY_REPORTED = "uncertainty_reported"
TIPO_POST_ERROR_ACTION = "post_error_action"
TIPO_NAVIGATION = "navigation"
TIPO_ROUTE_SELECTED = "route_selected"
TIPO_LEARNING_PATH_COMPLETED = "learning_path_completed"
TIPO_VOLUNTARY_BREAK = "voluntary_break"
TIPO_BREAK_SUGGESTED = "break_suggested"
TIPO_ITEM_BANK_EXHAUSTED = "item_bank_exhausted"

# Campo con bug conocido: guarda una referencia mutable y puede mostrar etapas
# futuras. Se filtra siempre de cualquier resultado expuesto por el resumen.
CAMPO_DECISION_EVALUATED_CON_BUG = "learning"

OUTCOME_SOLVED = "solved"

# Catalogo fijo del taller de matematicas: 6 habilidades x 4 etapas CPA = 24
# casillas. id, nombre para mostrar y prerrequisitos (otros ids de esta misma
# lista), tal como los especifico el equipo.
ETAPAS_CPA: tuple[str, str, str, str] = ("concrete", "pictorial", "abstract", "transfer")

CATALOGO_HABILIDADES: list[dict[str, Any]] = [
    {"id": "meaning", "nombre": "Partes de un entero", "prerrequisitos": []},
    {"id": "equivalent", "nombre": "Fracciones equivalentes", "prerrequisitos": ["meaning"]},
    {"id": "add_same", "nombre": "Sumar partes del mismo tamano", "prerrequisitos": ["meaning"]},
    {"id": "sub_same", "nombre": "Restar partes del mismo tamano", "prerrequisitos": ["meaning"]},
    {
        "id": "add_diff",
        "nombre": "Sumar con distintos denominadores",
        "prerrequisitos": ["equivalent", "add_same"],
    },
    {
        "id": "sub_diff",
        "nombre": "Restar con distintos denominadores",
        "prerrequisitos": ["equivalent", "sub_same"],
    },
]

CANTIDAD_CASILLAS_CPA = len(CATALOGO_HABILIDADES) * len(ETAPAS_CPA)  # 24

ESTADO_CASILLA_ACREDITADA = "acreditada"
ESTADO_CASILLA_EN_CURSO = "en_curso"
ESTADO_CASILLA_PENDIENTE = "pendiente"

# Regla de dominio bayesiano del motor: n intentos suficientes y probabilidad alta.
UMBRAL_N_DOMINIO = 3
UMBRAL_P_DOMINIO = 0.85

# --- respuesta_ante_error: tres salidas EXCLUYENTES ante un fallo (attempt correct=false) ---
CATEGORIA_REINTENTO_INMEDIATO = "reintento_inmediato"
CATEGORIA_BUSCA_AYUDA = "busca_ayuda"
CATEGORIA_INACTIVIDAD_BLOQUEO = "inactividad_bloqueo"
CATEGORIA_SIN_CLASIFICAR = "sin_clasificar"

CATEGORIAS_RESPUESTA_ANTE_ERROR = (
    CATEGORIA_REINTENTO_INMEDIATO,
    CATEGORIA_BUSCA_AYUDA,
    CATEGORIA_INACTIVIDAD_BLOQUEO,
)

# Listas blancas EXPLICITAS, verificadas por el equipo contra los 33 valores de
# data-action del motor (ninguno se construye dinamicamente: una lista cerrada es
# viable y es lo correcto, no una heuristica por subcadena).
#
# 'rhythm' queda deliberadamente FUERA de ayuda: el propio motor lo declara medio
# de respuesta, no pista ("no revelan el resultado ni el denominador comun"), y
# emite rhythm_played con assistance=false.
ACCIONES_POST_ERROR_DE_AYUDA = frozenset(
    {
        "hint",  # pide pista
        "support",  # cambio de canal (visual/audio/hands)
        "dont_know",  # boton "Todavia no se"; emite uncertainty_reported y fuerza apoyo concreto
        "use_pieces",  # "Responder con mis piezas"; pone assisted=true explicitamente
        "garden_sound",  # "Escuchar el jardin"; emite support_selected con voluntary=true
        "piece",  # tocar una pieza manipulativa; solo existe en el DOM ya en apoyo concreto
    }
)

ACCIONES_POST_ERROR_REINTENTO = frozenset(
    {
        "keydown",  # escribir en el campo de respuesta: la senal mas limpia de reintento
        "send",
        "shelter",
        "signal",
        "creature",
        "experience_submit",
        "experience_cell",
        "undo",
        "plan_step",
        "cargo_add",
        "cargo_remove",
        "paint_color",
    }
)

# Union usada solo para localizar el primer post_error_action "reconocido" al
# calcular la mediana de latencia: 'pointerdown' (clic en cualquier parte de la
# pantalla, incluidos botones de cabecera sin data-action) y cualquier otro valor
# desconocido no deben ensuciar la mediana, igual que no clasifican el fallo.
ACCIONES_POST_ERROR_RECONOCIDAS = ACCIONES_POST_ERROR_DE_AYUDA | ACCIONES_POST_ERROR_REINTENTO

RAZON_PAUSA_INACTIVIDAD = "idle"

# --- autonomia: ruta elegida y navegacion libre ---
DESTINOS_NAVEGACION = ("greenhouse", "station", "garden", "map")

# --- motivo_final: solo tiene sentido cuando la fase actual es 'complete' ---
FASE_COMPLETA = "complete"
MOTIVO_FINAL_MASTERY = "mastery"
MOTIVO_FINAL_BREAK = "break"
# item_bank_exhausted trae masteryGranted=false: es agotamiento del banco de
# items, NO dominio. Se expone con su propio motivo para no confundirlo con mastery.
MOTIVO_FINAL_BANK_EXHAUSTED = "bank_exhausted"


class SimulacionRechazadaError(Exception):
    """El cliente pidio abrir una partida marcada como simulation=true."""


# ---------------------------------------------------------------------------
# Token opaco por partida
# ---------------------------------------------------------------------------


def calcular_token(run_id: UUID) -> str:
    mensaje = TOKEN_ESPACIO_DE_NOMBRES + str(run_id).encode("ascii")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), mensaje, hashlib.sha256).hexdigest()


def token_valido_para(run_id: UUID, token: str | None) -> bool:
    return hmac.compare_digest(calcular_token(run_id), token or "")


# ---------------------------------------------------------------------------
# POST /sesion
# ---------------------------------------------------------------------------


async def _ultimo_evento_de(db: AsyncSession, sesion_id: UUID) -> tuple[int, str | None]:
    """(ultimo_indice, ultimo_evento_id) del evento con la secuencia mas alta ya
    guardado, o (-1, None) si la sesion no tiene ninguno. Una sola consulta
    (ORDER BY secuencia DESC LIMIT 1), apoyada en el indice (sesion_id, secuencia).

    La usan tanto POST /sesion (para reanudar) como POST /eventos (tras ingerir un
    lote): las dos rutas comparten esta unica funcion a proposito, para que nunca
    puedan divergir en su definicion de "el ultimo evento". El cliente compara el
    evento_id devuelto contra el suyo en esa misma posicion para detectar un
    conflicto multipestana por IDENTIDAD, no solo por cantidad (una cantidad igual
    no prueba que sean los mismos eventos)."""
    resultado = await db.execute(
        select(LumaEvento.secuencia, LumaEvento.evento_id)
        .where(LumaEvento.sesion_id == sesion_id)
        .order_by(LumaEvento.secuencia.desc())
        .limit(1)
    )
    fila = resultado.first()
    if fila is None:
        return -1, None
    return fila.secuencia, fila.evento_id


async def abrir_o_reanudar_sesion(db: AsyncSession, datos: LumaSesionEntrada) -> LumaSesionSalida:
    """Crea la sesion si no existe ese run_id, o reanuda la existente.

    Precondicion: el llamador (router) ya rechazo `simulation=true` con 403 antes de
    invocar esta funcion; los datos sinteticos no llegan a tocar la base de datos.
    """
    sesion = (
        await db.execute(select(LumaSesion).where(LumaSesion.run_id == datos.run_id))
    ).scalar_one_or_none()

    if sesion is None:
        sesion = LumaSesion(
            run_id=datos.run_id,
            version=datos.version,
            schema_version=datos.schema_version,
            policy_version=datos.policy_version,
            simulation=False,
        )
        db.add(sesion)
        await db.commit()
        await db.refresh(sesion)
        ultimo_indice, ultimo_evento_id = -1, None
        logger.info("Nueva partida de LumaSprout abierta (run_id=%s)", datos.run_id)
    else:
        # Misma funcion que POST /eventos, para que las dos rutas nunca puedan
        # divergir en su definicion de "el ultimo evento": el cliente necesita
        # poder verificar el evento_id antes de aceptar el cursor al reanudar
        # (sin esto, reanudaria a ciegas y podria saltarse eventos intermedios si
        # otra pestana o dispositivo escribio mientras tanto).
        ultimo_indice, ultimo_evento_id = await _ultimo_evento_de(db, sesion.id)
        logger.info(
            "Partida de LumaSprout reanudada (run_id=%s, ultimo_indice=%s)",
            datos.run_id,
            ultimo_indice,
        )

    return LumaSesionSalida(
        token=calcular_token(datos.run_id),
        ultimo_indice=ultimo_indice,
        ultimo_evento_id=ultimo_evento_id,
    )


# ---------------------------------------------------------------------------
# POST /eventos
# ---------------------------------------------------------------------------


def _parsear_secuencia(evento_id: str) -> int | None:
    _, _, sufijo = evento_id.rpartition(":")
    if not sufijo:
        return None
    try:
        return int(sufijo)
    except ValueError:
        return None


def _parsear_fecha(valor: Any) -> datetime | None:
    if not isinstance(valor, str) or not valor:
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parsear_uuid(valor: Any) -> UUID | None:
    if isinstance(valor, UUID):
        return valor
    if isinstance(valor, str):
        try:
            return UUID(valor)
        except ValueError:
            return None
    return None


def _validar_evento(sesion_id: UUID, evento: dict[str, Any]) -> dict[str, Any] | LumaEventoRechazado:
    """Valida y aplana un evento crudo, o explica por que se rechaza.

    Solo ESTE evento se descarta si algo no cuadra: el resto del lote se procesa
    igual (requisito explicito del encargo).
    """
    evento_id = evento.get("id")
    if not isinstance(evento_id, str) or not evento_id:
        return LumaEventoRechazado(id=None, motivo="id faltante o invalido")

    secuencia = _parsear_secuencia(evento_id)
    if secuencia is None:
        return LumaEventoRechazado(
            id=evento_id,
            motivo="id no tiene el formato '{session}:{indice}' con indice entero",
        )

    tipo = evento.get("type")
    if not isinstance(tipo, str) or not tipo:
        return LumaEventoRechazado(id=evento_id, motivo="type faltante")

    at_cliente = _parsear_fecha(evento.get("at"))
    if at_cliente is None:
        return LumaEventoRechazado(id=evento_id, motivo="at faltante o con formato invalido")

    session_carga = _parsear_uuid(evento.get("session"))
    if session_carga is None:
        return LumaEventoRechazado(id=evento_id, motivo="session faltante o con formato invalido")

    return {
        "id": uuid4(),
        "sesion_id": sesion_id,
        "evento_id": evento_id,
        "session_carga": session_carga,
        "secuencia": secuencia,
        "tipo": tipo,
        "at_cliente": at_cliente,
        "phase": evento.get("phase"),
        "scene": evento.get("scene"),
        "task": evento.get("task"),
        "experience": evento.get("experience"),
        "play_ms": evento.get("playMs"),
        "math_ms": evento.get("mathMs"),
        # Solo el sub-objeto `data` del envoltorio, NO el envoltorio completo: las
        # demas claves (phase, task, type, runId, session, version...) ya viven en
        # sus propias columnas de arriba, y guardarlas tambien aqui las duplicaria
        # sin aportar nada (bug real hallado por el equipo probando con datos del
        # juego: antes se guardaba `evento` completo).
        "data": evento.get("data") if isinstance(evento.get("data"), dict) else {},
    }


async def ingerir_eventos(
    db: AsyncSession, sesion: LumaSesion, eventos_crudos: list[dict[str, Any]]
) -> LumaEventosSalida:
    filas: list[dict[str, Any]] = []
    rechazados: list[LumaEventoRechazado] = []

    for evento in eventos_crudos:
        validado = _validar_evento(sesion.id, evento)
        if isinstance(validado, LumaEventoRechazado):
            rechazados.append(validado)
        else:
            filas.append(validado)

    guardados = 0
    if filas:
        sentencia = (
            pg_insert(LumaEvento)
            .values(filas)
            .on_conflict_do_nothing(index_elements=[LumaEvento.sesion_id, LumaEvento.evento_id])
            .returning(LumaEvento.evento_id)
        )
        resultado = await db.execute(sentencia)
        guardados = len(resultado.scalars().all())

        ats_cliente = [fila["at_cliente"] for fila in filas]
        sesion.primer_evento_at = (
            min(sesion.primer_evento_at, *ats_cliente) if sesion.primer_evento_at else min(ats_cliente)
        )
        sesion.ultimo_evento_at = (
            max(sesion.ultimo_evento_at, *ats_cliente) if sesion.ultimo_evento_at else max(ats_cliente)
        )

    duplicados = len(filas) - guardados
    sesion.ultima_recepcion_at = datetime.now(UTC)
    # `total_eventos` tiene default=0 a nivel de columna, pero ese default solo se
    # aplica durante un INSERT real; defensivo aqui por si alguna vez llega None.
    sesion.total_eventos = (sesion.total_eventos or 0) + guardados

    await db.commit()

    ultimo_indice, ultimo_evento_id = await _ultimo_evento_de(db, sesion.id)

    if rechazados:
        logger.warning(
            "Eventos de LumaSprout rechazados dentro de un lote (run_id=%s, cantidad=%s)",
            sesion.run_id,
            len(rechazados),
        )

    return LumaEventosSalida(
        guardados=guardados,
        duplicados=duplicados,
        ultimo_indice=ultimo_indice,
        ultimo_evento_id=ultimo_evento_id,
        rechazados=rechazados,
    )


# ---------------------------------------------------------------------------
# Administrativo: listar sesiones y eventos
# ---------------------------------------------------------------------------


async def listar_sesiones(
    db: AsyncSession, pagina: int, tamano_pagina: int
) -> tuple[list[LumaSesion], int]:
    """Partidas reales (simulation=false), mas recientes primero."""
    filtro = LumaSesion.simulation.is_(False)

    total = (await db.execute(select(func.count()).select_from(LumaSesion).where(filtro))).scalar_one()

    resultado = await db.execute(
        select(LumaSesion)
        .where(filtro)
        .order_by(LumaSesion.ultima_recepcion_at.desc())
        .offset((pagina - 1) * tamano_pagina)
        .limit(tamano_pagina)
    )
    return list(resultado.scalars().all()), total


async def listar_eventos(
    db: AsyncSession, sesion_id: UUID, desde: int, limite: int
) -> list[LumaEvento]:
    """Eventos de una partida con secuencia > desde, en orden ascendente."""
    resultado = await db.execute(
        select(LumaEvento)
        .where(LumaEvento.sesion_id == sesion_id, LumaEvento.secuencia > desde)
        .order_by(LumaEvento.secuencia.asc())
        .limit(limite)
    )
    return list(resultado.scalars().all())


# ---------------------------------------------------------------------------
# Administrativo: resumen derivado
# ---------------------------------------------------------------------------


def _interior_de(evento: LumaEvento) -> dict[str, Any]:
    """Devuelve el sub-objeto `data` real de un evento, para cuando hace falta el
    objeto COMPLETO (no un campo suelto: para eso esta `_campo`).

    `evento.data` ya es ese sub-objeto tras el fix de ingesta. RED TRANSITORIA: si
    la fila es de antes del fix (se guardaba el envoltorio completo), el contenido
    real vive un nivel mas abajo, en evento.data["data"]; se detecta por la
    presencia de esa clave y se usa esa en su lugar. Se puede borrar esta red el
    dia que se confirme que no quedan filas de antes del fix.
    """
    if isinstance(evento.data.get("data"), dict):
        return evento.data["data"]
    return evento.data


def _campo(evento: LumaEvento, nombre: str) -> Any:
    """Lee un campo del evento. `evento.data` YA ES el sub-objeto `data` del
    envoltorio (p.ej. attempt.data.attemptNumber vive en evento.data.attemptNumber),
    asi que se lee de ahi directamente.

    RED TRANSITORIA: antes del fix que guardaba el envoltorio COMPLETO en la
    columna `data` (bug real hallado por el equipo probando contra Postgres real),
    las filas ya ingeridas tienen el campo anidado un nivel mas abajo, en
    evento.data["data"][nombre]. Se prueba ahi solo como ultimo recurso, para no
    romper la lectura de filas guardadas antes de la correccion. Se puede borrar
    esta red el dia que se confirme que no quedan filas de antes del fix.
    """
    if nombre in evento.data:
        return evento.data[nombre]
    return _interior_de(evento).get(nombre)


def _motivo_final(eventos: list[LumaEvento], fase_actual: str | None) -> str | None:
    """Solo se calcula cuando la fase actual es 'complete': el motivo no viaja en un
    campo propio del sobre, se deriva del ULTIMO de estos eventos en toda la sesion.
    Si ninguno aparece, devuelve None ('sin dato'): no se adivina.

    item_bank_exhausted trae masteryGranted=false (agotamiento del banco de items,
    NO dominio), por eso tiene su propio motivo distinto de 'mastery'.
    """
    if fase_actual != FASE_COMPLETA:
        return None

    tipos_relevantes = (
        TIPO_LEARNING_PATH_COMPLETED,
        TIPO_VOLUNTARY_BREAK,
        TIPO_BREAK_SUGGESTED,
        TIPO_ITEM_BANK_EXHAUSTED,
    )
    ultimo_relevante = next((e for e in reversed(eventos) if e.tipo in tipos_relevantes), None)
    if ultimo_relevante is None:
        return None

    if ultimo_relevante.tipo == TIPO_LEARNING_PATH_COMPLETED:
        return MOTIVO_FINAL_MASTERY
    if ultimo_relevante.tipo in (TIPO_VOLUNTARY_BREAK, TIPO_BREAK_SUGGESTED):
        return MOTIVO_FINAL_BREAK
    return MOTIVO_FINAL_BANK_EXHAUSTED


def _estado_actual(eventos: list[LumaEvento]) -> LumaEstadoActual:
    ultimo = eventos[-1]
    ahora = datetime.now(UTC)
    ultimo_heartbeat = next((e for e in reversed(eventos) if e.tipo == TIPO_HEARTBEAT), None)
    heartbeat_reciente = (
        ultimo_heartbeat is not None
        and (ahora - ultimo_heartbeat.recibido_at).total_seconds() <= SEGUNDOS_HEARTBEAT_RECIENTE
    )
    return LumaEstadoActual(
        phase=ultimo.phase,
        scene=ultimo.scene,
        task=ultimo.task,
        experience=ultimo.experience,
        heartbeat_reciente=heartbeat_reciente,
        limite_heartbeat=LIMITE_HEARTBEAT,
        motivo_final=_motivo_final(eventos, ultimo.phase),
    )


def _conteos_por_tipo(eventos: list[LumaEvento]) -> list[LumaConteoTipo]:
    contador = Counter(e.tipo for e in eventos)
    return [
        LumaConteoTipo(tipo=tipo, cantidad=cantidad)
        for tipo, cantidad in sorted(contador.items(), key=lambda item: (-item[1], item[0]))
    ]


def _intentos(eventos: list[LumaEvento]) -> LumaIntentos:
    """`resueltos_independientes` es la fuente PRINCIPAL de "resuelto sin ayuda": lee
    decision_evaluated.data.independent, que el motor ya calcula como
    `!wasAssisted` (wasAssisted = assisted || !firstAttempt), asi que un reintento
    tambien cuenta como no independiente aunque el intento final no fuera asistido.
    El desglose sobre attempt (aciertos_primer_intento_sin_ayuda, reintentos,
    asistidos) es secundario y se calcula sobre correct/attemptNumber/assisted."""
    intentos = [e for e in eventos if e.tipo == TIPO_ATTEMPT]
    total = len(intentos)
    reintentos = 0
    asistidos = 0
    aciertos_primer_intento_sin_ayuda = 0
    for intento in intentos:
        numero = _campo(intento, "attemptNumber")
        asistido = bool(_campo(intento, "assisted"))
        correcto = bool(_campo(intento, "correct"))
        if isinstance(numero, int) and numero > 1:
            reintentos += 1
        if asistido:
            asistidos += 1
        if correcto and numero == 1 and not asistido:
            aciertos_primer_intento_sin_ayuda += 1

    resueltos_independientes = sum(
        1
        for e in eventos
        if e.tipo == TIPO_DECISION_EVALUATED and _campo(e, "independent") is True
    )

    return LumaIntentos(
        total=total,
        aciertos_primer_intento_sin_ayuda=aciertos_primer_intento_sin_ayuda,
        reintentos=reintentos,
        asistidos=asistidos,
        resueltos_independientes=resueltos_independientes,
    )


def _ayuda(eventos: list[LumaEvento]) -> LumaAyuda:
    hint_requested = sum(1 for e in eventos if e.tipo == TIPO_HINT_REQUESTED)
    apoyos = [e for e in eventos if e.tipo == TIPO_SUPPORT_SELECTED]
    voluntarios = sum(1 for e in apoyos if _campo(e, "voluntary") is True)
    impuestos = sum(1 for e in apoyos if _campo(e, "voluntary") is False)
    return LumaAyuda(
        hint_requested=hint_requested,
        apoyo_voluntario=voluntarios,
        apoyo_impuesto=impuestos,
    )


def _inactividad(eventos: list[LumaEvento]) -> LumaInactividad:
    idle_started = sum(1 for e in eventos if e.tipo == TIPO_IDLE_STARTED)

    pausas: list[LumaPausa] = []
    inicio_pendiente: datetime | None = None
    for evento in eventos:
        if evento.tipo == TIPO_PAUSE_STARTED:
            if inicio_pendiente is not None:
                # pause_started sin su pause_ended correspondiente: se reporta como
                # pausa sin cerrar en vez de perderse silenciosamente.
                pausas.append(LumaPausa(inicio_at=inicio_pendiente, fin_at=None, duracion_ms=None))
            inicio_pendiente = evento.at_cliente
        elif evento.tipo == TIPO_PAUSE_ENDED:
            if inicio_pendiente is not None:
                duracion_ms = int((evento.at_cliente - inicio_pendiente).total_seconds() * 1000)
                pausas.append(
                    LumaPausa(inicio_at=inicio_pendiente, fin_at=evento.at_cliente, duracion_ms=duracion_ms)
                )
                inicio_pendiente = None
            else:
                # pause_ended huerfano: no habia pause_started previo en la ventana.
                pausas.append(LumaPausa(inicio_at=None, fin_at=evento.at_cliente, duracion_ms=None))
    if inicio_pendiente is not None:
        pausas.append(LumaPausa(inicio_at=inicio_pendiente, fin_at=None, duracion_ms=None))

    return LumaInactividad(idle_started=idle_started, pausas=pausas)


def _resultado_decision_evaluated(evento: LumaEvento) -> dict[str, Any]:
    interior = _interior_de(evento)
    # CAMPO_DECISION_EVALUATED_CON_BUG guarda una referencia mutable con un bug
    # conocido (puede mostrar etapas futuras): nunca se expone en el resumen.
    return {k: v for k, v in interior.items() if k != CAMPO_DECISION_EVALUATED_CON_BUG}


def _decisiones_adaptacion(eventos: list[LumaEvento]) -> list[LumaDecisionAdaptacion]:
    decisiones = [e for e in eventos if e.tipo == TIPO_ADAPTATION_DECISION]
    evaluados = {
        _campo(e, "decisionId"): e for e in eventos if e.tipo == TIPO_DECISION_EVALUATED and _campo(e, "decisionId")
    }
    respuestas = {
        _campo(e, "decisionId"): e for e in eventos if e.tipo == TIPO_DECISION_RESPONSE and _campo(e, "decisionId")
    }

    salida: list[LumaDecisionAdaptacion] = []
    for decision in decisiones:
        decision_id = _campo(decision, "decisionId")
        evidencia = _campo(decision, "evidenceIds")
        evaluado = evaluados.get(decision_id) if decision_id else None
        respuesta = respuestas.get(decision_id) if decision_id else None

        if evaluado is not None:
            resuelta, resultado = True, _resultado_decision_evaluated(evaluado)
        elif respuesta is not None:
            resuelta, resultado = False, _interior_de(respuesta)
        else:
            resuelta, resultado = False, None

        salida.append(
            LumaDecisionAdaptacion(
                decision_id=decision_id,
                reason=_campo(decision, "reason"),
                effective_support=_campo(decision, "effectiveSupport"),
                evidencia_cantidad=len(evidencia) if isinstance(evidencia, list) else 0,
                resuelta=resuelta,
                resultado=resultado,
            )
        )
    return salida


# ---------------------------------------------------------------------------
# Progresion: rejilla de 6 habilidades x 4 etapas CPA
# ---------------------------------------------------------------------------


def _skill_y_stage_de_task_presented(evento: LumaEvento) -> tuple[str | None, str | None]:
    """Forma real verificada por el equipo contra el motor (app.js:602):
    task_presented.data = { item, skill, selection, prior, experience,
    representation, policy }, con item = el objeto de learningTask() completo
    ({ id, kind, a, b, op, answer, ..., stage, ... }).

    Es decir: `skill` vive en el NIVEL SUPERIOR de data; `stage` vive DENTRO de
    `item`, nunca al nivel superior de data. Orden de busqueda, tal como lo dio
    el equipo:
    1. data.skill + data.item.stage   -- la forma real, confirmada contra el motor.
    2. data.item.id + data.item.stage -- respaldo: el motor usa item.id como
       identificador de habilidad (state.knowledge[t.id]) si data.skill faltara.
    3. data.skill + data.stage        -- ultima red por si algun evento llega
       aplanado de una forma que no se ha visto todavia.
    """
    interior = _interior_de(evento)
    item = interior.get("item") if isinstance(interior.get("item"), dict) else {}

    stage_en_item = item.get("stage")
    if isinstance(interior.get("skill"), str) and isinstance(stage_en_item, str):
        return interior["skill"], stage_en_item

    if isinstance(item.get("id"), str) and isinstance(stage_en_item, str):
        return item["id"], stage_en_item

    return interior.get("skill"), interior.get("stage")


def _casillas_acreditadas(eventos: list[LumaEvento]) -> set[tuple[str, str]]:
    """(skill, stage) acreditados: decision_evaluated con independent=true y
    outcome='solved'. Nunca lee decision_evaluated.data.learning (bug conocido).

    LIMITACION CONOCIDA: el motor exige ademas `novel || stage !== 'transfer'`, dato
    que no recibimos, asi que una casilla de 'transfer' puede aparecer aqui como
    acreditada aunque el motor no la haya acreditado por no ser "novel". Ver
    docstring del modulo.
    """
    acreditadas: set[tuple[str, str]] = set()
    for evento in eventos:
        if evento.tipo != TIPO_DECISION_EVALUATED:
            continue
        if _campo(evento, "independent") is not True:
            continue
        if _campo(evento, "outcome") != OUTCOME_SOLVED:
            continue
        skill = _campo(evento, "skill")
        stage = _campo(evento, "stage")
        if isinstance(skill, str) and isinstance(stage, str):
            acreditadas.add((skill, stage))
    return acreditadas


def _etapa_en_curso_por_habilidad(eventos: list[LumaEvento]) -> dict[str, str]:
    """La etapa del ultimo task_presented de cada habilidad. `eventos` ya viene
    ordenado ascendente por secuencia, asi que la ultima asignacion por skill gana."""
    en_curso: dict[str, str] = {}
    for evento in eventos:
        if evento.tipo != TIPO_TASK_PRESENTED:
            continue
        skill, stage = _skill_y_stage_de_task_presented(evento)
        if isinstance(skill, str) and isinstance(stage, str):
            en_curso[skill] = stage
    return en_curso


def _bayesiano_por_habilidad(eventos: list[LumaEvento]) -> dict[str, dict[str, Any]]:
    """El ultimo knowledge_updated.data.posterior ({p, n, correct}) de cada habilidad."""
    posteriores: dict[str, dict[str, Any]] = {}
    for evento in eventos:
        if evento.tipo != TIPO_KNOWLEDGE_UPDATED:
            continue
        skill = _campo(evento, "skill")
        posterior = _campo(evento, "posterior")
        if isinstance(skill, str) and isinstance(posterior, dict):
            posteriores[skill] = posterior
    return posteriores


def _dominada(posterior: dict[str, Any] | None) -> tuple[float | None, int | None, bool]:
    if posterior is None:
        return None, None, False
    p = posterior.get("p")
    n = posterior.get("n")
    dominada = (
        isinstance(n, int) and isinstance(p, int | float) and n >= UMBRAL_N_DOMINIO and p >= UMBRAL_P_DOMINIO
    )
    return p, n, dominada


def construir_progresion(eventos: list[LumaEvento]) -> LumaProgresion:
    acreditadas = _casillas_acreditadas(eventos)
    en_curso_por_habilidad = _etapa_en_curso_por_habilidad(eventos)
    bayesianos_por_habilidad = _bayesiano_por_habilidad(eventos)

    habilidades: list[LumaHabilidadProgresion] = []
    acreditadas_total = 0
    for catalogo in CATALOGO_HABILIDADES:
        skill_id = catalogo["id"]
        en_curso = en_curso_por_habilidad.get(skill_id)

        etapas: dict[str, str] = {}
        for etapa in ETAPAS_CPA:
            if (skill_id, etapa) in acreditadas:
                etapas[etapa] = ESTADO_CASILLA_ACREDITADA
                acreditadas_total += 1
            elif en_curso == etapa:
                etapas[etapa] = ESTADO_CASILLA_EN_CURSO
            else:
                etapas[etapa] = ESTADO_CASILLA_PENDIENTE

        p, n, dominada = _dominada(bayesianos_por_habilidad.get(skill_id))

        habilidades.append(
            LumaHabilidadProgresion(
                id=skill_id,
                nombre=catalogo["nombre"],
                prerrequisitos=catalogo["prerrequisitos"],
                bayesiano=LumaBayesiano(p=p, n=n, dominada=dominada),
                etapas=LumaEtapasCPA(**etapas),
            )
        )

    return LumaProgresion(
        habilidades=habilidades,
        acreditadas_total=acreditadas_total,
        de_24=CANTIDAD_CASILLAS_CPA,
    )


def _progresion_vacia() -> LumaProgresion:
    return construir_progresion([])


# ---------------------------------------------------------------------------
# respuesta_ante_error: tres salidas EXCLUYENTES ante un fallo, fallo por fallo
# ---------------------------------------------------------------------------


def _categoria_de_evento(evento: LumaEvento) -> str | None:
    """Devuelve la categoria que determina ESTE evento si es uno de los que el
    equipo listo como clasificadores, o None si no aplica (el llamador sigue
    buscando en el siguiente evento posterior al fallo).

    Para post_error_action, SOLO clasifica si su `action` esta en una de las dos
    listas blancas explicitas del motor. 'pointerdown' o cualquier valor
    desconocido devuelven None a proposito: un clic en cualquier parte de la
    pantalla (incluidos botones de cabecera sin data-action) no es evidencia de
    reintento ni de ayuda, y contarlo como reintento confundiria un desenganche
    con perseverancia.
    """
    if evento.tipo in (TIPO_HINT_REQUESTED, TIPO_UNCERTAINTY_REPORTED):
        return CATEGORIA_BUSCA_AYUDA
    if evento.tipo == TIPO_SUPPORT_SELECTED and _campo(evento, "voluntary") is True:
        return CATEGORIA_BUSCA_AYUDA
    if evento.tipo == TIPO_PAUSE_ENDED and _campo(evento, "help") is True:
        # El boton "Volver con una pista" del dialogo de pausa nunca aparece en
        # post_error_action (el registro de interacciones esta desactivado
        # durante la pausa); esta es su unica senal.
        return CATEGORIA_BUSCA_AYUDA
    if evento.tipo == TIPO_IDLE_STARTED:
        return CATEGORIA_INACTIVIDAD_BLOQUEO
    if evento.tipo == TIPO_PAUSE_STARTED and _campo(evento, "reason") == RAZON_PAUSA_INACTIVIDAD:
        return CATEGORIA_INACTIVIDAD_BLOQUEO
    if evento.tipo == TIPO_ATTEMPT:
        return CATEGORIA_REINTENTO_INMEDIATO
    if evento.tipo == TIPO_POST_ERROR_ACTION:
        accion = _campo(evento, "action")
        if accion in ACCIONES_POST_ERROR_DE_AYUDA:
            return CATEGORIA_BUSCA_AYUDA
        if accion in ACCIONES_POST_ERROR_REINTENTO:
            return CATEGORIA_REINTENTO_INMEDIATO
        return None
    return None


def _mediana(valores: list[float]) -> float | None:
    return statistics.median(valores) if valores else None


def _clasificar_fallos(eventos: list[LumaEvento]) -> list[tuple[LumaEvento, str, list[LumaEvento]]]:
    """Encuentra cada fallo (attempt con correct=false) de UNA sesion y, para cada
    uno, su categoria y los eventos posteriores que se consideraron para llegar a
    ella. Es el nucleo que reutilizan tanto el resumen de una partida
    (`_respuesta_ante_error`) como las series agregadas por dia
    (`services/luma_dashboard.py`): la definicion de "como se clasifica un fallo"
    vive en un solo lugar.

    La "ventana" de un fallo termina en el siguiente fallo de la MISMA lista de
    eventos recibida, o al final de esa lista, para no atribuirle a un fallo lo
    que en realidad siguio a otro posterior. Si `eventos` no es la sesion
    completa (p.ej. solo una ventana de dias), esa es tambien la frontera de la
    clasificacion: ver la limitacion documentada en el llamador correspondiente.
    """
    fallos = [e for e in eventos if e.tipo == TIPO_ATTEMPT and _campo(e, "correct") is False]

    resultado: list[tuple[LumaEvento, str, list[LumaEvento]]] = []
    for indice, fallo in enumerate(fallos):
        limite_ventana = fallos[indice + 1].secuencia if indice + 1 < len(fallos) else None
        posteriores = [
            e
            for e in eventos
            if e.secuencia > fallo.secuencia and (limite_ventana is None or e.secuencia < limite_ventana)
        ]
        categoria = next(
            (posible for e in posteriores if (posible := _categoria_de_evento(e)) is not None),
            CATEGORIA_SIN_CLASIFICAR,
        )
        resultado.append((fallo, categoria, posteriores))
    return resultado


def _latencia_util_de_categoria(categoria: str, posteriores: list[LumaEvento]) -> float | None:
    """El primer post_error_action RECONOCIDO (accion en alguna de las dos listas
    blancas) dentro de la ventana de un fallo ya clasificado, o None si no hay
    ninguno. Un 'pointerdown' de por medio (clic sin relacion con el fallo) no
    debe ensuciar la mediana de latencia."""
    if categoria == CATEGORIA_SIN_CLASIFICAR:
        return None
    primer_post_error_action_util = next(
        (
            e
            for e in posteriores
            if e.tipo == TIPO_POST_ERROR_ACTION and _campo(e, "action") in ACCIONES_POST_ERROR_RECONOCIDAS
        ),
        None,
    )
    if primer_post_error_action_util is None:
        return None
    latencia = _campo(primer_post_error_action_util, "latencyMs")
    return latencia if isinstance(latencia, int | float) else None


def _respuesta_ante_error(eventos: list[LumaEvento]) -> LumaRespuestaAnteError:
    """Clasifica CADA fallo (attempt con correct=false) de una partida por
    separado; ver `_clasificar_fallos` para el algoritmo."""
    conteos = dict.fromkeys((*CATEGORIAS_RESPUESTA_ANTE_ERROR, CATEGORIA_SIN_CLASIFICAR), 0)
    latencias: dict[str, list[float]] = {categoria: [] for categoria in CATEGORIAS_RESPUESTA_ANTE_ERROR}

    for _fallo, categoria, posteriores in _clasificar_fallos(eventos):
        conteos[categoria] += 1
        latencia = _latencia_util_de_categoria(categoria, posteriores)
        if latencia is not None:
            latencias[categoria].append(latencia)

    return LumaRespuestaAnteError(
        reintento_inmediato=conteos[CATEGORIA_REINTENTO_INMEDIATO],
        busca_ayuda=conteos[CATEGORIA_BUSCA_AYUDA],
        inactividad_bloqueo=conteos[CATEGORIA_INACTIVIDAD_BLOQUEO],
        sin_clasificar=conteos[CATEGORIA_SIN_CLASIFICAR],
        latencia_mediana_ms=LumaLatenciaMedianaPorCategoria(
            reintento_inmediato=_mediana(latencias[CATEGORIA_REINTENTO_INMEDIATO]),
            busca_ayuda=_mediana(latencias[CATEGORIA_BUSCA_AYUDA]),
            inactividad_bloqueo=_mediana(latencias[CATEGORIA_INACTIVIDAD_BLOQUEO]),
        ),
    )


# ---------------------------------------------------------------------------
# autonomia: ruta elegida (guiada/libre) y navegacion
# ---------------------------------------------------------------------------


def _autonomia(eventos: list[LumaEvento]) -> LumaAutonomia:
    ruta_actual: str | None = None
    cambios_de_ruta = 0
    for evento in eventos:
        if evento.tipo != TIPO_ROUTE_SELECTED:
            continue
        ruta = _campo(evento, "route")
        if not isinstance(ruta, str):
            continue
        if ruta_actual is not None and ruta != ruta_actual:
            cambios_de_ruta += 1
        ruta_actual = ruta

    navegaciones = [e for e in eventos if e.tipo == TIPO_NAVIGATION]
    conteo_destinos = Counter(
        destino
        for e in navegaciones
        if (destino := _campo(e, "destination")) in DESTINOS_NAVEGACION
    )

    return LumaAutonomia(
        ruta_actual=ruta_actual,
        cambios_de_ruta=cambios_de_ruta,
        navegaciones=len(navegaciones),
        destinos=LumaDestinos(**{destino: conteo_destinos.get(destino, 0) for destino in DESTINOS_NAVEGACION}),
    )


def construir_resumen(run_id: UUID, eventos: list[LumaEvento]) -> LumaResumenSalida:
    if not eventos:
        return LumaResumenSalida(
            run_id=run_id,
            estado_actual=LumaEstadoActual(
                phase=None,
                scene=None,
                task=None,
                experience=None,
                heartbeat_reciente=False,
                motivo_final=None,
            ),
            conteos_por_tipo=[],
            intentos=LumaIntentos(
                total=0,
                aciertos_primer_intento_sin_ayuda=0,
                reintentos=0,
                asistidos=0,
                resueltos_independientes=0,
            ),
            ayuda=LumaAyuda(hint_requested=0, apoyo_voluntario=0, apoyo_impuesto=0),
            inactividad=LumaInactividad(idle_started=0, pausas=[]),
            decisiones_adaptacion=[],
            progresion=_progresion_vacia(),
            respuesta_ante_error=_respuesta_ante_error([]),
            autonomia=_autonomia([]),
        )

    eventos_ordenados = sorted(eventos, key=lambda e: e.secuencia)
    return LumaResumenSalida(
        run_id=run_id,
        estado_actual=_estado_actual(eventos_ordenados),
        conteos_por_tipo=_conteos_por_tipo(eventos_ordenados),
        intentos=_intentos(eventos_ordenados),
        ayuda=_ayuda(eventos_ordenados),
        inactividad=_inactividad(eventos_ordenados),
        decisiones_adaptacion=_decisiones_adaptacion(eventos_ordenados),
        progresion=construir_progresion(eventos_ordenados),
        respuesta_ante_error=_respuesta_ante_error(eventos_ordenados),
        autonomia=_autonomia(eventos_ordenados),
    )
