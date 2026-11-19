"""Marketplace writes preserve dated district evidence through the normal checkout flow."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app import market_service
from app.db import Session, User
from app.market_models import OrderItem, Product, SellerOrder
from tests.test_marketplace import API, account, actors, address, cart, checkout, product
from tests.test_marketplace_edges import admin
from tests.test_platform import client


def test_commodity_and_price_age_follow_the_offer(client, actors, monkeypatch):
    farmer = actors[0]
    first = datetime.now(timezone.utc)
    current = first
    monkeypatch.setattr(market_service, 'clock', lambda: current)
    p = product(client, farmer, name='Morning harvest', commodity='টমেটো', status='draft')
    assert p['commodity'] == 'tomato'

    def patch(**changes):
        nonlocal p
        response = client.patch(API+'/market/products/'+p['id'], headers=farmer,
                                json={'expected_version': p['version'], **changes})
        assert response.status_code == 200, response.text
        p = response.json()

    def observed():
        with Session() as db:
            return db.get(Product, p['id']).price_observed_at

    assert observed() is None
    current += timedelta(days=3)
    patch(status='published')
    published = current.isoformat()
    assert observed() == published
    current += timedelta(days=2)
    patch(description='New pickup instructions', stock_quantity='50', price_bdt='45.00')
    assert observed() == published
    patch(price_bdt='51.50')
    assert observed() == current.isoformat()
    current += timedelta(days=1)
    patch(commodity=None, name='Potato')
    assert p['commodity'] is None
    assert observed() == current.isoformat()
    current += timedelta(days=1)
    patch(name='Potatoes')
    assert observed() != current.isoformat()
    response = client.patch(API+'/market/products/'+p['id'], headers=farmer,
                            json={'expected_version': p['version'], 'commodity': 'mystery crop'})
    assert response.status_code == 422
    later = (current + timedelta(days=8)).date()
    patch(available_from=str(later))
    assert observed() == datetime.combine(later, datetime.min.time(), timezone.utc).isoformat()
    current += timedelta(days=2)
    patch(available_from=None)
    assert observed() == current.isoformat()


def test_order_snapshots_and_first_confirmation(client, actors, monkeypatch):
    seller, _, buyer, _, _, _ = actors
    p = product(client, seller, name='Harvest lot', commodity='tomato', quantity_step='0.001',
                price_bdt='43.78')
    receiver = address(client, buyer, district='Dhaka')
    assert cart(client, buyer, p['id'], '1.5').status_code == 200
    order = checkout(client, buyer, receiver, p['id']).json()
    group = order['seller_orders'][0]
    with Session() as db:
        line = db.scalar(select(OrderItem).where(OrderItem.seller_order_id == group['id']))
        assert (line.commodity, line.district, line.unit_price_bdt) == ('tomato','Gazipur',Decimal('43.78'))
        assert db.get(SellerOrder, group['id']).confirmed_at is None
    p = client.get(API+'/market/products/'+p['id'], headers=seller).json()
    assert client.patch(API+'/market/products/'+p['id'], headers=seller, json={
        'expected_version':p['version'], 'commodity':'potato', 'price_bdt':'70'}).status_code == 200
    accepted = datetime.now(timezone.utc)
    moment = accepted
    monkeypatch.setattr(market_service, 'clock', lambda: moment)
    for stage in ['confirmed','preparing','cancelled']:
        response = client.patch(API+'/market/seller-orders/'+group['id'], headers=seller,
                                json={'status': stage,'reason':'Seller updated order'})
        assert response.status_code == 200, response.text
        with Session() as db:
            row = db.get(SellerOrder, group['id'])
            assert row.confirmed_at == accepted.isoformat()
            line = db.scalar(select(OrderItem).where(OrderItem.seller_order_id == row.id))
            assert (line.commodity, line.district, line.unit_price_bdt) == ('tomato','Gazipur',Decimal('43.78'))
        moment += timedelta(hours=1)


def test_moderation_dates_only_newly_disclosed_terms(client, actors, monkeypatch):
    farmer = actors[0]
    op = admin(client)
    first = datetime.now(timezone.utc)
    moment = first
    monkeypatch.setattr(market_service, 'clock', lambda: moment)
    p = product(client, farmer, commodity='tomato')

    def moderate(status):
        response = client.patch(API+'/admin/market/products/'+p['id'], headers=op,
                                json={'moderation_status':status,'reason':'Review of listing'})
        assert response.status_code == 200, response.text
        return response.json()

    moderate('hidden')
    moment += timedelta(days=5)
    moderate('visible')
    with Session() as db:
        assert db.get(Product, p['id']).price_observed_at == first.isoformat()
    hidden = moderate('hidden')
    changed = client.patch(API+'/market/products/'+p['id'], headers=farmer,
                           json={'expected_version': hidden['version'], 'price_bdt':'58.50'})
    assert changed.status_code == 200, changed.text
    with Session() as db:
        assert db.get(Product, p['id']).price_observed_at is None
    moment += timedelta(days=3)
    moderate('visible')
    with Session() as db:
        assert db.get(Product, p['id']).price_observed_at == moment.isoformat()


def test_signup_provenance_is_server_owned(client):
    demo = client.post(API+'/auth/demo', json={'name':'A non-demo sounding name'}).json()
    _, fixture = account(client, 'farmer', 'fixture')
    body = {'name':'Public farmer','email':'farmer@agro-growers.bd','password':'a long enough password','role':'farmer'}
    manual = client.post(API+'/auth/register', json=body).json()['user']
    assert client.post(API+'/auth/register', json={**body, 'is_demo':False}).status_code == 422
    with Session() as db:
        assert db.get(User, demo['user_id']).is_demo is True
        assert db.get(User, fixture['id']).is_demo is True
        assert db.get(User, manual['id']).is_demo is False


def test_public_summary_follows_real_marketplace_flow(client):
    def signup(name, role):
        response = client.post(API+'/auth/register', json={
            'name':name, 'email':name+'@growers.bd', 'password':'a long enough password', 'role':role,
        })
        assert response.status_code == 200, response.text
        return {'Authorization':'Bearer '+response.json()['token']}

    def summary():
        response = client.get(API+'/market/district-prices', params={'crop':'potato','district':'Gazipur'})
        assert response.status_code == 200, response.text
        return response.json()

    def place(p, purchaser, destination, key):
        assert cart(client, purchaser, p['id'], '1').status_code == 200
        response = checkout(client, purchaser, destination, p['id'], key=key)
        assert response.status_code == 200, response.text
        return response.json()['seller_orders'][0]['id']

    def status(group, owner, state):
        response = client.patch(API+'/market/seller-orders/'+group, headers=owner,
                                json={'status':state, 'reason':'Updated by seller'})
        assert response.status_code == 200, response.text

    seller = signup('local-farmer', 'farmer')
    buyer = signup('local-buyer', 'customer')
    receiver = address(client, buyer)
    demo = client.post(API+'/auth/demo', json={}).json()
    demo_session = {'Authorization':'Bearer '+demo['token']}
    fixture_product = product(client, demo_session, commodity='potato', price_bdt='999')
    status(place(fixture_product, buyer, receiver, 'demo-seller'), demo_session, 'confirmed')

    groups = []
    for amount in ('40','60','80'):
        listing = product(client, seller, price_bdt=amount)
        groups.append(place(listing, buyer, receiver, 'buy-'+amount))
    demo_buyer, _ = account(client, 'customer', 'demo-customer')
    status(place(listing, demo_buyer, address(client, demo_buyer), 'demo-buyer'), seller, 'confirmed')
    assert summary()['asking'] == {'count':3,'median_bdt':'60.00'}
    assert summary()['agreed'] == {'count':0,'median_bdt':None}
    for group in groups:
        status(group, seller, 'confirmed')
    assert summary()['agreed'] == {'count':3,'median_bdt':'60.00'}
    status(groups[0], seller, 'cancelled')
    assert summary()['agreed'] == {'count':2,'median_bdt':None}
