import sys
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

    # Verify top brand banner renders cleanly without raw unparsed code blocks
    banner_markdowns = [m.value for m in at.markdown if '<div class="brand-container">' in m.value]
    assert len(banner_markdowns) > 0
    assert "LOCAL AI WORKBENCH" in banner_markdowns[0]
    assert "100% Private" in banner_markdowns[0]
    # Ensure no raw unclosed or pre-formatted code block escapes
    assert "```" not in banner_markdowns[0]


def test_streamlit_settings_page_renders_cleanly():
    """Headless test verifying Settings page and Hardware & Acceleration card render cleanly."""
    app_path = Path(__file__).parent.parent.parent / "streamlit_app.py"
    at = AppTest.from_file(str(app_path.resolve()), default_timeout=30)
    at.run()
    assert len(at.exception) == 0

    if len(at.sidebar.radio) > 0:
        at.sidebar.radio[0].set_value("⚙️ More").run()
        assert len(at.exception) == 0
        hardware_markdowns = [m.value for m in at.markdown if "Hardware & Acceleration" in m.value or "Compute Device" in m.value]
        assert len(hardware_markdowns) > 0

        # Verify Image Generation tab rendered
        img_tab_markdowns = [m.value for m in at.markdown if "AI Image Generation Studio" in m.value or "Target Resolution" in m.value]
        assert len(img_tab_markdowns) > 0


def test_render_winxp_progress_bar_downloading_and_complete():
    """Verify Windows XP style progress bar renders Downloading state and Complete with Green Tick."""
    root_dir = str(Path(__file__).parent.parent.parent)
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    from app.core.ui_components import render_winxp_progress_bar

    # 1. Downloading state
    html_dl = render_winxp_progress_bar(
        percent=45.5,
        status="downloading",
        detail="downloading layer 8a37e96 (450 MB / 1000 MB)"
    )
    assert "Status:" in html_dl
    assert "Downloading..." in html_dl
    assert "45.5%" in html_dl
    assert "repeating-linear-gradient" in html_dl  # XP segmented bricks
    assert "downloading layer 8a37e96" in html_dl

    # 2. Complete state with Green Tick
    html_comp = render_winxp_progress_bar(
        percent=100.0,
        status="complete",
        detail="Model ready"
    )
    assert "Status:" in html_comp
    assert "Complete" in html_comp
    assert "✔" in html_comp  # Green Tick
    assert "100.0%" in html_comp
    assert "width:100.0%" in html_comp

    # 3. Stopped / Paused state
    html_stop = render_winxp_progress_bar(
        percent=62.5,
        status="stopped",
        detail="Cancelled by user"
    )
    assert "Status:" in html_stop
    assert "Stopped" in html_stop
    assert "⏹" in html_stop
    assert "62.5%" in html_stop
