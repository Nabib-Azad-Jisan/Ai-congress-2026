"""Saved rainfall advice is tied to a plot's current farm and vulnerability."""
import pytest

from tests.test_platform import client, session


@pytest.mark.parametrize('route', ['farm', 'plot_vulnerability', 'flood_vulnerability'])
@pytest.mark.parametrize('changed', [True, False])
def test_changing_flood_context_retires_saved_advice(client, session, route, changed):
    plot = '/api/v1/plots/' + session['plot_id']
    flood = '/api/v1/flood/plots/' + session['plot_id']
    previous = client.get(plot).json()
    assert client.get(flood + '/outlook').status_code == 200
    before = client.get(plot + '/action-center').json()
    evidence = before['evidence']['weather'][0]['id']
    if route == 'farm':
        farm_id = previous['farm_id']
        if changed:
            farm_id = client.post('/api/v1/farms', json={'name':'Other farm','district':'Sylhet'}).json()['id']
        response = client.patch(plot, json={'farm_id':farm_id})
    else:
        low_lying = previous.get('low_lying', False)
        payload = {'low_lying': not low_lying if changed else low_lying}
        response = (client.patch(plot, json=payload) if route == 'plot_vulnerability'
                    else client.post(flood + '/vulnerability', json=payload))
    assert response.status_code == 200, response.text
    after = client.get(plot + '/action-center').json()
    active = [a for a in after['actions'] if a['topic'] == 'flood' and a['status'] == 'open']
    if changed:
        assert after['evidence']['weather'] == []
        assert active and all('refresh' in a['title'].lower() for a in active)
        assert all(a.get('source_record_id') != evidence for a in active)
    else:
        assert after['evidence']['weather'][0]['id'] == evidence
        assert active and all(a['title'] == 'Review rain preparedness' for a in active)
