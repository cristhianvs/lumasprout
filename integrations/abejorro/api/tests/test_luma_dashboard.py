"""Tests de services/luma_dashboard.py (panorama, series, historico).

La base de datos SIEMPRE se mockea: estos tests no abren conexion real a Postgres, y
por lo tanto NO verifican que las consultas SQL sean validas contra un servidor real
(sintaxis, tipos de columnas JSONB, planes de ejecucion). Lo que se verifica es:

1. Con `_DBCapturador` (una fake AsyncSession que registra cada sentencia y devuelve
   resultados vacios "seguros" por defecto): que cada funcion de agregacion
   construye una consulta que, compilada contra el dialecto de PostgreSQL, incluye
   el filtro `simulation = false`. Esto NO prueba que la consulta sea correcta,
   solo que el filtro de simulacion sigue presente (regresion barata contra que
   alguien lo borre sin querer).
2. Con resultados canned (filas de ejemplo tal como las devolveria `.all()`,
   `.scalar_one()`, etc.): que el mapeo de esas filas al schema de respuesta es
   correcto (agrupacion por dia, ceros/nulos explicitos en huecos, acumulados).
3. Funciones puras (`_motivo_desde_tipo_relevante`, `_sesion_historica_de`) sin
   ningun mock, directamente.
"""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from models.luma import LumaEvento, LumaSesion
from services import luma_dashboard
from services.luma_service import (
    FASE_COMPLETA,
    MOTIVO_FINAL_BANK_EXHAUSTED,
    MOTIVO_FINAL_BREAK,
    MOTIVO_FINAL_MASTERY,
)


def _evento(
    secuencia: int, tipo: str, data: dict, *, session_carga=None, phase=None, play_ms=None, math_ms=None
) -> LumaEvento:
    return LumaEvento(
        id=uuid4(),
        sesion_id=uuid4(),
        evento_id=f"s:{secuencia}",
        session_carga=session_carga or uuid4(),
        secuencia=secuencia,
        tipo=tipo,
        at_cliente=datetime(2026, 9, 10, 10, 0, secuencia % 60, tzinfo=UTC),
        recibido_at=datetime.now(UTC),
        phase=phase,
        play_ms=play_ms,
        math_ms=math_ms,
        data=data,
    )


class _ResultadoFlexible:
    """Imita lo suficiente de sqlalchemy.Result para que el codigo bajo prueba no
    truene sin importar que metodo llame (.all(), .one_or_none(), .scalar_one(),
    .scalars().all()...). Por defecto, "vacio" en cualquiera de esas formas."""

    def __init__(self, filas: list | None = None, escalar: int = 0):
        self._filas = filas if filas is not None else []
        self._escalar = escalar

    def all(self):
        return self._filas

    def one(self):
        return self._filas[0]

    def one_or_none(self):
        return self._filas[0] if self._filas else None

    def scalar_one(self):
        return self._escalar

    def scalar_one_or_none(self):
        return self._filas[0] if self._filas else None

    def scalars(self):
        return _EscalaresFlexible(self._filas)


class _EscalaresFlexible:
    def __init__(self, filas: list):
        self._filas = filas

    def all(self):
        return self._filas


class _DBCapturador:
    """Fake de AsyncSession: registra cada sentencia ejecutada en `.consultas` y
    devuelve resultados "canned" en orden si se le dan, o un resultado vacio
    seguro por cada llamada si no."""

    def __init__(self, resultados: list | None = None):
        self._resultados = list(resultados) if resultados is not None else None
        self.consultas: list = []

    async def execute(self, stmt):
        self.consultas.append(stmt)
        if self._resultados is not None:
            return self._resultados.pop(0)
        return _ResultadoFlexible()


def _sql_de(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect()))


class TestFiltroSimulacion:
    """Ninguno de estos agregados debe perder el filtro simulation=false."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "funcion",
        [
            luma_dashboard._totales,
            luma_dashboard._sesiones_por_dia,
            luma_dashboard._embudo_fases,
            luma_dashboard._motivos_cierre,
            luma_dashboard._modalidades,
            luma_dashboard._retencion,
            luma_dashboard._banco_agotado,
            luma_dashboard._puntos_de_fuga,
        ],
    )
    async def test_agregados_de_panorama_filtran_simulation(self, funcion):
        db = _DBCapturador()
        await funcion(db)

        assert db.consultas, "la funcion no ejecuto ninguna consulta"
        for consulta in db.consultas:
            assert "simulation" in _sql_de(consulta).lower()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "funcion",
        [
            luma_dashboard._independencia_por_dia,
            luma_dashboard._ayuda_por_dia,
            luma_dashboard._casillas_acreditadas_por_dia,
            luma_dashboard._tiempo_activo_mediana_por_dia,
            luma_dashboard._inactividad_por_dia,
            luma_dashboard._respuesta_ante_error_por_dia,
        ],
    )
    async def test_agregados_de_series_filtran_simulation(self, funcion):
        db = _DBCapturador()
        desde = datetime(2026, 9, 1, tzinfo=UTC)
        hasta = datetime(2026, 9, 30, tzinfo=UTC)

        await funcion(db, desde, hasta)

        assert db.consultas, "la funcion no ejecuto ninguna consulta"
        for consulta in db.consultas:
            assert "simulation" in _sql_de(consulta).lower()


class TestMotivoDesdeTipoRelevante:
    def test_sin_dato_si_la_ultima_fase_no_es_complete(self):
        assert luma_dashboard._motivo_desde_tipo_relevante("playing", None) == luma_dashboard.MOTIVO_SIN_DATO

    def test_sin_dato_si_es_complete_pero_sin_evento_relevante(self):
        assert luma_dashboard._motivo_desde_tipo_relevante(FASE_COMPLETA, None) == luma_dashboard.MOTIVO_SIN_DATO

    def test_mastery(self):
        assert (
            luma_dashboard._motivo_desde_tipo_relevante(FASE_COMPLETA, "learning_path_completed")
            == MOTIVO_FINAL_MASTERY
        )

    def test_break_desde_voluntary_o_suggested(self):
        assert luma_dashboard._motivo_desde_tipo_relevante(FASE_COMPLETA, "voluntary_break") == MOTIVO_FINAL_BREAK
        assert luma_dashboard._motivo_desde_tipo_relevante(FASE_COMPLETA, "break_suggested") == MOTIVO_FINAL_BREAK

    def test_bank_exhausted(self):
        assert (
            luma_dashboard._motivo_desde_tipo_relevante(FASE_COMPLETA, "item_bank_exhausted")
            == MOTIVO_FINAL_BANK_EXHAUSTED
        )


class TestSesionHistoricaDe:
    def test_tiempo_activo_es_el_delta_no_el_valor_bruto_acumulado(self):
        """play_ms/math_ms son acumulativos a lo largo de TODA la partida
        (confirmado por el equipo contra datos reales), asi que el tiempo de esta
        carga es MAX-MIN de cada reloj, sumados, no el valor bruto mas alto."""
        session_carga = uuid4()
        eventos = [
            _evento(1, "attempt", {"correct": True}, session_carga=session_carga, phase="math", play_ms=1000, math_ms=500),
            _evento(2, "attempt", {"correct": False}, session_carga=session_carga, phase="math", play_ms=2500, math_ms=800),
        ]
        acreditadas: set[tuple[str, str]] = set()

        historica = luma_dashboard._sesion_historica_de(eventos, acreditadas)

        # delta_play = 2500-1000 = 1500; delta_math = 800-500 = 300; suma = 1800.
        assert historica.tiempo_activo_ms == 1800

    def test_una_sola_sesion_sin_acreditaciones_previas(self):
        session_carga = uuid4()
        eventos = [
            _evento(1, "attempt", {"correct": True}, session_carga=session_carga, phase="math", play_ms=1000),
            _evento(2, "attempt", {"correct": False}, session_carga=session_carga, phase="math", play_ms=2000),
        ]
        acreditadas: set[tuple[str, str]] = set()

        historica = luma_dashboard._sesion_historica_de(eventos, acreditadas)

        assert historica.eventos == 2
        assert historica.tiempo_activo_ms == 1000
        assert historica.casillas_acreditadas_acumuladas == 0
        assert historica.fase_final == "math"
        assert historica.motivo_final is None
        assert historica.fecha == date(2026, 9, 10)

    def test_acumula_casillas_entre_llamadas_sucesivas(self):
        """`acreditadas_acumuladas` se comparte entre sesiones: la segunda sesion
        de un participante debe ver lo acreditado en la primera."""
        session_carga_1 = uuid4()
        session_carga_2 = uuid4()
        acreditadas: set[tuple[str, str]] = set()

        sesion_1 = [
            _evento(
                1,
                "decision_evaluated",
                {"skill": "meaning", "stage": "concrete", "independent": True, "outcome": "solved"},
                session_carga=session_carga_1,
            )
        ]
        historica_1 = luma_dashboard._sesion_historica_de(sesion_1, acreditadas)
        assert historica_1.casillas_acreditadas_acumuladas == 1

        sesion_2 = [_evento(2, "heartbeat", {}, session_carga=session_carga_2)]
        historica_2 = luma_dashboard._sesion_historica_de(sesion_2, acreditadas)
        # La segunda sesion no acredito nada nuevo, pero el acumulado sigue en 1.
        assert historica_2.casillas_acreditadas_acumuladas == 1

    def test_motivo_final_solo_si_la_fase_de_esa_sesion_es_complete(self):
        session_carga = uuid4()
        eventos = [_evento(1, "learning_path_completed", {}, session_carga=session_carga, phase="complete")]

        historica = luma_dashboard._sesion_historica_de(eventos, set())

        assert historica.motivo_final == MOTIVO_FINAL_MASTERY


class TestObtenerSeries:
    @pytest.mark.asyncio
    async def test_dias_sin_datos_se_devuelven_con_ceros_y_nulos_explicitos(self):
        with (
            patch("services.luma_dashboard._independencia_por_dia", new=AsyncMock(return_value={})),
            patch("services.luma_dashboard._ayuda_por_dia", new=AsyncMock(return_value={})),
            patch("services.luma_dashboard._casillas_acreditadas_por_dia", new=AsyncMock(return_value={})),
            patch("services.luma_dashboard._tiempo_activo_mediana_por_dia", new=AsyncMock(return_value={})),
            patch("services.luma_dashboard._inactividad_por_dia", new=AsyncMock(return_value={})),
            patch("services.luma_dashboard._respuesta_ante_error_por_dia", new=AsyncMock(return_value={})),
        ):
            salida = await luma_dashboard.obtener_series(AsyncMock(), dias=3)

        assert salida.dias == 3
        assert len(salida.serie) == 3
        for entrada in salida.serie:
            assert entrada.independencia is None
            assert entrada.casillas_acreditadas == 0
            assert entrada.tiempo_activo_mediana_ms is None
            assert entrada.inactividad_idle_started == 0
            assert entrada.respuesta_ante_error.sin_clasificar == 0
            assert entrada.respuesta_ante_error.busca_ayuda == 0
            assert entrada.ayuda.voluntaria == 0
            assert entrada.ayuda.impuesta == 0

    @pytest.mark.asyncio
    async def test_un_dia_con_datos_no_contamina_los_demas(self):
        hoy = datetime.now(UTC).date()
        with (
            patch("services.luma_dashboard._independencia_por_dia", new=AsyncMock(return_value={hoy: 0.5})),
            patch(
                "services.luma_dashboard._respuesta_ante_error_por_dia",
                new=AsyncMock(
                    return_value={hoy: luma_dashboard.LumaRespuestaAnteErrorDia(**{
                        "reintento_inmediato": 0,
                        "busca_ayuda": 3,
                        "inactividad_bloqueo": 0,
                        "sin_clasificar": 0,
                    })}
                ),
            ),
            patch("services.luma_dashboard._ayuda_por_dia", new=AsyncMock(return_value={})),
            patch("services.luma_dashboard._casillas_acreditadas_por_dia", new=AsyncMock(return_value={})),
            patch("services.luma_dashboard._tiempo_activo_mediana_por_dia", new=AsyncMock(return_value={})),
            patch("services.luma_dashboard._inactividad_por_dia", new=AsyncMock(return_value={})),
        ):
            salida = await luma_dashboard.obtener_series(AsyncMock(), dias=1)

        assert salida.serie[0].dia == hoy.isoformat()
        assert salida.serie[0].independencia == 0.5
        assert salida.serie[0].respuesta_ante_error.busca_ayuda == 3
        assert salida.serie[0].casillas_acreditadas == 0


class TestObtenerHistorico:
    @pytest.mark.asyncio
    async def test_participante_con_una_sola_sesion(self):
        sesion = LumaSesion(id=uuid4(), run_id=uuid4(), version="1.0", schema_version="1.0", policy_version="cpa-1")
        session_carga = uuid4()
        eventos = [
            _evento(1, "attempt", {"correct": True}, session_carga=session_carga, phase="math", play_ms=500),
            _evento(2, "heartbeat", {}, session_carga=session_carga, phase="math"),
        ]
        db = _DBCapturador([_ResultadoFlexible(filas=eventos)])

        historico = await luma_dashboard.obtener_historico(db, sesion)

        assert historico.run_id == sesion.run_id
        assert len(historico.sesiones) == 1
        assert historico.sesiones[0].eventos == 2
        assert historico.progresion_temporal == []
        assert historico.bayesiano_temporal == []

    @pytest.mark.asyncio
    async def test_progresion_temporal_no_repite_la_misma_casilla_dos_veces(self):
        sesion = LumaSesion(id=uuid4(), run_id=uuid4(), version="1.0", schema_version="1.0", policy_version="cpa-1")
        session_carga = uuid4()
        eventos = [
            _evento(
                1,
                "decision_evaluated",
                {"skill": "meaning", "stage": "concrete", "independent": True, "outcome": "solved"},
                session_carga=session_carga,
            ),
            # Misma casilla otra vez: no debe duplicarse en progresion_temporal.
            _evento(
                2,
                "decision_evaluated",
                {"skill": "meaning", "stage": "concrete", "independent": True, "outcome": "solved"},
                session_carga=session_carga,
            ),
        ]
        db = _DBCapturador([_ResultadoFlexible(filas=eventos)])

        historico = await luma_dashboard.obtener_historico(db, sesion)

        assert len(historico.progresion_temporal) == 1
        assert historico.progresion_temporal[0].habilidad == "meaning"
        assert historico.progresion_temporal[0].etapa == "concrete"

    @pytest.mark.asyncio
    async def test_bayesiano_temporal_registra_cada_knowledge_updated_en_orden(self):
        sesion = LumaSesion(id=uuid4(), run_id=uuid4(), version="1.0", schema_version="1.0", policy_version="cpa-1")
        session_carga = uuid4()
        eventos = [
            _evento(1, "knowledge_updated", {"skill": "meaning", "posterior": {"p": 0.5, "n": 1}}, session_carga=session_carga),
            _evento(2, "knowledge_updated", {"skill": "meaning", "posterior": {"p": 0.9, "n": 5}}, session_carga=session_carga),
        ]
        db = _DBCapturador([_ResultadoFlexible(filas=eventos)])

        historico = await luma_dashboard.obtener_historico(db, sesion)

        assert len(historico.bayesiano_temporal) == 2
        assert historico.bayesiano_temporal[0].p == 0.5
        assert historico.bayesiano_temporal[1].p == 0.9

    @pytest.mark.asyncio
    async def test_sin_eventos_devuelve_listas_vacias(self):
        sesion = LumaSesion(id=uuid4(), run_id=uuid4(), version="1.0", schema_version="1.0", policy_version="cpa-1")
        db = _DBCapturador([_ResultadoFlexible(filas=[])])

        historico = await luma_dashboard.obtener_historico(db, sesion)

        assert historico.sesiones == []
        assert historico.progresion_temporal == []
        assert historico.bayesiano_temporal == []


class TestPuntosDeFuga:
    @pytest.mark.asyncio
    async def test_clasifica_abandonos_por_fase_escena_y_habilidad(self):
        filas = [
            (FASE_COMPLETA, 5, None),  # llego a complete: no cuenta como abandono
            ("play", 3, None),
            ("play", 7, None),
            ("math", None, {"skill": "meaning", "item": {"stage": "concrete"}}),
        ]
        db = _DBCapturador([_ResultadoFlexible(filas=filas), _ResultadoFlexible(filas=[])])

        fuga = await luma_dashboard._puntos_de_fuga(db)

        por_fase = {c.fase: c.participantes for c in fuga.abandono_por_fase}
        assert por_fase == {"play": 2, "math": 1}
        por_escena = {c.scene: c.participantes for c in fuga.abandono_por_escena}
        assert por_escena == {3: 1, 7: 1}
        assert len(fuga.abandono_por_habilidad_y_etapa) == 1
        assert fuga.abandono_por_habilidad_y_etapa[0].habilidad == "meaning"
        assert fuga.abandono_por_habilidad_y_etapa[0].etapa == "concrete"

    @pytest.mark.asyncio
    async def test_banco_agotado_agrupa_por_habilidad_y_etapa(self):
        filas = [({"skill": "add_diff", "stage": "abstract"},), ({"skill": "add_diff", "stage": "abstract"},)]
        db = _DBCapturador([_ResultadoFlexible(filas=filas)])

        resultado = await luma_dashboard._banco_agotado(db)

        assert len(resultado) == 1
        assert resultado[0].habilidad == "add_diff"
        assert resultado[0].etapa == "abstract"
        assert resultado[0].veces == 2


class TestEmbudoFases:
    """Bug real hallado por el equipo contra datos reales: el embudo original
    contaba "quien tuvo algun evento en esa fase" y podia crecer (math > play),
    lo que no se puede leer como embudo. Ahora es ACUMULATIVO: cuenta quien llego
    AL MENOS hasta cada fase, segun la mas avanzada que alcanzo."""

    @pytest.mark.asyncio
    async def test_es_monotono_no_creciente_segun_la_fase_mas_avanzada(self):
        # Participantes: uno llego hasta 'play' (posicion 1), dos hasta 'math' (3).
        filas = [(1,), (3,), (3,)]
        db = _DBCapturador([_ResultadoFlexible(filas=filas)])

        embudo = await luma_dashboard._embudo_fases(db)
        por_fase = {c.fase: c.participantes for c in embudo}

        assert por_fase["welcome"] == 3  # los 3 llegaron al menos hasta welcome
        assert por_fase["play"] == 3
        assert por_fase["bridge"] == 2  # solo los 2 que llegaron a math pasaron por bridge
        assert por_fase["math"] == 2
        assert por_fase["complete"] == 0
        # Monotono no creciente:
        valores = [por_fase[fase] for fase in luma_dashboard.FASES_EMBUDO]
        assert all(valores[i] >= valores[i + 1] for i in range(len(valores) - 1))

    @pytest.mark.asyncio
    async def test_fase_desconocida_o_nula_no_cuenta_en_ninguna(self):
        filas = [(None,)]
        db = _DBCapturador([_ResultadoFlexible(filas=filas)])

        embudo = await luma_dashboard._embudo_fases(db)

        assert all(c.participantes == 0 for c in embudo)


class TestCasosDeSimulacion:
    """Team-lead pidio explicitamente un test de que simulation=true queda
    excluido de TODOS los agregados: cubierto arriba por TestFiltroSimulacion
    (verifica que el filtro esta presente en cada consulta SQL). Aqui se agrega
    un caso end-to-end sobre motivos_cierre con datos canned, para probar tambien
    el mapeo de resultados, no solo la presencia del filtro."""

    @pytest.mark.asyncio
    async def test_motivos_cierre_clasifica_filas_canned(self):
        filas = [
            (FASE_COMPLETA, "learning_path_completed"),
            (FASE_COMPLETA, "item_bank_exhausted"),
            ("playing", None),
        ]
        db = _DBCapturador([_ResultadoFlexible(filas=filas)])

        conteos = await luma_dashboard._motivos_cierre(db)
        por_motivo = {c.motivo: c.participantes for c in conteos}

        assert por_motivo[MOTIVO_FINAL_MASTERY] == 1
        assert por_motivo[MOTIVO_FINAL_BANK_EXHAUSTED] == 1
        assert por_motivo[luma_dashboard.MOTIVO_SIN_DATO] == 1
        assert por_motivo[MOTIVO_FINAL_BREAK] == 0
