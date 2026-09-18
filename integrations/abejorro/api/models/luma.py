"""Telemetria de LumaSprout.

El juego (abejorro.ai/luma) emite eventos de juego (attempt, hint_requested,
adaptation_decision, heartbeat, etc, unos 60 tipos distintos). Cada carga de pagina
genera un UUID de "session" que se descarta al cerrar; lo que persiste entre sesiones
del mismo nino es el "runId", el hilo continuo de una partida.

Dos tablas:

- LumaSesion: una fila por runId. Es el resumen/estado de una partida completa.
- LumaEvento: el diario append-only de eventos. Nunca se actualiza ni se borra fila a
  fila; solo se inserta. El id de cada evento (formato "{session}:{indice}") junto con
  la sesion a la que pertenece forman la clave de idempotencia: si el juego reenvia un
  lote tras un corte de red, la insercion debe hacerse con ON CONFLICT (sesion_id,
  evento_id) DO NOTHING para no duplicar filas.

LumaEvento NO hereda BaseModel a proposito: BaseModel trae un updated_at con
onupdate=func.now(), que no tiene sentido en una tabla de solo insercion. En su lugar
declara su propio id UUID y un unico timestamp de servidor, recibido_at.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUuid  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import BaseModel


class LumaSesion(BaseModel):
    """Una fila por partida (runId). Resumen de una partida entera del nino."""

    __tablename__ = "luma_sesiones"

    # UUID persistido por el juego entre sesiones del navegador. Es el hilo continuo
    # de la partida, a diferencia del UUID de "session" que se regenera en cada carga.
    run_id: Mapped[UUID] = mapped_column(
        PgUuid(as_uuid=True),
        nullable=False,
        unique=True,
        index=True,
    )

    # Seudonimo corto que teclea el nino o su tutor. Nunca un nombre real: no es un
    # dato personal identificable por si solo. Nulo hasta que el juego lo asigne.
    participante_codigo: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # Version del juego, del esquema del evento y de la politica de adaptacion,
    # p.ej. '2026-09-prototype-1', '1.4', 'cpa-2'. Se guardan tal cual llegan.
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Distingue datos sinteticos (QA, pruebas de carga) de partidas de participantes
    # reales. Es el primer filtro de cualquier panel o reporte: nunca deben mezclarse.
    simulation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Reloj del CLIENTE: cuando ocurrio el primer y el ultimo evento recibido.
    primer_evento_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ultimo_evento_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Reloj del SERVIDOR: cuando llego el ultimo lote. Es lo que permite mostrar
    # "hace cuanto que no sabemos de este nino" sin depender del reloj del cliente.
    ultima_recepcion_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
    )

    total_eventos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        # Consulta: "que sesiones han recibido datos recientemente", casi siempre
        # filtrando primero por simulation = false. El indice ascendente sirve tanto
        # para ORDER BY ultima_recepcion_at ASC como DESC (Postgres puede recorrerlo
        # hacia atras), asi que no hace falta declarar un indice DESC aparte.
        # Esta misma columna compuesta cubre tambien un filtro de solo "simulation",
        # por eso no se agrega un indice separado para esa columna.
        Index("ix_luma_sesiones_simulation_recepcion", "simulation", "ultima_recepcion_at"),
    )

    def __repr__(self) -> str:
        return f"<LumaSesion(run_id={self.run_id}, simulation={self.simulation})>"


class LumaEvento(Base):
    """Diario append-only de eventos de una partida. No se actualiza ni se borra."""

    __tablename__ = "luma_eventos"

    id: Mapped[UUID] = mapped_column(
        PgUuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )

    sesion_id: Mapped[UUID] = mapped_column(
        PgUuid(as_uuid=True),
        ForeignKey("luma_sesiones.id", ondelete="CASCADE"),
        nullable=False,
    )

    # El "id" del evento tal cual lo genera el juego: "{session}:{indice}". Junto con
    # sesion_id es la clave de idempotencia (ver restriccion unique mas abajo).
    evento_id: Mapped[str] = mapped_column(String(80), nullable=False)

    # UUID de la carga de pagina que genero el evento. El juego lo descarta al
    # cerrar la pestana; aqui se guarda solo como dato de diagnostico.
    session_carga: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)

    # Indice correlativo dentro de la partida, extraido del evento_id. Permite
    # ordenar sin depender del reloj del cliente y detectar huecos en la secuencia.
    secuencia: Mapped[int] = mapped_column(Integer, nullable=False)

    tipo: Mapped[str] = mapped_column(String(50), nullable=False)

    # Reloj del CLIENTE, tal como lo reporta el evento.
    at_cliente: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Reloj del SERVIDOR, cuando la API recibio el evento.
    recibido_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Columnas desnormalizadas a proposito: el panel filtra por estas sin tener que
    # abrir el JSONB de "data". No todos los tipos de evento las traen, por eso
    # son nulas.
    phase: Mapped[str | None] = mapped_column(String(50), nullable=True)
    scene: Mapped[int | None] = mapped_column(Integer, nullable=True)
    task: Mapped[str | None] = mapped_column(String(100), nullable=True)
    experience: Mapped[str | None] = mapped_column(String(50), nullable=True)

    play_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    math_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Cuerpo libre del evento, distinto por tipo. Sin indice GIN por ahora: todavia
    # no hay una consulta real que filtre dentro de este JSON (las tres consultas
    # conocidas del panel se resuelven con las columnas desnormalizadas de arriba),
    # y un GIN aqui encarece cada insercion en una tabla que va a recibir cientos de
    # miles de filas. Se agrega el dia que aparezca una consulta concreta que lo
    # necesite.
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        # Idempotencia: si el juego reenvia un lote tras un corte de red, el mismo
        # evento no se puede guardar dos veces. La insercion debe usar
        # ON CONFLICT (sesion_id, evento_id) DO NOTHING.
        # Esta restriccion tambien sirve como indice para consultas que solo
        # filtran por sesion_id (es la columna izquierda), asi que no se agrega un
        # indice separado para esa columna.
        Index("ix_luma_eventos_sesion_evento", "sesion_id", "evento_id", unique=True),
        # Consulta: "los ultimos N eventos de esta sesion, en orden".
        Index("ix_luma_eventos_sesion_secuencia", "sesion_id", "secuencia"),
        # Consulta: "los eventos de tipo X de esta sesion" (p.ej. adaptation_decision).
        Index("ix_luma_eventos_sesion_tipo", "sesion_id", "tipo"),
    )

    def __repr__(self) -> str:
        return f"<LumaEvento(sesion_id={self.sesion_id}, tipo={self.tipo}, secuencia={self.secuencia})>"
