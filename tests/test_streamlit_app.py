import os
from unittest.mock import MagicMock, patch
import pytest
import streamlit as st

from app.streamlit_app import (
    setup_api_key,
    init_session_state,
    reset_session,
    process_user_input,
    render_sop_trace
)


@pytest.fixture(autouse=True)
def clear_streamlit_session():
    """Clear st.session_state before each test."""
    st.session_state.clear()
    yield
    st.session_state.clear()


def test_init_session_state():
    """Verify session state initializes thread_id and messages list."""
    init_session_state()
    assert "thread_id" in st.session_state
    assert isinstance(st.session_state.thread_id, str)
    assert len(st.session_state.thread_id) > 0
    assert "messages" in st.session_state
    assert st.session_state.messages == []


def test_thread_id_retained_across_inits():
    """Verify calling init_session_state multiple times retains the original thread_id."""
    init_session_state()
    original_id = st.session_state.thread_id

    init_session_state()
    assert st.session_state.thread_id == original_id


def test_reset_session_creates_new_thread_id():
    """Verify reset_session changes thread_id and clears message history."""
    init_session_state()
    original_id = st.session_state.thread_id
    st.session_state.messages.append({"role": "user", "content": "Hello"})

    reset_session()
    assert st.session_state.thread_id != original_id
    assert st.session_state.messages == []


def test_process_user_input_invokes_graph():
    """Verify process_user_input passes user_message and config thread_id to app_graph."""
    init_session_state()
    thread_id = st.session_state.thread_id

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "response": "Mock advisory response.",
        "selected_sop": {"id": "SOP-001", "name": "High UV", "severity": "medium"},
        "weather": {"uv_index": 9.0}
    }

    result = process_user_input("Can I go cycling in Mumbai?", graph_instance=mock_graph)

    mock_graph.invoke.assert_called_once_with(
        {"user_message": "Can I go cycling in Mumbai?"},
        config={"configurable": {"thread_id": thread_id}}
    )
    assert result["response"] == "Mock advisory response."
    assert result["selected_sop"]["id"] == "SOP-001"


def test_render_sop_trace_safe_execution():
    """Verify render_sop_trace executes safely when selected_sop is None or valid."""
    # 1. None / empty SOP does not crash and renders nothing
    render_sop_trace(None, None)

    # 2. Valid SOP renders without exception
    with patch("streamlit.expander") as mock_expander:
        mock_exp = MagicMock()
        mock_expander.return_value.__enter__.return_value = mock_exp
        render_sop_trace(
            {"id": "SOP-001", "name": "High UV", "severity": "medium"},
            {"uv_index": 9.0}
        )
        mock_expander.assert_called_once_with("Why am I seeing this advice?")


def test_setup_api_key_env_copy():
    """Verify GEMINI_API_KEY is copied to GOOGLE_API_KEY if GOOGLE_API_KEY is missing."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_gemini_key"}, clear=True):
        setup_api_key()
        assert os.environ.get("GOOGLE_API_KEY") == "test_gemini_key"
