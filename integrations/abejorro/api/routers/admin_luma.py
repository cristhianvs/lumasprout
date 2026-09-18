"""Panel administrativo de telemetria de LumaSprout.

Solo lectura, y TODOS los endpoints exigen `verify_admin` (JWT de administrador) sin
excepciones: son datos de partidas de menores, y la autorizacion no es un adorno.

`GET /sesiones/{run_id}/eventos` es el endpoint que el panel llama cada 2-3 segundos
mientras alguien observa una partida en vivo: se apoya en el indice
(sesion_id, secuencia) y no recalcula nada, a diferencia de `resumen`, que si agrega
sobre el historial completo y esta pensado para refrescarse con menos frecuencia.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_admin
from database import get_db
from models.luma import LumaSesion
from schemas.luma import (
    LumaEventoAdminSalida,
    LumaEventosListaSalida,
    LumaResumenSalida,
    LumaSesionAdminSalida,
    LumaSesionesListaSalida,
)
from schemas.luma_dashboard import (
    DIAS_SERIES_DEFECTO,
    DIAS_SERIES_MAXIMO,
    LumaHistoricoSalida,
    LumaPanoramaSalida,
    LumaSeriesSalida,
)
from schemas.luma_items import LumaAdaptacionSalida, LumaItemsSalida
from services.luma_dashboard import obtener_historico, obtener_panorama, obtener_series
from services.luma_items import obtener_adaptacion, obtener_items
from services.luma_service import (
    LIMITE_EVENTOS_RESUMEN,
    construir_resumen,
    listar_eventos,
    listar_sesiones,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/luma", tags=["admin"])
limiter = Limiter(key_func=get_remote_address)

RATE_LIMIT_SESIONES = "30/minute"
RATE_LIMIT_EVENTOS = "120/minute"
RATE_LIMIT_RESUMEN = "20/minute"
RATE_LIMIT_PANORAMA = "10/minute"
RATE_LIMIT_SERIES = "10/minute"
RATE_LIMIT_HISTORICO = "20/minute"
RATE_LIMIT_ITEMS = "10/minute"
RATE_LIMIT_ADAPTACION = "10/minute"

PAGINA_DEFECTO = 1
TAMANO_PAGINA_DEFECTO = 20
TAMANO_PAGINA_MAXIMO = 100

DESDE_DEFECTO = -1
LIMITE_EVENTOS_DEFECTO = 200
LIMITE_EVENTOS_MAXIMO = 1000


async def _obtener_sesion_o_404(db: AsyncSession, run_id: UUID) -> LumaSesion:
    sesion = (await db.execute(select(LumaSesion).where(LumaSesion.run_id == run_id))).scalar_one_or_none()
    if sesion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe esa partida.")
    return sesion


@router.get(
    "/sesiones",
    response_model=LumaSesionesListaSalida,
    status_code=status.HTTP_200_OK,
    summary="Listar partidas de LumaSprout (admin)",
    description="Partidas reales (simulation=false), ordenadas por ultima recepcion descendente.",
)
@limiter.limit(RATE_LIMIT_SESIONES)
async def listar_sesiones_admin(
    request: Request,
    pagina: int = Query(default=PAGINA_DEFECTO, ge=1),
    tamano_pagina: int = Query(default=TAMANO_PAGINA_DEFECTO, ge=1, le=TAMANO_PAGINA_MAXIMO),
    username: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
) -> LumaSesionesListaSalida:
    filas, total = await listar_sesiones(db, pagina, tamano_pagina)
    ahora = datetime.now(UTC)

    sesiones = [
        LumaSesionAdminSalida(
            run_id=fila.run_id,
            participante_codigo=fila.participante_codigo,
            version=fila.version,
            total_eventos=fila.total_eventos,
            primer_evento_at=fila.primer_evento_at,
            ultimo_evento_at=fila.ultimo_evento_at,
            ultima_recepcion_at=fila.ultima_recepcion_at,
            antiguedad_segundos=(
                (ahora - fila.ultima_recepcion_at).total_seconds()
                if fila.ultima_recepcion_at is not None
                else None
            ),
        )
        for fila in filas
    ]
    logger.info("Listado de partidas de LumaSprout servido (usuario=%s, pagina=%s)", username, pagina)
    return LumaSesionesListaSalida(sesiones=sesiones, total=total, pagina=pagina, tamano_pagina=tamano_pagina)


@router.get(
    "/sesiones/{run_id}/eventos",
    response_model=LumaEventosListaSalida,
    status_code=status.HTTP_200_OK,
    summary="Eventos nuevos de una partida (admin)",
    description="Eventos con secuencia > desde, en orden ascendente. Pensado para pollear "
    "cada 2-3 segundos mientras se observa una partida en vivo.",
)
@limiter.limit(RATE_LIMIT_EVENTOS)
async def listar_eventos_admin(
    request: Request,
    run_id: UUID,
    desde: int = Query(default=DESDE_DEFECTO, ge=-1),
    limite: int = Query(default=LIMITE_EVENTOS_DEFECTO, ge=1, le=LIMITE_EVENTOS_MAXIMO),
    username: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
) -> LumaEventosListaSalida:
    sesion = await _obtener_sesion_o_404(db, run_id)
    eventos = await listar_eventos(db, sesion.id, desde, limite)
    ultimo_indice = eventos[-1].secuencia if eventos else desde
    return LumaEventosListaSalida(
        eventos=[LumaEventoAdminSalida.model_validate(evento) for evento in eventos],
        ultimo_indice=ultimo_indice,
    )


@router.get(
    "/sesiones/{run_id}/resumen",
    response_model=LumaResumenSalida,
    status_code=status.HTTP_200_OK,
    summary="Resumen derivado de una partida (admin)",
    description="Estado actual, conteos por tipo, intentos, ayuda, inactividad y decisiones "
    "de adaptacion. No infiere estados emocionales ni produce etiquetas clinicas.",
)
@limiter.limit(RATE_LIMIT_RESUMEN)
async def resumen_admin(
    request: Request,
    run_id: UUID,
    username: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
) -> LumaResumenSalida:
    sesion = await _obtener_sesion_o_404(db, run_id)
    eventos = await listar_eventos(db, sesion.id, DESDE_DEFECTO, LIMITE_EVENTOS_RESUMEN)
    logger.info("Resumen de partida de LumaSprout servido (usuario=%s, run_id=%s)", username, run_id)
    return construir_resumen(run_id, eventos)


@router.get(
    "/panorama",
    response_model=LumaPanoramaSalida,
    status_code=status.HTTP_200_OK,
    summary="Vision de conjunto del estudio (admin)",
    description="Totales, actividad por dia, embudo de fases, motivos de cierre, modalidades "
    "y retencion. Agregado sobre partidas reales (simulation=false).",
)
@limiter.limit(RATE_LIMIT_PANORAMA)
async def panorama_admin(
    request: Request,
    username: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
) -> LumaPanoramaSalida:
    logger.info("Panorama de LumaSprout servido (usuario=%s)", username)
    return await obtener_panorama(db)


@router.get(
    "/series",
    response_model=LumaSeriesSalida,
    status_code=status.HTTP_200_OK,
    summary="Evolucion agregada en el tiempo (admin)",
    description="Una entrada por dia (independencia, respuesta ante error, ayuda, casillas "
    "acreditadas, tiempo activo e inactividad). Dias sin datos se devuelven con ceros/nulos "
    "explicitos, no se omiten.",
)
@limiter.limit(RATE_LIMIT_SERIES)
async def series_admin(
    request: Request,
    dias: int = Query(default=DIAS_SERIES_DEFECTO, ge=1, le=DIAS_SERIES_MAXIMO),
    username: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
) -> LumaSeriesSalida:
    logger.info("Series de LumaSprout servidas (usuario=%s, dias=%s)", username, dias)
    return await obtener_series(db, dias)


@router.get(
    "/sesiones/{run_id}/historico",
    response_model=LumaHistoricoSalida,
    status_code=status.HTTP_200_OK,
    summary="Evolucion de un participante en el tiempo (admin)",
    description="Sus sesiones de juego en orden cronologico, cuando acredito cada casilla CPA "
    "y la evolucion de su estado bayesiano por habilidad.",
)
@limiter.limit(RATE_LIMIT_HISTORICO)
async def historico_admin(
    request: Request,
    run_id: UUID,
    username: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
) -> LumaHistoricoSalida:
    sesion = await _obtener_sesion_o_404(db, run_id)
    logger.info("Historico de LumaSprout servido (usuario=%s, run_id=%s)", username, run_id)
    return await obtener_historico(db, sesion)


@router.get(
    "/items",
    response_model=LumaItemsSalida,
    status_code=status.HTTP_200_OK,
    summary="Analisis por item/tarea, agregando todos los participantes (admin)",
    description="Dificultad empirica, intentos, ayuda, abandonos, patrones de error y errores "
    "de interfaz por cada combinacion habilidad+etapa+variantId. Describe al JUEGO, no al nino.",
)
@limiter.limit(RATE_LIMIT_ITEMS)
async def items_admin(
    request: Request,
    username: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
) -> LumaItemsSalida:
    logger.info("Analisis de items de LumaSprout servido (usuario=%s)", username)
    return await obtener_items(db)


@router.get(
    "/adaptacion",
    response_model=LumaAdaptacionSalida,
    status_code=status.HTTP_200_OK,
    summary="Evaluacion del algoritmo de adaptacion (admin)",
    description="Que paso despues de cada decision del motor (por razon y por regla dentro del "
    "reto), efecto real del andamiaje y de las oportunidades de resolucion independiente. "
    "Evalua al ALGORITMO, no al nino.",
)
@limiter.limit(RATE_LIMIT_ADAPTACION)
async def adaptacion_admin(
    request: Request,
    username: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
) -> LumaAdaptacionSalida:
    logger.info("Evaluacion de adaptacion de LumaSprout servida (usuario=%s)", username)
    return await obtener_adaptacion(db)
