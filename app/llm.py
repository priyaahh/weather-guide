import os
from langchain_google_genai import ChatGoogleGenerativeAI


class LLMError(Exception):
    """Custom exception raised when LLM operations fail or credentials are missing."""
    pass


ALLOWED_WEATHER_FIELDS = [
    "temperature_2m",
    "apparent_temperature",
    "precipitation",
    "precipitation_probability",
    "wind_speed_10m",
    "wind_gusts_10m",
    "uv_index",
    "visibility",
]

DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"


def build_weather_facts(weather: dict) -> dict:
    """
    Filters the weather dictionary to include only the allowed 8 weather metrics.
    Prevents arbitrary or unverified fields from being passed into LLM prompts.

    Args:
        weather (dict): Input weather dictionary.

    Returns:
        dict: Controlled dictionary containing only allowed fields that are present and non-null.
    """
    if not isinstance(weather, dict):
        return {}
    return {
        k: weather[k]
        for k in ALLOWED_WEATHER_FIELDS
        if k in weather and weather[k] is not None
    }


def get_llm_model(model_name: str = None):
    """
    Instantiates and returns a ChatGoogleGenerativeAI model instance.
    Reads GOOGLE_API_KEY from environment variables.

    Args:
        model_name (str, optional): Model identifier. Defaults to GEMINI_MODEL env var or gemini-1.5-flash.

    Returns:
        ChatGoogleGenerativeAI: Configured LangChain Gemini model.

    Raises:
        LLMError: If GOOGLE_API_KEY is not set or model initialization fails.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise LLMError("GOOGLE_API_KEY environment variable is missing. Please set GOOGLE_API_KEY.")

    target_model = model_name or os.environ.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL

    try:
        return ChatGoogleGenerativeAI(
            model=target_model,
            google_api_key=api_key,
            temperature=0.0
        )
    except Exception as exc:
        raise LLMError(f"Failed to initialize ChatGoogleGenerativeAI model '{target_model}': {exc}") from exc


def select_fuzzy_sop(sops: list, user_request: str, weather: dict, model=None) -> dict | None:
    """
    Considers only fuzzy SOPs (trigger_type == 'fuzzy') and uses Gemini to select the applicable SOP ID.

    Args:
        sops (list): List of SOP dictionaries.
        user_request (str): The user's query or intent description.
        weather (dict): Verified weather facts.
        model (optional): Pre-configured LLM instance or mock.

    Returns:
        dict | None: The matching fuzzy SOP dictionary, or None if no match/invalid ID/NONE returned.

    Raises:
        LLMError: If LLM invocation fails.
    """
    if not sops or not isinstance(sops, list):
        return None

    fuzzy_candidates = [sop for sop in sops if isinstance(sop, dict) and sop.get("trigger_type") == "fuzzy"]
    if not fuzzy_candidates:
        return None

    valid_ids = {sop["id"]: sop for sop in fuzzy_candidates if "id" in sop}

    weather_facts = build_weather_facts(weather)

    candidates_text = "\n".join([
        f"- ID: {sop['id']} | Name: {sop.get('name')} | Description: {sop.get('description', '')}"
        for sop in fuzzy_candidates
    ])

    prompt = (
        f"You are a weather policy classifier.\n"
        f"User Request: \"{user_request}\"\n"
        f"Current Weather Facts: {weather_facts}\n\n"
        f"Candidate Fuzzy SOP Policies:\n{candidates_text}\n\n"
        f"Task: Identify which single fuzzy SOP policy ID applies to the user's request given the weather facts.\n"
        f"Respond ONLY with the exact SOP ID (e.g. 'SOP-010') or 'NONE' if no fuzzy SOP policy applies.\n"
        f"Do not include any explanation or extra text."
    )

    if model is None:
        model = get_llm_model()

    try:
        response = model.invoke(prompt)
        raw_text = response.content if hasattr(response, "content") else str(response)
        sop_id = raw_text.strip().strip("'\"`")
    except Exception as exc:
        if isinstance(exc, LLMError):
            raise
        raise LLMError(f"Fuzzy SOP selection failed during Gemini API call: {exc}") from exc

    if sop_id == "NONE" or sop_id not in valid_ids:
        return None

    return valid_ids[sop_id]


def compose_response(user_request: str, weather_facts: dict, selected_sop: dict = None, model=None) -> str:
    """
    Composes a concise, grounded natural-language weather advisory response using Gemini.

    Args:
        user_request (str): The user's query.
        weather_facts (dict): Weather metrics dictionary (will be filtered to controlled fields).
        selected_sop (dict, optional): Selected SOP dictionary (or None).
        model (optional): Pre-configured LLM instance or mock.

    Returns:
        str: Concise natural language response text.

    Raises:
        LLMError: If LLM invocation fails.
    """
    controlled_facts = build_weather_facts(weather_facts)

    sop_details = "None"
    if selected_sop and isinstance(selected_sop, dict):
        sop_details = (
            f"ID: {selected_sop.get('id')}\n"
            f"Name: {selected_sop.get('name')}\n"
            f"Severity: {selected_sop.get('severity')}\n"
            f"Advice: {selected_sop.get('advice')}"
        )

    prompt = (
        f"You are a Weather Advisory Support Assistant.\n"
        f"User Query: \"{user_request}\"\n\n"
        f"Verified Weather Facts (STRICT GROUNDING SOURCE):\n{controlled_facts}\n\n"
        f"Matched SOP Advisory Policy:\n{sop_details}\n\n"
        f"STRICT INSTRUCTIONS FOR COMPOSING YOUR RESPONSE:\n"
        f"1. Use ONLY the supplied weather facts. Do NOT invent weather values.\n"
        f"2. Use ONLY the supplied SOP advice and policy guidelines. Do NOT invent safety rules or warnings.\n"
        f"3. Do NOT claim an official government or emergency agency alert unless that exact text is provided in the SOP.\n"
        f"4. If the SOP contains a proxy/disclaimer (such as for automated weather proxies), preserve the disclaimer.\n"
        f"5. Provide a clear, polite, concise natural-language response directly answering the user query.\n"
        f"6. If facts or SOPs are insufficient, state so clearly instead of guessing."
    )

    if model is None:
        model = get_llm_model()

    try:
        response = model.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        return text.strip()
    except Exception as exc:
        if isinstance(exc, LLMError):
            raise
        raise LLMError(f"Response composition failed during Gemini API call: {exc}") from exc
