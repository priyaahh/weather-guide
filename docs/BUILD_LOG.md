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
1. **`numeric`**: Single-field threshold comparison (e.g., `uv_index >= 6.0` or `visibility <= 1000.0`).
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
- No Open-Meteo weather API integration.
- No Google Gemini LLM integration.
- No LangGraph agent state/graph implementation.
- No Streamlit frontend user interface.
- No rule matching or evaluation engine code yet (deferred to Phase 3).

### Current Status
- **Phase 2 complete**: All 12 SOP definitions created, loader built, unit tests passing 100%.

### Next Phase
- **Phase 3**: SOP Evaluation Engine & Weather Data Integration (or next planned module per workflow).
