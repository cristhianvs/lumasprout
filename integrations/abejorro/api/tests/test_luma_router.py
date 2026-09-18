"""Tests de los routers publicos routers/luma.py.

La base de datos se mockea siempre (via dependency_overrides de get_db o parcheando
la funcion de servicio que la usa): estos tests no abren conexion real a Postgres.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from database import get_db
from main import app
from models.luma import LumaSesion
from routers import luma
from schemas.luma import LumaEventosSalida, LumaSesionSalida
from services.luma_service import calcular_token

MAXIMO_EVENTOS_POR_LOTE = 200


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _rate_limit_limpio():
    luma.limiter.reset()
    yield
    luma.limiter.reset()
    app.dependency_overrides.pop(get_db, None)


def _evento_valido(session_id, indice: int = 1) -> dict:
    return {
        "id": f"{session_id}:{indice}",
        "type": "attempt",
        "at": "2026-09-17T10:00:00Z",
        "session": str(session_id),
        "data": {"attemptNumber": 1, "assisted": False},
    }


def _override_get_db(mock_db):
    async def _generador():
        yield mock_db

    app.dependency_overrides[get_db] = _generador


class TestAbrirSesion:
    def test_simulation_true_es_rechazado_con_403_sin_tocar_la_bd(self, client: TestClient):
        with patch("routers.luma.abrir_o_reanudar_sesion", new=AsyncMock()) as servicio:
            response = client.post(
                "/api/luma/sesion",
                json={
                    "runId": str(uuid4()),
                    "version": "1.0",
                    "schemaVersion": "1.0",
                    "policyVersion": "cpa-1",
                    "simulation": True,
                },
            )

        assert response.status_code == 403
        servicio.assert_not_awaited()

    def test_sesion_valida_delega_al_servicio(self, client: TestClient):
        run_id = uuid4()
        mock_servicio = AsyncMock(
            return_value=LumaSesionSalida(token="abc123", ultimoIndice=-1, ultimoEventoId=None)
        )
        with patch("routers.luma.abrir_o_reanudar_sesion", new=mock_servicio):
            response = client.post(
                "/api/luma/sesion",
                json={
                    "runId": str(run_id),
                    "version": "1.0",
                    "schemaVersion": "1.0",
                    "policyVersion": "cpa-1",
                    "simulation": False,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["token"] == "abc123"
        assert data["ultimoIndice"] == -1
        assert data["ultimoEventoId"] is None
        mock_servicio.assert_awaited_once()


class TestRecibirEventos:
    def test_falta_header_token_devuelve_422(self, client: TestClient):
        response = client.post(
            "/api/luma/eventos",
            json={"runId": str(uuid4()), "eventos": [_evento_valido(uuid4())]},
        )
        assert response.status_code == 422

    def test_lote_de_mas_de_200_eventos_es_rechazado(self, client: TestClient):
        session_id = uuid4()
        eventos = [_evento_valido(session_id, i) for i in range(MAXIMO_EVENTOS_POR_LOTE + 1)]

        response = client.post(
            "/api/luma/eventos",
            json={"runId": str(uuid4()), "eventos": eventos},
            headers={"X-Luma-Token": "cualquier-cosa"},
        )

        assert response.status_code == 422

    def test_token_de_otra_partida_es_rechazado_con_403(self, client: TestClient):
        run_id_real = uuid4()
        run_id_ajeno = uuid4()
        token_ajeno = calcular_token(run_id_ajeno)

        response = client.post(
            "/api/luma/eventos",
            json={"runId": str(run_id_real), "eventos": [_evento_valido(uuid4())]},
            headers={"X-Luma-Token": token_ajeno},
        )

        assert response.status_code == 403

    def test_sesion_inexistente_devuelve_404(self, client: TestClient):
        run_id = uuid4()
        token = calcular_token(run_id)

        mock_db = AsyncMock()
        resultado = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        mock_db.execute = AsyncMock(return_value=resultado)
        _override_get_db(mock_db)

        response = client.post(
            "/api/luma/eventos",
            json={"runId": str(run_id), "eventos": [_evento_valido(uuid4())]},
            headers={"X-Luma-Token": token},
        )

        assert response.status_code == 404

    def test_lote_valido_delega_al_servicio_y_devuelve_su_resultado(self, client: TestClient):
        run_id = uuid4()
        token = calcular_token(run_id)
        sesion_falsa = LumaSesion(id=uuid4(), run_id=run_id, version="1.0", schema_version="1.0", policy_version="cpa-1")

        mock_db = AsyncMock()
        resultado = MagicMock(scalar_one_or_none=MagicMock(return_value=sesion_falsa))
        mock_db.execute = AsyncMock(return_value=resultado)
        _override_get_db(mock_db)

        mock_servicio = AsyncMock(
            return_value=LumaEventosSalida(
                guardados=1, duplicados=0, ultimoIndice=0, ultimoEventoId="abc:0", rechazados=[]
            )
        )
        with patch("routers.luma.ingerir_eventos", new=mock_servicio):
            response = client.post(
                "/api/luma/eventos",
                json={"runId": str(run_id), "eventos": [_evento_valido(uuid4())]},
                headers={"X-Luma-Token": token},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["guardados"] == 1
        assert data["duplicados"] == 0
        assert data["ultimoIndice"] == 0
        assert data["ultimoEventoId"] == "abc:0"
        mock_servicio.assert_awaited_once()

    def test_rate_limit_devuelve_429_al_superar_el_limite(self, client: TestClient):
        limite_por_minuto = int(luma.RATE_LIMIT_EVENTOS.split("/")[0])
        run_id_ajeno = uuid4()
        token_ajeno = calcular_token(run_id_ajeno)
        payload = {"runId": str(uuid4()), "eventos": [_evento_valido(uuid4())]}

        respuestas = [
            client.post("/api/luma/eventos", json=payload, headers={"X-Luma-Token": token_ajeno})
            for _ in range(limite_por_minuto)
        ]
        extra = client.post("/api/luma/eventos", json=payload, headers={"X-Luma-Token": token_ajeno})

        # Todas las anteriores fueron rechazadas por token invalido (403); la que
        # excede el limite debe ser 429 independientemente de la validez del token.
        assert all(r.status_code == 403 for r in respuestas)
        assert extra.status_code == 429
