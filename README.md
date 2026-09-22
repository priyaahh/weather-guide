# Weather Advisory Support Bot

- **Live Demo**: [https://wime-bot.streamlit.app/](https://wime-bot.streamlit.app/)
- **GitHub Repository**: [https://github.com/priyaahh/weather-guide](https://github.com/priyaahh/weather-guide)

A LangGraph-based weather advisory chatbot that combines live weather data from Open-Meteo, structured Standard Operating Procedures (SOPs), deterministic rule matching, and Gemini-based language understanding and response composition.

---

## Features

- **Live Weather Lookup**: Fetches current/forecast weather metrics from the Open-Meteo API.
- **Location Resolution**: Geocodes natural-language location queries via Open-Meteo Geocoding.
- **Structured SOP Engine**: Evaluates 12 curated Standard Operating Procedures defined in `data/sops.yaml`.
- **Deterministic & Compound Matching**: Matches numeric thresholds (e.g., UV >= 8.0, Apparent Temp >= 35°C) and multi-variable compound rules (e.g., Precipitation >= 10mm + Wind Gusts >= 40km/h).
- **Fuzzy / Paraphrase Matching**: Handles natural-language activity requests via Gemini LLM classification when no deterministic rules match.
- **Multi-Match Severity Prioritization**: Resolves overlapping SOP triggers by selecting the highest severity advisory (`critical` > `high` > `medium` > `low`) with YAML-order tie-breaking.
- **Grounded Response Composition**: Composes concise natural-language advice strictly bounded by verified weather facts and matched SOP guidelines.
- **LangGraph Branching Workflow**: Stateful orchestration with dedicated fallback nodes for location errors, weather API timeouts, and unmapped SOP requests.
- **Session Memory (`MemorySaver`)**: In-memory state retention across turns via session `thread_id`, preserving location context while fetching fresh weather data on every turn.
- **Streamlit Chat Interface**: Interactive chat UI with conversation history preservation and a single-click conversation reset.
- **Visible SOP Traceability**: Interactive expander in Streamlit ("Why am I seeing this advice?") displaying matched SOP ID, policy name, severity, and verified weather facts directly from API state.
- **Evaluation Suite**: 10 evaluation tests (9 offline mocked tests + 1 live Open-Meteo test) and documentation covering deterministic matching, paraphrases, fallback accuracy, multi-match resolution, live weather severe proxy evaluation, and adversarial input safety.
- **Graceful Failure Handling**: Returns exact assignment-mandated fallback messages on failures.

---

## Architecture & Module Responsibilities

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
Streamlit Response & SOP Trace Display
```

### Module Responsibilities
- `app/streamlit_app.py`: Streamlit chat UI, session state management, and SOP traceability expander rendering.
- `app/graph.py`: LangGraph stateful workflow definition, node functions, and conditional error branching.
- `app/sop_loader.py`: Dynamically loads SOP policies from YAML so policy additions/changes do not require control-flow code changes.
- `app/sop_engine.py`: Evaluates deterministic numeric and compound condition rules against weather data.
- `app/weather.py`: Interacts with Open-Meteo REST APIs for geocoding and live weather metrics.
- `app/llm.py`: Gemini model integration, fuzzy SOP selection fallback, and grounded response composition.

### Error Handling Branches
- **Location Error**: `"I couldn't resolve that location. Please provide a valid city or location."`
- **Weather API Error**: `"I couldn't retrieve the current weather right now. Please try again later."`
- **No SOP Error**: `"I don't have an applicable advisory for this request and weather situation."`

---

## Tech Stack

- **Language**: Python 3.10+ (tested on Python 3.12)
- **Orchestration**: LangGraph (`langgraph>=0.2.0`)
- **LLM Integration**: Gemini via `langchain-google-genai`
- **Weather & Geocoding**: Open-Meteo REST APIs
- **Frontend**: Streamlit (`streamlit>=1.30.0`)
- **Data Validation & Serialisation**: Pydantic, PyYAML
- **HTTP Client**: Requests
- **Testing**: pytest

---

## SOP Design & Rationale

Standard Operating Procedures are defined in `data/sops.yaml`. This decoupling ensures policy rules can be updated or added without modifying application code.

### Categories & Severity Distribution (12 SOPs Total)
- **Categories (4)**: `outdoor_exercise`, `travel`, `vulnerable_groups`, `leisure_general`
- **Severity Distribution**:
  - `critical` (1): `SOP-012`
  - `high` (5): `SOP-003`, `SOP-005`, `SOP-006`, `SOP-007`, `SOP-009`
  - `medium` (3): `SOP-001`, `SOP-002`, `SOP-008`
  - `low` (3): `SOP-004`, `SOP-010`, `SOP-011`

### Matching Rules
- **Deterministic SOPs** (`trigger_type: numeric` or `compound`): Evaluated first by `app/sop_engine.py` using Python comparison logic.
- **Fuzzy SOPs** (`trigger_type: fuzzy`): Evaluated by Gemini LLM (`app/llm.py`) only when zero deterministic SOPs match.
- **Multi-Match Resolution**: When multiple SOPs match, the engine selects the highest severity SOP (`critical` > `high` > `medium` > `low`), breaking ties using YAML declaration order.

### Design Rationale
- **Why YAML for SOPs**: Plain-text, diffable, and editable by non-engineers without touching Python — directly supports changing or adding a policy without touching application control-flow code.
- **Why severity ranking instead of surfacing multiple matches**: A single authoritative answer avoids conflicting advice reaching the user; severity provides a deterministic, policy-owner-maintained tie-break mechanism.
- **Severe-Weather Proxy (`SOP-012`)**: Triggered when `precipitation >= 25.0 mm AND wind_gusts_10m >= 60.0 km/h`. This is an automated severe-weather proxy based on Open-Meteo metrics, NOT an official IMD, government, or emergency agency warning.

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

- **Total Test Suite**: **75 passed** (including 10 dedicated evaluation test cases).
- **Evaluation Categories Covered (10 Named Cases)**:
  - Cases A1 & A2: Deterministic SOP matches (High UV, High Rain Travel)
  - Cases B1 & B2: Paraphrased query matching (Strong Sun Exposure, Downpour Driving)
  - Case C: No-SOP fallback execution
  - Case D: Multi-match severity precedence (`high` > `low`)
  - Case E: Location resolution failure fallback
  - Case F: Weather API network failure fallback
  - Case G: Prompt injection and adversarial input isolation
  - Case H: Live unmocked Open-Meteo weather evaluation (`SOP-012`)

---

## Limitations

- **Live API Dependency**: Real-time evaluation relies on Open-Meteo API availability and live regional conditions.
- **Severe Weather Proxy Disclaimer**: Automated proxy advisories (e.g., `SOP-012`) are based on weather data metrics and do NOT represent official IMD, government, or emergency agency warnings.
- **In-Memory Storage**: `MemorySaver` maintains session state in memory during runtime and does not persist data to an external database.
- **Prompt Injection Testing**: Adversarial tests verify workflow containment, but do not replace formal external penetration testing.

---

## Setup & Run Instructions

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Git

### 1. Repository Setup & Environment Installation

Clone the repository and install project dependencies in a virtual environment:

```powershell
# Clone the repository
git clone https://github.com/priyaahh/weather-guide.git
cd weather-guide

# Create and activate virtual environment (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install required dependencies
pip install -r requirements.txt
```

---

### 2. Application Setup & Programmatic Execution

The backend contains the compiled LangGraph workflow (`app/graph.py`), SOP engine (`app/sop_engine.py`), and evaluation test suite (`tests/`).

#### API Key Configuration
Set your Gemini API Key in your terminal session for LLM operations:

```powershell
$env:GOOGLE_API_KEY="your_actual_gemini_api_key_here"
```

> **Security Note**: API key is read from an environment variable or Streamlit secret; `.env` and `.streamlit/secrets.toml` are gitignored and no API key is committed.

#### Running Backend Invocation Programmatically
You can invoke the compiled LangGraph backend directly via Python:

```powershell
python -c "from app.graph import app_graph; print(app_graph.invoke({'user_message': 'Can I go cycling in Mumbai?'}, config={'configurable': {'thread_id': 'session-1'}}))"
```

#### Running Test Suite & Evaluation Suite
Run the full test suite (75 tests):

```powershell
pytest -q
```

Run the evaluation test suite specifically (10 tests):

```powershell
pytest tests/test_evaluation.py -v
```

---

### 3. Frontend Setup & Web UI Execution

The frontend is an interactive chat web app built with Streamlit ([`app/streamlit_app.py`](app/streamlit_app.py)).

#### Launching the Frontend Web App
Ensure your virtual environment is active and run:

```powershell
streamlit run app/streamlit_app.py
```

#### Accessing the Web Interface
Open your browser and navigate to:
```text
http://localhost:8501
```

#### Features in Frontend:
- **Chat Input**: Enter natural language activity or weather queries.
- **SOP Traceability**: Expand `"Why am I seeing this advice?"` under any assistant response to view matched SOP ID, policy name, severity, and verified weather facts.
- **Session Memory**: Follow-up questions (e.g. *"What about this afternoon?"*) reuse location context.
- **New Conversation**: Click `"New Conversation"` in the sidebar to reset session state and start fresh.
