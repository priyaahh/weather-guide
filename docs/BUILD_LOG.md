# WeatherGuide - Build & Revision Log

## Phase 1 — Project Setup

### Overview
Initial setup of the repository structure, environment isolation, and version control configuration for the WeatherGuide project (a LangGraph-based Weather Advisory Support Bot).

### What We Created
- `app/`: Directory for application source code.
- `tests/`: Directory for automated tests.
- `data/`: Directory for local dataset storage and SOP documents.
- `docs/`: Directory for project documentation and logs.
- `docs/BUILD_LOG.md`: Project build and revision tracking log.
- `.gitignore`: Git configuration file specifying exclusions.
- `.venv/`: Python isolated virtual environment.

### Why Each Folder/File Exists
- **`app/`**: Keeps all production source code structured and modular.
- **`tests/`**: Ensures test files are separated from core application code.
- **`data/`**: Holds datasets, SOP files, or cached response data needed by the weather advisory bot.
- **`docs/`**: Central location for developer documentation, architectural logs, and phase updates.
- **`.gitignore`**: Prevents sensitive keys (`.env`), cache files (`__pycache__`), virtual environment files (`.venv/`), and local configuration files (`.streamlit/secrets.toml`) from being committed to source control.
- **`.venv/`**: Isolates Python packages and dependencies specifically for this project to prevent conflicts with global environment packages.

### Virtual Environment Setup
- Created a Python virtual environment named `.venv` in the project root directory using `python -m venv .venv`.
- Provisioned basic setup in Phase 1.

### Important Decisions
- Kept Phase 1 strictly focused on base directory structure and virtual environment creation without premature dependency installation or dummy code additions.
- Configured strict `.gitignore` rules upfront to safeguard environment variables and secrets from accidental commits.

### Current Status
- **Phase 1 complete**.

---

## Phase 2 — SOP / Policy Layer

### What an SOP Means in This Project
A Standard Operating Procedure (SOP) represents a domain-specific advisory rule or policy constraint. Rather than hardcoding safety rules directly inside application code or relying on unconstrained LLM prompts, SOPs define explicit weather triggers, severity levels, and standardized safety recommendations for users.

### Why SOPs Are Stored in YAML
- **Declarative & Human-Readable**: Non-technical domain experts or safety auditors can inspect and modify advisory guidelines without modifying Python code.
- **Separation of Concerns**: Decouples business/safety policy rules from application logic and orchestration code.
- **Maintainability**: New advisories can be added or thresholds updated seamlessly by editing declarative YAML.

### The Three Trigger Types
1. **`numeric`**: Single-field threshold comparison (e.g., `uv_index >= 8.0` or `visibility <= 1000.0`).
2. **`compound`**: Multi-condition evaluation requiring explicit **AND semantics** (all conditions must evaluate to `True` for the SOP to match).
3. **`fuzzy`**: Qualitative or multi-variable comfort evaluation (e.g., picnic suitability or pleasant walk conditions) intended for LLM/heuristic reasoning.

### The Four High-Level Categories
1. **`outdoor_exercise`**: Advisories targeting workouts, cycling, and outdoor exertion under harsh weather.
2. **`travel`**: Driving and commuting safety advisories based on rain, wind, and visibility.
3. **`vulnerable_groups`**: Targeted health and safety guidelines for elderly individuals, children, and pets.
4. **`leisure_general`**: General outdoor activities (picnics, walks) and severe weather proxy alerts.

### The 12 SOPs at a High Level
- **`SOP-001`**: High UV Index Outdoor Exercise Advisory (UV index >= 8.0).
- **`SOP-002`**: High Wind Cycling Safety Advisory (wind speed >= 25.0 km/h).
- **`SOP-003`**: Extreme Heat Outdoor Exercise Advisory (apparent temperature >= 35.0 °C).
- **`SOP-004`**: High Precipitation Probability Travel Advisory (rain probability >= 70%).
- **`SOP-005`**: Heavy Rain and Strong Wind Travel Advisory (precipitation >= 10mm AND wind gusts >= 40 km/h).
- **`SOP-006`**: Low Visibility Travel Advisory (visibility <= 1000m).
- **`SOP-007`**: Extreme Heat Vulnerability Advisory for Elderly (apparent temperature >= 33.0 °C).
- **`SOP-008`**: High UV Outdoor Protection Advisory for Children (UV index >= 5.0).
- **`SOP-009`**: High Heat Outdoor Safety Advisory for Pets (apparent temperature >= 30.0 °C).
- **`SOP-010`**: Fuzzy Picnic Outdoor Comfort Advisory (qualitative assessment for picnics).
- **`SOP-011`**: Fuzzy Good Day for a Walk Advisory (qualitative assessment for walking).
- **`SOP-012`**: Severe Weather Proxy Advisory (wind gusts >= 60 km/h AND precipitation >= 25mm; automated proxy based on weather data metrics, NOT official IMD/government alerts).

### How Numeric Conditions Work
Numeric conditions evaluate a specific weather metric (e.g., `apparent_temperature`) against a threshold value using relational operators (`>=`, `<=`, `>`, `<`).

### How Compound AND Conditions Work
Compound conditions contain a list of individual numeric criteria. Under strict **AND semantics**, every listed criterion must evaluate to `True` for the compound SOP to trigger.

### How Fuzzy SOPs Will Later Be Handled
Fuzzy SOPs provide descriptive guidelines for subjective comfort levels (e.g., picnic feasibility). In later phases, these descriptions will be parsed by heuristic evaluators or passed to the LLM agent to ground qualitative user recommendations.

### How Severity/Priority Will Later Help with Multiple Matches
Each SOP is assigned a severity rank (`low`, `medium`, `high`, `critical`). When a user query matches multiple SOPs concurrently, the system can rank, filter, or prioritize advisories so critical safety warnings (such as `SOP-012`) take precedence.

### What Was Implemented
- Created `data/sops.yaml` with exactly 12 structured SOPs matching all schema specifications.
- Implemented `app/sop_loader.py` to parse `data/sops.yaml` cleanly and handle file loading errors.
- Created `tests/test_sop_loader.py` with 7 automated unit tests validating schema, count, unique IDs, and valid trigger types.
- Created `requirements.txt` containing required dependencies (`pyyaml`, `pytest`).
- Added `pytest.ini` and `app/__init__.py` for seamless package resolution.

### What Was Intentionally NOT Implemented
- No Open-Meteo weather API integration (deferred to Phase 3).
- No Google Gemini LLM integration.
- No LangGraph agent state/graph implementation.
- No Streamlit frontend user interface.
- No rule matching or evaluation engine code yet.

### Current Status
- **Phase 2 complete**.

---

## Phase 3 — Live Weather Layer

### Overview
Built the live weather integration layer that resolves city/place names to geographical coordinates via the Open-Meteo Geocoding API and retrieves current weather conditions via the Open-Meteo Forecast API.

### What Was Implemented
- **`app/weather.py`**:
  - `geocode_location(location: str)`: Resolves city names to latitude, longitude, and country metadata using `https://geocoding-api.open-meteo.com/v1/search`.
  - `fetch_weather(latitude: float, longitude: float)`: Retrieves live weather data from `https://api.open-meteo.com/v1/forecast` containing exclusively the 8 required SOP weather fields (`temperature_2m`, `apparent_temperature`, `precipitation`, `precipitation_probability`, `wind_speed_10m`, `wind_gusts_10m`, `uv_index`, `visibility`).
  - `get_weather_for_location(location: str)`: Helper function linking geocoding and weather retrieval.
  - Custom hierarchy of exceptions (`WeatherError`, `LocationNotFoundError`, `WeatherAPIError`, `MalformedWeatherResponseError`).
- **`tests/test_weather.py`**:
  - 8 automated unit tests using `unittest.mock` to test geocoding success, location not found, weather response parsing, API HTTP/network errors, malformed responses, and input validation without external network dependency.
- **`requirements.txt`**: Added `requests>=2.31.0` dependency.

### Key Technical Decisions & Features
- **Strict Metric Extraction**: Only requests and returns the exact 8 weather fields required by the SOP evaluation layer.
- **Robust Exception Handling**: Differentiates between invalid location input (`ValueError`), missing locations (`LocationNotFoundError`), network/HTTP failures (`WeatherAPIError`), and bad API response formats (`MalformedWeatherResponseError`).
- **Network-Isolated Testing**: All automated tests in `tests/test_weather.py` mock HTTP calls using `unittest.mock.patch`, ensuring fast, deterministic test execution without live API reliance.

### What Was Intentionally NOT Implemented
- No SOP evaluation engine matching logic.
- No LangGraph workflow graph or state management.
- No Google Gemini LLM prompt integration.
- No Streamlit UI interface.

### Test Results
- Ran complete test suite: `.\.venv\Scripts\pytest.exe -v`
- **Result**: 15 passed in 0.81s (7 Phase 2 tests + 8 Phase 3 tests).

### Current Status
- **Phase 3 complete**.

---

## Phase 4 — Deterministic SOP Engine

### Overview
Implemented a deterministic rule evaluation engine (`app/sop_engine.py`) that matches weather metrics against declared SOP conditions in `data/sops.yaml` without relying on LLM logic.

### Key Features Implemented
- **Deterministic Condition Evaluation**: Evaluates numeric metrics using relational operators (`>=`, `<=`, `>`, `<`, `==`).
- **Compound AND Semantics**: Evaluates list-based SOP conditions requiring all individual criteria to be `True`.
- **Fuzzy SOP Handling**: Explicitly skips `fuzzy` trigger types for later LLM heuristic processing.
- **Multiple Concurrent Matches**: Returns all matching SOPs rather than terminating at the first match.
- **Deterministic Severity Ordering**: Sorts matches by severity (`critical` > `high` > `medium` > `low`) while preserving YAML definition order for equal severity.
- **Fault-Tolerant Field Matching**: Missing or null weather fields evaluate to `False` without causing runtime exceptions.

### Files Created & Modified
- **`app/sop_engine.py`**: Deterministic SOP engine logic (`evaluate_condition`, `is_sop_matching`, `match_sops`).
- **`tests/test_sop_engine.py`**: 11 automated unit tests covering all operators, compound AND logic, fuzzy skipping, severity sorting, and missing field handling.

### What Was Intentionally NOT Implemented
- No LLM / Gemini prompt integration.
- No LangGraph state graph.
- No Streamlit UI interface.

### Test Results
- Ran complete test suite: `.\.venv\Scripts\pytest.exe -v`
- **Result**: 26 passed in 0.63s (7 Phase 2 tests + 8 Phase 3 tests + 11 Phase 4 tests).

### Current Status
- **Phase 4 complete**.

---

## Phase 5 — LLM Layer

### Overview
Integrated Google Gemini (`langchain-google-genai`) for fuzzy SOP policy selection and grounded natural-language response composition. The LLM acts strictly as a selection and phrasing layer, maintaining verified weather facts and deterministic SOP engine results as the single source of truth.

### Key Features & Components Implemented
- **`app/llm.py`**:
  - `build_weather_facts(weather)`: Filters weather inputs to a strict whitelist of 8 allowed metrics (`temperature_2m`, `apparent_temperature`, `precipitation`, `precipitation_probability`, `wind_speed_10m`, `wind_gusts_10m`, `uv_index`, `visibility`).
  - `get_llm_model(model_name)`: Configures `ChatGoogleGenerativeAI` reading `GOOGLE_API_KEY` from environment variables.
  - `select_fuzzy_sop(sops, user_request, weather)`: Passes candidate fuzzy SOPs (`trigger_type == "fuzzy"`) to Gemini to select the matching SOP ID or return `NONE`. Validates LLM response against supplied SOP candidates.
  - `compose_response(user_request, weather_facts, selected_sop)`: Formulates concise, natural-language responses using strict grounding prompts (no invented weather values, no hallucinated safety policies, disclaimer preservation).
  - `LLMError`: Custom exception wrapping Gemini/LangChain failures and missing credentials.
- **`tests/test_llm.py`**: 9 automated unit tests using `unittest.mock` to test fact filtering, fuzzy candidate selection, valid/invalid SOP ID handling, response composition grounding, API error handling, and API key environment resolution without live network calls.
- **`requirements.txt`**: Added `langchain-google-genai>=2.0.0`.

### Key Architectural Decisions & Safety
- **Strict Grounding**: The LLM is prohibited from generating arbitrary weather numbers or inventing unlisted policy advisories.
- **Zero Hard-Coded Credentials**: `GOOGLE_API_KEY` is loaded dynamically from the environment. `.env` remains in `.gitignore`.
- **Mocked Testing**: All automated tests run offline using mocks without consuming API quota or requiring live network access.

### What Was Intentionally NOT Implemented
- No LangGraph graph/workflow graph yet (deferred to Phase 6).
- No Streamlit UI interface.
- No session memory.

### Test Results
- Ran complete test suite: `.\.venv\Scripts\pytest.exe -v`
- **Result**: 35 passed in 2.44s (7 Phase 2 + 8 Phase 3 + 11 Phase 4 + 9 Phase 5 tests).

### Current Status
- **Phase 5 complete**.

---

## Phase 6 — LangGraph Orchestration

### Overview
Orchestrated all modules (Geocoding, Live Weather, SOP Policy Engine, and Gemini LLM Grounding) into a stateful, deterministic graph workflow using LangGraph (`StateGraph`).

### Graph Structure & Routing Flow
```text
parse_request -> resolve_location
                     ├── [location_error] -> location_error -> END
                     └── [success]        -> fetch_weather
                                                ├── [weather_error] -> weather_error -> END
                                                └── [success]       -> match_sop
                                                                         ├── [no_sop] -> no_sop -> END
                                                                         └── [success] -> compose_response -> END
```

### Key Components Implemented
- **`app/graph.py`**:
  - `WeatherGuideState`: Strongly-typed `TypedDict` capturing `user_message`, `user_request`, `location`, `resolved_location`, `weather`, `matched_sop_ids`, `selected_sop`, `response`, and `error`.
  - Node functions: `parse_request_node`, `resolve_location_node`, `fetch_weather_node`, `match_sop_node`, `compose_response_node`, `handle_location_error_node`, `handle_weather_error_node`, `handle_no_sop_response_node`.
  - Conditional edge functions: `route_after_resolve_location`, `route_after_fetch_weather`, `route_after_match_sop`.
  - Exact fallback error messages for location failure, weather API failure, and unmapped SOP queries.
  - Multi-match severity prioritization (`critical` > `high` > `medium` > `low`) with YAML order tie-breaking.
  - Deterministic SOP priority over fuzzy LLM selection (fuzzy SOPs queried only if zero deterministic matches exist).
- **`tests/test_graph.py`**: 9 unit tests verifying deterministic flow, exact fallback error messages, multi-match severity selection, YAML tie-breaking, fuzzy selection fallbacks, and non-override guarantees without network calls.
- **`requirements.txt`**: Added `langgraph>=0.2.0`.

### What Was Intentionally NOT Implemented
- No Streamlit frontend UI (deferred to Phase 7).
- No session memory / checkpoint database storage.

### Test Results
- Ran complete test suite: `.\.venv\Scripts\pytest.exe -v`
- **Result**: 44 passed in 4.14s (7 Phase 2 + 8 Phase 3 + 11 Phase 4 + 9 Phase 5 + 9 Phase 6 tests).

### Current Status
- **Phase 6 complete**.

---

## Phase 7 — Session Memory

### Overview
Integrated in-memory conversation session state retention using LangGraph's `MemorySaver` checkpointer. State (such as user location and context) persists across multiple turns within the same `thread_id` session, but resets automatically upon application restart without any external database dependency.

### Key Components & Implementations
- **`app/graph.py`**:
  - `memory = MemorySaver()`: Initialized in-memory checkpointer.
  - `build_graph(checkpointer=None)`: Compiles `StateGraph` with `MemorySaver` checkpointer.
  - `parse_request_node`: Updated to retain previously resolved session location across turns on the same `thread_id` while still requiring `fetch_weather_node` to execute fresh live weather fetching on every turn.
- **`tests/test_memory.py`**:
  - 4 automated unit tests verifying same-thread state retention, cross-thread state isolation, in-memory `MemorySaver` verification (no database dependency), and fresh weather fetching on every turn.

### Key Architectural Rules
- **No External Database**: Memory is strictly in-memory (`MemorySaver`). No SQL, Redis, or file database used.
- **Fresh Weather Enforcement**: Memory retains session location and context, but does NOT cache stale weather. Every turn executes `fetch_weather_node` to get fresh metrics from Open-Meteo.
- **Thread Isolation**: Distinct `thread_id` configurations maintain 100% separate state spaces.

### Test Results
- Ran complete test suite: `.\.venv\Scripts\pytest.exe -v`
- **Result**: 50 passed in 1.89s (7 Phase 2 + 8 Phase 3 + 13 Phase 4 + 9 Phase 5 + 9 Phase 6 + 4 Phase 7 tests).

### Current Status
- **Phase 7 complete**: In-memory session checkpointer integrated, 100% test pass rate, multi-turn state retention smoke test verified.

### Next Phase
- **Phase 8**: Streamlit UI & Final Application Assembly.




