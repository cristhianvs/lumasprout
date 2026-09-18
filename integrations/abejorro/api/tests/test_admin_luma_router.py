"""Tests de los routers administrativos routers/admin_luma.py.

Todos los endpoints exigen `verify_admin`; la base de datos se mockea siempre
(via patch de las funciones de servicio), nunca se abre conexion real a Postgres.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.jwt_auth import create_jwt_token
from main import app
from models.luma import LumaEvento, LumaSesion
from routers import admin_luma
from schemas.luma import (
    LumaAyuda,
    LumaEstadoActual,
    LumaInactividad,
    LumaIntentos,
    LumaResumenSalida,
)
from schemas.luma_dashboard import (
    LumaHistoricoSalida,
    LumaPanoramaSalida,
    LumaPuntosDeFuga,
    LumaRetencion,
    LumaSeriesSalida,
)
from services.luma_service import _autonomia, _respuesta_ante_error, construir_progresion


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def token_admin() -> str:
    token, _expires_in = create_jwt_token("admin")
    return token


@pytest.fixture(autouse=True)
def _rate_limit_limpio():
    admin_luma.limiter.reset()
    yield
    admin_luma.limiter.reset()


ENDPOINTS_ADMIN = [
    ("GET", "/api/admin/luma/sesiones"),
    ("GET", f"/api/admin/luma/sesiones/{uuid4()}/eventos"),
    ("GET", f"/api/admin/luma/sesiones/{uuid4()}/resumen"),
    ("GET", "/api/admin/luma/panorama"),
    ("GET", "/api/admin/luma/series"),
    ("GET", f"/api/admin/luma/sesiones/{uuid4()}/historico"),
    ("GET", "/api/admin/luma/items"),
    ("GET", "/api/admin/luma/adaptacion"),
]


@pytest.mark.parametrize("metodo,ruta", ENDPOINTS_ADMIN)
def test_sin_token_es_rechazado_con_403(client: TestClient, metodo: str, ruta: str):
    response = client.request(metodo, ruta)
    assert response.status_code == 403


@pytest.mark.parametrize("metodo,ruta", ENDPOINTS_ADMIN)
def test_con_token_invalido_es_rechazado_con_401(client: TestClient, metodo: str, ruta: str):
    response = client.request(metodo, ruta, headers={"Authorization": "Bearer token-invalido"})
    assert response.status_code == 401


class TestListarSesiones:
    def test_con_token_valido_devuelve_200_con_antiguedad_calculada(self, client: TestClient, token_admin: str):
        hace_10s = datetime.now(UTC)
        fila = LumaSesion(
            id=uuid4(),
            run_id=uuid4(),
            participante_codigo="ana01",
            version="1.0",
            schema_version="1.0",
            policy_version="cpa-1",
            simulation=False,
            total_eventos=5,
            ultima_recepcion_at=hace_10s,
        )

        with patch("routers.admin_luma.listar_sesiones", new=AsyncMock(return_value=([fila], 1))):
            response = client.get(
                "/api/admin/luma/sesiones",
                headers={"Authorization": f"Bearer {token_admin}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["sesiones"]) == 1
        assert data["sesiones"][0]["antiguedad_segundos"] >= 0


class TestListarEventos:
    def test_sesion_inexistente_devuelve_404(self, client: TestClient, token_admin: str):
        with patch("routers.admin_luma._obtener_sesion_o_404", new=AsyncMock(side_effect=__import__("fastapi").HTTPException(status_code=404))):
            response = client.get(
                f"/api/admin/luma/sesiones/{uuid4()}/eventos",
                headers={"Authorization": f"Bearer {token_admin}"},
            )
        assert response.status_code == 404

    def test_devuelve_eventos_con_secuencia_mayor_a_desde(self, client: TestClient, token_admin: str):
        sesion = LumaSesion(id=uuid4(), run_id=uuid4(), version="1.0", schema_version="1.0", policy_version="cpa-1")
        evento = LumaEvento(
            id=uuid4(),
            sesion_id=sesion.id,
            evento_id="s:5",
            session_carga=uuid4(),
            secuencia=5,
            tipo="attempt",
            at_cliente=datetime.now(UTC),
            recibido_at=datetime.now(UTC),
            data={"id": "s:5", "type": "attempt"},
        )

        with (
            patch("routers.admin_luma._obtener_sesion_o_404", new=AsyncMock(return_value=sesion)),
            patch("routers.admin_luma.listar_eventos", new=AsyncMock(return_value=[evento])),
        ):
            response = client.get(
                f"/api/admin/luma/sesiones/{sesion.run_id}/eventos?desde=3",
                headers={"Authorization": f"Bearer {token_admin}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["ultimo_indice"] == 5
        assert len(data["eventos"]) == 1
        assert data["eventos"][0]["secuencia"] == 5

    def test_limite_por_encima_del_maximo_es_rechazado(self, client: TestClient, token_admin: str):
        response = client.get(
            f"/api/admin/luma/sesiones/{uuid4()}/eventos?limite=5000",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 422


class TestResumen:
    def test_devuelve_el_resumen_construido_por_el_servicio(self, client: TestClient, token_admin: str):
        sesion = LumaSesion(id=uuid4(), run_id=uuid4(), version="1.0", schema_version="1.0", policy_version="cpa-1")
        resumen_falso = LumaResumenSalida(
            run_id=sesion.run_id,
            estado_actual=LumaEstadoActual(
                phase="p1",
                scene=1,
                task="t1",
                experience="e1",
                heartbeat_reciente=True,
                limite_heartbeat="ausencia no implica inactividad",
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
            progresion=construir_progresion([]),
            respuesta_ante_error=_respuesta_ante_error([]),
            autonomia=_autonomia([]),
        )

        with (
            patch("routers.admin_luma._obtener_sesion_o_404", new=AsyncMock(return_value=sesion)),
            patch("routers.admin_luma.listar_eventos", new=AsyncMock(return_value=[])),
            patch("routers.admin_luma.construir_resumen", return_value=resumen_falso),
        ):
            response = client.get(
                f"/api/admin/luma/sesiones/{sesion.run_id}/resumen",
                headers={"Authorization": f"Bearer {token_admin}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["estado_actual"]["heartbeat_reciente"] is True
        assert "limite_latencia" in data["intentos"]
        assert "limite" in data["inactividad"]


class TestPanorama:
    def test_delega_al_servicio(self, client: TestClient, token_admin: str):
        panorama_falso = LumaPanoramaSalida(
            generado=datetime.now(UTC),
            sesiones_total=5,
            participantes_total=3,
            eventos_total=100,
            sesiones_por_dia=[],
            embudo_fases=[],
            motivos_cierre=[],
            modalidades=[],
            retencion=LumaRetencion(
                con_una_sesion=2, con_dos_sesiones=1, con_tres_o_mas_sesiones=0, mediana_dias_entre_sesiones=None
            ),
            puntos_de_fuga=LumaPuntosDeFuga(
                abandono_por_fase=[], abandono_por_escena=[], abandono_por_habilidad_y_etapa=[], banco_agotado=[]
            ),
        )

        with patch("routers.admin_luma.obtener_panorama", new=AsyncMock(return_value=panorama_falso)):
            response = client.get(
                "/api/admin/luma/panorama",
                headers={"Authorization": f"Bearer {token_admin}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["sesiones_total"] == 5
        assert data["participantes_total"] == 3


class TestSeries:
    def test_delega_al_servicio_con_dias_por_defecto(self, client: TestClient, token_admin: str):
        series_falsa = LumaSeriesSalida(generado=datetime.now(UTC), dias=30, serie=[])
        mock_servicio = AsyncMock(return_value=series_falsa)

        with patch("routers.admin_luma.obtener_series", new=mock_servicio):
            response = client.get(
                "/api/admin/luma/series",
                headers={"Authorization": f"Bearer {token_admin}"},
            )

        assert response.status_code == 200
        assert response.json()["dias"] == 30
        mock_servicio.assert_awaited_once()
        _db_arg, dias_arg = mock_servicio.await_args.args
        assert dias_arg == 30

    def test_dias_fuera_de_rango_es_rechazado(self, client: TestClient, token_admin: str):
        headers = {"Authorization": f"Bearer {token_admin}"}

        cero = client.get("/api/admin/luma/series?dias=0", headers=headers)
        excesivo = client.get("/api/admin/luma/series?dias=400", headers=headers)

        assert cero.status_code == 422
        assert excesivo.status_code == 422

    def test_dias_personalizado_se_pasa_al_servicio(self, client: TestClient, token_admin: str):
        series_falsa = LumaSeriesSalida(generado=datetime.now(UTC), dias=7, serie=[])
        mock_servicio = AsyncMock(return_value=series_falsa)

        with patch("routers.admin_luma.obtener_series", new=mock_servicio):
            response = client.get(
                "/api/admin/luma/series?dias=7",
                headers={"Authorization": f"Bearer {token_admin}"},
            )

        assert response.status_code == 200
        _db_arg, dias_arg = mock_servicio.await_args.args
        assert dias_arg == 7


class TestHistorico:
    def test_sesion_inexistente_devuelve_404(self, client: TestClient, token_admin: str):
        with patch(
            "routers.admin_luma._obtener_sesion_o_404",
            new=AsyncMock(side_effect=__import__("fastapi").HTTPException(status_code=404)),
        ):
            response = client.get(
                f"/api/admin/luma/sesiones/{uuid4()}/historico",
                headers={"Authorization": f"Bearer {token_admin}"},
            )
        assert response.status_code == 404

    def test_delega_al_servicio(self, client: TestClient, token_admin: str):
        sesion = LumaSesion(id=uuid4(), run_id=uuid4(), version="1.0", schema_version="1.0", policy_version="cpa-1")
        historico_falso = LumaHistoricoSalida(
            run_id=sesion.run_id, sesiones=[], progresion_temporal=[], bayesiano_temporal=[]
        )

        with (
            patch("routers.admin_luma._obtener_sesion_o_404", new=AsyncMock(return_value=sesion)),
            patch("routers.admin_luma.obtener_historico", new=AsyncMock(return_value=historico_falso)),
        ):
            response = client.get(
                f"/api/admin/luma/sesiones/{sesion.run_id}/historico",
                headers={"Authorization": f"Bearer {token_admin}"},
            )

        assert response.status_code == 200
        assert response.json()["run_id"] == str(sesion.run_id)


class TestItems:
    def test_delega_al_servicio(self, client: TestClient, token_admin: str):
        from schemas.luma_items import LumaItemsSalida

        items_falso = LumaItemsSalida(generado=datetime.now(UTC), items=[])

        with patch("routers.admin_luma.obtener_items", new=AsyncMock(return_value=items_falso)):
            response = client.get(
                "/api/admin/luma/items",
                headers={"Authorization": f"Bearer {token_admin}"},
            )

        assert response.status_code == 200
        assert response.json()["items"] == []
        assert "umbral_muestra_suficiente" in response.json()


class TestAdaptacion:
    def test_delega_al_servicio(self, client: TestClient, token_admin: str):
        from schemas.luma_items import (
            LumaAdaptacionSalida,
            LumaEfectoAndamiaje,
            LumaOportunidadesIndependientes,
        )

        adaptacion_falsa = LumaAdaptacionSalida(
            generado=datetime.now(UTC),
            por_razon_decision=[],
            por_regla_mid_reto=[],
            efecto_del_andamiaje=LumaEfectoAndamiaje(
                tasa_acierto_con_andamiaje=None,
                presentaciones_con_andamiaje=0,
                tasa_acierto_sin_andamiaje=None,
                presentaciones_sin_andamiaje=0,
                muestra_suficiente=False,
            ),
            oportunidades_independientes=LumaOportunidadesIndependientes(
                total=0, resueltas_independientemente=0, muestra_suficiente=False
            ),
        )

        with patch("routers.admin_luma.obtener_adaptacion", new=AsyncMock(return_value=adaptacion_falsa)):
            response = client.get(
                "/api/admin/luma/adaptacion",
                headers={"Authorization": f"Bearer {token_admin}"},
            )

        assert response.status_code == 200
        assert response.json()["por_razon_decision"] == []
