"""add luma telemetria tables

Telemetria del juego educativo LumaSprout (abejorro.ai/luma). Dos tablas nuevas:

- luma_sesiones: una fila por partida (runId).
- luma_eventos: diario append-only de eventos de juego, con clave de idempotencia
  unica (sesion_id, evento_id) para poder reinsertar con ON CONFLICT DO NOTHING
  cuando el juego reenvia un lote tras un corte de red.

Esta migracion es puramente aditiva: solo CREATE TABLE y CREATE INDEX. No toca
ninguna tabla existente (quotes, contacts, blog_posts, podcasts, protocolo42_partidas).

Revision ID: 004
Revises: 003
Create Date: 2026-09-17 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '004'
down_revision: str | None = '003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'luma_sesiones',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('participante_codigo', sa.String(length=40), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('schema_version', sa.String(length=50), nullable=False),
        sa.Column('policy_version', sa.String(length=50), nullable=False),
        sa.Column('simulation', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('primer_evento_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ultimo_evento_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ultima_recepcion_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('total_eventos', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_luma_sesiones_run_id', 'luma_sesiones', ['run_id'], unique=True)
    op.create_index('ix_luma_sesiones_created_at', 'luma_sesiones', ['created_at'])
    # Consulta del panel: "que sesiones han recibido datos recientemente", casi
    # siempre filtrando primero por simulation = false. Un indice ascendente sirve
    # tanto para ORDER BY ultima_recepcion_at ASC como DESC (Postgres puede
    # recorrerlo hacia atras), asi que no hace falta un indice DESC aparte. La misma
    # columna compuesta cubre tambien un filtro de solo "simulation" (columna
    # izquierda), por eso no se crea un indice separado para esa columna.
    op.create_index(
        'ix_luma_sesiones_simulation_recepcion',
        'luma_sesiones',
        ['simulation', 'ultima_recepcion_at'],
    )

    op.create_table(
        'luma_eventos',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sesion_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('evento_id', sa.String(length=80), nullable=False),
        sa.Column('session_carga', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('secuencia', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=50), nullable=False),
        sa.Column('at_cliente', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recibido_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('phase', sa.String(length=50), nullable=True),
        sa.Column('scene', sa.Integer(), nullable=True),
        sa.Column('task', sa.String(length=100), nullable=True),
        sa.Column('experience', sa.String(length=50), nullable=True),
        sa.Column('play_ms', sa.Integer(), nullable=True),
        sa.Column('math_ms', sa.Integer(), nullable=True),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(['sesion_id'], ['luma_sesiones.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    # Idempotencia: si el juego reenvia un lote tras un corte de red, el mismo
    # evento no puede guardarse dos veces. La insercion debe usar
    # ON CONFLICT (sesion_id, evento_id) DO NOTHING. Esta restriccion unique tambien
    # sirve como indice para consultas que solo filtran por sesion_id (columna
    # izquierda), por eso no se crea un indice separado para esa columna.
    op.create_index(
        'ix_luma_eventos_sesion_evento',
        'luma_eventos',
        ['sesion_id', 'evento_id'],
        unique=True,
    )
    # Consulta del panel: "los ultimos N eventos de esta sesion, en orden".
    op.create_index('ix_luma_eventos_sesion_secuencia', 'luma_eventos', ['sesion_id', 'secuencia'])
    # Consulta del panel: "los eventos de tipo X de esta sesion" (p.ej. adaptation_decision).
    op.create_index('ix_luma_eventos_sesion_tipo', 'luma_eventos', ['sesion_id', 'tipo'])


def downgrade() -> None:
    op.drop_index('ix_luma_eventos_sesion_tipo', table_name='luma_eventos')
    op.drop_index('ix_luma_eventos_sesion_secuencia', table_name='luma_eventos')
    op.drop_index('ix_luma_eventos_sesion_evento', table_name='luma_eventos')
    op.drop_table('luma_eventos')

    op.drop_index('ix_luma_sesiones_simulation_recepcion', table_name='luma_sesiones')
    op.drop_index('ix_luma_sesiones_created_at', table_name='luma_sesiones')
    op.drop_index('ix_luma_sesiones_run_id', table_name='luma_sesiones')
    op.drop_table('luma_sesiones')
