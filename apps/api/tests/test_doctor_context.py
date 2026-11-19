import pytest
from fastapi import HTTPException

from app.doctor_context import FarmerContext


def test_context_records_only_reported_answers():
    answers = FarmerContext.from_form('{"kind":"produce","location":"storage","extent":"many"}')
    assert answers.model_dump() == {
        'kind': 'produce', 'onset': 'unknown', 'location': 'storage', 'extent': 'many'
    }


@pytest.mark.parametrize('value', [
    'not-json', '{}', '{"kind":"plant"}', '{"kind":"leaf","extent":"entire farm"}',
    '{"kind":"produce","onset":"today"}', '{"kind":"leaf","location":"storage"}',
    '{"kind":"leaf","unrelated":"extra"}',
])
def test_malformed_or_mixed_context_is_rejected(value):
    with pytest.raises(HTTPException) as error:
        FarmerContext.from_form(value)
    assert error.value.status_code == 422

