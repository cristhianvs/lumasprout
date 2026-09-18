"""Tests unitarios de services/luma_service.py.

La base de datos SIEMPRE se mockea (AsyncMock): estos tests no abren conexion real a
Postgres. Lo que se verifica es la logica que le corresponde a este servicio: el
token derivado por HMAC, el conteo de guardados/duplicados a partir de lo que
"devolveria" un INSERT ... ON CONFLICT DO NOTHING (simulado via el valor de retorno
mockeado, no por una restriccion unica real de Postgres), el rechazo de un evento
puntual sin tumbar el lote, y la agregacion del resumen a partir de una lista de
LumaEvento ya construida en memoria.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from models.luma import LumaEvento, LumaSesion
from schemas.luma import LumaSesionEntrada
from services.luma_service import (
    CANTIDAD_CASILLAS_CPA,
    CATALOGO_HABILIDADES,
    _ultimo_evento_de,
    _validar_evento,
    abrir_o_reanudar_sesion,
    calcular_token,
    construir_progresion,
    construir_resumen,
    ingerir_eventos,
    token_valido_para,
)

ETAPAS_CPA_TEST = ("concrete", "pictorial", "abstract", "transfer")


def _evento_crudo(session_id, indice: int, tipo: str = "attempt", **extra) -> dict:
    return {
        "id": f"{session_id}:{indice}",
        "type": tipo,
        "at": "2026-09-17T10:00:00Z",
        "session": str(session_id),
        **extra,
    }


def _evento_modelo(secuencia: int, tipo: str, data: dict, *, legacy: bool = False, **overrides) -> LumaEvento:
    """Construye un LumaEvento de prueba. `data` representa el CONTENIDO REAL de
    la columna `data` tal como la guarda la ingesta ya corregida (bug hallado por
    el equipo: antes se guardaba el envoltorio COMPLETO, no solo su sub-objeto
    `data`).

    Por conveniencia, si `data` viene escrito como {"data": {...}} (un solo nivel,
    la forma en que se escribian estas pruebas antes de conocerse el bug) se
    desenvuelve automaticamente una vez, asi los fixtures existentes en este
    archivo representan la fila CORRECTA sin reescribir cada literal. Pasa
    `legacy=True` para los pocos tests que deliberadamente quieren probar la RED
    TRANSITORIA de _campo/_interior_de con una fila anterior al fix (sin
    desenvolver)."""
    if not legacy and set(data.keys()) == {"data"} and isinstance(data["data"], dict):
        data = data["data"]
    base = LumaEvento(
        id=uuid4(),
        sesion_id=uuid4(),
        evento_id=f"s:{secuencia}",
        session_carga=uuid4(),
        secuencia=secuencia,
        tipo=tipo,
        at_cliente=datetime(2026, 9, 17, 10, 0, secuencia % 60, tzinfo=UTC),
        recibido_at=datetime.now(UTC),
        phase=overrides.get("phase"),
        scene=overrides.get("scene"),
        task=overrides.get("task"),
        experience=overrides.get("experience"),
        play_ms=overrides.get("play_ms"),
        math_ms=overrides.get("math_ms"),
        data=data,
    )
    return base


class TestToken:
    def test_token_es_determinista_para_el_mismo_run_id(self):
        run_id = uuid4()
        assert calcular_token(run_id) == calcular_token(run_id)

    def test_tokens_de_run_ids_distintos_son_distintos(self):
        assert calcular_token(uuid4()) != calcular_token(uuid4())

    def test_token_valido_para_su_propio_run_id(self):
        run_id = uuid4()
        assert token_valido_para(run_id, calcular_token(run_id)) is True

    def test_token_de_una_partida_es_rechazado_para_otra(self):
        run_id_a = uuid4()
        run_id_b = uuid4()
        token_de_a = calcular_token(run_id_a)

        assert token_valido_para(run_id_b, token_de_a) is False

    def test_token_vacio_o_none_es_rechazado(self):
        run_id = uuid4()
        assert token_valido_para(run_id, None) is False
        assert token_valido_para(run_id, "") is False


class TestUltimoEventoDe:
    """POST /sesion y POST /eventos comparten esta unica funcion a proposito
    (pedido explicito del equipo): asi nunca pueden divergir en su definicion de
    "el ultimo evento". Sale de UNA sola fila (secuencia + evento_id juntos, no
    dos consultas separadas), asi que ultimo_indice y ultimo_evento_id son
    coherentes entre si por construccion."""

    @pytest.mark.asyncio
    async def test_partida_sin_eventos_devuelve_menos_uno_y_none(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(first=MagicMock(return_value=None)))

        ultimo_indice, ultimo_evento_id = await _ultimo_evento_de(mock_db, uuid4())

        assert ultimo_indice == -1
        assert ultimo_evento_id is None

    @pytest.mark.asyncio
    async def test_devuelve_secuencia_y_evento_id_de_la_misma_fila(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(first=MagicMock(return_value=SimpleNamespace(secuencia=12, evento_id="s:12")))
        )

        ultimo_indice, ultimo_evento_id = await _ultimo_evento_de(mock_db, uuid4())

        assert ultimo_indice == 12
        assert ultimo_evento_id == "s:12"
        # Coherencia por construccion: el indice numerico es el sufijo del propio
        # evento_id devuelto (misma fila, no dos consultas que podrian divergir).
        assert ultimo_evento_id.endswith(f":{ultimo_indice}")

    @pytest.mark.asyncio
    async def test_una_sola_consulta_a_la_base(self):
        """Guarda de regresion: si alguien la reescribe con dos consultas
        separadas (una para la secuencia, otra para el evento_id), ultimo_indice
        y ultimo_evento_id podrian dejar de corresponder a la misma fila."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(first=MagicMock(return_value=SimpleNamespace(secuencia=1, evento_id="s:1")))
        )

        await _ultimo_evento_de(mock_db, uuid4())

        assert mock_db.execute.await_count == 1


class TestAbrirOReanudarSesion:
    @pytest.mark.asyncio
    async def test_crea_sesion_nueva_con_ultimo_indice_menos_uno(self):
        mock_db = AsyncMock()
        resultado_busqueda = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        mock_db.execute = AsyncMock(return_value=resultado_busqueda)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        async def _refresh(obj):
            obj.id = uuid4()

        mock_db.refresh = AsyncMock(side_effect=_refresh)

        datos = LumaSesionEntrada(
            runId=uuid4(), version="1.0", schemaVersion="1.0", policyVersion="cpa-1", simulation=False
        )

        salida = await abrir_o_reanudar_sesion(mock_db, datos)

        mock_db.add.assert_called_once()
        assert salida.ultimo_indice == -1
        assert salida.token == calcular_token(datos.run_id)

    @pytest.mark.asyncio
    async def test_reanuda_sesion_existente_devuelve_ultimo_indice_y_evento_id(self):
        run_id = uuid4()
        sesion_existente = LumaSesion(id=uuid4(), run_id=run_id, version="1.0", schema_version="1.0", policy_version="cpa-1")

        mock_db = AsyncMock()
        resultado_busqueda = MagicMock(scalar_one_or_none=MagicMock(return_value=sesion_existente))
        resultado_ultimo = MagicMock(first=MagicMock(return_value=SimpleNamespace(secuencia=7, evento_id="s:7")))
        mock_db.execute = AsyncMock(side_effect=[resultado_busqueda, resultado_ultimo])

        datos = LumaSesionEntrada(
            runId=run_id, version="1.0", schemaVersion="1.0", policyVersion="cpa-1", simulation=False
        )

        salida = await abrir_o_reanudar_sesion(mock_db, datos)

        assert salida.ultimo_indice == 7
        assert salida.ultimo_evento_id == "s:7"
        assert salida.token == calcular_token(run_id)

    @pytest.mark.asyncio
    async def test_sesion_nueva_devuelve_ultimo_evento_id_none(self):
        mock_db = AsyncMock()
        resultado_busqueda = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        mock_db.execute = AsyncMock(return_value=resultado_busqueda)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        async def _refresh(obj):
            obj.id = uuid4()

        mock_db.refresh = AsyncMock(side_effect=_refresh)

        datos = LumaSesionEntrada(
            runId=uuid4(), version="1.0", schemaVersion="1.0", policyVersion="cpa-1", simulation=False
        )

        salida = await abrir_o_reanudar_sesion(mock_db, datos)

        assert salida.ultimo_indice == -1
        assert salida.ultimo_evento_id is None


class TestValidarEvento:
    """Bug real hallado por el equipo probando contra Postgres real: la ingesta
    guardaba el SOBRE COMPLETO del evento en la columna `data` (duplicando phase,
    task, tipo, session, runId, version... que ya viven en sus propias columnas),
    en vez de solo el sub-objeto `data` del evento."""

    def test_guarda_solo_el_subobjeto_data_no_el_sobre_completo(self):
        sesion_id = uuid4()
        session_carga = uuid4()
        evento_crudo = {
            "id": f"{session_carga}:1",
            "type": "hint_requested",
            "at": "2026-09-17T10:00:00Z",
            "session": str(session_carga),
            "phase": "math",
            "runId": str(uuid4()),
            "version": "1.4",
            "simulation": False,
            "data": {"latencyMs": 1900, "afterError": True},
        }

        fila = _validar_evento(sesion_id, evento_crudo)

        assert isinstance(fila, dict)
        assert fila["data"] == {"latencyMs": 1900, "afterError": True}
        # Las claves del sobre no deben colarse en la columna data: ya viven en
        # sus propias columnas desnormalizadas (phase, tipo, session_carga...).
        assert "runId" not in fila["data"]
        assert "type" not in fila["data"]
        assert "session" not in fila["data"]
        assert "phase" not in fila["data"]

    def test_evento_sin_data_guarda_diccionario_vacio(self):
        sesion_id = uuid4()
        evento_crudo = _evento_crudo(uuid4(), 1)  # _evento_crudo no incluye "data"

        fila = _validar_evento(sesion_id, evento_crudo)

        assert fila["data"] == {}

    def test_evento_con_data_no_diccionario_guarda_diccionario_vacio(self):
        """Defensivo: si `data` llegara con un tipo raro (no dict), no se propaga
        tal cual a una columna JSONB pensada para objetos."""
        sesion_id = uuid4()
        evento_crudo = dict(_evento_crudo(uuid4(), 1))
        evento_crudo["data"] = "no-es-un-diccionario"

        fila = _validar_evento(sesion_id, evento_crudo)

        assert fila["data"] == {}


class TestCampoRedTransitoria:
    """_campo/_interior_de deben seguir leyendo correctamente las filas guardadas
    ANTES del fix de ingesta (con el sobre completo anidado), sin que eso afecte
    la lectura de filas nuevas (ya cubierta por el resto de la suite, que usa
    `_evento_modelo` en su forma correcta por defecto)."""

    def test_intentos_lee_una_fila_antigua_con_el_sobre_completo_anidado(self):
        run_id = uuid4()
        eventos = [
            _evento_modelo(
                1,
                "attempt",
                {"data": {"attemptNumber": 1, "assisted": False, "correct": True}},
                legacy=True,
            ),
        ]

        resumen = construir_resumen(run_id, eventos)

        assert resumen.intentos.aciertos_primer_intento_sin_ayuda == 1

    def test_fila_nueva_correcta_no_necesita_la_red_transitoria(self):
        """Misma aserción que la prueba anterior, pero con la forma NUEVA (plana,
        sin sobre anidado): ambas deben dar el mismo resultado."""
        run_id = uuid4()
        eventos = [
            _evento_modelo(1, "attempt", {"attemptNumber": 1, "assisted": False, "correct": True}),
        ]

        resumen = construir_resumen(run_id, eventos)

        assert resumen.intentos.aciertos_primer_intento_sin_ayuda == 1


class TestIngerirEventos:
    @pytest.mark.asyncio
    async def test_evento_con_id_no_parseable_se_rechaza_sin_tumbar_el_lote(self):
        sesion = LumaSesion(id=uuid4(), run_id=uuid4(), version="1.0", schema_version="1.0", policy_version="cpa-1")
        session_carga = uuid4()

        evento_valido = _evento_crudo(session_carga, 1)
        evento_malo = dict(_evento_crudo(session_carga, 2))
        evento_malo["id"] = "sin-indice-entero"

        mock_db = AsyncMock()
        resultado_insert = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=["x:1"]))))
        resultado_ultimo = MagicMock(first=MagicMock(return_value=SimpleNamespace(secuencia=1, evento_id="x:1")))
        mock_db.execute = AsyncMock(side_effect=[resultado_insert, resultado_ultimo])
        mock_db.commit = AsyncMock()

        salida = await ingerir_eventos(mock_db, sesion, [evento_valido, evento_malo])

        assert salida.guardados == 1
        assert salida.duplicados == 0
        assert salida.ultimo_evento_id == "x:1"
        assert len(salida.rechazados) == 1
        assert salida.rechazados[0].id == "sin-indice-entero"
        assert "indice entero" in salida.rechazados[0].motivo

    @pytest.mark.asyncio
    async def test_reenviar_el_mismo_lote_no_produce_duplicados_nuevos(self):
        """Simula ON CONFLICT DO NOTHING: la segunda vez, el RETURNING no trae filas
        porque Postgres las descarto todas por la restriccion unica (sesion_id, evento_id).
        No se prueba contra Postgres real: se mockea el resultado que produciria ese
        comportamiento para verificar la aritmetica guardados/duplicados del servicio."""
        sesion = LumaSesion(id=uuid4(), run_id=uuid4(), version="1.0", schema_version="1.0", policy_version="cpa-1")
        session_carga = uuid4()
        lote = [_evento_crudo(session_carga, 1), _evento_crudo(session_carga, 2)]

        mock_db = AsyncMock()
        resultado_insert_primero = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=["s:1", "s:2"])))
        )
        resultado_ultimo_primero = MagicMock(first=MagicMock(return_value=SimpleNamespace(secuencia=2, evento_id="s:2")))
        mock_db.execute = AsyncMock(side_effect=[resultado_insert_primero, resultado_ultimo_primero])
        mock_db.commit = AsyncMock()

        primera = await ingerir_eventos(mock_db, sesion, lote)
        assert primera.guardados == 2
        assert primera.duplicados == 0
        assert primera.ultimo_evento_id == "s:2"

        resultado_insert_segundo = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
        # El reenvio no inserta nada nuevo, pero el ultimo evento_id sigue siendo
        # el del ultimo REAL ya guardado (de la primera vez), no None ni vacio.
        resultado_ultimo_segundo = MagicMock(first=MagicMock(return_value=SimpleNamespace(secuencia=2, evento_id="s:2")))
        mock_db.execute = AsyncMock(side_effect=[resultado_insert_segundo, resultado_ultimo_segundo])

        segunda = await ingerir_eventos(mock_db, sesion, lote)
        assert segunda.guardados == 0
        assert segunda.duplicados == 2
        assert segunda.ultimo_indice == 2
        assert segunda.ultimo_evento_id == "s:2"

    @pytest.mark.asyncio
    async def test_partida_sin_ningun_evento_guardado_devuelve_ultimo_evento_id_none(self):
        """Si el lote entero se rechaza (o la partida nunca tuvo eventos), la
        partida sigue vacia: ultimo_evento_id debe ser None, no una cadena vacia
        ni un valor inventado."""
        sesion = LumaSesion(id=uuid4(), run_id=uuid4(), version="1.0", schema_version="1.0", policy_version="cpa-1")
        session_carga = uuid4()
        evento_malo = dict(_evento_crudo(session_carga, 1))
        evento_malo["id"] = "sin-indice-entero"

        mock_db = AsyncMock()
        # No hay filas validas: no se llega a ejecutar el INSERT, solo la consulta
        # de _ultimo_evento_de (partida vacia -> first() devuelve None).
        resultado_ultimo = MagicMock(first=MagicMock(return_value=None))
        mock_db.execute = AsyncMock(return_value=resultado_ultimo)
        mock_db.commit = AsyncMock()

        salida = await ingerir_eventos(mock_db, sesion, [evento_malo])

        assert salida.guardados == 0
        assert salida.ultimo_indice == -1
        assert salida.ultimo_evento_id is None
        assert len(salida.rechazados) == 1


class TestConstruirResumen:
    def test_intentos_clasifica_por_correct_attempt_number_y_assisted(self):
        """Correccion del equipo: aciertos_primer_intento_sin_ayuda exige
        correct==True ademas de attemptNumber==1 y assisted==False. Un primer
        intento fallido (correct=False) NO cuenta como acierto."""
        run_id = uuid4()
        eventos = [
            _evento_modelo(1, "attempt", {"data": {"attemptNumber": 1, "assisted": False, "correct": True}}),
            _evento_modelo(2, "attempt", {"data": {"attemptNumber": 2, "assisted": False, "correct": True}}),
            _evento_modelo(3, "attempt", {"data": {"attemptNumber": 1, "assisted": True, "correct": True}}),
            _evento_modelo(4, "attempt", {"data": {"attemptNumber": 1, "assisted": False, "correct": False}}),
        ]

        resumen = construir_resumen(run_id, eventos)

        assert resumen.intentos.total == 4
        assert resumen.intentos.reintentos == 1
        assert resumen.intentos.asistidos == 1
        # Solo el evento 1 cumple correct=True, attemptNumber=1 y assisted=False;
        # el evento 4 es primer intento sin ayuda pero FALLIDO, no cuenta.
        assert resumen.intentos.aciertos_primer_intento_sin_ayuda == 1

    def test_resueltos_independientes_usa_decision_evaluated_no_attempt(self):
        """Fuente PRINCIPAL de 'resuelto sin ayuda': decision_evaluated.data.independent,
        no el desglose sobre attempt. Un intento marcado correct+attemptNumber=1+no
        asistido no debe inflar este contador si el motor NO emitio independent=true."""
        run_id = uuid4()
        eventos = [
            _evento_modelo(1, "attempt", {"data": {"attemptNumber": 1, "assisted": False, "correct": True}}),
            _evento_modelo(2, "decision_evaluated", {"data": {"decisionId": "d1", "independent": True}}),
            _evento_modelo(3, "decision_evaluated", {"data": {"decisionId": "d2", "independent": False}}),
        ]

        resumen = construir_resumen(run_id, eventos)

        assert resumen.intentos.resueltos_independientes == 1

    def test_ayuda_distingue_voluntario_de_impuesto(self):
        run_id = uuid4()
        eventos = [
            _evento_modelo(1, "hint_requested", {}),
            _evento_modelo(2, "support_selected", {"data": {"voluntary": True}}),
            _evento_modelo(3, "support_selected", {"data": {"voluntary": False}}),
        ]

        resumen = construir_resumen(run_id, eventos)

        assert resumen.ayuda.hint_requested == 1
        assert resumen.ayuda.apoyo_voluntario == 1
        assert resumen.ayuda.apoyo_impuesto == 1

    def test_pausas_se_emparejan_por_inicio_y_fin(self):
        run_id = uuid4()
        eventos = [
            _evento_modelo(1, "pause_started", {}),
            _evento_modelo(2, "pause_ended", {}),
        ]

        resumen = construir_resumen(run_id, eventos)

        assert resumen.inactividad.idle_started == 0
        assert len(resumen.inactividad.pausas) == 1
        pausa = resumen.inactividad.pausas[0]
        assert pausa.duracion_ms == 1000
        assert "no inferible" in resumen.inactividad.limite.lower() or "diagnostico" in resumen.inactividad.limite.lower()

    def test_decision_evaluated_filtra_el_campo_con_bug(self):
        run_id = uuid4()
        eventos = [
            _evento_modelo(
                1,
                "adaptation_decision",
                {"data": {"decisionId": "d1", "reason": "three_failures", "effectiveSupport": "visual", "evidenceIds": ["e1", "e2"]}},
            ),
            _evento_modelo(
                2,
                "decision_evaluated",
                {"data": {"decisionId": "d1", "learning": {"stage": "futuro-no-confiable"}, "correct": True}},
            ),
        ]

        resumen = construir_resumen(run_id, eventos)

        assert len(resumen.decisiones_adaptacion) == 1
        decision = resumen.decisiones_adaptacion[0]
        assert decision.resuelta is True
        assert decision.evidencia_cantidad == 2
        assert "learning" not in (decision.resultado or {})
        assert decision.resultado == {"decisionId": "d1", "correct": True}

    def test_decision_sin_resolver_usa_decision_response(self):
        run_id = uuid4()
        eventos = [
            _evento_modelo(1, "adaptation_decision", {"data": {"decisionId": "d2", "reason": "repeated_help_requests"}}),
            _evento_modelo(2, "decision_response", {"data": {"error": "timeout"}}),
        ]
        # decision_response sin decisionId: no deberia enlazarse por accidente.
        resumen = construir_resumen(run_id, eventos)
        decision = resumen.decisiones_adaptacion[0]
        assert decision.resuelta is False
        assert decision.resultado is None

    def test_estado_vacio_sin_eventos(self):
        resumen = construir_resumen(uuid4(), [])
        assert resumen.intentos.total == 0
        assert resumen.estado_actual.heartbeat_reciente is False
        assert resumen.decisiones_adaptacion == []
        assert resumen.progresion.acreditadas_total == 0
        assert resumen.progresion.de_24 == CANTIDAD_CASILLAS_CPA


class TestConstruirProgresion:
    def test_catalogo_tiene_6_habilidades_y_24_casillas(self):
        progresion = construir_progresion([])

        assert len(progresion.habilidades) == 6
        assert progresion.de_24 == 24
        assert CANTIDAD_CASILLAS_CPA == 24
        for habilidad in progresion.habilidades:
            assert habilidad.etapas.concrete == "pendiente"
            assert habilidad.etapas.pictorial == "pendiente"
            assert habilidad.etapas.abstract == "pendiente"
            assert habilidad.etapas.transfer == "pendiente"
            assert habilidad.bayesiano.dominada is False
            assert habilidad.bayesiano.p is None
            assert habilidad.bayesiano.n is None

    def test_prerrequisitos_vienen_del_catalogo_del_equipo(self):
        progresion = construir_progresion([])
        por_id = {h.id: h for h in progresion.habilidades}

        assert por_id["meaning"].prerrequisitos == []
        assert por_id["equivalent"].prerrequisitos == ["meaning"]
        assert por_id["add_same"].prerrequisitos == ["meaning"]
        assert por_id["sub_same"].prerrequisitos == ["meaning"]
        assert por_id["add_diff"].prerrequisitos == ["equivalent", "add_same"]
        assert por_id["sub_diff"].prerrequisitos == ["equivalent", "sub_same"]
        assert {h["id"] for h in CATALOGO_HABILIDADES} == set(por_id.keys())

    def test_casilla_acreditada_exige_independent_y_outcome_solved(self):
        eventos = [
            _evento_modelo(
                1,
                "decision_evaluated",
                {"data": {"skill": "meaning", "stage": "concrete", "independent": True, "outcome": "solved"}},
            ),
            # independent=False: NO debe acreditar aunque outcome sea 'solved'.
            _evento_modelo(
                2,
                "decision_evaluated",
                {"data": {"skill": "meaning", "stage": "pictorial", "independent": False, "outcome": "solved"}},
            ),
            # outcome distinto de 'solved': NO debe acreditar aunque independent sea True.
            _evento_modelo(
                3,
                "decision_evaluated",
                {"data": {"skill": "meaning", "stage": "abstract", "independent": True, "outcome": "failed"}},
            ),
        ]

        progresion = construir_progresion(eventos)
        meaning = next(h for h in progresion.habilidades if h.id == "meaning")

        assert meaning.etapas.concrete == "acreditada"
        assert meaning.etapas.pictorial == "pendiente"
        assert meaning.etapas.abstract == "pendiente"
        assert progresion.acreditadas_total == 1

    def test_en_curso_usa_la_forma_real_skill_arriba_stage_dentro_de_item(self):
        """Forma confirmada por el equipo contra el motor (app.js:602):
        task_presented.data = { item, skill, ... }, con `stage` DENTRO de `item`,
        nunca al nivel superior de data."""
        eventos = [
            _evento_modelo(1, "task_presented", {"data": {"skill": "meaning", "item": {"stage": "concrete"}}}),
            _evento_modelo(2, "task_presented", {"data": {"skill": "meaning", "item": {"stage": "pictorial"}}}),
        ]

        progresion = construir_progresion(eventos)
        meaning = next(h for h in progresion.habilidades if h.id == "meaning")

        # Solo el ULTIMO task_presented cuenta como "en curso"; el primero, al no
        # estar acreditado, queda pendiente.
        assert meaning.etapas.pictorial == "en_curso"
        assert meaning.etapas.concrete == "pendiente"

    def test_en_curso_usa_item_id_como_respaldo_si_falta_data_skill(self):
        """Respaldo confirmado por el equipo: el motor usa item.id como
        identificador de habilidad (state.knowledge[t.id]) si data.skill faltara."""
        eventos = [_evento_modelo(1, "task_presented", {"data": {"item": {"id": "sub_same", "stage": "abstract"}}})]

        progresion = construir_progresion(eventos)
        sub_same = next(h for h in progresion.habilidades if h.id == "sub_same")

        assert sub_same.etapas.abstract == "en_curso"

    def test_en_curso_ultima_red_con_todo_aplanado_en_data(self):
        """Ultima red por si algun evento llega sin 'item' en absoluto (no es la
        forma real confirmada, pero el codigo la sigue tolerando)."""
        eventos = [_evento_modelo(1, "task_presented", {"data": {"skill": "add_same", "stage": "abstract"}})]

        progresion = construir_progresion(eventos)
        add_same = next(h for h in progresion.habilidades if h.id == "add_same")

        assert add_same.etapas.abstract == "en_curso"

    def test_acreditada_tiene_prioridad_sobre_en_curso(self):
        eventos = [
            _evento_modelo(1, "task_presented", {"data": {"skill": "meaning", "item": {"stage": "concrete"}}}),
            _evento_modelo(
                2,
                "decision_evaluated",
                {"data": {"skill": "meaning", "stage": "concrete", "independent": True, "outcome": "solved"}},
            ),
        ]

        progresion = construir_progresion(eventos)
        meaning = next(h for h in progresion.habilidades if h.id == "meaning")

        assert meaning.etapas.concrete == "acreditada"

    def test_bayesiano_dominada_exige_n_y_p_del_umbral(self):
        eventos = [
            _evento_modelo(1, "knowledge_updated", {"data": {"skill": "meaning", "posterior": {"p": 0.5, "n": 5}}}),
            _evento_modelo(
                2, "knowledge_updated", {"data": {"skill": "meaning", "posterior": {"p": 0.9, "n": 5}}}
            ),  # el ultimo sobrescribe al anterior
            _evento_modelo(3, "knowledge_updated", {"data": {"skill": "equivalent", "posterior": {"p": 0.95, "n": 2}}}),
        ]

        progresion = construir_progresion(eventos)
        por_id = {h.id: h for h in progresion.habilidades}

        assert por_id["meaning"].bayesiano.p == 0.9
        assert por_id["meaning"].bayesiano.n == 5
        assert por_id["meaning"].bayesiano.dominada is True
        # n=2 < UMBRAL_N_DOMINIO=3: no domina aunque p sea alto.
        assert por_id["equivalent"].bayesiano.dominada is False

    def test_decision_evaluated_learning_nunca_se_lee_para_la_rejilla(self):
        """El campo con bug conocido no debe influir en absoluto en la rejilla: la
        presencia (o ausencia) de 'learning' no cambia el resultado."""
        eventos = [
            _evento_modelo(
                1,
                "decision_evaluated",
                {
                    "data": {
                        "skill": "meaning",
                        "stage": "concrete",
                        "independent": True,
                        "outcome": "solved",
                        "learning": {"stage": "etapa-futura-no-confiable"},
                    }
                },
            ),
        ]

        progresion = construir_progresion(eventos)
        meaning = next(h for h in progresion.habilidades if h.id == "meaning")

        assert meaning.etapas.concrete == "acreditada"

    def test_acreditadas_total_nunca_supera_24(self):
        eventos = []
        secuencia = 1
        # Acredita las 24 casillas reales DOS veces cada una: el set de (skill,
        # stage) debe deduplicar, asi que el total sigue siendo 24, no 48.
        for habilidad in CATALOGO_HABILIDADES:
            for etapa in ETAPAS_CPA_TEST:
                for _ in range(2):
                    eventos.append(
                        _evento_modelo(
                            secuencia,
                            "decision_evaluated",
                            {
                                "data": {
                                    "skill": habilidad["id"],
                                    "stage": etapa,
                                    "independent": True,
                                    "outcome": "solved",
                                }
                            },
                        )
                    )
                    secuencia += 1
        # Una habilidad que no existe en el catalogo: no debe inflar el conteo.
        eventos.append(
            _evento_modelo(
                secuencia,
                "decision_evaluated",
                {"data": {"skill": "skill_inventada", "stage": "concrete", "independent": True, "outcome": "solved"}},
            )
        )

        progresion = construir_progresion(eventos)

        assert progresion.acreditadas_total == 24
        assert progresion.de_24 == 24


class TestRespuestaAnteError:
    def test_clasifica_busca_ayuda(self):
        eventos = [
            _evento_modelo(1, "attempt", {"data": {"correct": False}}),
            _evento_modelo(2, "hint_requested", {}),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.respuesta_ante_error.busca_ayuda == 1
        assert resumen.respuesta_ante_error.reintento_inmediato == 0
        assert resumen.respuesta_ante_error.inactividad_bloqueo == 0
        assert resumen.respuesta_ante_error.sin_clasificar == 0

    def test_clasifica_inactividad_bloqueo(self):
        eventos = [
            _evento_modelo(1, "attempt", {"data": {"correct": False}}),
            _evento_modelo(2, "idle_started", {}),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.respuesta_ante_error.inactividad_bloqueo == 1

    def test_clasifica_reintento_inmediato_con_otro_attempt(self):
        eventos = [
            _evento_modelo(1, "attempt", {"data": {"correct": False}}),
            _evento_modelo(2, "attempt", {"data": {"correct": True}}),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.respuesta_ante_error.reintento_inmediato == 1

    def test_sin_clasificar_si_la_sesion_termina_en_el_fallo(self):
        eventos = [_evento_modelo(1, "attempt", {"data": {"correct": False}})]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.respuesta_ante_error.sin_clasificar == 1
        assert resumen.respuesta_ante_error.reintento_inmediato == 0

    def test_post_error_action_de_ayuda_clasifica_busca_ayuda_y_aporta_latencia(self):
        eventos = [
            _evento_modelo(1, "attempt", {"data": {"correct": False}}),
            _evento_modelo(2, "post_error_action", {"data": {"action": "hint", "latencyMs": 500}}),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.respuesta_ante_error.busca_ayuda == 1
        assert resumen.respuesta_ante_error.reintento_inmediato == 0
        assert resumen.respuesta_ante_error.latencia_mediana_ms.busca_ayuda == 500

    def test_post_error_action_de_reintento_clasifica_reintento_y_aporta_latencia(self):
        eventos = [
            _evento_modelo(1, "attempt", {"data": {"correct": False}}),
            _evento_modelo(2, "post_error_action", {"data": {"action": "keydown", "latencyMs": 800}}),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.respuesta_ante_error.reintento_inmediato == 1
        assert resumen.respuesta_ante_error.latencia_mediana_ms.reintento_inmediato == 800

    @pytest.mark.parametrize("accion", ["dont_know", "use_pieces", "garden_sound", "piece"])
    def test_las_cuatro_acciones_sin_palabras_de_ayuda_clasifican_busca_ayuda(self, accion):
        """Estas cuatro acciones son ayuda segun el motor pero no contienen
        'hint'/'help'/'support'/'ayuda': una heuristica por subcadena las clasificaria
        mal como reintento_inmediato. La lista blanca explicita las cubre bien."""
        eventos = [
            _evento_modelo(1, "attempt", {"data": {"correct": False}}),
            _evento_modelo(2, "post_error_action", {"data": {"action": accion}}),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.respuesta_ante_error.busca_ayuda == 1
        assert resumen.respuesta_ante_error.reintento_inmediato == 0

    def test_rhythm_no_cuenta_como_ayuda(self):
        """Decision explicita del equipo: 'rhythm' es medio de respuesta, no pista
        (el motor emite rhythm_played con assistance=false), asi que queda fuera de
        la lista blanca de ayuda. Tampoco es reintento, asi que un post_error_action
        con esta accion no clasifica nada por si solo."""
        eventos = [
            _evento_modelo(1, "attempt", {"data": {"correct": False}}),
            _evento_modelo(2, "post_error_action", {"data": {"action": "rhythm"}}),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.respuesta_ante_error.busca_ayuda == 0
        assert resumen.respuesta_ante_error.reintento_inmediato == 0
        assert resumen.respuesta_ante_error.sin_clasificar == 1

    def test_pointerdown_se_ignora_y_no_clasifica_como_reintento(self):
        """Un clic en cualquier parte de la pantalla (incluidos botones de cabecera
        sin data-action) no es evidencia de reintento: contarlo asi confundiria un
        desenganche con perseverancia."""
        eventos = [
            _evento_modelo(1, "attempt", {"data": {"correct": False}}),
            _evento_modelo(2, "post_error_action", {"data": {"action": "pointerdown", "latencyMs": 100}}),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.respuesta_ante_error.sin_clasificar == 1
        assert resumen.respuesta_ante_error.reintento_inmediato == 0
        # 'pointerdown' tampoco debe ensuciar la mediana de latencia.
        assert resumen.respuesta_ante_error.latencia_mediana_ms.reintento_inmediato is None

    def test_pointerdown_se_ignora_pero_sigue_buscando_el_siguiente_evento(self):
        eventos = [
            _evento_modelo(1, "attempt", {"data": {"correct": False}}),
            _evento_modelo(2, "post_error_action", {"data": {"action": "pointerdown"}}),
            _evento_modelo(3, "hint_requested", {}),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.respuesta_ante_error.busca_ayuda == 1
        assert resumen.respuesta_ante_error.sin_clasificar == 0

    def test_pause_ended_con_help_true_clasifica_busca_ayuda(self):
        """El boton 'Volver con una pista' del dialogo de pausa nunca aparece en
        post_error_action (registro de interacciones desactivado durante la
        pausa); su unica senal es pause_ended con help=true."""
        eventos = [
            _evento_modelo(1, "attempt", {"data": {"correct": False}}),
            _evento_modelo(2, "pause_started", {}),
            _evento_modelo(3, "pause_ended", {"data": {"help": True}}),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.respuesta_ante_error.busca_ayuda == 1

    def test_pause_ended_sin_help_no_clasifica_busca_ayuda(self):
        eventos = [
            _evento_modelo(1, "attempt", {"data": {"correct": False}}),
            _evento_modelo(2, "pause_started", {}),
            _evento_modelo(3, "pause_ended", {"data": {"help": False}}),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.respuesta_ante_error.busca_ayuda == 0
        assert resumen.respuesta_ante_error.sin_clasificar == 1

    def test_intentos_correctos_no_cuentan_como_fallo(self):
        eventos = [_evento_modelo(1, "attempt", {"data": {"correct": True}})]

        resumen = construir_resumen(uuid4(), eventos)

        total = (
            resumen.respuesta_ante_error.reintento_inmediato
            + resumen.respuesta_ante_error.busca_ayuda
            + resumen.respuesta_ante_error.inactividad_bloqueo
            + resumen.respuesta_ante_error.sin_clasificar
        )
        assert total == 0


class TestAutonomia:
    def test_cuenta_cambios_de_ruta_sin_contar_la_eleccion_inicial(self):
        eventos = [
            _evento_modelo(1, "route_selected", {"data": {"route": "guided"}}),
            _evento_modelo(2, "route_selected", {"data": {"route": "guided"}}),  # repite: no es un cambio
            _evento_modelo(3, "route_selected", {"data": {"route": "free"}}),
            _evento_modelo(4, "route_selected", {"data": {"route": "guided"}}),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.autonomia.ruta_actual == "guided"
        assert resumen.autonomia.cambios_de_ruta == 2

    def test_cuenta_navegaciones_y_destinos(self):
        eventos = [
            _evento_modelo(1, "navigation", {"data": {"destination": "greenhouse"}}),
            _evento_modelo(2, "navigation", {"data": {"destination": "station"}}),
            _evento_modelo(3, "navigation", {"data": {"destination": "greenhouse"}}),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.autonomia.navegaciones == 3
        assert resumen.autonomia.destinos.greenhouse == 2
        assert resumen.autonomia.destinos.station == 1
        assert resumen.autonomia.destinos.garden == 0
        assert resumen.autonomia.destinos.map == 0

    def test_sin_route_selected_ruta_actual_es_none(self):
        resumen = construir_resumen(uuid4(), [_evento_modelo(1, "heartbeat", {})])
        assert resumen.autonomia.ruta_actual is None
        assert resumen.autonomia.cambios_de_ruta == 0


class TestMotivoFinal:
    def test_null_cuando_no_hay_evidencia_aunque_la_fase_sea_complete(self):
        eventos = [_evento_modelo(1, "phase_transition", {}, phase="complete")]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.estado_actual.motivo_final is None

    def test_mastery_desde_learning_path_completed(self):
        eventos = [
            _evento_modelo(1, "learning_path_completed", {}, phase="complete"),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.estado_actual.motivo_final == "mastery"

    def test_break_desde_voluntary_break_o_break_suggested(self):
        eventos = [_evento_modelo(1, "break_suggested", {}, phase="complete")]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.estado_actual.motivo_final == "break"

    def test_bank_exhausted_no_se_confunde_con_mastery(self):
        eventos = [
            _evento_modelo(1, "item_bank_exhausted", {"data": {"masteryGranted": False}}, phase="complete"),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.estado_actual.motivo_final == "bank_exhausted"

    def test_solo_aplica_cuando_la_fase_actual_es_complete(self):
        """Un learning_path_completed viejo no debe filtrarse si la fase actual
        (del ultimo evento) ya no es 'complete'."""
        eventos = [
            _evento_modelo(1, "learning_path_completed", {}, phase="complete"),
            _evento_modelo(2, "heartbeat", {}, phase="playing"),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.estado_actual.motivo_final is None

    def test_usa_el_ultimo_evento_relevante_no_el_primero(self):
        eventos = [
            _evento_modelo(1, "break_suggested", {}, phase="complete"),
            _evento_modelo(2, "learning_path_completed", {}, phase="complete"),
        ]

        resumen = construir_resumen(uuid4(), eventos)

        assert resumen.estado_actual.motivo_final == "mastery"
