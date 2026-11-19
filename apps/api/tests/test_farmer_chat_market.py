"""Farmer-entered selling scenarios use per-kg bids and whole-trip expenses."""
import json

import pytest

from app.farmer_chat_market import calculate_market_turn


def turn(text, state=None, locale="en", slots=None):
    result = calculate_market_turn(text, state or {}, locale, slots)
    assert result is not None
    state, reply = result
    return json.loads(json.dumps(state)), reply.lower()


@pytest.mark.parametrize(("text", "locale", "expected"), [
    ("I have 100 kg. The farther market pays ৳5/kg more with extra transport ৳600.", "en", "nearer"),
    ("১০০ কেজি বিক্রি করব। দূরের বাজারে কেজিতে ৫ টাকা বেশি, অতিরিক্ত ভাড়া ৬০০ টাকা।", "bn", "কাছের"),
    ("100 kg bechbo, durer bazare proti kg 5 taka beshi, extra vara 600 taka.", "en", "nearer"),
])
def test_relative_price_and_trip_cost_flip_after_fare_change(text, locale, expected):
    state, reply = turn(text, locale=locale)
    assert expected in reply and ("100" in reply or "১০০" in reply)
    state, reply = turn("ভাড়া ৩০০ হলে?", state, "bn")
    assert "দূরের" in reply and ("২০০" in reply or "200" in reply)
    assert state["quantity_kg"] == "100"


def test_absolute_quotes_separate_transport_and_handling_then_changed_bid():
    state, reply = turn("20 kg. Buyer A offers ৳30/kg, transport ৳10, handling ৳5; "
                        "Buyer B offers ৳32/kg, transport ৳25, handling ৳9.")
    assert "buyer b" in reply and "৳21" in reply
    state, reply = turn("Buyer A will pay ৳31.25/kg instead.", state)
    assert "buyer a" in reply and "৳4" in reply


def test_leg_total_does_not_imply_incremental_cost():
    state, reply = turn("100 kg. Far market offers ৳5/kg more. Far market transport is ৳600.")
    assert "near" in reply and "?" in reply
    assert "extra_transport" not in state
    state, reply = turn("near transport ৳250", state)
    assert "farther" in reply and "৳150" in reply


def test_missing_information_persists_and_bare_answer_has_requested_units():
    state, reply = turn("Farther market offers ৳2.5/kg more. Extra transport costs ৳100.")
    assert "kg" in reply and "?" in reply
    state, reply = turn("40", state)
    assert "equal" in reply or "same" in reply
    assert state["quantity_kg"] == "40"


def test_relative_price_replaces_earlier_absolutes_and_single_later_quote_cannot_use_stale_pair():
    state, _ = turn("100 kg. Near market ৳30/kg and far market ৳40/kg. Extra fare ৳200.")
    state, reply = turn("Actually far market now pays ৳3/kg less.", state)
    assert "nearer" in reply and "৳500" in reply
    state, reply = turn("Far market is now ৳45/kg.", state)
    assert "near" in reply and "?" in reply


def test_prices_and_model_values_are_never_invented():
    state, reply = turn("I have 25 kg. Can I compare two buyers?", slots={
        "far_price_per_kg": 25, "near_price_per_kg": 80, "extra_transport": 100,
    })
    assert state["quantity_kg"] == "25"
    assert all(key not in state for key in ("near_price_per_kg", "far_price_per_kg", "extra_transport"))
    assert "?" in reply
    assert calculate_market_turn("What weather is expected tomorrow?", state, "en") is None


def test_buyer_totals_and_sacks_are_not_silently_treated_as_kg():
    state, reply = turn("I have 4 sacks. Buyer A pays ৳1200 for the lot, buyer B pays ৳1300 total.")
    assert all(key not in state for key in ("near_price_per_kg", "far_price_per_kg", "quantity_kg"))
    assert "kg" in reply and "?" in reply


def test_per_kg_handling_cost_scales_with_quantity():
    state, reply = turn("10 kg. Far market offers ৳2/kg more, extra transport ৳5, extra handling ৳1/kg.")
    assert "farther" in reply and "৳5" in reply
    state, reply = turn("What if I sell 20 kg?", state)
    assert "farther" in reply and "৳15" in reply


def test_new_comparison_does_not_reuse_the_old_trip_cost_or_quantity():
    state, _ = turn("10 kg. Far market pays ৳5/kg more, extra transport ৳10.")
    state, reply = turn("New comparison: near buyer offers ৳12/kg.", state)
    assert "quantity_kg" not in state and "extra_transport" not in state
    assert "?" in reply


def test_minimal_replies_complete_the_questions_the_bot_asked():
    state, _ = turn("Compare two buyers")
    state, _ = turn("১০০", state)
    state, reply = turn("30 and 35", state)
    assert "transport" in reply and "?" in reply
    state, reply = turn("0", state)
    assert "৳500" in reply and "?" not in reply


def test_new_price_with_confirmed_unit_updates_only_named_buyer():
    state, _ = turn("100 kg. Buyer A pays 30 taka/kg. Buyer B pays 35 taka/kg. Extra transport 600.")
    state, reply = turn("Buyer B now offers 38", state)
    assert "buyer b" in reply and "৳200" in reply
    state, reply = turn("What if the price is 39/kg?", state)
    assert "?" in reply and "39" in reply
    state, reply = turn("Buyer A", state)
    assert "buyer a" in reply and "৳700" in reply


def test_explicit_extra_cannot_inherit_sign_from_previous_near_market_clause():
    state, reply = turn("100 kg. Far market pays 35 taka/kg; near market pays 30 taka/kg. Extra transport 600.")
    assert state["extra_transport"] == "600" and "nearer" in reply


def test_unlabeled_fare_does_not_inherit_a_role_from_earlier_sentence():
    state, reply = turn("100 kg. The far buyer pays 5 taka/kg more. Transport is 600 taka.")
    assert state.get("unassigned", {}).get("value") == "600" and "?" in reply
    state, reply = turn("That's the extra expense.", state)
    assert "nearer" in reply and "৳100" in reply


def test_percent_or_per_km_expenses_are_not_whole_trip_taka():
    state, reply = turn("10 kg. Far buyer pays 2 taka/kg more. Extra transport 5 taka/km. Extra handling 3%.")
    assert "extra_transport" not in state and "extra_handling" not in state
    assert "?" in reply


def test_named_quotes_can_use_grounded_model_roles_without_far_and_near_inference():
    state, reply = turn("Compare buyers. 100 kg. Mina offers 20 taka/kg. Sumi offers 22 taka/kg. Extra fare 25.",
                        slots={"near_price_per_kg": 20, "far_price_per_kg": 22, "extra_transport": 999})
    assert "buyer b" in reply and "৳175" in reply


def test_non_market_location_does_not_start_a_comparison():
    assert calculate_market_turn("How do I keep water near my plants?", {}, "en") is None


def test_total_costs_can_replace_an_itemized_comparison_without_double_counting():
    state, _ = turn("100 kg. Far buyer pays 5 taka/kg more; extra transport 600.")
    state, reply = turn("Near market total costs 50 taka; far market total costs 370 taka.", state)
    assert "farther" in reply and "৳180" in reply
    state, reply = turn("Far market total costs are now 600.", state)
    assert "nearer" in reply and "৳50" in reply


def test_single_combined_expense_replaces_both_categories():
    state, reply = turn("100 kg. Far market 5 taka/kg higher. Extra transport and handling together 450 taka.")
    assert state["extra_total_cost"] == "450"
    assert "৳50" in reply and "farther" in reply
    state, reply = turn("Extra transport on its own is 350 now.", state)
    assert "handling" in reply and "?" in reply


@pytest.mark.parametrize("unknown", ["I have no idea about transport.", "Is transport the same?"])
def test_unsure_about_transport_does_not_confirm_a_zero_fare(unknown):
    state, _ = turn("100 kg. Far market 5 taka/kg higher.")
    result = calculate_market_turn(unknown, state, "en")
    assert result is None or ("extra_transport" not in result[0] and "?" in result[1])


def test_far_market_chitchat_does_not_reprint_an_old_comparison():
    state, _ = turn("100 kg. Far market pays 5 taka/kg more; extra fare 600.")
    assert calculate_market_turn("Is the far market open today?", state, "en") is None


def test_changed_lot_bid_must_be_reconfirmed_in_matching_units():
    state, _ = turn("100 kg. Far market pays 5 taka/kg more. Extra fare 600.")
    state, reply = turn("Far buyer now offers ৳3200 for the whole lot.", state)
    assert "?" in reply and "kg" in reply and "leaves you" not in reply
    state, reply = turn("30 and 32", state)
    assert "nearer" in reply and "৳400" in reply


def test_changed_load_of_unknown_sack_weight_requires_new_weight():
    state, _ = turn("100 kg. Far market pays 5 taka/kg more. Extra fare 600.")
    state, reply = turn("What if I sell 8 sacks instead?", state)
    assert "kg" in reply and "quantity_kg" not in state
    state, reply = turn("200 kg", state)
    assert "farther" in reply and "৳400" in reply


def test_confirmed_absolute_quotes_show_bid_units_and_net_proceeds_for_each_buyer():
    _, reply = turn("20 kg. Buyer A pays 30 taka/kg with transport 10 and handling 5. "
                    "Buyer B pays 32 taka/kg with transport 25 and handling 9.")
    assert all(value in reply for value in ("৳585", "৳606", "৳21", "/kg"))


def test_standalone_request_to_start_again_drops_the_old_scenario():
    state, _ = turn("100 kg. Far market pays 5 taka/kg more. Extra transport 600.")
    state, reply = turn("Start a new comparison", state)
    assert "quantity_kg" not in state and "extra_transport" not in state
    assert "kg" in reply and "?" in reply
