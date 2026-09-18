"""Schemas del panel agregado/historico de LumaSprout (panorama, series, historico).

Distinto del resumen en vivo de una partida (schemas/luma.py): estos endpoints
responden "esta funcionando el juego" viendo la evolucion en el tiempo de TODO el
estudio o de un participante, no el estado de una partida puntual.

Reutiliza las constantes de limite (LIMITE_LATENCIA, LIMITE_INACTIVIDAD, etc.) y las
categorias de respuesta_ante_error de schemas/luma.py: un agregado no deja de
necesitar su advertencia por ser agregado.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from schemas.luma import LIMITE_INACTIVIDAD, LIMITE_RESPUESTA_ANTE_ERROR

LIMITE_MODALIDADES = (
    "Distribucion de que modalidad (experience) se uso, NO una medida de eficacia: "
    "una modalidad mas frecuente no es una modalidad mejor."
)
LIMITE_INDEPENDENCIA = (
    "Se calcula igual que 'resueltos_independientes' en el resumen de una partida: "
    "decision_evaluated.data.independent, no una inferencia de esfuerzo o dificultad."
)
LIMITE_TIEMPO_ACTIVO = (
    "Suma dos relojes independientes del propio juego: play_ms (la aventura) y "
    "math_ms (el taller de matematicas), cada uno con un tope duro de 300000 ms. "
    "Ambos son ACUMULATIVOS a lo largo de toda la partida (persisten en localStorage "
    "entre recargas), por eso se mide como MAX-MIN dentro de cada carga de pagina, "
    "no como su valor bruto. Es tiempo de EXPOSICION al juego, no esfuerzo ni "
    "dificultad."
)
LIMITE_RESPUESTA_ANTE_ERROR_SERIE = (
    LIMITE_RESPUESTA_ANTE_ERROR
    + " Ademas: la clasificacion de un fallo cercano al limite de la ventana de dias "
    "solicitada puede salir como 'sin_clasificar' aunque el nino si haya recibido "
    "una respuesta (ver limitacion en el docstring de services/luma_dashboard.py); "
    "un pico de sin_clasificar en el primer dia de la ventana no es un hallazgo "
    "sobre los ninos."
)

DIAS_SERIES_DEFECTO = 30
DIAS_SERIES_MAXIMO = 365


# ---------------------------------------------------------------------------
# GET /api/admin/luma/panorama
# ---------------------------------------------------------------------------


class LumaConteoSesionesPorDia(BaseModel):
    dia: str
    sesiones: int
    eventos: int


class LumaConteoFase(BaseModel):
    """Se reutiliza en dos contextos con significado distinto: en `embudo_fases`,
    `participantes` es ACUMULATIVO (llegaron al menos hasta esa fase, segun la fase
    mas avanzada que registraron); en `abandono_por_fase`, es la fase en la que se
    quedaron (no acumulativo). Ver la descripcion del campo que la contiene."""

    fase: str
    participantes: int


class LumaConteoMotivoCierre(BaseModel):
    motivo: str = Field(description="'mastery', 'break', 'bank_exhausted' o 'sin_dato'.")
    participantes: int


class LumaConteoModalidad(BaseModel):
    experience: str
    eventos: int
    limite: str = LIMITE_MODALIDADES


class LumaRetencion(BaseModel):
    con_una_sesion: int
    con_dos_sesiones: int
    con_tres_o_mas_sesiones: int
    mediana_dias_entre_sesiones: float | None = Field(
        description="Mediana, sobre todos los participantes con 2+ sesiones, del "
        "numero de dias entre sesiones consecutivas del mismo run_id. None si "
        "ningun participante tiene 2 o mas sesiones."
    )


class LumaConteoEscena(BaseModel):
    scene: int
    participantes: int


class LumaConteoHabilidadEtapa(BaseModel):
    habilidad: str
    etapa: str
    participantes: int


class LumaBancoAgotado(BaseModel):
    habilidad: str | None
    etapa: str | None
    veces: int


class LumaPuntosDeFuga(BaseModel):
    """Solo participantes cuya ULTIMA fase conocida no es 'complete': donde se
    quedan los que no terminan."""

    abandono_por_fase: list[LumaConteoFase] = Field(
        description="Participantes que se quedaron en cada fase (excluye 'complete')."
    )
    abandono_por_escena: list[LumaConteoEscena] = Field(
        description="Entre los que se quedaron en fase 'play', ultimo scene alcanzado."
    )
    abandono_por_habilidad_y_etapa: list[LumaConteoHabilidadEtapa] = Field(
        description="Entre los que se quedaron en fase 'math', ultima casilla CPA "
        "(del ultimo task_presented) en la que estaban."
    )
    banco_agotado: list[LumaBancoAgotado] = Field(
        description="Veces que se emitio item_bank_exhausted, por habilidad y etapa: "
        "senala directamente que parte del banco de ejercicios hay que ampliar."
    )


class LumaPanoramaSalida(BaseModel):
    generado: datetime
    sesiones_total: int = Field(description="Sesiones de juego (session_carga) distintas.")
    participantes_total: int = Field(description="run_id distintos.")
    eventos_total: int
    sesiones_por_dia: list[LumaConteoSesionesPorDia]
    embudo_fases: list[LumaConteoFase] = Field(
        description="ACUMULATIVO y monotono no creciente en el orden welcome/play/"
        "bridge/math/complete: cada fase cuenta a quien llego AL MENOS hasta ahi, "
        "segun la fase mas avanzada que registro (no solo quien tuvo algun evento "
        "en esa fase puntual)."
    )
    motivos_cierre: list[LumaConteoMotivoCierre]
    modalidades: list[LumaConteoModalidad]
    retencion: LumaRetencion
    puntos_de_fuga: LumaPuntosDeFuga


# ---------------------------------------------------------------------------
# GET /api/admin/luma/series
# ---------------------------------------------------------------------------


class LumaRespuestaAnteErrorDia(BaseModel):
    reintento_inmediato: int
    busca_ayuda: int
    inactividad_bloqueo: int
    sin_clasificar: int
    limite: str = LIMITE_RESPUESTA_ANTE_ERROR_SERIE


class LumaAyudaDia(BaseModel):
    voluntaria: int
    impuesta: int


class LumaSerieDia(BaseModel):
    dia: str
    independencia: float | None = Field(
        description="Aciertos independientes / total de resoluciones, en tanto por "
        "uno. None (no 0) si ese dia no hubo ninguna resolucion que medir."
    )
    limite_independencia: str = LIMITE_INDEPENDENCIA
    respuesta_ante_error: LumaRespuestaAnteErrorDia
    ayuda: LumaAyudaDia
    casillas_acreditadas: int = Field(description="Casillas CPA NUEVAS acreditadas ese dia (delta, no acumulado).")
    tiempo_activo_mediana_ms: float | None
    limite_tiempo_activo: str = LIMITE_TIEMPO_ACTIVO
    inactividad_idle_started: int
    limite_inactividad: str = LIMITE_INACTIVIDAD


class LumaSeriesSalida(BaseModel):
    generado: datetime
    dias: int
    serie: list[LumaSerieDia]


# ---------------------------------------------------------------------------
# GET /api/admin/luma/sesiones/{run_id}/historico
# ---------------------------------------------------------------------------


class LumaSesionHistorica(BaseModel):
    fecha: date
    eventos: int
    tiempo_activo_ms: int | None = Field(description=LIMITE_TIEMPO_ACTIVO)
    independencia: float | None
    casillas_acreditadas_acumuladas: int = Field(
        description="Total acumulado de casillas CPA acreditadas hasta el final de esta sesion (inclusive)."
    )
    fase_final: str | None
    motivo_final: str | None


class LumaProgresionTemporalEntrada(BaseModel):
    habilidad: str
    etapa: str
    fecha: datetime


class LumaBayesianoTemporalEntrada(BaseModel):
    habilidad: str
    fecha: datetime
    p: float | None
    n: int | None


class LumaHistoricoSalida(BaseModel):
    run_id: UUID
    sesiones: list[LumaSesionHistorica]
    progresion_temporal: list[LumaProgresionTemporalEntrada]
    bayesiano_temporal: list[LumaBayesianoTemporalEntrada]
