"""Recepcion publica de telemetria de LumaSprout (abejorro.ai/luma).

Dos rutas: abrir o reanudar una partida, e ingerir un lote de sus eventos. Sin
cuentas: el juego se identifica por su `runId` (persistido en el navegador) y, una vez
abierta la partida, recibe un token opaco derivado por HMAC del propio runId (ver
`services/luma_service.calcular_token`) que autoriza a escribir SOLO en esa partida.

Los datos sinteticos del laboratorio (`simulation: true`) no entran aqui: es una
frontera de seguridad para no mezclar telemetria real de menores con pruebas de
carga, no una preferencia de reporting.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.luma import LumaSesion
from schemas.luma import LumaEventosEntrada, LumaEventosSalida, LumaSesionEntrada, LumaSesionSalida
from services.luma_service import abrir_o_reanudar_sesion, ingerir_eventos, token_valido_para

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/luma", tags=["luma"])
limiter = Limiter(key_func=get_remote_address)

RATE_LIMIT_SESION = "20/minute"
RATE_LIMIT_EVENTOS = "60/minute"

# El mismo criterio que protocolo42.py: se mide sobre el cuerpo real recibido, no
# sobre lo que declare el cliente.
MAXIMO_BYTES_LOTE = 1 * 1024 * 1024


@router.post(
    "/sesion",
    response_model=LumaSesionSalida,
    status_code=status.HTTP_200_OK,
    summary="Abrir o reanudar una partida de LumaSprout",
    description="Crea la partida si el runId es nuevo, o la reanuda devolviendo el mayor "
    "indice de evento ya recibido. Rechaza datos sinteticos (simulation=true).",
)
@limiter.limit(RATE_LIMIT_SESION)
async def abrir_sesion(
    request: Request,
    datos: LumaSesionEntrada,
    db: AsyncSession = Depends(get_db),
) -> LumaSesionSalida:
    if datos.simulation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los datos sinteticos (simulation=true) no se aceptan en este endpoint.",
        )
    return await abrir_o_reanudar_sesion(db, datos)


@router.post(
    "/eventos",
    response_model=LumaEventosSalida,
    status_code=status.HTTP_200_OK,
    summary="Ingerir un lote de eventos de una partida",
    description="Requiere el header X-Luma-Token obtenido en POST /sesion. La insercion es "
    "idempotente: reenviar el mismo lote tras un corte de red no duplica eventos.",
)
@limiter.limit(RATE_LIMIT_EVENTOS)
async def recibir_eventos(
    request: Request,
    datos: LumaEventosEntrada,
    db: AsyncSession = Depends(get_db),
    x_luma_token: str = Header(..., alias="X-Luma-Token"),
) -> LumaEventosSalida:
    largo = int(request.headers.get("content-length") or 0)
    if largo > MAXIMO_BYTES_LOTE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El lote de eventos excede el tamano permitido.",
        )

    # El token esta ligado criptograficamente al run_id: un token valido para otra
    # partida nunca pasa esta verificacion, sin necesidad de columna ni consulta.
    if not token_valido_para(datos.run_id, x_luma_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token no valido para esta partida.",
        )

    sesion = (
        await db.execute(select(LumaSesion).where(LumaSesion.run_id == datos.run_id))
    ).scalar_one_or_none()
    if sesion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay partida abierta para ese runId. Llama a POST /sesion primero.",
        )

    resultado = await ingerir_eventos(db, sesion, datos.eventos)
    logger.info(
        "Lote de eventos de LumaSprout procesado (run_id=%s, guardados=%s, duplicados=%s, rechazados=%s)",
        datos.run_id,
        resultado.guardados,
        resultado.duplicados,
        len(resultado.rechazados),
    )
    return resultado
