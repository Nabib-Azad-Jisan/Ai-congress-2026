"""Farmer chat context, idempotency and explicit observation saves."""
from uuid import uuid4

import pytest
from app import farmer_chat as chat
from tests.test_platform import client, session, picture


def send(client, question, **kwargs):
    payload = {'message': question, 'locale': 'en', 'request_id': uuid4().hex, **kwargs}
    return client.post('/api/v1/farmer-chat/messages', json=payload)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(chat, 'collect_sources', lambda *args: [])


def test_plot_chat_is_private_and_resumes_without_duplicate_turns(client, session):
    params = dict(request_id='retry-12345678', plot_id=session['plot_id'])
    r = send(client, 'Brief me on my open tasks', **params)
    assert r.status_code == 200, r.text
    thread = r.json()
    assert len(thread['messages']) == 2
    assert 'Start your first crop screening' in thread['messages'][-1]['text']
    assert send(client, 'Brief me on my open tasks', **params).json() == thread
    path = '/api/v1/farmer-chat/conversations/' + thread['conversation_id']
    assert client.get(path).json() == thread
    index = '/api/v1/farmer-chat/conversations'
    assert client.get(index,params={'plot_id':session['plot_id']}).json()['items'][0]['id']==thread['conversation_id']
    assert client.get(index).json()=={'items':[]}
    other = client.post('/api/v1/auth/demo', json={}).json()
    assert client.get(path, headers={'Authorization':'Bearer '+other['token']}).status_code == 404
    assert send(client, 'tasks', plot_id=other['plot_id']).status_code == 404
    assert send(client, 'changed question', **params).status_code == 409


def test_case_notes_preserve_exact_farmer_words_and_save_only_on_click(client, session):
    case = client.post('/api/v1/doctor/cases', data={'plot_id':session['plot_id']},
                       files={'image':('leaf.jpg', picture(), 'image/jpeg')}).json()
    question = 'একই বস্তায় আরও ছয়টা আলু নষ্ট পেলাম।'
    reply = send(client, question, case_id=case['id'], locale='bn').json()
    item = reply['messages'][-1]
    action = next(a for a in item['actions'] if a['kind']=='note')
    assert action['target'] == question
    case_url = '/api/v1/doctor/cases/' + case['id']
    assert not client.get(case_url).json()['feedback']
    save = '/api/v1/farmer-chat/conversations/' + reply['conversation_id'] + '/notes'
    for _ in range(2):
        response = client.post(save, json={'message_id':item['id']})
        assert response.status_code == 200
        assert next(a for a in response.json()['messages'][-1]['actions'] if a['kind']=='note')['done']
    feedback = client.get(case_url).json()['feedback']
    assert len(feedback) == 1 and feedback[0]['note'] == question
    client.delete(case_url)
    assert client.get(save.removesuffix('/notes')).status_code == 404


def test_current_price_has_no_demo_quote_and_no_model_disguised_as_live(client, session):
    response = send(client, "What's the wholesale market price today?", plot_id=session['plot_id']).json()
    assert response['messages'][-1]['mode']=='limited'
    assert '42.00' not in response['messages'][-1]['text']


def test_provider_receives_curated_case_and_valid_sources_only(client, session, monkeypatch):
    case = client.post('/api/v1/doctor/cases', data={'plot_id':session['plot_id']},
                       files={'image':('a.jpg',picture(),'image/jpeg')}).json()
    calls = []
    def groq(system, inputs, tokens):
        calls.append(inputs)
        if 'question' in inputs and 'evidence' not in inputs:
            return {'topic':'health', 'language':'en'}
        return {'reply':'Your saved screening is uncertain. Can you photograph the underside?', 'citations':['case']}
    monkeypatch.setattr(chat, 'groq_json', groq)
    r = send(client,'Explain this photo',case_id=case['id'])
    assert r.status_code == 200
    m = r.json()['messages'][-1]
    assert m['mode']=='groq' and m['sources']
    assert len(calls)==2
    assert case['image_file'] not in str(calls) and session['token'] not in str(calls)


def test_live_weather_requires_consent_and_never_forwards_coordinates_to_groq(monkeypatch):
    inputs = []
    def groq(system, data, tokens):
        inputs.append(data)
        return {'topic':'weather','language':'en'} if 'evidence' not in data else {'reply':'Check the rain outlook.','citations':['weather']}
    monkeypatch.setattr(chat,'groq_json',groq)
    from app.services import DemoWeatherProvider
    calls = []
    def forecast(self, lat, lon):
        calls.append((lat,lon))
        return DemoWeatherProvider().forecast(lat,lon)
    monkeypatch.setattr(chat.OpenMeteoProvider,'forecast',forecast)
    context = {'district':'Gazipur','plot':{'crop':'tomato','stage':'vegetative'}}
    chat.make_turn('Will it rain?', 'en', [], {}, context)
    assert not calls and 'weather' not in inputs[-1]['evidence']
    chat.make_turn('Will it rain?', 'en', [], {}, {**context,'coordinates':(23.98765,90.12345)})
    assert calls==[(23.98765,90.12345)] and 'weather' in inputs[-1]['evidence']
    assert '23.98765' not in str(inputs) and '90.12345' not in str(inputs)


def test_market_followup_without_provider(client,session):
    body = {'plot_id':session['plot_id']}
    result = send(client,'100 kg. Farther market pays ৳5/kg more, extra transport ৳600.', **body).json()
    assert result['messages'][-1]['mode']=='tool'
    result = send(client,'ভাড়া ৩০০ হলে?',conversation_id=result['conversation_id'],**body).json()
    assert '২০০' in result['messages'][-1]['text'] and 'দূরের' in result['messages'][-1]['text']
    assert len(result['messages'])==4


def test_one_groq_model_throttled_can_use_another_without_disclosing_credentials(monkeypatch):
    import httpx
    calls = []
    def post(url, *, json, headers, timeout):
        calls.append(json['model'])
        if len(calls)==1:
            return httpx.Response(429)
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"topic":"weather"}'}}]})
    monkeypatch.setenv('GROQ_API_KEY','test-value')
    monkeypatch.setattr(httpx,'post',post)
    assert chat.groq_json(chat.ROUTE,{'question':'rain?'},300)=={'topic':'weather'}
    assert calls==['qwen/qwen3.8-27b','openai/gpt-oss-120b']


def test_banglish_irrigation_asks_before_scheduling_and_ignores_unreported_soil(monkeypatch):
    def route(system,inputs,tokens):
        assert 'evidence' not in inputs
        return {'topic':'irrigation','language':'bn','root_soil':'dry at root depth'}
    monkeypatch.setattr(chat,'groq_json',route)
    reply,_=chat.make_turn('mati ektu veja. kokhon sech dibo?', 'bn', [], {}, {})
    assert reply['mode']=='tool' and 'শিকড়' in reply['text'] and 'শেষ কবে' in reply['text']


def test_report_of_more_rotten_potatoes_is_never_reworded_as_a_total(monkeypatch):
    question = 'একই বস্তায় আরও ছয়টা আলু নষ্ট পেলাম। এখন কী করব?'
    def ask(system,data,tokens):
        if 'evidence' not in data:
            return {'topic':'handoff','language':'bn','observation':False}
        return {'reply':'আপনি মোট ৬টি আলু পেয়েছেন। নষ্ট আলুগুলো আলাদা করুন।',
                'handoff_bn':'মোট ছয়টা নষ্ট আলু পেয়েছি। করণীয় জানাবেন?'}
    monkeypatch.setattr(chat,'groq_json',ask)
    item,_=chat.make_turn('কর্মকর্তাকে কী বলব?', 'bn',[], {}, {'case_id':'a','case':{'farmer_notes':[question]}})
    handoff = next(a['target'] for a in item['actions'] if a['kind']=='handoff')
    assert 'আরও ছয়টা' in handoff and 'মোট' not in handoff
    assert '১৬১২৩' in item['text']
    assert not chat.observation_statement('What did the first photo show?',True)
    assert not chat.observation_statement('Explain the visible signs. How certain is the cause?',True)


def test_storage_uses_published_handling_steps_without_adding_materials(monkeypatch):
    monkeypatch.setattr(chat,'groq_json',lambda *args:{'topic':'storage','language':'bn','observation':True})
    detail = 'আলু বাছাই করুন এবং বাতাস চলাচলের ব্যবস্থা রাখুন।'
    monkeypatch.setattr(chat,'collect_sources',lambda *args:[{'label':'Potato storage','detail':detail,'status':'reference'}])
    item,_=chat.make_turn('আরও ছয়টা আলু নষ্ট পেলাম। এখন কী করব?', 'bn', [], {}, {'case_id':'a'})
    assert item['text'].endswith(detail) and 'আরও ছয়টা' in item['text'] and item['mode']=='tool'
    assert any(a['kind']=='note' for a in item['actions'])


def test_health_replaces_invented_confidence_and_chemical_advice_with_saved_findings(monkeypatch):
    def ask(system,data,tokens):
        return {'topic':'health','language':'en'} if 'evidence' not in data else {
            'reply':'About 80% sure. Apply a fungicide.'}
    monkeypatch.setattr(chat,'groq_json',ask)
    case = {'assessment':{'signs':['Concentric brown rings.'],'uncertainty':'Other leaf spots can look similar.'}}
    item,_=chat.make_turn('How certain is the cause?', 'en',[],{}, {'case_id':'x','case':case})
    assert item['mode']=='tool' and 'Concentric brown rings.' in item['text']
    assert '%' not in item['text'] and 'fungicide' not in item['text']


def test_authenticated_price_lookup_matches_crop_trade_type_market_and_date(client,session,monkeypatch):
    from app import main
    from datetime import datetime, timezone
    day = datetime.now(timezone.utc).date().isoformat()
    rows = f'market,commodity,price,unit,price_type,grade,observed_at\nTown,tomato,51,BDT/kg,wholesale,A,{day}\nTown,tomato,59,BDT/kg,retail,A,{day}\n'
    uploaded = client.post('/api/v1/market/imports',files={'file':('sample.csv',rows)},data={
        'source_name':'QA ledger','source_url':'https://example.org/ledger','permission_confirmed':'true'})
    assert uploaded.status_code==200
    own = main._chat_quotes(session['user_id'],'tomato','wholesale','town',day)
    assert len(own)==1 and float(own[0]['price'])==51 and own[0]['source']=='QA ledger'
    assert not main._chat_quotes('other-account','tomato','wholesale','town',day)
    assert not main._chat_quotes(session['user_id'],'rice','wholesale','town',day)

