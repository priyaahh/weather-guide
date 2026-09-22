import pytest
from app.sop_engine import match_sops, evaluate_condition, is_sop_matching


# 1. Numeric condition matches
def test_numeric_condition_matches():
    sop = {
        "id": "SOP-TEST-001",
        "name": "Test UV",
        "trigger_type": "numeric",
        "severity": "medium",
        "conditions": {"field": "uv_index", "operator": ">=", "value": 8.0}
    }
    weather = {"uv_index": 9.5}
    matches = match_sops([sop], weather)
    assert len(matches) == 1
    assert matches[0]["id"] == "SOP-TEST-001"


# 2. Numeric condition does not match
def test_numeric_condition_does_not_match():
    sop = {
        "id": "SOP-TEST-001",
        "name": "Test UV",
        "trigger_type": "numeric",
        "severity": "medium",
        "conditions": {"field": "uv_index", "operator": ">=", "value": 8.0}
    }
    weather = {"uv_index": 5.0}
    matches = match_sops([sop], weather)
    assert len(matches) == 0


# 3. Compound condition matches when ALL conditions are true
def test_compound_condition_all_true_matches():
    sop = {
        "id": "SOP-TEST-002",
        "name": "Heavy Rain & Wind",
        "trigger_type": "compound",
        "severity": "high",
        "conditions": [
            {"field": "precipitation", "operator": ">=", "value": 10.0},
            {"field": "wind_gusts_10m", "operator": ">=", "value": 40.0}
        ]
    }
    weather = {"precipitation": 15.0, "wind_gusts_10m": 50.0}
    matches = match_sops([sop], weather)
    assert len(matches) == 1
    assert matches[0]["id"] == "SOP-TEST-002"


# 4. Compound condition does not match when one condition is false
def test_compound_condition_one_false_no_match():
    sop = {
        "id": "SOP-TEST-002",
        "name": "Heavy Rain & Wind",
        "trigger_type": "compound",
        "severity": "high",
        "conditions": [
            {"field": "precipitation", "operator": ">=", "value": 10.0},
            {"field": "wind_gusts_10m", "operator": ">=", "value": 40.0}
        ]
    }
    weather = {"precipitation": 15.0, "wind_gusts_10m": 20.0}
    matches = match_sops([sop], weather)
    assert len(matches) == 0


# 5. Fuzzy SOPs are skipped
def test_fuzzy_sops_are_skipped():
    sop = {
        "id": "SOP-TEST-FUZZY",
        "name": "Fuzzy Picnic",
        "trigger_type": "fuzzy",
        "severity": "low",
        "description": "Fuzzy picnic assessment"
    }
    weather = {"temperature_2m": 22.0, "precipitation": 0.0}
    matches = match_sops([sop], weather)
    assert len(matches) == 0


# 6. Multiple SOPs can match simultaneously
def test_multiple_sops_match_simultaneously():
    sop1 = {
        "id": "SOP-001",
        "trigger_type": "numeric",
        "severity": "medium",
        "conditions": {"field": "uv_index", "operator": ">=", "value": 8.0}
    }
    sop2 = {
        "id": "SOP-003",
        "trigger_type": "numeric",
        "severity": "high",
        "conditions": {"field": "apparent_temperature", "operator": ">=", "value": 35.0}
    }
    weather = {"uv_index": 9.0, "apparent_temperature": 38.0}
    matches = match_sops([sop1, sop2], weather)
    assert len(matches) == 2


# 7. Severity ordering is critical -> high -> medium -> low
def test_severity_ordering():
    sop_low = {"id": "LOW", "trigger_type": "numeric", "severity": "low", "conditions": {"field": "temp", "operator": ">", "value": 0}}
    sop_critical = {"id": "CRITICAL", "trigger_type": "numeric", "severity": "critical", "conditions": {"field": "temp", "operator": ">", "value": 0}}
    sop_medium = {"id": "MEDIUM", "trigger_type": "numeric", "severity": "medium", "conditions": {"field": "temp", "operator": ">", "value": 0}}
    sop_high = {"id": "HIGH", "trigger_type": "numeric", "severity": "high", "conditions": {"field": "temp", "operator": ">", "value": 0}}

    sops = [sop_low, sop_critical, sop_medium, sop_high]
    weather = {"temp": 10}

    matches = match_sops(sops, weather)
    ordered_ids = [s["id"] for s in matches]
    assert ordered_ids == ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


# 8. Same-severity SOPs preserve YAML/input order
def test_same_severity_preserves_input_order():
    sop_a = {"id": "A", "trigger_type": "numeric", "severity": "high", "conditions": {"field": "v", "operator": "==", "value": 1}}
    sop_b = {"id": "B", "trigger_type": "numeric", "severity": "high", "conditions": {"field": "v", "operator": "==", "value": 1}}
    sop_c = {"id": "C", "trigger_type": "numeric", "severity": "high", "conditions": {"field": "v", "operator": "==", "value": 1}}

    matches = match_sops([sop_a, sop_b, sop_c], {"v": 1})
    ordered_ids = [s["id"] for s in matches]
    assert ordered_ids == ["A", "B", "C"]


# 9. Missing weather field does not crash and results in no match
def test_missing_weather_field_no_crash():
    sop = {
        "id": "SOP-MISSING",
        "trigger_type": "numeric",
        "severity": "medium",
        "conditions": {"field": "unknown_metric", "operator": ">=", "value": 10.0}
    }
    weather = {"temperature_2m": 25.0}
    matches = match_sops([sop], weather)
    assert len(matches) == 0


# 10. No matching SOP returns an empty list
def test_no_match_returns_empty_list():
    sop = {
        "id": "SOP-001",
        "trigger_type": "numeric",
        "severity": "high",
        "conditions": {"field": "temperature_2m", "operator": ">", "value": 50.0}
    }
    weather = {"temperature_2m": 20.0}
    assert match_sops([sop], weather) == []


# 11. All supported operators work: >=, <=, >, <, ==
def test_all_supported_operators():
    weather = {"val": 10}

    op_gte = {"id": "1", "trigger_type": "numeric", "severity": "low", "conditions": {"field": "val", "operator": ">=", "value": 10}}
    op_lte = {"id": "2", "trigger_type": "numeric", "severity": "low", "conditions": {"field": "val", "operator": "<=", "value": 10}}
    op_gt  = {"id": "3", "trigger_type": "numeric", "severity": "low", "conditions": {"field": "val", "operator": ">", "value": 5}}
    op_lt  = {"id": "4", "trigger_type": "numeric", "severity": "low", "conditions": {"field": "val", "operator": "<", "value": 15}}
    op_eq  = {"id": "5", "trigger_type": "numeric", "severity": "low", "conditions": {"field": "val", "operator": "==", "value": 10}}
    op_bad = {"id": "6", "trigger_type": "numeric", "severity": "low", "conditions": {"field": "val", "operator": "UNKNOWN", "value": 10}}

    all_sops = [op_gte, op_lte, op_gt, op_lt, op_eq, op_bad]
    matches = match_sops(all_sops, weather)
    matched_ids = [s["id"] for s in matches]

    assert matched_ids == ["1", "2", "3", "4", "5"]
