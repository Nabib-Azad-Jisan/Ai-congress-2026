"""Recover from a single bad vision generation while respecting service limits."""
import json

import httpx
import pytest
from fastapi import HTTPException
from PIL import Image

from app import doctor_vision as vision


def completion(**changes):
    data = {
        'outcome': 'possible_condition', 'subject': 'Potato leaf', 'part': 'leaf',
        'crop_match': 'match', 'pattern': 'Irregular burnt margins',
        'marker': 'nonspecific', 'condition': None, 'produce_finding': None,
        'distinguishing_sign': None, 'signs': ['Brown margins are visible.'],
        'explanation': 'Leaf damage is visible.', 'uncertainty': 'The cause is unclear.',
        'next_steps': ['Take a closer photo of the lesion margin.'],
    }
    data.update(changes)
    return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(data)}}]})


def run(monkeypatch, replies, calls):
    monkeypatch.setenv('GROQ_API_KEY', 'fake-test-value')
    def post(url, *, headers, json, timeout):
        calls.append(json.copy())
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply
    monkeypatch.setattr(httpx, 'post', post)
    return vision.inspect_photo(Image.new('RGB', (12, 12)), 'potato', 'leaf', 'English')


@pytest.mark.parametrize('first', [
    httpx.ConnectTimeout('connection timed out'),
    httpx.Response(503),
    httpx.Response(200, json={'choices':[{'message':{'content':'{"subject":'}, 'finish_reason':'length'}]}),
    httpx.Response(400, json={'error': {'code':'json_validate_failed'}}),
])
def test_one_transient_fault_is_recovered_without_resubmission(monkeypatch, first):
    calls = []
    report = run(monkeypatch, [first, completion()], calls)
    assert len(calls) == 2
    assert report['assessment']['signs'] == ['Brown margins are visible.']
    assert calls[0]['messages'][-1]['content'][-1] == calls[1]['messages'][-1]['content'][-1]


def test_leaf_can_omit_unobserved_optional_fields(monkeypatch):
    answer = completion().json()
    data = json.loads(answer['choices'][0]['message']['content'])
    for field in ('condition', 'produce_finding', 'distinguishing_sign'):
        del data[field]
    answer['choices'][0]['message']['content'] = json.dumps(data)
    calls = []
    result = run(monkeypatch, [httpx.Response(200, json=answer)], calls)
    assert len(calls) == 1
    assert result['assessment']['condition'] is None


@pytest.mark.parametrize('status,expected', [(429, 429), (401, 503), (403, 503), (400, 503)])
def test_quota_and_invalid_requests_do_not_consume_a_second_attempt(monkeypatch, status, expected):
    calls = []
    with pytest.raises(HTTPException) as exc:
        run(monkeypatch, [httpx.Response(status,headers={'Retry-After':'25'})], calls)
    assert exc.value.status_code == expected and len(calls) == 1
    if status == 429:
        assert exc.value.headers == {'Retry-After':'25'}


def test_unusable_response_after_retry_is_an_explicit_error(monkeypatch):
    calls = []
    bad = httpx.Response(200, json={'choices':[]})
    with pytest.raises(HTTPException) as exc:
        run(monkeypatch, [bad, bad], calls)
    assert exc.value.status_code == 502 and len(calls) == 2

def test_photo_response_preserves_specific_visible_features(monkeypatch):
    calls = []
    result = run(monkeypatch, [completion(visible_features=['irregular_brown_leaf_blotches'])], calls)
    assert result['assessment']['visible_features'] == ['irregular_brown_leaf_blotches']
    assert 'irregular_brown_leaf_blotches' in calls[0]['messages'][0]['content']
