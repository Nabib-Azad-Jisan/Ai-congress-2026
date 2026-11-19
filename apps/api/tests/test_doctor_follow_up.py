"""Two-view screening across the provider, private case, action and erasure boundaries."""
import base64
import io
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, BoundedSemaphore, Event

import httpx
import pytest
from PIL import Image

from app import main, services
from app.doctor_models import DoctorRegistry
from tests.test_doctor_vision import finding
from tests.test_platform import client, session


CASES = '/api/v1/doctor/cases'


def photo(color):
    stream = io.BytesIO()
    Image.new('RGB', (80, 60), color).save(stream, 'PNG')
    return ('crop.png', stream.getvalue(), 'image/png')


@pytest.fixture
def vision(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'mock-vision-only')
    calls = []

    def post(url, *, headers, json, timeout):
        content = json['messages'][-1]['content']
        prompt = content[0]['text']
        data = base64.b64decode(content[1]['image_url']['url'].split(',')[1])
        with Image.open(io.BytesIO(data)) as image:
            first = image.getpixel((40, 30))
            assert first[0] > 235 and first[1] < 15 and first[2] < 15
            if 'two panels' in prompt:
                assert 'top then bottom' in prompt and image.size == (80, 128)
                last = image.getpixel((40, 98))
                assert max(last[1:]) > 235 and last[0] < 15
        calls.append(prompt)
        label = 'Two views of the lesion' if 'two panels' in prompt else 'First view'
        return httpx.Response(200, json={'choices': [{'message': {'content': finding(
            part='leaf', produce_finding=None, subject='Tomato leaf', condition=label, next_steps=[label])}}]})

    monkeypatch.setattr(httpx, 'post', post)
    return calls


def saved(client, session):
    response = client.post(CASES, data={
        'plot_id': session['plot_id'], 'locale': 'bn',
        'farmer_context': json.dumps({'kind': 'leaf', 'extent': 'several'}),
    }, files={'image': photo('red')})
    assert response.status_code == 200, response.text
    return response.json()


def test_saved_follow_up_changes_one_case_and_one_action(client, session, vision):
    first = saved(client, session)
    case = f"{CASES}/{first['id']}"
    original = client.get(case + '/image').content
    actions = '/api/v1/actions?plot_id=' + session['plot_id']
    action = next(a for a in client.get(actions).json() if a['source_record_id'] == first['id'])
    client.patch('/api/v1/actions/' + action['id'], json={'status': 'done', 'comment': 'Checked in field'})
    response = client.post(case + '/follow-up', files={'image': photo('blue')}, data={'locale': 'en'})
    assert response.status_code == 200, response.text
    combined = response.json()
    assert combined['id'] == first['id'] and combined['photo_count'] == 2 and combined['second_photo_available']
    assert combined['initial_assessment'] == first['assessment'] and combined['initial_screening_locale'] == 'bn'
    assert combined['screening_locale'] == 'en' and combined['farmer_context'] == first['farmer_context']
    assert combined['assessment']['condition'] == 'Two views of the lesion'
    assert client.get(case + '/image').content == original
    assert Image.open(io.BytesIO(client.get(case + '/image?view=follow_up').content)).getpixel((40, 30))[2] > 235
    assert client.get(case).json()['assessment'] == combined['assessment']
    assert client.get(CASES).json()['total'] == 1
    updated = [a for a in client.get(actions).json() if a['source_record_id'] == first['id']]
    assert len(updated) == 1 and updated[0]['id'] == action['id'] and updated[0]['status'] == 'done'
    assert updated[0]['comment'] == 'Checked in field' and 'Two views' in updated[0]['reason']
    assert client.post(case + '/follow-up', files={'image': photo('blue')}).json()['id'] == first['id']
    assert client.post(case + '/follow-up', files={'image': photo('lime')}).status_code == 409
    assert len(vision) == 2
    assert 'follow_up_image_file' not in client.get('/api/v1/me/export').text


def test_unsaved_pair_counts_both_photos_and_leaves_no_files(client, session, vision):
    before = set(main.storage.iterdir())
    for _ in range(3):
        response = client.post(CASES, data={'crop': 'auto'}, files={'image': photo('red'), 'follow_up_image': photo('blue')})
        assert response.status_code == 200, response.text
        assert response.json()['photo_count'] == 2 and 'id' not in response.json()
        assert response.json()['assessment']['condition'] == 'Two views of the lesion'
        assert 'farmer_context' not in response.json()
    assert client.post(CASES, data={'crop': 'auto'}, files={'image': photo('red')}).status_code == 429
    assert len(vision) == 3 and client.get(CASES).json()['total'] == 0 and set(main.storage.iterdir()) == before


def test_invalid_context_and_invalid_preview_photo_never_reach_provider(client, session, vision):
    form = {'crop': 'auto', 'farmer_context': '{"kind":"leaf","location":"storage"}'}
    assert client.post(CASES, data=form, files={'image': photo('red')}).status_code == 422
    files = {'image': photo('red'), 'follow_up_image': ('second.png', b'bad image')}
    assert client.post(CASES, data={'crop': 'auto'}, files=files).status_code == 415
    assert not vision and client.get(CASES).json()['total'] == 0


def test_negative_leaf_assessment_requires_both_views_to_agree(client, session, vision, monkeypatch):
    def negative(*args, **kwargs):
        return httpx.Response(200, json={'choices': [{'message': {'content': finding(
            part='leaf', outcome='no_visible_damage', condition=None)}}]})
    monkeypatch.setattr(httpx, 'post', negative)
    def local_check(self, image, crop):
        red, _, blue = image.getpixel((40, 30))
        label = 'Tomato___healthy' if red > blue else 'Tomato___Late_blight'
        return {'model': {'version': 'test-leaf'}, 'classification': {'abstained': False, 'top_label': label}}
    monkeypatch.setattr(DoctorRegistry, 'infer', local_check)
    response = client.post(CASES, data={'crop': 'tomato'}, files={'image': photo('red'), 'follow_up_image': photo('blue')})
    assert response.status_code == 200, response.text
    assert response.json()['classification']['rejection_reason'] == 'model_disagreement'
    assert response.json()['assessment']['outcome'] == 'uncertain'


def test_lost_follow_up_file_keeps_two_view_history(client, session, vision):
    first = saved(client, session)
    case = f"{CASES}/{first['id']}"
    original_files = set(main.storage.iterdir())
    assert client.post(case + '/follow-up', files={'image': photo('blue')}).status_code == 200
    second, = set(main.storage.iterdir()) - original_files
    second.unlink()
    detail = client.get(case).json()
    assert detail['photo_count'] == 2 and not detail['second_photo_available'] and detail['image_available']
    assert detail['initial_assessment'] == first['assessment']
    assert client.get(case + '/image?view=follow_up').status_code == 410


def test_follow_up_failure_keeps_the_first_file_and_assessment(client, session, vision, monkeypatch):
    first = saved(client, session)
    case = f"{CASES}/{first['id']}"
    before = set(main.storage.iterdir())
    outsider = client.post('/api/v1/auth/demo', json={}).json()
    headers = {'Authorization': 'Bearer ' + outsider['token']}
    assert client.post(case + '/follow-up', files={'image': ('wrong.gif', b'bad')}, headers=headers).status_code == 404
    assert client.get(case + '/image?view=follow_up', headers=headers).status_code == 404
    assert client.post(case + '/follow-up', files={'image': ('crop.png', b'bad')}).status_code == 415
    assert len(vision) == 1
    with monkeypatch.context() as sub:
        sub.setattr(httpx, 'post', lambda *a, **kw: httpx.Response(200, json={
            'choices': [{'message': {'content': finding(crop_match='mismatch')}}]}))
        assert client.post(case + '/follow-up', files={'image': photo('blue')}).status_code == 422
    def fail(*args):
        raise RuntimeError('injected audit failure')
    with monkeypatch.context() as sub:
        sub.setattr(main, 'audit', fail)
        with pytest.raises(RuntimeError, match='injected audit failure'):
            client.post(case + '/follow-up', files={'image': photo('blue')})
    assert set(main.storage.iterdir()) == before
    detail = client.get(case).json()
    assert detail['assessment'] == first['assessment'] and not detail['second_photo_available']
    assert client.get(case + '/image?view=follow_up').status_code == 410


@pytest.mark.parametrize('target', ['case', 'plot', 'farm', 'account'])
def test_erasure_removes_both_private_photos(client, session, vision, target):
    before = set(main.storage.iterdir())
    first = saved(client, session)
    case = f"{CASES}/{first['id']}"
    assert client.post(case + '/follow-up', files={'image': photo('blue')}).status_code == 200
    assert len(set(main.storage.iterdir()) - before) == 2
    farm = client.get('/api/v1/farms').json()[0]['id']
    paths = {'case': case, 'plot': '/api/v1/plots/' + session['plot_id'], 'farm': '/api/v1/farms/' + farm,
             'account': '/api/v1/me'}
    deleted = client.delete(paths[target])
    assert deleted.status_code == 200, deleted.text
    assert set(main.storage.iterdir()) == before


def test_racing_follow_ups_keep_only_the_winning_pair(client, session, vision, monkeypatch):
    before = set(main.storage.iterdir())
    first = saved(client, session)
    case = f"{CASES}/{first['id']}"
    provider = httpx.post
    rendezvous = Barrier(2, timeout=8)
    monkeypatch.setattr(services, '_INFERENCE_SEMAPHORE', BoundedSemaphore(2))
    def together(*args, **kwargs):
        response = provider(*args, **kwargs)
        rendezvous.wait()
        return response
    monkeypatch.setattr(httpx, 'post', together)
    with ThreadPoolExecutor(2) as pool:
        futures = {color: pool.submit(client.post, case + '/follow-up', files={'image': photo(color)})
                   for color in ('blue', 'lime')}
        statuses = {color: f.result().status_code for color, f in futures.items()}
    assert sorted(statuses.values()) == [200, 409]
    data = client.get(case + '/image?view=follow_up').content
    pixel = Image.open(io.BytesIO(data)).getpixel((40, 30))
    assert pixel[2 if statuses['blue'] == 200 else 1] > 235
    assert client.get(CASES).json()['total'] == 1 and len(set(main.storage.iterdir()) - before) == 2


def test_delete_during_inference_cannot_restore_case_or_photos(client, session, vision, monkeypatch):
    before = set(main.storage.iterdir())
    first = saved(client, session)
    case = f"{CASES}/{first['id']}"
    started, finished = Event(), Event()
    provider = httpx.post
    def delayed(*args, **kwargs):
        response = provider(*args, **kwargs)
        started.set()
        assert finished.wait(8)
        return response
    monkeypatch.setattr(httpx, 'post', delayed)
    with ThreadPoolExecutor(1) as pool:
        request = pool.submit(client.post, case + '/follow-up', files={'image': photo('blue')})
        try:
            assert started.wait(8)
            assert client.delete(case).status_code == 200
        finally:
            finished.set()
        assert request.result().status_code == 404
    assert client.get(CASES).json()['total'] == 0 and set(main.storage.iterdir()) == before
