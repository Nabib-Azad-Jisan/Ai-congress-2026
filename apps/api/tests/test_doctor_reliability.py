"""Exercise private leaf screening when the vision service cannot complete a request."""
import pytest
from fastapi import HTTPException
from PIL import Image

from app import doctor_vision
from app.doctor_models import DoctorRegistry, PLANT_LABELS
from tests.test_doctor_models import fixture_bundle
from tests.test_doctor_vision import upload
from tests.test_platform import client, session


@pytest.fixture
def unavailable(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-only')
    def rate_limit(*args):
        raise HTTPException(429, 'Try again in 12 seconds.', headers={'Retry-After': '12'})
    monkeypatch.setattr(doctor_vision, 'inspect_photo', rate_limit)


@pytest.fixture
def local_model(monkeypatch):
    def screen(self, image, crop):
        assert crop in ('tomato', 'potato')
        return dict(crop=crop, classification={'top_label': 'unknown', 'abstained': True,
                    'rejection_reason': 'crop_mismatch'}, model={'model_id':'plantvillage',
                    'version':'leaf-reference','available':True}, status='unable_to_classify',
                    advice=['Check the underside of a leaf.'], quality_flags=[], disclaimer='Research screening.')
    monkeypatch.setattr(DoctorRegistry, 'infer', screen)


def test_remote_outage_uses_actual_leaf_result_and_preserves_provenance(client, session, unavailable, local_model):
    response = upload(client, plot_id=session['plot_id'], plant_part='leaf')
    assert response.status_code == 200, response.text
    case = response.json()
    assert case['fallback_reason'] == 'vision_unavailable'
    assert case['model']['model_id'] == 'plantvillage' and case['classification']['abstained']
    assert case['meta']['mode'] == 'MIXED' and 'assessment' not in case
    assert client.get('/api/v1/doctor/cases/'+case['id']).json()['fallback_reason'] == case['fallback_reason']


@pytest.mark.parametrize('part', ['auto','other'])
def test_cloud_outage_never_assumes_a_leaf(client, session, unavailable, monkeypatch, part):
    monkeypatch.setattr(DoctorRegistry, 'infer', lambda *_: pytest.fail('Leaf identity is unknown'))
    response = upload(client, plot_id=session['plot_id'], plant_part=part)
    assert response.status_code == 429 and response.json()['code'] == 'VISION_UNAVAILABLE'
    assert response.headers['retry-after'] == '12'
    assert client.get('/api/v1/doctor/cases').json()['total'] == 0


def test_explicit_local_retry_skips_remote_call(client, session, local_model, monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-only')
    monkeypatch.setattr(doctor_vision, 'inspect_photo', lambda *_: pytest.fail('Duplicate remote request'))
    assert upload(client, crop='potato', plant_part='other', screening_mode='local_leaf').status_code == 422
    case = upload(client, crop='potato', plant_part='leaf', screening_mode='local_leaf').json()
    assert case['model']['model_id'] == 'plantvillage' and 'id' not in case


@pytest.mark.parametrize('wide, strength, hint', [('Potato___Early_blight', 8, True),
    ('Potato___healthy', 8, False), ('Strawberry___Leaf_scorch', 8, False),
    ('Potato___Early_blight', 0.05, False)])
def test_local_crop_mismatch_checks_full_photo_without_forcing_a_diagnosis(monkeypatch, tmp_path, wide, strength, hint):
    import torch
    registry, _ = fixture_bundle(tmp_path, monkeypatch)
    bundle = registry._bundle('plantvillage')
    def logits(label):
        row = torch.zeros((1, len(PLANT_LABELS)))
        row[0, PLANT_LABELS.index(label)] = strength
        return row
    views = iter([logits('Tomato___Late_blight'), logits(wide)])
    monkeypatch.setitem(bundle, 'model', lambda _: next(views))
    monkeypatch.setattr('app.doctor_models.image_quality', lambda _: [])
    result = registry.infer(Image.new('RGB', (480, 320)), 'potato')['classification']
    assert result['abstained'] and result['top_label'] == 'unknown'
    if hint:
        assert result.get('pattern_hint') == 'blight_like'
        assert result['rejection_reason'] == 'conflicting_leaf_views'
    else:
        assert not result.get('pattern_hint')
