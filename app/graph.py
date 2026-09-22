import re
from typing import TypedDict, Optional, List, Dict, Any

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.sop_loader import load_sops
from app.sop_engine import match_sops
from app.weather import geocode_location, fetch_weather as api_fetch_weather, LocationNotFoundError, WeatherAPIError
from app.llm import select_fuzzy_sop, compose_response, build_weather_facts, LLMError

# Fixed Fallback Error Messages
LOCATION_ERROR_MESSAGE = "I couldn't resolve that location. Please provide a valid city or location."
WEATHER_ERROR_MESSAGE = "I couldn't retrieve the current weather right now. Please try again later."
NO_SOP_ERROR_MESSAGE = "I don't have an applicable advisory for this request and weather situation."


class WeatherGuideState(TypedDict, total=False):
    user_message: str
    user_request: str
    location: str
    resolved_location: Dict[str, Any]
    weather: Dict[str, Any]
    matched_sop_ids: List[str]
    selected_sop: Dict[str, Any]
    response: str
    error: Optional[str]


def parse_request_node(state: WeatherGuideState) -> WeatherGuideState:
    """
    Node 1: Parses raw user message to extract user_request and location.
    Retains location from previous checkpoint if present on the same session thread.
    Resets turn error state.
    """
    user_message = state.get("user_message", "").strip()
    user_request = state.get("user_request", user_message)

    # Retain location from previous checkpoint if present
    location = state.get("location", "").strip()

    if user_message:
        # Check if user message explicitly specifies a new location (preferring in, at, near over for)
        match = re.search(r'\b(?:in|at|near)\s+([A-Za-z\s]+?)(?:\?|\.|$|,|for|with)', user_message, re.IGNORECASE)
        if not match:
            match = re.search(r'\bfor\s+([A-Za-z\s]+?)(?:\?|\.|$|,|with)', user_message, re.IGNORECASE)

        if match:
            extracted = match.group(1).strip()
            ignored = {"elderly", "children", "pets", "cycling", "walking", "picnic", "tomorrow", "today", "a walk", "a picnic", "a workout", "an exercise"}
            if len(extracted) > 1 and extracted.lower() not in ignored:
                location = extracted

    return {
        "user_message": user_message,
        "user_request": user_request or user_message,
        "location": location,
        "error": None
    }


def resolve_location_node(state: WeatherGuideState) -> WeatherGuideState:
    """
    Node 2: Resolves location string using Open-Meteo geocoding.
    Routes to location_error on failure.
    """
    location = state.get("location", "").strip()
    if not location:
        return {"error": "LOCATION_ERROR"}

    try:
        resolved = geocode_location(location)
        return {
            "resolved_location": resolved,
            "location": resolved["name"],
            "error": None
        }
    except (LocationNotFoundError, WeatherAPIError, ValueError):
        return {"error": "LOCATION_ERROR"}


def fetch_weather_node(state: WeatherGuideState) -> WeatherGuideState:
    """
    Node 3: Fetches live weather for resolved location coordinates.
    Routes to weather_error on failure.
    """
    resolved_location = state.get("resolved_location")
    if not resolved_location:
        return {"error": "WEATHER_ERROR"}

    try:
        lat = resolved_location["latitude"]
        lon = resolved_location["longitude"]
        weather = api_fetch_weather(lat, lon)
        return {
            "weather": weather,
            "error": None
        }
    except (WeatherAPIError, Exception):
        return {"error": "WEATHER_ERROR"}


def match_sop_node(state: WeatherGuideState) -> WeatherGuideState:
    """
    Node 4: Evaluates deterministic SOPs first. If none match, evaluates fuzzy SOPs via Gemini.
    Selects highest severity SOP (critical > high > medium > low), using YAML order as tie-breaker.
    """
    weather = state.get("weather", {})
    user_request = state.get("user_request", "")

    sops = load_sops()

    # 1. Deterministic SOP evaluation with user context filtering
    deterministic_matches = match_sops(sops, weather, user_request=user_request)

    if deterministic_matches:
        matched_ids = [sop["id"] for sop in deterministic_matches]
        # Primary selected SOP is highest severity (first in sorted list)
        selected_sop = deterministic_matches[0]
        return {
            "matched_sop_ids": matched_ids,
            "selected_sop": selected_sop,
            "error": None
        }

    # 2. Fuzzy SOP evaluation if no deterministic matches exist
    try:
        fuzzy_sop = select_fuzzy_sop(sops, user_request, weather)
    except LLMError:
        fuzzy_sop = None

    if fuzzy_sop:
        return {
            "matched_sop_ids": [fuzzy_sop["id"]],
            "selected_sop": fuzzy_sop,
            "error": None
        }

    # 3. No match
    return {
        "matched_sop_ids": [],
        "selected_sop": None,
        "error": None
    }


def compose_response_node(state: WeatherGuideState) -> WeatherGuideState:
    """
    Node 5: Composes natural-language response using LLM composer with grounded weather facts.
    """
    user_request = state.get("user_request", "")
    weather = state.get("weather", {})
    selected_sop = state.get("selected_sop")

    try:
        response_text = compose_response(user_request, weather, selected_sop)
    except LLMError:
        # Fallback to direct advice from SOP if LLM invocation fails
        advice = selected_sop.get("advice", "") if selected_sop else ""
        response_text = f"Advisory ({selected_sop.get('name')}): {advice}" if advice else NO_SOP_ERROR_MESSAGE

    return {"response": response_text}


def handle_location_error_node(state: WeatherGuideState) -> WeatherGuideState:
    """Node 6: Handles location resolution failures with exact fixed message."""
    return {"response": LOCATION_ERROR_MESSAGE}


def handle_weather_error_node(state: WeatherGuideState) -> WeatherGuideState:
    """Node 7: Handles weather API failures with exact fixed message."""
    return {"response": WEATHER_ERROR_MESSAGE}


def handle_no_sop_response_node(state: WeatherGuideState) -> WeatherGuideState:
    """Node 8: Handles unmapped SOP situations with exact fixed message."""
    return {"response": NO_SOP_ERROR_MESSAGE}


# --- Conditional Routing Functions ---

def route_after_resolve_location(state: WeatherGuideState) -> str:
    if state.get("error") == "LOCATION_ERROR":
        return "location_error"
    return "fetch_weather"


def route_after_fetch_weather(state: WeatherGuideState) -> str:
    if state.get("error") == "WEATHER_ERROR":
        return "weather_error"
    return "match_sop"


def route_after_match_sop(state: WeatherGuideState) -> str:
    if not state.get("selected_sop"):
        return "no_sop"
    return "compose_response"


# Shared in-memory checkpointer instance
memory = MemorySaver()


def build_graph(checkpointer=None):
    """
    Constructs and compiles the WeatherGuide LangGraph workflow graph.
    Uses in-memory MemorySaver checkpointer for session state isolation.
    """
    if checkpointer is None:
        checkpointer = memory

    workflow = StateGraph(WeatherGuideState)

    # Add Nodes
    workflow.add_node("parse_request", parse_request_node)
    workflow.add_node("resolve_location", resolve_location_node)
    workflow.add_node("fetch_weather", fetch_weather_node)
    workflow.add_node("match_sop", match_sop_node)
    workflow.add_node("compose_response", compose_response_node)
    workflow.add_node("location_error", handle_location_error_node)
    workflow.add_node("weather_error", handle_weather_error_node)
    workflow.add_node("no_sop", handle_no_sop_response_node)

    # Add Edges
    workflow.add_edge(START, "parse_request")
    workflow.add_edge("parse_request", "resolve_location")

    # Conditional Edge 1: Location Resolution
    workflow.add_conditional_edges(
        "resolve_location",
        route_after_resolve_location,
        {
            "location_error": "location_error",
            "fetch_weather": "fetch_weather"
        }
    )

    # Conditional Edge 2: Weather Fetching
    workflow.add_conditional_edges(
        "fetch_weather",
        route_after_fetch_weather,
        {
            "weather_error": "weather_error",
            "match_sop": "match_sop"
        }
    )

    # Conditional Edge 3: SOP Matching
    workflow.add_conditional_edges(
        "match_sop",
        route_after_match_sop,
        {
            "no_sop": "no_sop",
            "compose_response": "compose_response"
        }
    )

    # Terminal Edges
    workflow.add_edge("compose_response", END)
    workflow.add_edge("location_error", END)
    workflow.add_edge("weather_error", END)
    workflow.add_edge("no_sop", END)

    return workflow.compile(checkpointer=checkpointer)


# Export compiled graph instance
app_graph = build_graph()
