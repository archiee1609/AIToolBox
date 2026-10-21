import pytest
from unittest.mock import patch, MagicMock

from app.core.resource_balancer import (
    get_live_telemetry,
    get_current_load_profile,
    get_balanced_ollama_options,
    get_balanced_comfyui_args,
    get_balanced_image_dimensions,
    check_system_headroom,
)


def test_get_live_telemetry_structure():
    """Verifies that live telemetry returns valid metrics."""
    telemetry = get_live_telemetry(force_refresh=True)
    assert "cpu" in telemetry
    assert "memory" in telemetry
    assert "accelerator" in telemetry

    cpu = telemetry["cpu"]
    assert "percent_used" in cpu
    assert "logical_cores" in cpu
    assert cpu["logical_cores"] >= 1

    mem = telemetry["memory"]
    assert "total_gb" in mem
    assert mem["total_gb"] > 0
    assert "available_gb" in mem

    accel = telemetry["accelerator"]
    assert "vendor" in accel
    assert "type" in accel


def test_load_profile_ultra_simulation():
    """Simulates a high-end workstation with 16GB VRAM (e.g. RTX 4090 / 5090)."""
    mock_telemetry = {
        "accelerator": {
            "vendor": "nvidia",
            "type": "cuda",
            "total_vram_gb": 16.0,
            "free_vram_gb": 12.0,
            "is_unified_memory": False,
        },
        "cpu": {
            "logical_cores": 16,
            "physical_cores": 8,
            "percent_used": 15.0,
        },
        "memory": {
            "total_gb": 32.0,
            "available_gb": 20.0,
            "percent_used": 37.5,
        }
    }
    profile = get_current_load_profile(mock_telemetry)
    assert profile["tier"] == "ULTRA"
    assert profile["max_safe_context"] == 16384
    assert profile["prompt_batch_size"] == 512
    assert profile["optimal_threads"] == 14  # 16 - 2
    assert "--highvram" in profile["comfyui_cli_flags"]


def test_load_profile_balanced_simulation():
    """Simulates a standard 8GB VRAM GPU system."""
    mock_telemetry = {
        "accelerator": {
            "vendor": "nvidia",
            "type": "cuda",
            "total_vram_gb": 8.0,
            "free_vram_gb": 6.0,
            "is_unified_memory": False,
        },
        "cpu": {
            "logical_cores": 12,
            "physical_cores": 6,
            "percent_used": 25.0,
        },
        "memory": {
            "total_gb": 16.0,
            "available_gb": 9.0,
            "percent_used": 43.7,
        }
    }
    profile = get_current_load_profile(mock_telemetry)
    assert profile["tier"] == "BALANCED"
    assert profile["max_safe_context"] == 8192
    assert profile["prompt_batch_size"] == 256
    assert "--medvram" in profile["comfyui_cli_flags"]


def test_load_profile_eco_simulation():
    """Simulates a resource-constrained 4GB / CPU-only machine."""
    mock_telemetry = {
        "accelerator": {
            "vendor": "generic",
            "type": "cpu",
            "total_vram_gb": 0.0,
            "free_vram_gb": 0.0,
            "is_unified_memory": False,
        },
        "cpu": {
            "logical_cores": 4,
            "physical_cores": 4,
            "percent_used": 40.0,
        },
        "memory": {
            "total_gb": 8.0,
            "available_gb": 3.0,
            "percent_used": 62.5,
        }
    }
    profile = get_current_load_profile(mock_telemetry)
    assert profile["tier"] == "ECO"
    assert profile["max_safe_context"] == 4096
    assert profile["prompt_batch_size"] == 128
    assert "--cpu" in profile["comfyui_cli_flags"]


def test_balanced_ollama_options_auto_bounding():
    """Verifies that requesting excessive context length is auto-bounded to safe hardware ceiling."""
    # Request an extreme 65,536 tokens
    opts = get_balanced_ollama_options(
        model_name="gemma4:12b",
        requested_context=65536,
        requested_temperature=0.8
    )
    assert "num_ctx" in opts
    # On any hardware, num_ctx should be bounded to safe ceiling (at most 16,384)
    assert opts["num_ctx"] <= 16384
    assert opts["temperature"] == 0.8
    assert "num_thread" in opts
    assert opts["num_thread"] >= 1
    assert "num_batch" in opts


def test_balanced_image_dimensions():
    """Verifies image dimension bounding for safe memory usage."""
    w, h, scaled = get_balanced_image_dimensions(1024, 768)
    assert w % 8 == 0
    assert h % 8 == 0
    assert w >= 256 and h >= 256


def test_system_headroom_check():
    """Tests system headroom detection."""
    is_ok, msg = check_system_headroom()
    assert isinstance(is_ok, bool)
    assert isinstance(msg, str)
    assert len(msg) > 0


@pytest.mark.asyncio
async def test_rest_balancer_endpoint():
    """Tests GET /api/health/balancer returns 200 OK with telemetry and profile."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health/balancer")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "profile" in data
        assert "tier" in data["profile"]
        assert "max_safe_context" in data["profile"]
