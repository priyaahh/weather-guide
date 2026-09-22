import os
import sys
import uuid
from pathlib import Path
import streamlit as st

# Ensure project root is in sys.path for Streamlit execution
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from app.graph import app_graph
except ModuleNotFoundError:
    from graph import app_graph


def setup_api_key() -> None:
    """
    Syncs API key from Streamlit secrets or environment variables.
    Ensures GOOGLE_API_KEY is available for LLM operations.
    """
    try:
        if hasattr(st, "secrets"):
            if "GOOGLE_API_KEY" in st.secrets:
                os.environ.setdefault("GOOGLE_API_KEY", str(st.secrets["GOOGLE_API_KEY"]))
            elif "GEMINI_API_KEY" in st.secrets:
                os.environ.setdefault("GOOGLE_API_KEY", str(st.secrets["GEMINI_API_KEY"]))
    except Exception:
        pass

    if "GEMINI_API_KEY" in os.environ and "GOOGLE_API_KEY" not in os.environ:
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


def init_session_state() -> None:
    """Initializes session state variables for chat history and thread_id."""
    if "thread_id" not in st.session_state or not st.session_state.thread_id:
        st.session_state.thread_id = str(uuid.uuid4())

    if "messages" not in st.session_state:
        st.session_state.messages = []


def reset_session() -> None:
    """Generates a new thread_id and clears displayed chat history."""
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []


def process_user_input(prompt: str, graph_instance=None) -> str:
    """
    Invokes the LangGraph workflow with the user request and thread config.
    Returns the assistant response string or raises an exception on unexpected error.
    """
    if graph_instance is None:
        graph_instance = app_graph

    thread_id = st.session_state.thread_id
    config = {"configurable": {"thread_id": thread_id}}

    result = graph_instance.invoke({"user_message": prompt}, config=config)
    return result.get("response", "No response generated.")


def main() -> None:
    """Main entrypoint for running the Streamlit app UI."""
    st.set_page_config(
        page_title="Weather Advisory Support Bot",
        page_icon="🌤️",
        layout="centered"
    )

    setup_api_key()
    init_session_state()

    st.title("🌤️ Weather Advisory Support Bot")
    st.markdown(
        "Welcome! Ask for weather-based activity guidance and safety advisories for any location. "
        "For example: *\"Can I go cycling in Mumbai?\"* or *\"What about this afternoon?\"*"
    )

    # Sidebar controls
    with st.sidebar:
        st.header("Session Management")
        if st.button("New Conversation", help="Reset conversation state and start a new session"):
            reset_session()
            st.rerun()

        st.caption(f"Session Thread ID: `{st.session_state.thread_id[:8]}...`")

    # Render stored chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("Ask about weather advisories (e.g. 'Can I go cycling in Mumbai?')..."):
        # 1. Append and display user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Process query via graph and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Checking weather and safety policies..."):
                try:
                    response_text = process_user_input(prompt)
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                except Exception:
                    error_msg = "An unexpected error occurred while processing your request. Please try again."
                    st.error(error_msg)


if __name__ == "__main__":
    main()
