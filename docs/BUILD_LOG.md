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
- Dependencies have **not** been installed yet (deferred to Phase 2).

### Important Decisions
- Kept Phase 1 strictly focused on base directory structure and virtual environment creation without premature dependency installation or dummy code additions.
- Configured strict `.gitignore` rules upfront to safeguard environment variables and secrets from accidental commits.

### Current Status
- **Phase 1 complete**: Workspace initialized, folder hierarchy established, `.gitignore` created, virtual environment `.venv` provisioned, and build log initialized.

### Next Phase
- **Phase 2**: Dependency specification, SOP integration, and environment activation.
