"""A native compatibility-created database can adopt migrations without data loss."""
import os,subprocess
from pathlib import Path
import pytest
from sqlalchemy import create_engine,text
from sqlalchemy.orm import Session
from app.db import Base, Record, SignupIdentity, User, ensure_compat_schema
from app.market_auth import hash_password
from app.market_models import Audit, Order, OrderItem, Product, SellerOrder

def test_unversioned_existing_workspace_upgrade_is_additive(tmp_path):
    url='sqlite:///'+str(tmp_path/'existing.db').replace('\\','/')
    engine=create_engine(url);Base.metadata.create_all(engine)
    with engine.begin() as db:
        db.execute(text("INSERT INTO users (id,name,preferences,role,is_active) VALUES ('preserved','Existing farmer','{}','farmer',1)"))
        db.execute(text("INSERT INTO records (id,owner_id,kind,created_at,payload) VALUES ('original','preserved','farm','2026-11-17T00:00:00+00:00','{}')"))
    env={**os.environ,'DATABASE_URL':url}
    api=Path(__file__).resolve().parents[1];python=Path(__file__).resolve().parents[3]/'.venv/Scripts/python.exe'
    # sys.executable also works on Linux CI; local environment selection is not hardcoded.
    import sys
    for _ in range(2):
        result=subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=api,env=env,capture_output=True,text=True)
        assert result.returncode==0,result.stderr+result.stdout
    with engine.connect() as db:
        assert db.scalar(text("SELECT name FROM users WHERE id='preserved'"))=='Existing farmer'
        assert db.scalar(text("SELECT id FROM records WHERE id='original'"))=='original'
        assert db.scalar(text('SELECT version_num FROM alembic_version'))=='0008'
        assert db.scalar(text('SELECT COUNT(*) FROM email_verifications'))==0


@pytest.mark.parametrize('startup', ['native', 'alembic'])
def test_old_marketplace_recovers_only_defensible_observations(tmp_path, startup):
    import sys
    url = 'sqlite:///' + (tmp_path / 'legacy.db').as_posix()
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    older = '2026-10-01T12:00:00+00:00'
    newer = '2026-11-19T12:00:00+00:00'
    with Session(engine) as db:
        credential = hash_password('Legacy account test password')
        db.add_all([
            User(id='seller', name='Demo sounding name', email='seller@growers.bd', password_hash=credential),
            User(id='buyer', name='Buyer', phone='+8801711119999'),
            User(id='fixture', name='Farmer', email='farm@EXAMPLE.TEST', password_hash=credential),
            User(id='demo', name='Farmer', email='sample@growers.bd', password_hash=credential),
            User(id='unknown', name='Farmer'),
        ])
        db.flush()
        db.add(Record(owner_id='demo', kind='audit', payload={'event':'demo.created'}))
        db.add(SignupIdentity(user_id='buyer', gender='male', encrypted_details=b'x', encrypted_photo=b'y'))
        listing = dict(farmer_id='seller', name='Updated cucumber name', district='Gazipur', category='vegetables',
                       price_bdt=40, unit='kg', quantity_step=1, stock_quantity=5, status='published',
                       created_at=older, updated_at=newer)
        db.add_all([Product(id='edited', version=4, **listing),
                    Product(id='untraced', version=1, **listing),
                    Product(id='untouched', version=3, available_from='2026-10-05', **listing),
                    Order(id='order', customer_id='buyer', total_bdt=40)])
        for product_id, event in [('edited','product.created'), ('edited','product.updated'),
                                  ('untouched','product.created')]:
            db.add(Audit(event=event, actor_id='seller', entity_type='product',
                         entity_id=product_id, details={}, created_at=older))
        for key in ('recorded', 'undated'):
            db.add(SellerOrder(id=key, order_id='order', farmer_id='seller', fulfillment='delivery',
                               status='delivered', subtotal_bdt=40, delivery_fee_bdt=0, total_bdt=40,
                               destination={'district':'Dhaka'}, updated_at=newer))
        db.flush()
        db.add(OrderItem(id='line', seller_order_id='recorded', product_id='edited', name='Potatoes',
                         unit='kg', quantity=1, unit_price_bdt=40, line_total_bdt=40))
        for status, timestamp in [('confirmed', older), ('delivered', newer)]:
            db.add(Audit(event='order.status_changed', actor_id='seller', entity_type='seller_order',
                         entity_id='recorded', details={'status':status}, created_at=timestamp))
        db.commit()
    with engine.begin() as connection:
        for table, column in [('market_products','price_observed_at'),('market_seller_orders','confirmed_at')]:
            connection.execute(text(f'DROP INDEX ix_{table}_{column}'))
        for table, columns in [
            ('users',['is_demo']), ('market_products',['commodity','price_observed_at']),
            ('market_order_items',['commodity','district']), ('market_seller_orders',['confirmed_at']),
        ]:
            for column in columns:
                connection.execute(text(f'ALTER TABLE {table} DROP COLUMN {column}'))
    if startup == 'native':
        for _ in range(2):
            ensure_compat_schema(engine)
    else:
        command = [sys.executable, '-m', 'alembic', 'upgrade', 'head']
        for _ in range(2):
            subprocess.run(command, cwd=Path(__file__).resolve().parents[1], env={**os.environ, 'DATABASE_URL':url},
                           capture_output=True, text=True, check=True)
    with Session(engine) as db:
        for key, expected in [('seller',False),('buyer',False),('demo',True),('fixture',True),('unknown',None)]:
            assert db.get(User, key).is_demo is expected
        assert db.get(Product, 'edited').price_observed_at is None
        assert db.get(Product, 'untraced').price_observed_at is None
        untouched = db.get(Product, 'untouched')
        assert untouched.price_observed_at == '2026-10-05T00:00:00+00:00'
        assert untouched.commodity is None
        assert db.get(SellerOrder, 'recorded').confirmed_at == older
        assert db.get(SellerOrder, 'undated').confirmed_at is None
        line = db.get(OrderItem, 'line')
        assert (line.commodity, line.district) == ('potato', 'Gazipur')
    engine.dispose()
