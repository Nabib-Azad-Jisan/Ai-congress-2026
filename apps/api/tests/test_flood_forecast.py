"""Hourly accumulations, window completeness and expiry of saved FloodCrop outlooks."""
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app import services


START = datetime(2026, 11, 19, 23, tzinfo=timezone.utc)
HOUR = timedelta(hours=1)


def provider_data(monkeypatch, change=None):
    # Open-Meteo labels each precipitation amount with the END of its hour.
    times = [(START + i * HOUR).strftime('%Y-%m-%dT%H:%M') for i in range(73)]
    precipitation = [90] + [0]*23 + [10] + [0]*47 + [20]
    data = {'hourly': {'time':times,'precipitation':precipitation},
            'hourly_units': {'time':'iso8601','precipitation':'mm'}}
    if change:
        change(data)
    monkeypatch.setattr(services, 'current_utc', lambda: START + timedelta(minutes=35))
    def get(url, **kwargs):
        return httpx.Response(200, json=data, request=httpx.Request('GET',url))
    monkeypatch.setattr(services.httpx, 'get', get)
    return services.OpenMeteoProvider().forecast(24,90)


def test_intervals_align_to_current_hour_across_midnight(monkeypatch):
    data = provider_data(monkeypatch)
    for horizon, expected in [(24,10), (48,10), (72,30)]:
        result = services.preparedness(data, horizon)
        assert result['total_mm'] == expected
        assert result['level'] == 'monitor'
        assert result['valid_from'] == START.isoformat()
        assert result['horizon_valid_until'] == (START + horizon*HOUR).isoformat()
    assert data['hourly'][23] == {'time': (START + 23*HOUR).isoformat(), 'rain_mm':10}


@pytest.mark.parametrize('bad', [None, '0', True, -1])
def test_missing_or_invalid_later_values_only_block_incomplete_horizons(monkeypatch, bad):
    def change(data):
        data['hourly']['precipitation'][30] = bad
    data = provider_data(monkeypatch, change)
    assert services.preparedness(data, 24)['total_mm'] == 10
    with pytest.raises(ValueError):
        services.preparedness(data, 48)


@pytest.mark.parametrize('change', [
    lambda d: d['hourly']['time'].__setitem__(10, d['hourly']['time'][9]),
    lambda d: d['hourly'].__setitem__('time', None),
    lambda d: d.__setitem__('hourly', []),
    lambda d: d['hourly_units'].__setitem__('precipitation','inch'),
])
def test_invalid_provider_data_cannot_become_dry_forecast(monkeypatch, change):
    with pytest.raises(ValueError):
        services.preparedness(provider_data(monkeypatch, change), 24)


def test_expiry_tracks_selected_total_not_all_downloaded_hours(monkeypatch):
    saved = services.preparedness(provider_data(monkeypatch), 24)
    effective = services.compute_effective_weather(saved, START + 24*HOUR)
    assert effective['is_expired']
    assert effective['meta']['freshness'] == 'expired'
    assert effective['valid_until'] == (START + 72*HOUR).isoformat()


@pytest.mark.parametrize('retrieved', [None, 'not-a-date', (START + 2*HOUR).isoformat()])
def test_live_freshness_requires_a_valid_retrieval_time(monkeypatch, retrieved):
    saved = services.preparedness(provider_data(monkeypatch), 24)
    saved['meta']['retrieved_at'] = retrieved
    assert services.compute_effective_weather(saved, START + HOUR)['meta']['freshness'] == 'unknown'
