"""Forecast requests must respect location consent and retain trustworthy plot evidence."""
import pytest
import httpx

from app.db import Record, Session
from app.services import DemoWeatherProvider, OpenMeteoProvider
from tests.test_platform import client, session


def configure(client, lat=24.0):
    farm = client.get('/api/v1/farms').json()[0]
    fields = dict(latitude=lat, longitude=90, location_consent=True, location_name='Test farm',
                  district='Gazipur', country='Bangladesh')
    client.patch('/api/v1/farms/'+farm['id']+'/location', json=fields).raise_for_status()
    return farm['id']


def example(self, lat, lon):
    data = DemoWeatherProvider().forecast(lat, lon)
    data['meta'].update(mode='LIVE', is_simulated=False, source_name='Weather test provider')
    return data


def test_live_requires_explicit_consent_even_with_legacy_coordinates(client, session, monkeypatch):
    farm = configure(client)
    with Session() as db:
        row = db.get(Record, farm)
        row.payload = {k:v for k,v in row.payload.items() if k != 'location_consent'}
        db.commit()
    monkeypatch.setattr(OpenMeteoProvider, 'forecast', example)
    url = '/api/v1/flood/plots/'+session['plot_id']+'/outlook'
    assert client.get(url+'?mode=LIVE').status_code == 422


def test_demo_preview_preserves_live_evidence_and_actions(client, session, monkeypatch):
    configure(client)
    monkeypatch.setattr(OpenMeteoProvider, 'forecast', example)
    plot = session['plot_id']
    url = '/api/v1/flood/plots/'+plot+'/outlook'
    client.get(url+'?mode=LIVE&horizon_hours=24').raise_for_status()
    demo = client.get(url+'?mode=DEMO&horizon_hours=72').json()
    assert demo['meta']['is_simulated'] and demo['horizon_hours']==72
    center = client.get('/api/v1/plots/'+plot+'/action-center').json()
    saved = center['evidence']['weather'][0]
    assert saved['meta']['mode']=='LIVE' and saved['horizon_hours']==24
    active = [a for a in center['actions'] if a['topic']=='flood' and a['status']=='open']
    assert len(active)==1 and active[0]['meta']['mode']=='LIVE'


def test_demo_viewed_during_first_live_fetch_cannot_keep_demo_as_saved_evidence(client, session, monkeypatch):
    configure(client)
    plot = session['plot_id']
    url = '/api/v1/flood/plots/'+plot+'/outlook'
    def preview_during_live(self, lat, lon):
        client.get(url+'?mode=DEMO').raise_for_status()
        return example(self, lat, lon)
    monkeypatch.setattr(OpenMeteoProvider, 'forecast', preview_during_live)
    client.get(url+'?mode=LIVE').raise_for_status()
    evidence = client.get('/api/v1/plots/'+plot+'/action-center').json()['evidence']
    assert evidence['weather'][0]['meta']['mode'] == 'LIVE'


@pytest.mark.parametrize('outage', [False, True])
def test_location_changed_during_refresh_cannot_restore_old_forecast(client, session, monkeypatch, outage):
    configure(client)
    plot = session['plot_id']
    url = '/api/v1/flood/plots/'+plot+'/outlook'
    def change_location(self, lat, lon):
        configure(client, lat=25.0)
        if outage:
            raise httpx.ConnectError('test outage')
        return example(self,lat,lon)
    monkeypatch.setattr(OpenMeteoProvider, 'forecast', change_location)
    assert client.get(url+'?mode=LIVE').status_code == 409
    assert not client.get('/api/v1/plots/'+plot+'/action-center').json()['evidence']['weather']
