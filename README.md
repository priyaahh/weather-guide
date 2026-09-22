# Weather Advisory Support Bot

A LangGraph-based weather advisory chatbot that combines live weather data from Open-Meteo, structured Standard Operating Procedures (SOPs), deterministic rule matching, and Gemini-based language understanding and response composition.

---

## Features

- **Live Weather Lookup**: Fetches current weather metrics from the Open-Meteo API.
- **Location Resolution**: Geocodes natural-language location queries via Open-Meteo Geocoding.
- **Structured SOP Engine**: Evaluates 12 curated Standard Operating Procedures defined in `data/sops.yaml`.
- **Deterministic & Compound Matching**: Matches numeric thresholds (e.g., UV >= 8.0, Apparent Temp >= 35°C) and multi-variable compound rules (e.g., Precipitation >= 10mm + Wind Gusts >= 40km/h).
- **Fuzzy / Paraphrase Matching**: Handles natural-language activity requests via Gemini LLM classification when no deterministic rules match.
- **Multi-Match Severity Prioritization**: Resolves overlapping SOP triggers by selecting the highest severity advisory (`critical` > `high` > `medium` > `low`) with YAML-order tie-breaking.
- **Grounded Response Composition**: Composes concise natural-language advice strictly bounded by verified weather facts and matched SOP guidelines.
- **LangGraph Branching Workflow**: Stateful orchestration with dedicated fallback nodes for location errors, weather API timeouts, and unmapped SOP requests.
- **Session Memory (`MemorySaver`)**: In-memory state retention across turns via session `thread_id`, preserving location context while fetching fresh weather data on every turn.
- **Streamlit Chat Interface**: Interactive chat UI with conversation history preservation and a single-click conversation reset.
- **Evaluation Suite**: 9 deterministic evaluation tests and documentation covering deterministic matching, paraphrases, fallback accuracy, multi-match resolution, and adversarial input safety.
- **Graceful Failure Handling**: Returns exact assignment-mandated fallback messages on failures.

---

## Architecture

```text
User Input
  ↓
Streamlit Chat UI (app/streamlit_app.py)
  ↓
LangGraph Workflow (app/graph.py)
  ↓
parse_request node (Extract user intent & retain session location)
  ↓
resolve_location node (Geocode location via Open-Meteo)
  ├── [Location Resolution Failure] ──> location_error node ──> END
  ↓
fetch_weather node (Fetch live weather metrics from Open-Meteo API)
  ├── [Weather API Failure] ──────────> weather_error node ───> END
  ↓
match_sop node (Evaluate deterministic rules & fuzzy Gemini SOP fallback)
  ├── [No Applicable SOP Match] ──────> no_sop node ──────────> END
  ↓
compose_response node (Gemini grounded natural-language composition)
  ↓
MemorySaver Checkpointer (Retain session state under thread_id)
  ↓
Streamlit Response Display
```

### Error Handling Branches
- **Location Error**: `"I couldn't resolve that location. Please provide a valid city or location."`
- **Weather API Error**: `"I couldn't retrieve the current weather right now. Please try again later."`
- **No SOP Error**: `"I don't have an applicable advisory for this request and weather situation."`

---

## Tech Stack

- **Language**: Python 3.12+
- **Orchestration**: LangGraph (`langgraph>=0.2.0`)
- **LLM Integration**: Gemini via `langchain-google-genai`
- **Weather & Geocoding**: Open-Meteo REST APIs
- **Frontend**: Streamlit (`streamlit>=1.30.0`)
- **Data Validation & Serialisation**: Pydantic, PyYAML
- **HTTP Client**: Requests
- **Testing**: pytest

---

## SOP Design

Standard Operating Procedures are defined in `data/sops.yaml`. This decoupling allows policy rules to be updated or added without modifying application matching code.

- **Deterministic SOPs** (`trigger_type: numeric` or `compound`): Evaluated first by `app/sop_engine.py` using Python comparison logic.
- **Fuzzy SOPs** (`trigger_type: fuzzy`): Evaluated by Gemini LLM (`app/llm.py`) only when zero deterministic SOPs match.
- **Multi-Match Resolution**: When multiple SOPs match, the engine selects the highest severity SOP (`critical` > `high` > `medium` > `low`), breaking ties using YAML declaration order.

---

## Weather Data Metrics

The system strictly controls weather metrics passed into LLM prompts using `build_weather_facts()`:

- `temperature_2m` (Temperature at 2m)
- `apparent_temperature` (Feels-like Temperature)
- `precipitation` (Precipitation amount)
- `precipitation_probability` (Rain probability)
- `wind_speed_10m` (Wind speed at 10m)
- `wind_gusts_10m` (Peak wind gusts)
- `uv_index` (Ultraviolet Index)
- `visibility` (Visibility distance)

---

## Grounding & Safety

Response composition receives verified, filtered weather metrics and the matched SOP dictionary. Grounding instructions enforce:
1. Using **ONLY** verified weather facts from Open-Meteo.
2. Using **ONLY** safety guidelines provided by the matched SOP.
3. Prohibiting invented agency alerts or unverified safety warnings.
4. Preserving proxy/disclaimer notices for automated severe weather proxies.

---

## Session Memory

Session continuity is powered by LangGraph's in-memory `MemorySaver` checkpointer:
- **`thread_id`**: A unique session UUID stored in Streamlit `st.session_state`.
- **Location Context**: Retained across conversation turns (e.g. Turn 1: *"Can I go cycling in Mumbai?"*, Turn 2: *"What about this afternoon?"* reuses `"Mumbai"`).
- **Fresh Weather Enforcement**: Memory retains session location, but `fetch_weather_node` executes on every turn to fetch fresh live metrics.
- **Reset**: Clicking *"New Conversation"* generates a new `thread_id` UUID and clears displayed message history.

---

## Evaluation Suite

Detailed evaluation documentation is available in [`docs/EVALUATION.md`](docs/EVALUATION.md).

- **Total Test Suite**: **64 passed** (including 9 dedicated evaluation tests).
- **Evaluation Categories Covered**:
  - Deterministic SOP matches (High UV, High Rain Travel)
  - Paraphrased query matching (Strong Sun Exposure, Downpour Driving)
  - No-SOP fallback execution
  - Multi-match severity precedence (`high` > `low`)
  - Location resolution failure fallback
  - Weather API network failure fallback
  - Prompt injection and adversarial input isolation

---

## Limitations

- **Live API Dependency**: Real-time evaluation relies on Open-Meteo API availability and live regional conditions.
- **Severe Weather Proxy Disclaimer**: Automated proxy advisories (e.g., `SOP-012`) are based on weather data metrics and do NOT represent official IMD, government, or emergency agency warnings.
- **In-Memory Storage**: `MemorySaver` maintains session state in memory during runtime and does not persist data to an external database.
- **Prompt Injection Testing**: Adversarial tests verify workflow containment, but do not replace formal external penetration testing.

---

## Setup & Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Git

### Installation Steps (Windows PowerShell)

```powershell
# 1. Clone the repository
git clone https://github.com/priyaahh/weather-guide.git
cd weather-guide

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install required dependencies
pip install -r requirements.txt
```

### API Key Configuration

Set your Gemini API Key in your terminal session before launching:

```powershell
$env:GOOGLE_API_KEY="your_gemini_api_key_here"
```

*Alternatively, Streamlit secrets (`.streamlit/secrets.toml`) are supported locally (do not commit secrets files).*

### Running the Application

Launch the Streamlit web app:

```powershell
streamlit run app/streamlit_app.py
```

Open `http://localhost:8501` in your browser.

---

## Running Tests

Run the complete test suite:

```powershell
pytest -q
```

Expected output:
```text
64 passed in 2.43s
```

Run the evaluation test suite specifically:

```powershell
pytest tests/test_evaluation.py -v
```

Expected output:
```text
9 passed in 1.90s
```
