"""Schemas de telemetria de LumaSprout (abejorro.ai/luma).

El envoltorio de cada evento de juego llega en camelCase (viene de un cliente en
TypeScript): runId, schemaVersion, policyVersion, playMs, mathMs. Los dos modelos
publicos (abrir sesion, ingerir eventos) reflejan ese contrato con alias. Los modelos
administrativos usan snake_case, igual que el resto del panel (ver
schemas/protocolo42_estadisticas.py).

Limites que deben viajar en la respuesta del resumen (punto no negociable del contrato):
el motor no infiere estados emocionales ni produce diagnosticos (anxiety: 'no inferible',
isClinicalInference: false), y `latencyMs` de un intento mide el tiempo ENTRE intentos,
no el tiempo en el reto. Ver LIMITE_LATENCIA y LIMITE_INACTIVIDAD mas abajo.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MAXIMO_EVENTOS_POR_LOTE = 200

LIMITE_LATENCIA = (
    "latencyMs mide el tiempo ENTRE intentos, no el tiempo empleado en el reto: el "
    "contador se reinicia tras cada intento (trampa verificada del motor)."
)
LIMITE_INACTIVIDAD = (
    "No es una inferencia de estado emocional ni un diagnostico clinico. El motor "
    "declara explicitamente anxiety='no inferible' e isClinicalInference=false; esto "
    "solo cuenta pausas e inicios de inactividad tal como los reporta el cliente."
)
LIMITE_HEARTBEAT = (
    "Su ausencia NO implica inactividad del nino: el heartbeat solo se emite cada "
    "5000 ms cuando el juego esta activo, asi que su ausencia puede deberse a una "
    "pausa, a inactividad real o a una caida de red. No asumir cual de las tres."
)
LIMITE_RESPUESTA_ANTE_ERROR = (
    "Es una clasificacion CONDUCTUAL de que ocurrio despues del fallo, no una "
    "inferencia de estado emocional: un nino que se queda quieto puede estar "
    "pensando, no bloqueado."
)


# ---------------------------------------------------------------------------
# Publico: POST /api/luma/sesion
# ---------------------------------------------------------------------------


class LumaSesionEntrada(BaseModel):
    """Cuerpo de POST /sesion: abre o reanuda una partida."""

    model_config = ConfigDict(populate_by_name=True)

    run_id: UUID = Field(alias="runId")
    version: str = Field(min_length=1, max_length=50)
    schema_version: str = Field(alias="schemaVersion", min_length=1, max_length=50)
    policy_version: str = Field(alias="policyVersion", min_length=1, max_length=50)
    simulation: bool


class LumaSesionSalida(BaseModel):
    """Respuesta de POST /sesion."""

    model_config = ConfigDict(populate_by_name=True)

    token: str
    ultimo_indice: int = Field(alias="ultimoIndice")
    ultimo_evento_id: str | None = Field(
        alias="ultimoEventoId",
        description="El evento_id correspondiente a ultimoIndice, o None si la "
        "partida no tiene ningun evento. El cliente lo compara contra su propio "
        "evento en esa posicion ANTES de aceptar el cursor al reanudar: sin esto, "
        "reanudaria a ciegas y, si otra pestana o dispositivo escribio mientras "
        "tanto, saltaria el cursor sin enviar nunca los eventos intermedios.",
    )


# ---------------------------------------------------------------------------
# Publico: POST /api/luma/eventos
# ---------------------------------------------------------------------------


class LumaEventosEntrada(BaseModel):
    """Cuerpo de POST /eventos: un lote de eventos de una partida.

    Los eventos se aceptan como dict crudo (no un schema estricto por tipo): el
    envoltorio tiene unos 60 tipos distintos y cada uno valida su propio `id` por
    separado en el servicio, de forma que un evento malformado se rechaza SOLO a el,
    sin tumbar el resto del lote. Un error de forma aqui (falta runId, eventos vacio o
    con mas de MAXIMO_EVENTOS_POR_LOTE) si tumba el lote entero: son errores del
    cliente, no del contenido de un evento puntual.
    """

    model_config = ConfigDict(populate_by_name=True)

    run_id: UUID = Field(alias="runId")
    eventos: list[dict[str, Any]] = Field(min_length=1, max_length=MAXIMO_EVENTOS_POR_LOTE)


class LumaEventoRechazado(BaseModel):
    """Un evento del lote que no se pudo guardar, sin tumbar el resto del lote."""

    id: str | None
    motivo: str


class LumaEventosSalida(BaseModel):
    """Respuesta de POST /eventos."""

    model_config = ConfigDict(populate_by_name=True)

    guardados: int
    duplicados: int
    ultimo_indice: int = Field(alias="ultimoIndice")
    ultimo_evento_id: str | None = Field(
        alias="ultimoEventoId",
        description="El evento_id (formato '{session}:{indice}') del evento con la "
        "secuencia mas alta ya guardado para esta partida, es decir el que "
        "corresponde a ultimoIndice. None si la partida no tiene ningun evento. "
        "El cliente lo compara contra el suyo en esa misma posicion: si no "
        "coinciden, otra pestana escribio eventos distintos con la misma "
        "cantidad (deteccion de conflicto multipestana por IDENTIDAD, no por "
        "cantidad).",
    )
    rechazados: list[LumaEventoRechazado] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Administrativo: GET /api/admin/luma/sesiones
# ---------------------------------------------------------------------------


class LumaSesionAdminSalida(BaseModel):
    """Una fila de GET /admin/luma/sesiones."""

    run_id: UUID
    participante_codigo: str | None
    version: str
    total_eventos: int
    primer_evento_at: datetime | None
    ultimo_evento_at: datetime | None
    ultima_recepcion_at: datetime | None
    antiguedad_segundos: float | None = Field(
        description="Segundos desde ultima_recepcion_at (reloj del SERVIDOR) hasta ahora."
    )


class LumaSesionesListaSalida(BaseModel):
    sesiones: list[LumaSesionAdminSalida]
    total: int
    pagina: int
    tamano_pagina: int


# ---------------------------------------------------------------------------
# Administrativo: GET /api/admin/luma/sesiones/{run_id}/eventos
# ---------------------------------------------------------------------------


class LumaEventoAdminSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    evento_id: str
    secuencia: int
    tipo: str
    at_cliente: datetime
    recibido_at: datetime
    phase: str | None
    scene: int | None
    task: str | None
    experience: str | None
    play_ms: int | None
    math_ms: int | None
    data: dict[str, Any]


class LumaEventosListaSalida(BaseModel):
    eventos: list[LumaEventoAdminSalida]
    ultimo_indice: int


# ---------------------------------------------------------------------------
# Administrativo: GET /api/admin/luma/sesiones/{run_id}/resumen
# ---------------------------------------------------------------------------


class LumaEstadoActual(BaseModel):
    phase: str | None
    scene: int | None
    task: str | None
    experience: str | None
    heartbeat_reciente: bool = Field(
        description="True si llego un evento 'heartbeat' en los ultimos 15 s (reloj del servidor)."
    )
    limite_heartbeat: str = LIMITE_HEARTBEAT
    motivo_final: str | None = Field(
        description="Solo se calcula cuando phase=='complete': 'mastery', 'break', "
        "'bank_exhausted' o None si no hay evidencia (el panel debe mostrar 'sin dato', "
        "nunca adivinar)."
    )


class LumaConteoTipo(BaseModel):
    tipo: str
    cantidad: int


class LumaIntentos(BaseModel):
    total: int
    aciertos_primer_intento_sin_ayuda: int = Field(
        description="Desglose SECUNDARIO calculado sobre attempt.data "
        "(correct && attemptNumber==1 && !assisted). La fuente principal de "
        "'resuelto sin ayuda' es resueltos_independientes."
    )
    reintentos: int
    asistidos: int
    resueltos_independientes: int = Field(
        description="Fuente PRINCIPAL: cantidad de decision_evaluated.data.independent "
        "== true, ya calculado por el motor como !wasAssisted "
        "(wasAssisted = assisted || !firstAttempt)."
    )
    limite_latencia: str = LIMITE_LATENCIA


class LumaAyuda(BaseModel):
    hint_requested: int
    apoyo_voluntario: int
    apoyo_impuesto: int


class LumaPausa(BaseModel):
    inicio_at: datetime | None
    fin_at: datetime | None
    duracion_ms: int | None


class LumaInactividad(BaseModel):
    idle_started: int
    pausas: list[LumaPausa]
    limite: str = LIMITE_INACTIVIDAD


class LumaDecisionAdaptacion(BaseModel):
    decision_id: str | None
    reason: str | None
    effective_support: str | None
    evidencia_cantidad: int
    resuelta: bool
    resultado: dict[str, Any] | None = Field(
        description="decision_evaluated (sin el campo 'learning', con bug conocido) o "
        "decision_response si la decision fallo. None si aun no se resolvio."
    )


# ---------------------------------------------------------------------------
# Progresion: rejilla de 6 habilidades x 4 etapas CPA (taller de matematicas)
# ---------------------------------------------------------------------------


class LumaBayesiano(BaseModel):
    """Estado bayesiano de una habilidad (knowledge_updated.data.posterior).

    Distinto del recorrido CPA de `etapas`: p/n miden confianza estadistica sobre el
    dominio de la habilidad en su conjunto, no en que etapa concreta/pictorica/
    abstracta/transfer va el nino. El panel los muestra por separado, nunca como
    equivalentes.
    """

    p: float | None
    n: int | None
    dominada: bool = Field(description="Regla del motor: n >= 3 y p >= 0.85.")


class LumaEtapasCPA(BaseModel):
    concrete: str
    pictorial: str
    abstract: str
    transfer: str


class LumaHabilidadProgresion(BaseModel):
    id: str
    nombre: str
    prerrequisitos: list[str]
    bayesiano: LumaBayesiano
    etapas: LumaEtapasCPA


class LumaProgresion(BaseModel):
    """Rejilla completa: 6 habilidades x 4 etapas CPA = 24 casillas.

    Cada casilla es 'acreditada', 'en_curso' o 'pendiente'; ver
    services/luma_service.py (_casillas_acreditadas) para como se deriva de los
    eventos y su limitacion conocida sobre la etapa 'transfer'.
    """

    habilidades: list[LumaHabilidadProgresion]
    acreditadas_total: int
    de_24: int


# ---------------------------------------------------------------------------
# respuesta_ante_error: tres salidas EXCLUYENTES ante un fallo (attempt correct=false)
# ---------------------------------------------------------------------------


class LumaLatenciaMedianaPorCategoria(BaseModel):
    reintento_inmediato: float | None
    busca_ayuda: float | None
    inactividad_bloqueo: float | None


class LumaRespuestaAnteError(BaseModel):
    """Clasificacion, fallo por fallo, de que hizo el nino despues de un error.

    NO es un desglose de contadores sueltos de toda la sesion: cada fallo cuenta en
    UNA sola categoria (la del primer evento posterior que la determina), o en
    'sin_clasificar' si la sesion termino antes de que ocurriera algo clasificable.
    """

    reintento_inmediato: int
    busca_ayuda: int
    inactividad_bloqueo: int
    sin_clasificar: int
    latencia_mediana_ms: LumaLatenciaMedianaPorCategoria = Field(
        description="Mediana de post_error_action.data.latencyMs por categoria "
        "(None si esa categoria no tiene ningun post_error_action registrado)."
    )
    limite: str = LIMITE_RESPUESTA_ANTE_ERROR


# ---------------------------------------------------------------------------
# autonomia: ruta elegida (guiada/libre) y navegacion
# ---------------------------------------------------------------------------


class LumaDestinos(BaseModel):
    greenhouse: int
    station: int
    garden: int
    map: int


class LumaAutonomia(BaseModel):
    ruta_actual: str | None = Field(description="'guided', 'free' o None si no hubo route_selected.")
    cambios_de_ruta: int = Field(description="Veces que la ruta vigente cambio de valor (no cuenta la eleccion inicial).")
    navegaciones: int
    destinos: LumaDestinos


class LumaResumenSalida(BaseModel):
    run_id: UUID
    estado_actual: LumaEstadoActual
    conteos_por_tipo: list[LumaConteoTipo]
    intentos: LumaIntentos
    ayuda: LumaAyuda
    inactividad: LumaInactividad
    decisiones_adaptacion: list[LumaDecisionAdaptacion]
    progresion: LumaProgresion
    respuesta_ante_error: LumaRespuestaAnteError
    autonomia: LumaAutonomia
