"""Price evidence is grouped by commodity, seller district, unit and distinct order."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base, User
from app.district_prices import board
from app.district_prices_catalog import (
    COMMODITY_OPTIONS, DISTRICT_OPTIONS, canonical_commodity, canonical_district,
)
from app.market_models import Order, OrderItem, Policy, Product, Profile, SellerOrder


NOW = datetime(2026, 11, 18, 19, 0, tzinfo=timezone.utc)  # November 19 in Bangladesh.
RECENT = "2026-11-12T11:00:00+00:00"
BEGIN = "2026-10-20T18:00:00+00:00"  # Midnight, October 21 local time.


def test_bilingual_catalogs_and_strict_legacy_names():
    for value, commodity in [
        ("Fresh tomatoes", "tomato"), ("তাজা টমেটো", "tomato"), ("মিষ্টি আলু", "sweet_potato"),
        ("Potatoes", "potato"), ("Aman paddy", "paddy"), ("ধান", "paddy"),
        ("চাল", "rice"), ("milled rice", "rice"), ("Sweet pepper", "bell_pepper"),
        ("tomato sauce", None), ("fresh mixed tomato and mango", None), ("potato chips", None),
        ("potato and unknown produce", None), ("ধানের বীজ", None), ("black pepper", None),
        ("pineapple juice", None), ("mystery box", None),
    ]:
        assert canonical_commodity(value) == commodity, value
    assert canonical_district("Chittagong District, Bangladesh") == "Chattogram"
    assert canonical_district("চট্টগ্রাম জেলা") == "Chattogram"
    assert canonical_district("unknown location") is None
    assert len(DISTRICT_OPTIONS) == 64
    for option in COMMODITY_OPTIONS:
        assert canonical_commodity(option["en"]) == canonical_commodity(option["bn"]) == option["id"]
        assert canonical_commodity(option["id"]) == option["id"]


@pytest.fixture
def database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def actor(db, **kwargs):
    row = User(name="Private name", is_demo=False, **kwargs)
    db.add(row)
    db.flush()
    return row


def listing(db, seller, **overrides):
    fields = dict(
        farmer_id=seller.id, name="Private listing title", category="vegetables",
        price_bdt=Decimal("50"), commodity="tomato", district="Chittagong",
        quantity_step=1, stock_quantity=30, unit="kg", status="published",
        price_observed_at=RECENT, area="Private locality",
    )
    row = Product(**(fields | overrides))
    db.add(row)
    db.flush()
    return row


def sale(db, seller, buyer, product, lines, *, order=None, **overrides):
    if order is None:
        order = Order(customer_id=buyer.id, total_bdt=999)
        db.add(order)
        db.flush()
    fields = dict(
        order_id=order.id, farmer_id=seller.id, fulfillment="delivery", status="confirmed",
        confirmed_at=RECENT, subtotal_bdt=900, delivery_fee_bdt=99, total_bdt=999,
        destination={"district": "Dhaka", "phone": "01712345678"},
    )
    group = SellerOrder(**(fields | overrides))
    db.add(group)
    db.flush()
    for unit, quantity, total, district, commodity in lines:
        db.add(OrderItem(
            seller_order_id=group.id, product_id=product.id, name="Private product", unit=unit,
            quantity=quantity, line_total_bdt=total, unit_price_bdt=Decimal("5.55"),
            district=district, commodity=commodity,
        ))
    db.flush()
    return order


def report(db, unit="kg"):
    return board(db, "টমেটো", "চট্টগ্রাম", unit, now=NOW)


def test_empty_board_is_aggregate_only_and_uses_local_calendar(database):
    assert report(database) == dict(
        crop="tomato", district="Chattogram", unit="kg", currency="BDT",
        window_start="2026-10-21", window_end="2026-11-19", min_samples=3,
        asking={"count": 0, "median_bdt": None}, agreed={"count": 0, "median_bdt": None},
    )


def test_asking_uses_offer_observation_and_availability(database):
    db = database
    seller = actor(db)
    listing(db, seller, price_bdt=40, price_observed_at=BEGIN)
    listing(db, seller, price_bdt=Decimal("0.05"), unit="g")
    assert report(db)["asking"] == {"count": 2, "median_bdt": None}
    listing(db, seller, price_bdt=64, district="চট্টগ্রাম জেলা", price_observed_at=NOW.isoformat())
    for fields in (
        {"price_observed_at": "2026-10-20T17:59:59+00:00"},
        {"price_observed_at": "2026-11-18T19:00:01+00:00"},
        {"price_observed_at": None}, {"district": "Dhaka"}, {"commodity": "potato"},
        {"moderation_status": "hidden"}, {"stock_quantity": 0},
        {"available_from": "2026-11-20"}, {"status": "draft"}, {"status": "paused"},
    ):
        listing(db, seller, **fields)
    off = actor(db, is_active=False)
    listing(db, off)
    demo = actor(db)
    demo.is_demo = True
    listing(db, demo)
    assert report(db)["asking"] == {"count": 3, "median_bdt": "50.00"}
    listing(db, seller, price_bdt=Decimal("52.01"))
    assert report(db)["asking"] == {"count": 4, "median_bdt": "51.01"}
    db.add(Policy(key="settings", value={"require_verified_farmer": True}))
    db.flush()
    assert report(db)["asking"]["count"] == 0
    db.add(Profile(user_id=seller.id, verification_status="verified"))
    db.flush()
    assert report(db)["asking"]["count"] == 4


def test_agreed_uses_item_snapshots_one_weighted_price_per_order(database):
    db = database
    buyer, seller = actor(db), actor(db)
    p = listing(db, seller, status="archived", district="Dhaka", commodity="onion")
    # Same checkout contains two matching items in different fulfillment groups.
    first = sale(db, seller, buyer, p, [("kg", 1, 100, "Chittagong", "tomato")])
    sale(db, seller, buyer, p, [
        ("g", 3000, 120, "চট্টগ্রাম", "tomato"), ("kg", 4, 4000, "Dhaka", "tomato"),
        ("kg", 2, 900, "Chattogram", "potato"), ("piece", 1, 120, "Chattogram", "tomato"),
        ("kg", 2, 45, None, "tomato"),
    ], order=first)
    line = lambda total: [("kg", 1, total, "Chattogram", "tomato")]
    sale(db, seller, buyer, p, line(20), status="out_for_delivery", confirmed_at=BEGIN)
    assert report(db)["agreed"] == {"count": 2, "median_bdt": None}
    sale(db, seller, buyer, p, line(75), status="delivered", payment_status="cash_recorded")
    # First order is 220 BDT / 4 kg = 55 BDT/kg, irrespective of destination, fees or edition.
    assert report(db)["agreed"] == {"count": 3, "median_bdt": "55.00"}
    assert report(db, "piece")["agreed"] == {"count": 1, "median_bdt": None}
    assert report(db, "bundle")["agreed"]["count"] == 0


def test_agreed_requires_supported_confirmations_and_real_participants(database):
    db = database
    buyer, seller, demo = actor(db), actor(db), actor(db)
    demo.is_demo = True
    p = listing(db, seller)
    match = [("kg", 1, 20, "Chattogram", "tomato")]
    for fields in [
        {"status": "cancelled"}, {"status": "pending"}, {"payment_status": "refunded"},
        {"confirmed_at": None}, {"confirmed_at": "2026-10-20T17:59:59+00:00"},
        {"confirmed_at": "2026-11-18T19:00:01+00:00"},
    ]:
        sale(db, seller, buyer, p, match, **fields)
    sale(db, demo, buyer, p, match)
    sale(db, seller, demo, p, match)
    assert report(db)["agreed"] == {"count": 0, "median_bdt": None}


def test_units_never_pool_package_and_weight_prices(database):
    db = database
    seller = actor(db)
    for unit, values in [("crate", [200, 320, 500]), ("bundle", [10, 20]), ("piece", [8])]:
        for value in values:
            listing(db, seller, unit=unit, price_bdt=value)
    assert report(db, "crate")["asking"] == {"count": 3, "median_bdt": "320.00"}
    assert report(db, "bundle")["asking"] == {"count": 2, "median_bdt": None}
    assert report(db, "piece")["asking"] == {"count": 1, "median_bdt": None}
    assert report(db, "g")["unit"] == "kg"
    assert report(db)["asking"]["count"] == 0
    for query in [("tomato", "Dhaka", "box"), ("tomato", "unrecognized", "kg"), ("mystery", "Dhaka", "kg")]:
        with pytest.raises(ValueError):
            board(db, *query, now=NOW)


def test_scheduled_offers_follow_marketplace_release_time_and_reserved_stock_is_separate(database):
    db = database
    seller = actor(db)
    listing(db, seller, available_from="2026-11-19", auction_reserved=100, stock_quantity=1)
    listing(db, seller, available_from="2026-11-19", auction_reserved=100, stock_quantity=0)
    assert report(db)["asking"] == {"count": 0, "median_bdt": None}
    release = datetime(2026, 11, 19, 0, 0, tzinfo=timezone.utc)
    assert board(db, "tomato", "Chattogram", now=release)["asking"] == {"count": 1, "median_bdt": None}
    assert db.get(Policy, "settings") is None


def test_legacy_titles_contribute_only_if_clearly_identified(database):
    db = database
    seller = actor(db)
    listing(db, seller, commodity=None, name="Fresh tomatoes")
    listing(db, seller, commodity=None, name="Local tomato and potato")
    listing(db, seller, commodity=None, name="টমেটো সস")
    assert report(db)["asking"] == {"count": 1, "median_bdt": None}
