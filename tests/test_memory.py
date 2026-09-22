from unittest.mock import patch, MagicMock
import pytest
from langgraph.checkpoint.memory import MemorySaver

from app.graph import build_graph, app_graph

MOCK_LOCATION = {
    "name": "Mumbai",
    "latitude": 19.076,
    "longitude": 72.8777,
    "country": "India"
}

MOCK_SEVERE_WEATHER = {
    "temperature_2m": 32.0,
    "apparent_temperature": 36.0,
    "precipitation": 12.0,
    "precipitation_probability": 80.0,
    "wind_speed_10m": 28.0,
    "wind_gusts_10m": 45.0,
    "uv_index": 9.0,
    "visibility": 800.0
}


# Test 1: Same thread retains state across invocations
@patch("app.graph.geocode_location")
@patch("app.graph.api_fetch_weather")
@patch("app.graph.compose_response")
def test_same_thread_retains_state(mock_compose, mock_fetch, mock_geo):
    mock_geo.return_value = MOCK_LOCATION
    mock_fetch.return_value = MOCK_SEVERE_WEATHER
    mock_compose.return_value = "Stay hydrated during exercise."

    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "demo-session-1"}}

    # Turn 1: Explicit location
    res1 = graph.invoke(
        {"user_message": "Can I go cycling in Mumbai?", "location": "Mumbai"},
        config=config
    )
    assert res1["location"] == "Mumbai"

    # Turn 2: Follow-up query without location in user_message
    res2 = graph.invoke(
        {"user_message": "What about later today?"},
        config=config
    )
    # Location should be retained from Turn 1 state
    assert res2["location"] == "Mumbai"


# Test 2: Different threads are isolated
@patch("app.graph.geocode_location")
@patch("app.graph.api_fetch_weather")
@patch("app.graph.compose_response")
def test_different_threads_are_isolated(mock_compose, mock_fetch, mock_geo):
    mock_geo.return_value = MOCK_LOCATION
    mock_fetch.return_value = MOCK_SEVERE_WEATHER
    mock_compose.return_value = "Advisory response."

    graph = build_graph(checkpointer=MemorySaver())

    # Thread A sets location to Mumbai
    config_a = {"configurable": {"thread_id": "thread-a"}}
    graph.invoke({"user_message": "Cycling in Mumbai", "location": "Mumbai"}, config=config_a)

    # Thread B has no location
    config_b = {"configurable": {"thread_id": "thread-b"}}
    res_b = graph.invoke({"user_message": "Cycling?"}, config=config_b)

    # Thread B should NOT inherit Thread A's location
    state_b = graph.get_state(config_b)
    assert state_b.values.get("location") == "" or res_b.get("response") == "I couldn't resolve that location. Please provide a valid city or location."


# Test 3: No persistent external memory dependency
def test_checkpointer_is_in_memory():
    # Verify checkpointer class is MemorySaver (in-memory)
    assert hasattr(app_graph, "checkpointer")
    assert isinstance(app_graph.checkpointer, MemorySaver)


# Test 4 & 5: Memory does not bypass weather fetching
@patch("app.graph.geocode_location")
@patch("app.graph.api_fetch_weather")
@patch("app.graph.compose_response")
def test_memory_does_not_bypass_weather_fetching(mock_compose, mock_fetch, mock_geo):
    mock_geo.return_value = MOCK_LOCATION
    mock_fetch.return_value = MOCK_SEVERE_WEATHER
    mock_compose.return_value = "Response text."

    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "session-weather-test"}}

    # Turn 1
    graph.invoke({"user_message": "Cycling in Mumbai", "location": "Mumbai"}, config=config)
    assert mock_fetch.call_count == 1

    # Turn 2 on same thread
    graph.invoke({"user_message": "What about this afternoon?"}, config=config)
    # Fetch weather MUST be called again for Turn 2 to get fresh weather!
    assert mock_fetch.call_count == 2
