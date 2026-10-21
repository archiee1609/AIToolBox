from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_streamlit_app_renders_without_exceptions():
    """Headless Streamlit UI test verifying zero exceptions during boot, db init, and UI render."""
    app_path = Path(__file__).parent.parent.parent / "streamlit_app.py"
    at = AppTest.from_file(str(app_path.resolve()), default_timeout=30)
    at.run()
    assert len(at.exception) == 0, f"AppTest raised unexpected exceptions: {[e.value for e in at.exception]}"
    assert len(at.chat_input) > 0
    assert "messages" in at.session_state
    assert "active_conv_id" in at.session_state
