"""Analisis por item y evaluacion del algoritmo de adaptacion de LumaSprout.

Motivado por el propio usuario: "el core radica en los indicadores mas que en el
juego, porque el juego se puede perfeccionar en base a los indicadores". Los demas
modulos (luma_service.py, luma_dashboard.py) describen AL NINO; este describe AL
JUEGO: que item esta mal calibrado y si el algoritmo de adaptacion realmente ayuda.
Son las preguntas que permiten decidir que corregir en el juego mismo.

DECISION DE COSTO, distinta de luma_dashboard.py: panorama y series agregan con
SQL (GROUP BY, date_trunc) porque son vistas que se refrescan seguido sobre una
tabla que crece sin cota. /items y /adaptacion, en cambio, correlacionan eventos de
tipos MUY distintos (task_presented, attempt, decision_evaluated, hint_requested,
input_validation, adaptation, adaptation_decision...) que solo tienen sentido
juntos en el ORDEN en que ocurrieron dentro de una sesion (que item estaba activo
cuando paso cada cosa). Expresar eso en SQL puro exigiria funciones de ventana
encadenadas de una complejidad y riesgo de error muy altos para verificar sin una
base de datos real a mano. Se opto por traer los eventos reales (simulation=false)
UNA vez, ordenados por (sesion_id, secuencia), y procesarlos en Python en un solo
paso. Para un piloto de ~30 participantes (miles de eventos, no millones) esto es
razonable; si el estudio crece mucho, este es el primer lugar a revisar antes que
panorama/series (que ya estan en SQL).

ALGORITMO (una pasada por sesion, manteniendo "el item activo"):
- task_presented abre una "presentacion" para (skill, item.variantId): cierra la
  presentacion anterior si habia una abierta.
- attempt (identificado por su propio variantId, no por el item activo: el equipo
  confirmo que variantId tambien viaja en attempt) alimenta acierto_primer_intento,
  intentos_mediana y patrones_error.
- decision_evaluated con el mismo variantId que la presentacion activa la marca
  como resuelta (independiente o con ayuda).
- hint_requested/support_selected mientras hay presentacion activa cuentan como
  "pidio ayuda" para ESA presentacion.
- input_validation con reason='invalid_format' mientras hay presentacion activa
  cuenta como error de INTERFAZ para ese item, nunca como error matematico.
- Al cerrar una presentacion sin haberse marcado resuelta, cuenta como abandono.
- adaptation_decision (frontera de reto) se cruza por decisionId con
  decision_evaluated/decision_response, igual que en luma_service._decisiones_adaptacion,
  pero agregado por `reason` en vez de listado por partida.
- Los eventos "adaptation" con `rule` (dentro del reto) se atribuyen a la
  presentacion activa en ese momento; su resultado es el de esa presentacion.
- El andamiaje (effectiveSupport='concrete' en una decision, o scaffold_shown con
  reason='adaptive') marca la presentacion activa como "con andamiaje reciente":
  el SIGUIENTE attempt de esa presentacion se cuenta en el grupo "con andamiaje"
  al comparar tasas de acierto.
- independentProbe (de item_presentado.item) se guarda en la presentacion; al
  cerrarla, si estaba activo, alimenta oportunidades_independientes.
"""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import groupby
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.luma import LumaEvento, LumaSesion
from schemas.luma_items import (
    UMBRAL_MUESTRA_SUFICIENTE,
    LumaAdaptacionPorRazon,
    LumaAdaptacionPorRegla,
    LumaAdaptacionSalida,
    LumaEfectoAndamiaje,
    LumaItemAnalisis,
    LumaItemsSalida,
    LumaOportunidadesIndependientes,
    LumaResultadoConteo,
)
from services.luma_service import (
    TIPO_ATTEMPT,
    TIPO_DECISION_EVALUATED,
    TIPO_HINT_REQUESTED,
    TIPO_SUPPORT_SELECTED,
    TIPO_TASK_PRESENTED,
    _campo,
    _interior_de,
    _skill_y_stage_de_task_presented,
)

# NO se importa TIPO_DECISION_RESPONSE a proposito: decision_response no es un
# resultado (ver docstring de _procesar_decisiones_de_adaptacion) y este modulo
# nunca deberia iterar sobre el.

TIPO_ADAPTATION_DECISION = "adaptation_decision"
TIPO_ADAPTATION = "adaptation"
TIPO_INPUT_VALIDATION = "input_validation"
TIPO_SCAFFOLD_SHOWN = "scaffold_shown"

RAZON_INPUT_FORMATO_INVALIDO = "invalid_format"
RAZON_SCAFFOLD_ADAPTIVA = "adaptive"
SOPORTE_CONCRETO = "concrete"

RESULTADO_INDEPENDIENTE = "resuelto_independiente"
RESULTADO_CON_AYUDA = "resuelto_con_ayuda"
RESULTADO_NO_RESUELTO = "no_resuelto"


@dataclass
class _AcumuladorItem:
    skill: str | None = None
    stage: str | None = None
    presentaciones: int = 0
    intentos_attempt_number_uno: int = 0
    aciertos_primer_intento_sin_ayuda: int = 0
    intentos_por_episodio: list[int] = field(default_factory=list)
    pidio_ayuda: int = 0
    abandonos: int = 0
    patrones_error: Counter[str] = field(default_factory=Counter)
    errores_de_formato: int = 0


@dataclass
class _AcumuladorResultado:
    resuelto_independiente: int = 0
    resuelto_con_ayuda: int = 0
    no_resuelto: int = 0

    def sumar(self, resultado: str) -> None:
        if resultado == RESULTADO_INDEPENDIENTE:
            self.resuelto_independiente += 1
        elif resultado == RESULTADO_CON_AYUDA:
            self.resuelto_con_ayuda += 1
        else:
            self.no_resuelto += 1

    @property
    def total(self) -> int:
        return self.resuelto_independiente + self.resuelto_con_ayuda + self.no_resuelto


# Clave de agrupacion de un item: (habilidad, etapa, variantId), NUNCA variantId
# solo. Confirmado por el equipo: cada banco de items numera sus variantes por
# separado, asi que puede existir un "v1" en meaning/concrete y otro "v1"
# completamente distinto en add_diff/transfer. Agrupar solo por variantId
# mezclaria ejercicios sin relacion bajo una sola fila.
_ClaveItem = tuple[str | None, str | None, str]


@dataclass
class _ContextoAgregado:
    """Todo lo que acumula la pasada unica por sesion, para /items y /adaptacion a la vez."""

    items: dict[_ClaveItem, _AcumuladorItem] = field(default_factory=dict)
    por_razon_decision: dict[str, _AcumuladorResultado] = field(default_factory=dict)
    por_regla_mid_reto: dict[str, _AcumuladorResultado] = field(default_factory=dict)
    con_andamiaje_correctos: int = 0
    con_andamiaje_total: int = 0
    sin_andamiaje_correctos: int = 0
    sin_andamiaje_total: int = 0
    independientes_total: int = 0
    independientes_resueltas: int = 0

    def item(self, clave: _ClaveItem) -> _AcumuladorItem:
        return self.items.setdefault(clave, _AcumuladorItem())

    def resultado_decision(self, reason: str) -> _AcumuladorResultado:
        return self.por_razon_decision.setdefault(reason, _AcumuladorResultado())

    def resultado_regla(self, rule: str) -> _AcumuladorResultado:
        return self.por_regla_mid_reto.setdefault(rule, _AcumuladorResultado())


def _resultado_de_decision_evaluated(evaluado: LumaEvento) -> str:
    return RESULTADO_INDEPENDIENTE if _campo(evaluado, "independent") is True else RESULTADO_CON_AYUDA


def _procesar_decisiones_de_adaptacion(eventos_de_sesion: list[LumaEvento], contexto: _ContextoAgregado) -> None:
    """Igual que services.luma_service._decisiones_adaptacion, pero agregando por
    `reason` en toda la sesion en vez de devolver una lista por partida.

    REGLA CONFIRMADA por el equipo sobre decision_response: NO es un resultado.
    Se emite en CADA fallo intermedio (una misma decision puede tener varios), asi
    que nunca debe sumar a ninguna categoria. Solo decision_evaluated determina el
    resultado (independiente o con ayuda segun su campo `independent`); si no
    existe decision_evaluated para esa decisionId, es no_resuelto sin importar
    cuantos decision_response haya habido. Por eso esta funcion no itera siquiera
    sobre TIPO_DECISION_RESPONSE.
    """
    decisiones = [e for e in eventos_de_sesion if e.tipo == TIPO_ADAPTATION_DECISION]
    evaluados = {
        _campo(e, "decisionId"): e
        for e in eventos_de_sesion
        if e.tipo == TIPO_DECISION_EVALUATED and _campo(e, "decisionId")
    }

    for decision in decisiones:
        reason = _campo(decision, "reason")
        if not isinstance(reason, str):
            continue
        decision_id = _campo(decision, "decisionId")
        evaluado = evaluados.get(decision_id) if decision_id else None
        resultado = _resultado_de_decision_evaluated(evaluado) if evaluado is not None else RESULTADO_NO_RESUELTO
        contexto.resultado_decision(reason).sumar(resultado)


def _procesar_items_y_mid_reto(eventos_de_sesion: list[LumaEvento], contexto: _ContextoAgregado) -> None:
    item_activo: dict[str, Any] | None = None
    episodio_abierto: dict[_ClaveItem, int] = {}

    def _cerrar_episodio(clave: _ClaveItem) -> None:
        maximo = episodio_abierto.pop(clave, None)
        if maximo is not None:
            contexto.item(clave).intentos_por_episodio.append(maximo)

    def _cerrar_presentacion() -> None:
        nonlocal item_activo
        if item_activo is None:
            return
        clave = item_activo["clave"]
        acumulador = contexto.item(clave)
        acumulador.skill = item_activo["skill"]
        acumulador.stage = item_activo["stage"]
        acumulador.presentaciones += 1
        if item_activo["pidio_ayuda"]:
            acumulador.pidio_ayuda += 1

        resultado = item_activo["resultado"]
        if resultado is None:
            acumulador.abandonos += 1
        if item_activo["independent_probe"]:
            contexto.independientes_total += 1
            if resultado == RESULTADO_INDEPENDIENTE:
                contexto.independientes_resueltas += 1
        for rule in item_activo["reglas_disparadas"]:
            contexto.resultado_regla(rule).sumar(resultado or RESULTADO_NO_RESUELTO)

        _cerrar_episodio(clave)
        item_activo = None

    for evento in eventos_de_sesion:
        if evento.tipo == TIPO_TASK_PRESENTED:
            _cerrar_presentacion()
            skill, stage = _skill_y_stage_de_task_presented(evento)
            interior = _interior_de(evento)
            item = interior.get("item") if isinstance(interior.get("item"), dict) else {}
            variant_id = item.get("variantId")
            if isinstance(variant_id, str):
                item_activo = {
                    "clave": (skill, stage, variant_id),
                    "variant_id": variant_id,
                    "skill": skill,
                    "stage": stage,
                    "pidio_ayuda": False,
                    "resultado": None,
                    "independent_probe": item.get("independentProbe") is True,
                    "reglas_disparadas": [],
                    "andamiaje_reciente": False,
                }
            else:
                item_activo = None

        elif evento.tipo == TIPO_ATTEMPT:
            # attempt no trae skill/stage, solo variantId: se atribuye a la
            # presentacion ACTIVA (que ya sabe su habilidad+etapa), verificando
            # que el variantId coincide. Nunca se abre un acumulador nuevo
            # keyeado solo por variantId: eso es justo lo que mezclaria variantes
            # iguales de habilidades/etapas distintas.
            variant_id = _campo(evento, "variantId")
            numero = _campo(evento, "attemptNumber")
            correcto = _campo(evento, "correct")
            if (
                item_activo is not None
                and isinstance(variant_id, str)
                and variant_id == item_activo["variant_id"]
                and isinstance(numero, int)
            ):
                clave = item_activo["clave"]
                acumulador = contexto.item(clave)
                if numero == 1:
                    if clave in episodio_abierto:
                        _cerrar_episodio(clave)
                    acumulador.intentos_attempt_number_uno += 1
                    if correcto is True and not bool(_campo(evento, "assisted")):
                        acumulador.aciertos_primer_intento_sin_ayuda += 1
                episodio_abierto[clave] = max(episodio_abierto.get(clave, 0), numero)

                patron_error = _campo(evento, "errorPattern")
                if correcto is False and isinstance(patron_error, str):
                    acumulador.patrones_error[patron_error] += 1

            if item_activo is not None and isinstance(correcto, bool):
                if item_activo["andamiaje_reciente"]:
                    contexto.con_andamiaje_total += 1
                    contexto.con_andamiaje_correctos += 1 if correcto else 0
                    item_activo["andamiaje_reciente"] = False
                else:
                    contexto.sin_andamiaje_total += 1
                    contexto.sin_andamiaje_correctos += 1 if correcto else 0

        elif evento.tipo == TIPO_DECISION_EVALUATED:
            variant_id = _campo(evento, "variantId")
            if item_activo is not None and variant_id == item_activo["variant_id"]:
                item_activo["resultado"] = _resultado_de_decision_evaluated(evento)
                if _campo(evento, "effectiveSupport") == SOPORTE_CONCRETO:
                    item_activo["andamiaje_reciente"] = True

        elif evento.tipo in (TIPO_HINT_REQUESTED, TIPO_SUPPORT_SELECTED):
            if item_activo is not None:
                item_activo["pidio_ayuda"] = True

        elif evento.tipo == TIPO_INPUT_VALIDATION:
            if item_activo is not None and _campo(evento, "reason") == RAZON_INPUT_FORMATO_INVALIDO:
                contexto.item(item_activo["clave"]).errores_de_formato += 1

        elif evento.tipo == TIPO_SCAFFOLD_SHOWN:
            if item_activo is not None and _campo(evento, "reason") == RAZON_SCAFFOLD_ADAPTIVA:
                item_activo["andamiaje_reciente"] = True

        elif evento.tipo == TIPO_ADAPTATION_DECISION:
            if item_activo is not None and _campo(evento, "effectiveSupport") == SOPORTE_CONCRETO:
                item_activo["andamiaje_reciente"] = True

        elif evento.tipo == TIPO_ADAPTATION:
            regla = _campo(evento, "rule")
            if item_activo is not None and isinstance(regla, str):
                item_activo["reglas_disparadas"].append(regla)

    _cerrar_presentacion()
    for clave in list(episodio_abierto):
        _cerrar_episodio(clave)


async def _eventos_reales_ordenados(db: AsyncSession) -> list[LumaEvento]:
    """Trae TODOS los eventos reales (simulation=false), ordenados por sesion y
    secuencia. Ver el docstring del modulo para por que esto se hace en Python en
    vez de en SQL, y sus limites de escala."""
    resultado = await db.execute(
        select(LumaEvento)
        .join(LumaSesion, LumaSesion.id == LumaEvento.sesion_id)
        .where(LumaSesion.simulation.is_(False))
        .order_by(LumaEvento.sesion_id, LumaEvento.secuencia)
    )
    return list(resultado.scalars().all())


def _construir_contexto(eventos: list[LumaEvento]) -> _ContextoAgregado:
    contexto = _ContextoAgregado()
    for _sesion_id, grupo in groupby(eventos, key=lambda e: e.sesion_id):
        eventos_de_sesion = list(grupo)
        _procesar_items_y_mid_reto(eventos_de_sesion, contexto)
        _procesar_decisiones_de_adaptacion(eventos_de_sesion, contexto)
    return contexto


def _mediana(valores: list[int]) -> float | None:
    return statistics.median(valores) if valores else None


def _item_analisis_de(variant_id: str, acumulador: _AcumuladorItem) -> LumaItemAnalisis:
    tasa_acierto = (
        acumulador.aciertos_primer_intento_sin_ayuda / acumulador.intentos_attempt_number_uno
        if acumulador.intentos_attempt_number_uno > 0
        else None
    )
    proporcion_ayuda = (acumulador.pidio_ayuda / acumulador.presentaciones) if acumulador.presentaciones > 0 else None

    return LumaItemAnalisis(
        variant_id=variant_id,
        habilidad=acumulador.skill,
        etapa=acumulador.stage,
        presentaciones=acumulador.presentaciones,
        muestra_suficiente=acumulador.presentaciones >= UMBRAL_MUESTRA_SUFICIENTE,
        acierto_primer_intento_sin_ayuda=tasa_acierto,
        intentos_mediana=_mediana(acumulador.intentos_por_episodio),
        pidio_ayuda=proporcion_ayuda,
        abandonos=acumulador.abandonos,
        patrones_error=dict(acumulador.patrones_error),
        errores_de_formato=acumulador.errores_de_formato,
    )


def _resultado_conteo_de(acumulador: _AcumuladorResultado) -> LumaResultadoConteo:
    return LumaResultadoConteo(
        resuelto_independiente=acumulador.resuelto_independiente,
        resuelto_con_ayuda=acumulador.resuelto_con_ayuda,
        no_resuelto=acumulador.no_resuelto,
        muestra_suficiente=acumulador.total >= UMBRAL_MUESTRA_SUFICIENTE,
    )


async def obtener_items(db: AsyncSession) -> LumaItemsSalida:
    eventos = await _eventos_reales_ordenados(db)
    contexto = _construir_contexto(eventos)
    items = [
        _item_analisis_de(clave[2], acumulador)
        for clave, acumulador in contexto.items.items()
    ]
    return LumaItemsSalida(generado=datetime.now(UTC), items=items)


async def obtener_adaptacion(db: AsyncSession) -> LumaAdaptacionSalida:
    eventos = await _eventos_reales_ordenados(db)
    contexto = _construir_contexto(eventos)

    tasa_con = (
        contexto.con_andamiaje_correctos / contexto.con_andamiaje_total if contexto.con_andamiaje_total > 0 else None
    )
    tasa_sin = (
        contexto.sin_andamiaje_correctos / contexto.sin_andamiaje_total if contexto.sin_andamiaje_total > 0 else None
    )

    return LumaAdaptacionSalida(
        generado=datetime.now(UTC),
        por_razon_decision=[
            LumaAdaptacionPorRazon(razon=reason, veces=acumulador.total, resultado=_resultado_conteo_de(acumulador))
            for reason, acumulador in contexto.por_razon_decision.items()
        ],
        por_regla_mid_reto=[
            LumaAdaptacionPorRegla(regla=rule, veces=acumulador.total, resultado=_resultado_conteo_de(acumulador))
            for rule, acumulador in contexto.por_regla_mid_reto.items()
        ],
        efecto_del_andamiaje=LumaEfectoAndamiaje(
            tasa_acierto_con_andamiaje=tasa_con,
            presentaciones_con_andamiaje=contexto.con_andamiaje_total,
            tasa_acierto_sin_andamiaje=tasa_sin,
            presentaciones_sin_andamiaje=contexto.sin_andamiaje_total,
            muestra_suficiente=contexto.con_andamiaje_total >= UMBRAL_MUESTRA_SUFICIENTE
            and contexto.sin_andamiaje_total >= UMBRAL_MUESTRA_SUFICIENTE,
        ),
        oportunidades_independientes=LumaOportunidadesIndependientes(
            total=contexto.independientes_total,
            resueltas_independientemente=contexto.independientes_resueltas,
            muestra_suficiente=contexto.independientes_total >= UMBRAL_MUESTRA_SUFICIENTE,
        ),
    )
