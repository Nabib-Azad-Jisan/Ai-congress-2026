"""Read-only district summaries of asking prices and confirmed order line totals."""
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from statistics import median

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from .db import User
from .district_prices_catalog import canonical_commodity, canonical_district
from .farmer_chat_sources import DHAKA_TIME
from .market_models import Order, OrderItem, Product, Profile, SellerOrder
from .market_service import m, policy


MIN_SAMPLES = 3
_CONFIRMED_STATES = ("confirmed", "preparing", "ready_for_pickup", "out_for_delivery", "delivered")
_PAYMENT_STATES = ("demo_unpaid", "cash_recorded")
_GRAMS_PER_KG = Decimal(1000)


def _summary(prices: list[Decimal]) -> dict:
    return {"count": len(prices), "median_bdt": m(median(prices)) if len(prices) >= MIN_SAMPLES else None}


def _asking(db, crop, district, units, start, end):
    offers = (
        select(Product.commodity, Product.name, Product.district, Product.unit, Product.price_bdt)
        .join(User, User.id == Product.farmer_id)
        .where(
            User.is_demo.is_(False), User.is_active.is_(True),
            Product.status == "published", Product.moderation_status == "visible",
            Product.stock_quantity > 0, Product.price_bdt > 0,
            Product.price_observed_at.between(start, end), Product.unit.in_(units),
            # Marketplace listings are released at UTC midnight on available_from.
            or_(Product.available_from.is_(None), Product.available_from <= end[:10]),
            or_(Product.commodity == crop, Product.commodity.is_(None)),
        )
    )
    if policy(db)["require_verified_farmer"]:
        offers = offers.join(Profile, Profile.user_id == Product.farmer_id).where(
            Profile.verification_status == "verified"
        )
    prices = []
    for row in db.execute(offers):
        if canonical_district(row.district) != district or (row.commodity or canonical_commodity(row.name)) != crop:
            continue
        prices.append(row.price_bdt * _GRAMS_PER_KG if row.unit == "g" else row.price_bdt)
    return _summary(prices)


def _agreed(db, crop, district, units, start, end):
    buyer = aliased(User)
    seller = aliased(User)
    items = (
        select(Order.id, OrderItem.district, OrderItem.unit, OrderItem.quantity, OrderItem.line_total_bdt)
        .select_from(OrderItem)
        .join(SellerOrder, SellerOrder.id == OrderItem.seller_order_id)
        .join(Order, Order.id == SellerOrder.order_id)
        .join(seller, seller.id == SellerOrder.farmer_id)
        .join(buyer, buyer.id == Order.customer_id)
        .where(
            seller.is_demo.is_(False), buyer.is_demo.is_(False), seller.id != buyer.id,
            SellerOrder.status.in_(_CONFIRMED_STATES), SellerOrder.payment_status.in_(_PAYMENT_STATES),
            SellerOrder.confirmed_at.between(start, end), OrderItem.commodity == crop,
            OrderItem.unit.in_(units), OrderItem.quantity > 0, OrderItem.line_total_bdt >= 0,
        )
    )
    # A customer checkout can span multiple products, sellers and fulfillment groups.
    # Item totals capture actual lot amounts, even when the stored unit price was rounded.
    totals = defaultdict(Decimal)
    quantities = defaultdict(Decimal)
    for row in db.execute(items):
        if canonical_district(row.district) == district:
            totals[row.id] += row.line_total_bdt
            quantities[row.id] += row.quantity / _GRAMS_PER_KG if row.unit == "g" else row.quantity
    return _summary([total / quantities[order_id] for order_id, total in totals.items() if total > 0])


def board(db: Session, crop: str, district: str, unit: str = "kg", now: datetime | None = None) -> dict:
    crop_id = canonical_commodity(crop)
    place = canonical_district(district)
    if not crop_id:
        raise ValueError("Select a recognized commodity.")
    if not place:
        raise ValueError("Select a recognized Bangladesh district.")
    if unit not in {"kg", "g", "piece", "bundle", "crate"}:
        raise ValueError("Select kg, piece, bundle or crate.")
    if unit == "g":
        unit = "kg"
    units = ("kg", "g") if unit == "kg" else (unit,)

    current = now if now is not None else datetime.now(timezone.utc)
    if current.utcoffset() is None:
        raise ValueError("Price observation time must include a UTC offset.")
    today = current.astimezone(DHAKA_TIME).date()
    first_day = today - timedelta(days=29)
    # Marketplace writes timestamps as UTC ISO strings, including the +00:00 offset.
    start = datetime.combine(first_day, time.min, DHAKA_TIME).astimezone(timezone.utc).isoformat()
    end = current.astimezone(timezone.utc).isoformat()
    return {
        "crop": crop_id, "district": place, "unit": unit, "currency": "BDT",
        "window_start": first_day.isoformat(), "window_end": today.isoformat(), "min_samples": MIN_SAMPLES,
        "asking": _asking(db, crop_id, place, units, start, end),
        "agreed": _agreed(db, crop_id, place, units, start, end),
    }
