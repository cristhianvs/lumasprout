"""Tests de services/luma_items.py (/items y /adaptacion).

La base de datos se mockea siempre (la unica consulta se sustituye por una lista de
LumaEvento ya construida en memoria): estos tests no abren conexion real a Postgres
y por lo tanto no verifican el costo real de traer todos los eventos, solo la
logica de la maquina de estados que correlaciona task_presented/attempt/
decision_evaluated/hint_requested/input_validation/adaptation dentro de una sesion.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from models.luma import LumaEvento
from services.luma_items import (
    RESULTADO_CON_AYUDA,
    RESULTADO_INDEPENDIENTE,
    RESULTADO_NO_RESUELTO,
    _construir_contexto,
    _procesar_decisiones_de_adaptacion,
    obtener_adaptacion,
    obtener_items,
)

SESION_ID_POR_DEFECTO = uuid4()


def _evento(secuencia: int, tipo: str, data: dict, sesion_id=None) -> LumaEvento:
    # Todos los eventos de un mismo test comparten sesion_id por defecto: la
    # maquina de estados de luma_items.py opera POR SESION (via groupby), asi que
    # sesion_id aleatorios distintos por evento la romperian silenciosamente.
    return LumaEvento(
        id=uuid4(),
        sesion_id=sesion_id or SESION_ID_POR_DEFECTO,
        evento_id=f"s:{secuencia}",
        session_carga=uuid4(),
        secuencia=secuencia,
        tipo=tipo,
        at_cliente=datetime(2026, 9, 10, 10, 0, secuencia % 60, tzinfo=UTC),
        recibido_at=datetime.now(UTC),
        data=data,
    )


def _task_presented(secuencia: int, skill: str, stage: str, variant_id: str, **item_extra) -> LumaEvento:
    return _evento(secuencia, "task_presented", {"skill": skill, "item": {"stage": stage, "variantId": variant_id, **item_extra}})


def _attempt(secuencia: int, variant_id: str, attempt_number: int, correct: bool, **extra) -> LumaEvento:
    return _evento(secuencia, "attempt", {"variantId": variant_id, "attemptNumber": attempt_number, "correct": correct, **extra})


def _decision_evaluated(secuencia: int, variant_id: str, independent: bool, **extra) -> LumaEvento:
    return _evento(secuencia, "decision_evaluated", {"variantId": variant_id, "independent": independent, "outcome": "solved", **extra})


# La clave de agrupacion de un item es (habilidad, etapa, variantId), no solo
# variantId (ver _ClaveItem en services/luma_items.py): confirmado por el equipo,
# distintos bancos numeran sus variantes por separado.
CLAVE_V1 = ("meaning", "concrete", "v1")


class TestPresentacionesYAbandonos:
    def test_presentacion_resuelta_no_cuenta_como_abandono(self):
        variant_id = "v1"
        eventos = [
            _task_presented(1, "meaning", "concrete", variant_id),
            _attempt(2, variant_id, 1, True),
            _decision_evaluated(3, variant_id, True),
        ]
        contexto = _construir_contexto(eventos)

        item = contexto.items[CLAVE_V1]
        assert item.presentaciones == 1
        assert item.abandonos == 0
        assert item.skill == "meaning"
        assert item.stage == "concrete"

    def test_presentacion_sin_decision_evaluated_es_abandono(self):
        variant_id = "v1"
        eventos = [
            _task_presented(1, "meaning", "concrete", variant_id),
            _attempt(2, variant_id, 1, False),
            # La sesion se mueve a otro item sin resolver el primero.
            _task_presented(3, "meaning", "pictorial", "v2"),
        ]
        contexto = _construir_contexto(eventos)

        assert contexto.items[CLAVE_V1].presentaciones == 1
        assert contexto.items[CLAVE_V1].abandonos == 1

    def test_ultima_presentacion_de_la_sesion_se_cierra_al_final(self):
        """Si la sesion termina sin otro task_presented ni decision_evaluated, la
        ultima presentacion abierta igual debe cerrarse (y contar como abandono)."""
        variant_id = "v1"
        eventos = [_task_presented(1, "meaning", "concrete", variant_id), _attempt(2, variant_id, 1, False)]
        contexto = _construir_contexto(eventos)

        assert contexto.items[CLAVE_V1].presentaciones == 1
        assert contexto.items[CLAVE_V1].abandonos == 1

    def test_mismo_variant_id_en_habilidad_y_etapa_distintas_no_se_mezcla(self):
        """El bug que el equipo pidio evitar explicitamente: un mismo variantId
        ('v1') usado en dos combinaciones habilidad+etapa distintas debe quedar en
        DOS filas separadas, no mezclarse en una sola."""
        eventos = [
            _task_presented(1, "meaning", "concrete", "v1"),
            _attempt(2, "v1", 1, True),
            _decision_evaluated(3, "v1", True),
            _task_presented(4, "add_diff", "transfer", "v1"),
            _attempt(5, "v1", 1, False),
            _decision_evaluated(6, "v1", False),
        ]
        contexto = _construir_contexto(eventos)

        assert len(contexto.items) == 2
        primero = contexto.items[("meaning", "concrete", "v1")]
        segundo = contexto.items[("add_diff", "transfer", "v1")]
        assert primero.aciertos_primer_intento_sin_ayuda == 1
        assert segundo.aciertos_primer_intento_sin_ayuda == 0


class TestAciertoEIntentosMediana:
    def test_acierto_primer_intento_exige_correct_y_no_asistido(self):
        variant_id = "v1"
        eventos = [
            _task_presented(1, "meaning", "concrete", variant_id),
            _attempt(2, variant_id, 1, True, assisted=False),
            _decision_evaluated(3, variant_id, True),
            _task_presented(4, "meaning", "concrete", variant_id),
            _attempt(5, variant_id, 1, True, assisted=True),  # asistido: no cuenta
            _decision_evaluated(6, variant_id, False),
        ]
        contexto = _construir_contexto(eventos)

        item = contexto.items[CLAVE_V1]
        assert item.intentos_attempt_number_uno == 2
        assert item.aciertos_primer_intento_sin_ayuda == 1

    def test_intentos_mediana_usa_el_maximo_attempt_number_por_episodio(self):
        variant_id = "v1"
        eventos = [
            _task_presented(1, "meaning", "concrete", variant_id),
            _attempt(2, variant_id, 1, False),
            _attempt(3, variant_id, 2, False),
            _attempt(4, variant_id, 3, True),
            _decision_evaluated(5, variant_id, False),
        ]
        contexto = _construir_contexto(eventos)

        assert contexto.items[CLAVE_V1].intentos_por_episodio == [3]


class TestAyudaYErroresDeFormato:
    def test_hint_requested_mientras_el_item_esta_activo_cuenta_como_ayuda(self):
        variant_id = "v1"
        eventos = [
            _task_presented(1, "meaning", "concrete", variant_id),
            _evento(2, "hint_requested", {}),
            _attempt(3, variant_id, 1, True),
            _decision_evaluated(4, variant_id, True),
        ]
        contexto = _construir_contexto(eventos)

        assert contexto.items[CLAVE_V1].pidio_ayuda == 1

    def test_input_validation_invalid_format_no_es_error_matematico(self):
        variant_id = "v1"
        eventos = [
            _task_presented(1, "meaning", "concrete", variant_id),
            _evento(2, "input_validation", {"reason": "invalid_format"}),
            _evento(3, "input_validation", {"reason": "otro_motivo"}),
            _attempt(4, variant_id, 1, True),
            _decision_evaluated(5, variant_id, True),
        ]
        contexto = _construir_contexto(eventos)

        assert contexto.items[CLAVE_V1].errores_de_formato == 1


class TestPatronesError:
    def test_solo_los_intentos_fallidos_aportan_patron_de_error(self):
        variant_id = "v1"
        eventos = [
            _task_presented(1, "meaning", "concrete", variant_id),
            _attempt(2, variant_id, 1, False, errorPattern="target_denominator"),
            _attempt(3, variant_id, 2, True, errorPattern="target_denominator"),  # correcto: no cuenta
            _decision_evaluated(4, variant_id, False),
        ]
        contexto = _construir_contexto(eventos)

        assert contexto.items[CLAVE_V1].patrones_error == {"target_denominator": 1}


class TestDecisionesDeAdaptacionPorRazon:
    def test_agrupa_por_reason_y_clasifica_el_resultado(self):
        eventos = [
            _evento(1, "adaptation_decision", {"decisionId": "d1", "reason": "recent_errors_and_help"}),
            _evento(2, "decision_evaluated", {"decisionId": "d1", "independent": True}),
            _evento(3, "adaptation_decision", {"decisionId": "d2", "reason": "recent_errors_and_help"}),
            _evento(4, "decision_evaluated", {"decisionId": "d2", "independent": False}),
            _evento(5, "adaptation_decision", {"decisionId": "d3", "reason": "standard_pace"}),
            # d3 nunca se resuelve.
        ]
        contexto = _construir_contexto(eventos)

        recientes = contexto.por_razon_decision["recent_errors_and_help"]
        assert recientes.resuelto_independiente == 1
        assert recientes.resuelto_con_ayuda == 1

        estandar = contexto.por_razon_decision["standard_pace"]
        assert estandar.no_resuelto == 1

    def test_multiples_decision_response_no_inflan_no_resuelto(self):
        """Regla confirmada por el equipo: decision_response se emite en CADA
        fallo intermedio (una misma decision puede tener varios) y NUNCA es un
        resultado. Si al final SI hay decision_evaluated, cuenta una unica vez
        segun su independent, sin importar cuantos decision_response hubo antes."""
        eventos = [
            _evento(1, "adaptation_decision", {"decisionId": "d1", "reason": "recent_errors_and_help"}),
            _evento(2, "decision_response", {"decisionId": "d1"}),
            _evento(3, "decision_response", {"decisionId": "d1"}),
            _evento(4, "decision_response", {"decisionId": "d1"}),
            _evento(5, "decision_evaluated", {"decisionId": "d1", "independent": False}),
        ]
        contexto = _construir_contexto(eventos)

        recientes = contexto.por_razon_decision["recent_errors_and_help"]
        assert recientes.resuelto_con_ayuda == 1
        assert recientes.no_resuelto == 0
        assert recientes.resuelto_independiente == 0

    def test_decision_response_sin_decision_evaluated_es_no_resuelto_una_sola_vez(self):
        eventos = [
            _evento(1, "adaptation_decision", {"decisionId": "d1", "reason": "standard_pace"}),
            _evento(2, "decision_response", {"decisionId": "d1"}),
            _evento(3, "decision_response", {"decisionId": "d1"}),
        ]
        contexto = _construir_contexto(eventos)

        estandar = contexto.por_razon_decision["standard_pace"]
        assert estandar.no_resuelto == 1
        assert estandar.total == 1

    def test_procesar_decisiones_es_llamable_directamente(self):
        from services.luma_items import _ContextoAgregado

        contexto = _ContextoAgregado()
        eventos = [
            _evento(1, "adaptation_decision", {"decisionId": "d1", "reason": "standard_pace"}),
            _evento(2, "decision_evaluated", {"decisionId": "d1", "independent": True}),
        ]
        _procesar_decisiones_de_adaptacion(eventos, contexto)

        assert contexto.por_razon_decision["standard_pace"].resuelto_independiente == 1


class TestReglasMidReto:
    def test_regla_se_atribuye_al_resultado_de_la_presentacion_activa(self):
        variant_id = "v1"
        eventos = [
            _task_presented(1, "meaning", "concrete", variant_id),
            _evento(2, "adaptation", {"rule": "three_failures"}),
            _attempt(3, variant_id, 1, True),
            _decision_evaluated(4, variant_id, True),
        ]
        contexto = _construir_contexto(eventos)

        assert contexto.por_regla_mid_reto["three_failures"].resuelto_independiente == 1

    def test_regla_sin_resolucion_posterior_es_no_resuelto(self):
        variant_id = "v1"
        eventos = [
            _task_presented(1, "meaning", "concrete", variant_id),
            _evento(2, "adaptation", {"rule": "repeated_help_requests"}),
            # La sesion termina sin resolver.
        ]
        contexto = _construir_contexto(eventos)

        assert contexto.por_regla_mid_reto["repeated_help_requests"].no_resuelto == 1


class TestEfectoDelAndamiaje:
    def test_attempt_posterior_a_effective_support_concrete_cuenta_como_con_andamiaje(self):
        variant_id = "v1"
        eventos = [
            _task_presented(1, "meaning", "concrete", variant_id),
            _attempt(2, variant_id, 1, False),
            _decision_evaluated(3, variant_id, False, effectiveSupport="concrete"),
            _attempt(4, variant_id, 2, True),  # posterior al andamiaje
        ]
        contexto = _construir_contexto(eventos)

        assert contexto.con_andamiaje_total == 1
        assert contexto.con_andamiaje_correctos == 1
        # El primer intento (antes del andamiaje) va al grupo sin andamiaje.
        assert contexto.sin_andamiaje_total == 1

    def test_scaffold_shown_adaptive_tambien_marca_andamiaje(self):
        variant_id = "v1"
        eventos = [
            _task_presented(1, "meaning", "concrete", variant_id),
            _attempt(2, variant_id, 1, False),
            _evento(3, "scaffold_shown", {"reason": "adaptive"}),
            _attempt(4, variant_id, 2, False),
        ]
        contexto = _construir_contexto(eventos)

        assert contexto.con_andamiaje_total == 1
        assert contexto.con_andamiaje_correctos == 0


class TestOportunidadesIndependientes:
    def test_independent_probe_activo_cuenta_al_cerrar_la_presentacion(self):
        variant_id = "v1"
        eventos = [
            _task_presented(1, "meaning", "concrete", variant_id, independentProbe=True),
            _attempt(2, variant_id, 1, True),
            _decision_evaluated(3, variant_id, True),
        ]
        contexto = _construir_contexto(eventos)

        assert contexto.independientes_total == 1
        assert contexto.independientes_resueltas == 1

    def test_independent_probe_falso_no_cuenta(self):
        variant_id = "v1"
        eventos = [
            _task_presented(1, "meaning", "concrete", variant_id, independentProbe=False),
            _attempt(2, variant_id, 1, True),
            _decision_evaluated(3, variant_id, True),
        ]
        contexto = _construir_contexto(eventos)

        assert contexto.independientes_total == 0


class TestObtenerItemsYAdaptacion:
    @pytest.mark.asyncio
    async def test_obtener_items_delega_en_la_consulta_y_arma_la_respuesta(self):
        variant_id = "v1"
        eventos = [
            _task_presented(1, "meaning", "concrete", variant_id),
            _attempt(2, variant_id, 1, True),
            _decision_evaluated(3, variant_id, True),
        ]
        db = AsyncMock()
        resultado = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=eventos))))
        db.execute = AsyncMock(return_value=resultado)

        salida = await obtener_items(db)

        assert salida.umbral_muestra_suficiente == 10
        assert len(salida.items) == 1
        assert salida.items[0].variant_id == variant_id
        assert salida.items[0].muestra_suficiente is False  # 1 presentacion < umbral

    @pytest.mark.asyncio
    async def test_obtener_adaptacion_delega_en_la_consulta_y_arma_la_respuesta(self):
        db = AsyncMock()
        resultado = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
        db.execute = AsyncMock(return_value=resultado)

        salida = await obtener_adaptacion(db)

        assert salida.por_razon_decision == []
        assert salida.efecto_del_andamiaje.muestra_suficiente is False
        assert salida.oportunidades_independientes.total == 0


class TestConstantesDeResultado:
    def test_las_tres_categorias_son_distintas(self):
        assert len({RESULTADO_INDEPENDIENTE, RESULTADO_CON_AYUDA, RESULTADO_NO_RESUELTO}) == 3
