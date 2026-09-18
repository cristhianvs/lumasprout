"""Schemas del analisis por item y de la evaluacion del algoritmo de adaptacion.

Cita del usuario que motiva este archivo: "el core radica en los indicadores mas
que en el juego, porque el juego se puede perfeccionar en base a los indicadores".
Los schemas de luma.py y luma_dashboard.py describen AL NINO (que hizo, como va);
estos describen AL JUEGO (que item esta mal calibrado, si el algoritmo de
adaptacion realmente ayuda): son los que permiten decidir que corregir en el
juego mismo, no en el nino.
"""

from datetime import datetime

from pydantic import BaseModel, Field

UMBRAL_MUESTRA_SUFICIENTE = 10

LIMITE_ITEMS = (
    "Describe el COMPORTAMIENTO OBSERVADO con este item (cuantos participantes, "
    "que tan seguido acertaron, pidieron ayuda o lo abandonaron), no su calidad "
    "pedagogica: un item dificil no es necesariamente un item malo. Con pocas "
    "presentaciones, una tasa no significa nada; ver 'muestra_suficiente'."
)
LIMITE_MUESTRA_SUFICIENTE = (
    f"muestra_suficiente exige al menos {UMBRAL_MUESTRA_SUFICIENTE} presentaciones. "
    "Con menos, el panel debe atenuar visualmente esta fila en vez de presentarla "
    "con la misma confianza que el resto."
)
LIMITE_ADAPTACION = (
    "Evalua si las decisiones del ALGORITMO de adaptacion tuvieron el efecto "
    "esperado, no el desempeno del nino. Con pocas ocurrencias de una regla o "
    "razon, la comparacion no es confiable; ver 'muestra_suficiente' en cada fila."
)
LIMITE_INPUT_VALIDATION = (
    "Un input_validation alto NO es un problema de matematicas: es un problema de "
    "INTERFAZ. El nino puede saber la respuesta y no conseguir introducirla. No "
    "sumar este numero a las metricas de dificultad matematica del item."
)
LIMITE_EFECTO_ANDAMIAJE = (
    "Compara el acierto del intento siguiente a un apoyo concreto "
    "(effectiveSupport='concrete' o scaffold_shown con reason='adaptive') contra "
    "cuando no hubo andamiaje. Si no hay diferencia o es peor, el andamiaje esta "
    "interrumpiendo en vez de ayudar."
)


# ---------------------------------------------------------------------------
# GET /api/admin/luma/items
# ---------------------------------------------------------------------------


class LumaItemAnalisis(BaseModel):
    variant_id: str
    habilidad: str | None
    etapa: str | None

    presentaciones: int = Field(description="Cuantas veces se mostro este item, agregando todos los participantes.")
    muestra_suficiente: bool = Field(description=LIMITE_MUESTRA_SUFICIENTE)

    acierto_primer_intento_sin_ayuda: float | None = Field(
        description="OJO al denominador: NO es sobre `presentaciones`. Es "
        "aciertos-en-primer-intento-sin-ayuda / intentos-con-attemptNumber==1, es "
        "decir, sobre los episodios de resolucion REALMENTE INTENTADOS (una "
        "presentacion abandonada sin ningun intento no cuenta ni arriba ni abajo de "
        "esta fraccion; para eso esta `abandonos`, aparte). Es la dificultad "
        "empirica del item. None si nunca se intento."
    )
    intentos_mediana: float | None = Field(
        description="Mediana de cuantos intentos hicieron falta para resolver el item "
        "(maximo attemptNumber alcanzado por episodio de resolucion). None si nunca se "
        "completo un episodio."
    )
    pidio_ayuda: float | None = Field(
        description="Proporcion de presentaciones en las que se piso hint_requested o "
        "support_selected mientras el item estaba activo."
    )
    abandonos: int = Field(
        description="Presentaciones de este item que no terminaron en un decision_evaluated: "
        "la sesion se movio a otro item o termino sin resolverlo."
    )
    patrones_error: dict[str, int] = Field(
        description="Distribucion de attempt.data.errorPattern entre los intentos "
        "fallidos de este item."
    )
    errores_de_formato: int = Field(description=f"input_validation con reason='invalid_format' mientras este item estaba activo. {LIMITE_INPUT_VALIDATION}")

    limite: str = LIMITE_ITEMS


class LumaItemsSalida(BaseModel):
    generado: datetime
    umbral_muestra_suficiente: int = UMBRAL_MUESTRA_SUFICIENTE
    items: list[LumaItemAnalisis]


# ---------------------------------------------------------------------------
# GET /api/admin/luma/adaptacion
# ---------------------------------------------------------------------------


class LumaResultadoConteo(BaseModel):
    resuelto_independiente: int
    resuelto_con_ayuda: int
    no_resuelto: int
    muestra_suficiente: bool


class LumaAdaptacionPorRazon(BaseModel):
    razon: str
    veces: int
    resultado: LumaResultadoConteo


class LumaAdaptacionPorRegla(BaseModel):
    regla: str
    veces: int
    resultado: LumaResultadoConteo


class LumaEfectoAndamiaje(BaseModel):
    tasa_acierto_con_andamiaje: float | None
    presentaciones_con_andamiaje: int
    tasa_acierto_sin_andamiaje: float | None
    presentaciones_sin_andamiaje: int
    muestra_suficiente: bool
    limite: str = LIMITE_EFECTO_ANDAMIAJE


class LumaOportunidadesIndependientes(BaseModel):
    total: int = Field(description="Presentaciones con item.independentProbe=true.")
    resueltas_independientemente: int
    muestra_suficiente: bool


class LumaAdaptacionSalida(BaseModel):
    generado: datetime
    umbral_muestra_suficiente: int = UMBRAL_MUESTRA_SUFICIENTE
    por_razon_decision: list[LumaAdaptacionPorRazon]
    por_regla_mid_reto: list[LumaAdaptacionPorRegla]
    efecto_del_andamiaje: LumaEfectoAndamiaje
    oportunidades_independientes: LumaOportunidadesIndependientes
    limite: str = LIMITE_ADAPTACION
