import os
from unittest.mock import patch, MagicMock
import pytest

from app.llm import (
    build_weather_facts,
    select_fuzzy_sop,
    compose_response,
    get_llm_model,
    LLMError,
    ALLOWED_WEATHER_FIELDS
)


# Mock sample SOPs
SAMPLE_SOPS = [
    {
        "id": "SOP-001",
        "name": "High UV Exercise",
        "trigger_type": "numeric",
        "severity": "medium",
        "conditions": {"field": "uv_index", "operator": ">=", "value": 8.0}
    },
    {
        "id": "SOP-010",
        "name": "Fuzzy Picnic Comfort",
        "trigger_type": "fuzzy",
        "severity": "low",
        "description": "Fuzzy picnic evaluation"
    },
    {
        "id": "SOP-011",
        "name": "Fuzzy Walk Comfort",
        "trigger_type": "fuzzy",
        "severity": "low",
        "description": "Fuzzy walk evaluation"
    }
]

SAMPLE_WEATHER = {
    "temperature_2m": 22.5,
    "apparent_temperature": 23.0,
    "precipitation": 0.0,
    "precipitation_probability": 10.0,
    "wind_speed_10m": 8.0,
    "wind_gusts_10m": 12.0,
    "uv_index": 4.0,
    "visibility": 10000.0,
    "unauthorized_field": "secret_data",
    "internal_cache_id": 9999
}


# 1. build_weather_facts includes only allowed weather fields
def test_build_weather_facts_filters_allowed_fields_only():
    facts = build_weather_facts(SAMPLE_WEATHER)
    assert "temperature_2m" in facts
    assert "uv_index" in facts
    assert "unauthorized_field" not in facts
    assert "internal_cache_id" not in facts
    assert set(facts.keys()).issubset(set(ALLOWED_WEATHER_FIELDS))


# 2. Fuzzy SOP filtering only includes trigger_type == "fuzzy"
def test_select_fuzzy_sop_filters_fuzzy_trigger_types_only():
    mock_model = MagicMock()
    mock_model.invoke.return_value.content = "SOP-010"

    res = select_fuzzy_sop(SAMPLE_SOPS, "Can I go for a picnic?", SAMPLE_WEATHER, model=mock_model)

    assert res is not None
    assert res["id"] == "SOP-010"
    # Verify prompt sent contained SOP-010 and SOP-011 but NOT SOP-001
    prompt_sent = mock_model.invoke.call_args[0][0]
    assert "SOP-010" in prompt_sent
    assert "SOP-011" in prompt_sent
    assert "SOP-001" not in prompt_sent


# 3. Valid Gemini-selected SOP ID is accepted
def test_select_fuzzy_sop_valid_id_accepted():
    mock_model = MagicMock()
    mock_model.invoke.return_value.content = "SOP-011"

    res = select_fuzzy_sop(SAMPLE_SOPS, "Is it nice for a walk?", SAMPLE_WEATHER, model=mock_model)

    assert res is not None
    assert res["id"] == "SOP-011"


# 4. Invalid Gemini-selected SOP ID becomes None
def test_select_fuzzy_sop_invalid_id_returns_none():
    mock_model = MagicMock()
    mock_model.invoke.return_value.content = "SOP-999-FAKE"

    res = select_fuzzy_sop(SAMPLE_SOPS, "Picnic question", SAMPLE_WEATHER, model=mock_model)

    assert res is None


# 5. Gemini returning NONE becomes None
def test_select_fuzzy_sop_none_string_returns_none():
    mock_model = MagicMock()
    mock_model.invoke.return_value.content = "NONE"

    res = select_fuzzy_sop(SAMPLE_SOPS, "Random question", SAMPLE_WEATHER, model=mock_model)

    assert res is None


# 6. No fuzzy SOPs returns None without invoking model
def test_select_fuzzy_sop_no_fuzzy_candidates_returns_none():
    mock_model = MagicMock()
    numeric_sops_only = [SAMPLE_SOPS[0]]

    res = select_fuzzy_sop(numeric_sops_only, "Picnic question", SAMPLE_WEATHER, model=mock_model)

    assert res is None
    mock_model.invoke.assert_not_called()


# 7. Composer receives only controlled weather facts
def test_compose_response_receives_controlled_weather_facts():
    mock_model = MagicMock()
    mock_model.invoke.return_value.content = "Weather looks clear and mild for a picnic."

    response_text = compose_response(
        user_request="How is the picnic weather?",
        weather_facts=SAMPLE_WEATHER,
        selected_sop=SAMPLE_SOPS[1],
        model=mock_model
    )

    assert response_text == "Weather looks clear and mild for a picnic."

    prompt_sent = mock_model.invoke.call_args[0][0]
    assert "temperature_2m" in prompt_sent
    assert "unauthorized_field" not in prompt_sent
    assert "SOP-010" in prompt_sent


# 8. LLM/API failure is converted to LLMError
def test_llm_api_failure_raises_llm_error():
    mock_model = MagicMock()
    mock_model.invoke.side_effect = Exception("API connection quota exceeded")

    with pytest.raises(LLMError) as exc_info:
        select_fuzzy_sop(SAMPLE_SOPS, "Walk query", SAMPLE_WEATHER, model=mock_model)

    assert "Fuzzy SOP selection failed" in str(exc_info.value)

    with pytest.raises(LLMError) as exc_info_comp:
        compose_response("Walk query", SAMPLE_WEATHER, model=mock_model)

    assert "Response composition failed" in str(exc_info_comp.value)


# 9. API key is read from environment/configuration and is not hard-coded
def test_get_llm_model_reads_env_var_and_raises_error_when_missing():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(LLMError) as exc_info:
            get_llm_model()
        assert "GOOGLE_API_KEY environment variable is missing" in str(exc_info.value)

    with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_key_12345"}):
        with patch("app.llm.ChatGoogleGenerativeAI") as mock_chat_class:
            mock_chat_class.return_value = MagicMock()
            model = get_llm_model()
            mock_chat_class.assert_called_once_with(
                model="gemini-1.5-flash",
                google_api_key="fake_key_12345",
                temperature=0.0
            )
            assert model is not None
