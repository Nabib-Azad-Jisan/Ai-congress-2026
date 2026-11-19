"""Farmer-reported observations kept separate from image findings."""
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator


class FarmerContext(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['leaf', 'produce']
    onset: Literal['today', 'days', 'week_plus', 'unknown'] = 'unknown'
    location: Literal['field', 'storage', 'unknown'] = 'unknown'
    extent: Literal['one', 'several', 'many', 'unknown'] = 'unknown'

    @model_validator(mode='after')
    def check_answers_match_questions(self):
        if self.kind == 'leaf' and self.location != 'unknown':
            raise ValueError('Harvest location applies to produce.')
        if self.kind == 'produce' and self.onset != 'unknown':
            raise ValueError('Symptom onset applies to a leaf observation.')
        return self

    @classmethod
    def from_form(cls, value: str) -> 'FarmerContext':
        try:
            return cls.model_validate_json(value)
        except ValidationError as exc:
            raise HTTPException(422, 'Choose valid answers for the selected plant part.') from exc

