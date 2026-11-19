"""Additive district-price evidence upgrade, shared by Alembic and native startup."""
from datetime import date, datetime, time, timezone

from sqlalchemy import and_, case, func, inspect, or_, select, text, update

from .db import FIXTURE_EMAIL_DOMAINS, Record, SignupIdentity, User
from .district_prices_catalog import canonical_commodity
from .market_models import Audit, OrderItem, Product, SellerOrder


def _backfill_accounts(connection):
    email = func.lower(User.email)
    reserved = or_(*(email.like(pattern) for domain in FIXTURE_EMAIL_DOMAINS
                     for pattern in ('%@' + domain, '%.' + domain)))
    demo_signup = select(Record.id).where(
        Record.owner_id == User.id, Record.kind == 'audit',
        Record.payload['event'].as_string() == 'demo.created'
    ).exists()
    signup_identity = select(SignupIdentity.user_id).where(SignupIdentity.user_id == User.id).exists()
    # Match the full structure written only by the legacy password signup route.
    legacy_hash = 'scrypt$16384$8$1$' + '_' * 32 + '$' + '_' * 64
    password_signup = and_(User.email.is_not(None), User.password_hash.like(legacy_hash))
    registered = and_(User.role.in_(('farmer','customer')), or_(signup_identity, password_signup))
    connection.execute(update(User).where(User.is_demo.is_(None)).values(
        is_demo=case((or_(demo_signup, reserved), True), (registered, False), else_=None)
    ))


def _backfill_asking_dates(connection):
    # Checkouts and auction reservations incremented version/updated_at without
    # changing price. The old audit recorded every seller edit but not its fields.
    history = select(Audit.id).where(Audit.entity_type == 'product', Audit.entity_id == Product.id)
    created = history.where(Audit.event == 'product.created').exists()
    edited = history.where(Audit.event == 'product.updated').exists()
    rows = connection.execute(select(Product.id, Product.created_at, Product.available_from).where(
        created, ~edited, Product.status == 'published', Product.moderation_status == 'visible',
        Product.price_observed_at.is_(None),
    ))
    for product_id, created_at, availability in rows:
        try:
            observed = datetime.fromisoformat(created_at)
            if observed.tzinfo is None:
                continue
            if availability:
                observed = max(observed, datetime.combine(date.fromisoformat(availability), time.min, timezone.utc))
        except (ValueError, TypeError):
            continue
        connection.execute(update(Product).where(Product.id == product_id).values(
            price_observed_at=observed.astimezone(timezone.utc).isoformat()
        ))


def _backfill_order_items(connection):
    # The legacy marketplace assigned product.district once, at listing creation.
    # Item names were snapshotted even when a seller subsequently edited the title.
    origin = select(Product.district).where(Product.id == OrderItem.product_id).scalar_subquery()
    connection.execute(update(OrderItem).where(OrderItem.district.is_(None)).values(district=origin))
    names = connection.scalars(select(OrderItem.name).where(OrderItem.commodity.is_(None)).distinct())
    for name in names:
        commodity = canonical_commodity(name)
        if commodity:
            connection.execute(update(OrderItem).where(
                OrderItem.name == name, OrderItem.commodity.is_(None)
            ).values(commodity=commodity))


def ensure_district_evidence_schema(connection):
    # Nullable additions do not rewrite or delete unverifiable historical observations.
    # SQLite's legacy driver mode otherwise auto-commits ALTER before the backfill.
    if connection.dialect.name == 'sqlite' and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql('BEGIN IMMEDIATE')
    elif connection.dialect.name == 'postgresql':
        connection.execute(text('SELECT pg_advisory_xact_lock(781423602)'))
    inspector = inspect(connection)
    additions = {
        'users': {'is_demo':'BOOLEAN'},
        'market_products': {'commodity':'VARCHAR(60)', 'price_observed_at':'VARCHAR'},
        'market_order_items': {'commodity':'VARCHAR(60)', 'district':'VARCHAR(80)'},
        'market_seller_orders': {'confirmed_at':'VARCHAR'},
    }
    changed = set()
    for table, columns in additions.items():
        if not inspector.has_table(table):
            continue
        existing = {column['name'] for column in inspector.get_columns(table)}
        for name, declaration in columns.items():
            if name not in existing:
                connection.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {declaration}'))
                changed.add((table, name))

    if ('users', 'is_demo') in changed:
        _backfill_accounts(connection)
    if ('market_products', 'price_observed_at') in changed:
        _backfill_asking_dates(connection)
    if any(table == 'market_order_items' for table, _ in changed):
        _backfill_order_items(connection)
    if ('market_seller_orders', 'confirmed_at') in changed:
        confirmed = select(func.min(Audit.created_at)).where(
            Audit.entity_id == SellerOrder.id, Audit.entity_type == 'seller_order',
            Audit.event == 'order.status_changed', Audit.details['status'].as_string() == 'confirmed',
        ).scalar_subquery()
        connection.execute(update(SellerOrder).where(SellerOrder.confirmed_at.is_(None)).values(confirmed_at=confirmed))

    for table, column in ((Product.__table__, 'price_observed_at'), (SellerOrder.__table__, 'confirmed_at')):
        if inspector.has_table(table.name):
            index = next(index for index in table.indexes if index.name == f'ix_{table.name}_{column}')
            index.create(connection, checkfirst=True)
