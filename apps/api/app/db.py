import os
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import JSON, Boolean, ForeignKey, Integer, LargeBinary, String, UniqueConstraint, create_engine, inspect, text, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def uid() -> str:
    return uuid4().hex


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String(20), default='farmer', server_default='farmer')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text('true'))
    __table_args__ = (UniqueConstraint('email', name='uq_users_email'), UniqueConstraint('phone', name='uq_users_phone'))


class SignupIdentity(Base):
    __tablename__ = 'signup_identities'

    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    gender: Mapped[str] = mapped_column(String(6))
    encrypted_details: Mapped[bytes] = mapped_column(LargeBinary)
    encrypted_photo: Mapped[bytes] = mapped_column(LargeBinary)


class Token(Base):
    __tablename__ = 'sessions'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    expires: Mapped[str] = mapped_column(String)


class Record(Base):
    """Versioned domain document; ownership, plot, farm and source links are relational columns."""
    __tablename__ = 'records'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    kind: Mapped[str] = mapped_column(String, index=True)
    plot_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    farm_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    source_record_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[str] = mapped_column(String, default=now)
    updated_at: Mapped[str | None] = mapped_column(String, nullable=True, default=now)
    payload: Mapped[dict] = mapped_column(JSON)


class Reading(Base):
    __tablename__ = 'sensor_readings'
    __table_args__ = (UniqueConstraint('device_id', 'event_id'),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    device_id: Mapped[str] = mapped_column(ForeignKey('records.id'))
    event_id: Mapped[str] = mapped_column(String)
    event_timestamp: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    source_type: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str | None] = mapped_column(String, nullable=True, default=now)
    payload: Mapped[dict] = mapped_column(JSON)


def ensure_otp_schema(connection) -> None:
    inspector = inspect(connection)
    columns = {column['name'] for column in inspector.get_columns('users')}
    for name, declaration in [('phone', 'VARCHAR(16)'), ('age', 'INTEGER')]:
        if name not in columns:
            connection.execute(text(f'ALTER TABLE users ADD COLUMN {name} {declaration}'))
    unique_phone = any(constraint['column_names'] == ['phone'] for constraint in inspector.get_unique_constraints('users'))
    if not unique_phone:
        connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_users_phone ON users (phone)'))
    if inspector.has_table('market_products'):
        connection.execute(text(
            "UPDATE users SET role='farmer' WHERE role='customer' AND EXISTS "
            "(SELECT 1 FROM market_products WHERE market_products.farmer_id=users.id)"
        ))


def ensure_compat_schema(target_engine) -> None:
    """Create tables and add legacy lifecycle/identity columns without resetting data."""
    Base.metadata.create_all(target_engine)
    insp = inspect(target_engine)
    table_names = set(insp.get_table_names())
    if 'users' in table_names:
        user_cols = {c['name'] for c in insp.get_columns('users')}
        with target_engine.begin() as conn:
            for name, declaration in [
                ('email', 'VARCHAR(254)'),
                ('password_hash', 'VARCHAR'),
                ('role', "VARCHAR(20) NOT NULL DEFAULT 'farmer'"),
                ('is_active', 'BOOLEAN NOT NULL DEFAULT true'),
            ]:
                if name not in user_cols:
                    conn.execute(text(f'ALTER TABLE users ADD COLUMN {name} {declaration}'))
            # A unique index works additively on both SQLite and PostgreSQL.
            unique_sets = [set(c['column_names']) for c in insp.get_unique_constraints('users')]
            indexes = insp.get_indexes('users')
            if {'email'} not in unique_sets and not any(i.get('unique') and i['column_names'] == ['email'] for i in indexes):
                conn.execute(text('CREATE UNIQUE INDEX uq_users_email ON users (email)'))
        with target_engine.begin() as conn:
            ensure_otp_schema(conn)
    if 'records' in table_names:
        rec_cols = {c['name'] for c in insp.get_columns('records')}
        missing_rec = [
            ('farm_id', 'VARCHAR'),
            ('source_record_id', 'VARCHAR'),
            ('updated_at', 'VARCHAR'),
        ]
        with target_engine.begin() as conn:
            for col_name, col_type in missing_rec:
                if col_name not in rec_cols:
                    conn.execute(text(f'ALTER TABLE records ADD COLUMN {col_name} {col_type}'))
    if 'sensor_readings' in table_names:
        read_cols = {c['name'] for c in insp.get_columns('sensor_readings')}
        missing_read = [
            ('event_timestamp', 'VARCHAR'),
            ('source_type', 'VARCHAR'),
            ('created_at', 'VARCHAR'),
        ]
        with target_engine.begin() as conn:
            for col_name, col_type in missing_read:
                if col_name not in read_cols:
                    conn.execute(text(f'ALTER TABLE sensor_readings ADD COLUMN {col_name} {col_type}'))


url = os.getenv('DATABASE_URL', 'sqlite:///./agrosphere.db')
if url.startswith('postgres://'):
    url = 'postgresql+psycopg://' + url[len('postgres://'):]
elif url.startswith('postgresql://'):
    url = 'postgresql+psycopg://' + url[len('postgresql://'):]

engine = create_engine(
    url,
    connect_args={'check_same_thread': False} if url.startswith('sqlite') else {},
)
if url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def _sqlite_integrity(connection, _record):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA busy_timeout=15000')

Session = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with Session() as db:
        yield db
