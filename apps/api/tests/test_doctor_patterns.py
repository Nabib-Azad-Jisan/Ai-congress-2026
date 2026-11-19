"""Crop checks should explain a visible pattern without turning it into a diagnosis."""
from copy import deepcopy

import pytest


from app import doctor_patterns


def observation(*features, **changes):
    return {'outcome': 'uncertain', 'crop_match': 'match', 'part': 'leaf',
            'condition': None, 'signs': ['Discolored areas are visible.'],
            'visible_features': list(features), **changes}


def test_uncertain_blight_like_foliage_gets_a_field_check_without_changing_assessment():
    obs = observation('collapsed_brown_leaflets', 'dark_stem_lesion')
    original = deepcopy(obs)
    check = doctor_patterns.field_check('potato', obs, 'en')
    assert 'late blight' in check['possible_explanation'].lower()
    assert 'underside' in check['next_check'] and 'officer' in check['next_check']
    assert check['source_url'].startswith('https://extension.umn.edu/')
    assert obs == original
    bangla = doctor_patterns.field_check('potato', obs, 'bn')
    assert 'নাবি ধসা' in bangla['possible_explanation'] and 'পাতার' in bangla['next_check']


@pytest.mark.parametrize('changes', [
    {'visible_features': []}, {'visible_features': ['collapsed_brown_leaflets']},
    {'visible_features': ['suspected_late_blight', 'nonspecific']},
    {'crop_match': 'unknown'}, {'crop_match': 'mismatch'},
    {'outcome': 'unrelated'}, {'outcome': 'no_visible_damage'}, {'part': 'produce'},
])
def test_check_requires_a_supported_combination_on_a_matching_symptomatic_crop(changes):
    obs = observation('collapsed_brown_leaflets', 'dark_stem_lesion', **changes)
    assert doctor_patterns.field_check('potato', obs, 'en') is None


@pytest.mark.parametrize('crop,part,pair,term', [
    ('potato', 'leaf', ('irregular_brown_leaf_blotches', 'collapsed_brown_leaflets'), 'late blight'),
    ('tomato', 'leaf', ('round_brown_leaf_spots', 'rings_inside_leaf_spots'), 'early blight'),
    ('tomato', 'leaf', ('upper_yellow_patches', 'olive_underside_growth'), 'leaf mold'),
    ('tomato', 'leaf', ('pale_centered_leaf_spots', 'black_pinpoints_in_leaf_spots'), 'septoria'),
    ('potato', 'produce', ('rough_corky_tuber_patches', 'raised_or_pitted_tuber_skin'), 'common scab'),
    ('potato', 'produce', ('sunken_tuber_patches', 'wrinkled_rings_on_tuber'), 'dry rot'),
    ('tomato', 'produce', ('lesion_at_blossom_end', 'dark_sunken_fruit_tissue'), 'blossom-end rot'),
    ('tomato', 'produce', ('round_sunken_ripe_fruit_spots', 'dark_centers_in_fruit_spots'), 'anthracnose'),
])
def test_crop_and_part_specific_checks_are_evidence_gated(crop, part, pair, term):
    obs = observation(*pair, part=part, outcome='possible_condition')
    check = doctor_patterns.field_check(crop, obs, 'en')
    assert term in check['possible_explanation'].lower()
    assert check['next_check'] and check['source_url'].startswith('https://')
    assert doctor_patterns.field_check(crop, observation(pair[0], part=part), 'en') is None
    for token in pair:
        assert token in doctor_patterns.visual_guidance(crop, 'auto')


def test_unknown_crop_conflicting_patterns_and_old_responses_have_no_automated_check():
    obs = observation('collapsed_brown_leaflets', 'dark_stem_lesion', 'round_brown_leaf_spots', 'rings_inside_leaf_spots')
    assert doctor_patterns.field_check('rice', obs, 'en') is None
    assert doctor_patterns.field_check('potato', obs, 'en') is None
    obs.pop('visible_features')
    assert doctor_patterns.field_check('tomato', obs, 'bn') is None


def test_prompt_limits_cues_to_selected_crop_and_asks_for_visible_evidence():
    assert doctor_patterns.visual_guidance('rice', 'leaf') == ''
    assert 'tuber' not in doctor_patterns.visual_guidance('tomato', 'leaf')
    assert 'lesion_at_blossom_end' not in doctor_patterns.visual_guidance('tomato', 'leaf')
    assert 'round_brown_leaf_spots' not in doctor_patterns.visual_guidance('tomato', 'other')
    assert 'visible_features' in doctor_patterns.visual_guidance('potato', 'leaf')


def test_tagged_features_do_not_introduce_a_competing_name_on_a_specific_leaf_assessment():
    obs = observation('collapsed_brown_leaflets', 'dark_stem_lesion', outcome='possible_condition',
                      condition='Possible early blight', distinguishing_sign='Distinct target rings.')
    assert doctor_patterns.field_check('potato', obs, 'en') is None
