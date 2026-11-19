"""The same anonymous aggregates drive the listing editor and farmer conversations."""
import pytest
from app import farmer_chat
from tests.test_platform import client, session


def sample_board(crop, district, unit):
    assert crop == 'tomato' and district == 'Gazipur' and unit == 'kg'
    return {'crop':crop, 'district':district, 'unit':unit,'currency':'BDT',
            'window_start':'2026-10-21','window_end':'2026-11-19','min_samples':3,
            'asking':{'count':5,'median_bdt':'45.00'},'agreed':{'count':3,'median_bdt':'38.00'}}


def chat(question, lookup, state=None, lang='en'):
    return farmer_chat.make_turn(question,lang,[],state or {},
                                 {'plot':{'crop':'potato'},'district':'Dhaka'},board_lookup=lookup)


def test_single_offer_against_district_orders_is_not_a_second_buyer_scenario(monkeypatch):
    monkeypatch.setattr(farmer_chat,'groq_json',lambda *args:{})
    m,state = chat('A buyer offered me ৳40/kg for tomatoes. How does that compare with recent orders in Gazipur?',sample_board)
    assert m['mode']=='tool' and '৳38' in m['text'] and '৳45' in m['text'] and '৳2' in m['text']
    assert '3' in m['text'] and '5' in m['text'] and '2026-11-19' in m['text']
    assert 'KrishiMarket' in m['sources'][0]['label'] and 'district_prices' in state
    follow,_ = chat('I can sell 100 kg and my transport is ৳600. What would I take home?',sample_board,state)
    assert '3400' in follow['text'].replace(',','')


def test_bengali_one_sample_cannot_be_a_local_reference_price(monkeypatch):
    monkeypatch.setattr(farmer_chat,'groq_json',lambda *args:{})
    def thin(c,d,u):
        return {**sample_board(c,d,u),'agreed':{'count':1,'median_bdt':None}}
    m,_=chat('গাজীপুরে টমেটোর জন্য কেজি প্রতি ৪০ টাকা বলেছে। সাম্প্রতিক অর্ডারের তুলনায় কেমন?',thin,lang='bn')
    assert m['mode']=='tool' and '৪৫' in m['text'] and 'পর্যাপ্ত' in m['text']
    assert '৩৮' not in m['text'] and '৳২' not in m['text']


def test_official_wholesale_quote_is_separate_from_marketplace(monkeypatch):
    monkeypatch.setattr(farmer_chat,'groq_json',lambda *args:{})
    m,_=chat("What is today's official wholesale tomato price in Gazipur?",lambda *_:pytest.fail('marketplace is not an official quote'))
    assert m['mode']=='limited'


def test_api_filters_and_empty_evidence(client, session):
    url='/api/v1/market/district-prices'
    crop_options=client.get(url+'/crops').json()['items']
    assert any(r['id']=='tomato' and r['bn'] for r in crop_options)
    result=client.get(url,params={'crop':'টমেটো','district':'গাজীপুর','unit':'g'})
    assert result.status_code==200, result.text
    board=result.json()
    assert board['crop']=='tomato' and board['district']=='Gazipur' and board['unit']=='kg'
    assert board['asking']==board['agreed']=={'count':0,'median_bdt':None}
    for bad in ({'crop':'tomato sauce','district':'Gazipur'},{'crop':'tomato','district':'unknown-district'},
                {'crop':'tomato','district':'Gazipur','unit':'bag'}):
        assert client.get(url,params=bad).status_code==422


def test_freight_rate_and_unknown_unit_never_become_the_sale_price(monkeypatch):
    monkeypatch.setattr(farmer_chat, 'groq_json', lambda *args: {})
    _, state = chat('A buyer offered me ৳40/kg for tomatoes. Compare with recent orders in Gazipur.', sample_board)
    reply, kept = chat('I can sell 100 kg and transport costs ৳2/kg. What would I take home?', sample_board, state)
    assert '3800' in reply['text'] and kept['district_prices']['offer'] == '40'
    reply, _ = chat('I can sell 100 kg and transport costs ৳60 per crate. What would I take home?', sample_board, state)
    assert 'total transport' in reply['text'] and '3940' not in reply['text']
    reply, _ = chat('What about ৳450 per sack of tomatoes in Gazipur?', lambda *_: pytest.fail('Cannot assume kg for sacks'), state)
    assert 'per kg, piece, bundle, or crate' in reply['text']


def test_explicit_order_request_wins_over_inferred_trade_type(monkeypatch):
    monkeypatch.setattr(farmer_chat, 'groq_json', lambda *args: {
        'topic':'market', 'language':'bn', 'trade_type':'farm-gate', 'district_board':False,
        'slots':{'near_price_per_kg':40},
    })
    question = 'একজন ক্রেতা গাজীপুরে টমেটোর জন্য কেজি প্রতি ৪০ টাকা দেবে। জেলার সাম্প্রতিক অর্ডারের তুলনায় কেমন?'
    result, _ = chat(question, sample_board, lang='bn')
    assert '৩৮' in result['text'] and 'গাজীপুর' in result['text']
    assert 'KrishiMarket' in result['sources'][0]['detail']

def test_english_offer_with_taka_honors_the_english_interface(monkeypatch):
    monkeypatch.setattr(farmer_chat, 'groq_json', lambda *args: {
        'topic':'market', 'language':'bn', 'district_board':True,
    })
    message, _ = chat('A buyer offered me ৳40/kg for tomatoes. How does that compare with recent orders in Gazipur?', sample_board)
    assert 'Your offer is' in message['text']
