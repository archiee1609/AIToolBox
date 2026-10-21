import os
import sys
import platform
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.core.system_info import (
    get_os_friendly_name,
    get_cpu_info,
    get_memory_info,
    get_accelerator_info,
    get_system_summary,
    clear_hardware_cache,
)
from app.core.security import evaluate_command_safety, CommandPolicyError
from app.services.ollama_service import OllamaService
from app.services.comfyui_service import ComfyUIService


def test_system_info_current_platform():
    """Verifies that system info functions run without error and return expected structure."""
    os_name = get_os_friendly_name()
    assert isinstance(os_name, str)
    assert len(os_name) > 0

    cpu = get_cpu_info()
    assert "architecture" in cpu
    assert "logical_cores" in cpu
    assert cpu["logical_cores"] >= 1

    mem = get_memory_info()
    assert "total_gb" in mem
    assert mem["total_gb"] > 0
    assert "available_gb" in mem

    accel = get_accelerator_info()
    assert "type" in accel
    assert accel["type"] in ["cuda", "mps", "rocm", "cpu"]
    assert "name" in accel

    summary = get_system_summary()
    assert "os_platform" in summary
    assert "cpu" in summary
    assert "memory" in summary
    assert "accelerator" in summary
    assert summary["os_platform"] in ["Windows", "Darwin", "Linux"]


def test_system_info_simulated_mac_apple_silicon():
    """Simulates macOS Apple Silicon M3/M4 environment."""
    clear_hardware_cache()
    with patch("platform.system", return_value="Darwin"), \
         patch("platform.machine", return_value="arm64"), \
         patch("platform.mac_ver", return_value=("14.5", ("", "", ""), "arm64")), \
         patch("app.core.system_info._get_processor_name", return_value="Apple M3 Max"):
        
        friendly = get_os_friendly_name()
        assert "macOS Sonoma" in friendly or "14.5" in friendly

        cpu = get_cpu_info()
        assert cpu["is_apple_silicon"] is True
        assert cpu["is_arm64"] is True

        accel = get_accelerator_info(force_refresh=True)
        assert accel["vendor"] == "apple"
        assert accel["type"] == "mps"
        assert accel["is_unified_memory"] is True
        assert "Apple Silicon Metal" in accel["name"]
        assert "Apple M3 Max" in accel["device"]
    clear_hardware_cache()


def test_accelerator_simulated_nvidia_cuda():
    """Simulates an NVIDIA GeForce / RTX workstation."""
    clear_hardware_cache()
    mock_props = MagicMock()
    mock_props.total_memory = 12 * (1024 ** 3)  # 12 GB

    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.get_device_name.return_value = "NVIDIA GeForce RTX 3080 Ti"
    mock_torch.cuda.get_device_properties.return_value = mock_props
    mock_torch.version.hip = None

    with patch("platform.system", return_value="Linux"), \
         patch.dict("sys.modules", {"torch": mock_torch}):
        
        accel = get_accelerator_info(force_refresh=True)
        assert accel["vendor"] == "nvidia"
        assert accel["type"] == "cuda"
        assert "RTX 3080 Ti" in accel["device"]
        assert accel["vram_gb"] == 12.0
        assert accel["is_unified_memory"] is False
    clear_hardware_cache()


def test_accelerator_simulated_amd_rocm():
    """Simulates an AMD Radeon RX 7900 XTX running with ROCm/HIP."""
    clear_hardware_cache()
    mock_props = MagicMock()
    mock_props.total_memory = 24 * (1024 ** 3)  # 24 GB

    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.get_device_name.return_value = "AMD Radeon RX 7900 XTX"
    mock_torch.cuda.get_device_properties.return_value = mock_props
    mock_torch.version.hip = "5.7"

    with patch("platform.system", return_value="Linux"), \
         patch("shutil.which", return_value=None), \
         patch.dict("sys.modules", {"torch": mock_torch}):
        
        accel = get_accelerator_info(force_refresh=True)
        assert accel["vendor"] == "amd"
        assert accel["type"] == "rocm"
        assert "RX 7900 XTX" in accel["device"]
        assert accel["vram_gb"] == 24.0
    clear_hardware_cache()


def test_accelerator_simulated_intel_arc():
    """Simulates an Intel Arc A770 discrete GPU workstation."""
    clear_hardware_cache()
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = False
    mock_torch.version.hip = None
    mock_props = MagicMock()
    mock_props.total_memory = 16 * (1024 ** 3)
    mock_torch.xpu.is_available.return_value = True
    mock_torch.xpu.get_device_name.return_value = "Intel(R) Arc(TM) A770 Graphics"
    mock_torch.xpu.get_device_properties.return_value = mock_props

    with patch("platform.system", return_value="Windows"), \
         patch("shutil.which", return_value=None), \
         patch("app.core.system_info._get_system_display_adapters", return_value=["Intel(R) Arc(TM) A770 Graphics"]), \
         patch.dict("sys.modules", {"torch": mock_torch}):
        
        accel = get_accelerator_info(force_refresh=True)
        assert accel["vendor"] == "intel"
        assert accel["type"] == "xpu"
        assert "A770" in accel["device"]
    clear_hardware_cache()


def test_accelerator_simulated_snapdragon():
    """Simulates Qualcomm Snapdragon X Elite on ARM64 Windows."""
    clear_hardware_cache()
    with patch("platform.system", return_value="Windows"), \
         patch("platform.machine", return_value="ARM64"), \
         patch("app.core.system_info._get_processor_name", return_value="Snapdragon(R) X Elite - X1E-80-100 - Qualcomm(R) Oryon(TM) CPU"), \
         patch("app.core.system_info._get_system_display_adapters", return_value=["Qualcomm(R) Adreno(TM) GPU"]):
        
        cpu = get_cpu_info()
        assert cpu["is_snapdragon"] is True
        assert cpu["is_arm64"] is True

        accel = get_accelerator_info(force_refresh=True)
        assert accel["vendor"] == "qualcomm"
        assert accel["type"] == "npu_gpu"
        assert "Snapdragon X Elite" in accel["name"]
        assert "Adreno GPU & Hexagon NPU" in accel["device"]
        assert accel["is_unified_memory"] is True
    clear_hardware_cache()


def test_accelerator_cpu_fallback():
    """Simulates CPU-only machine when no accelerators are detected."""
    clear_hardware_cache()
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = False
    mock_torch.xpu.is_available.return_value = False
    mock_torch.backends.mps.is_available.return_value = False

    with patch("platform.system", return_value="Linux"), \
         patch("platform.machine", return_value="x86_64"), \
         patch("app.core.system_info._get_system_display_adapters", return_value=[]), \
         patch("shutil.which", return_value=None), \
         patch.dict("sys.modules", {"torch": mock_torch}):
        
        accel = get_accelerator_info(force_refresh=True)
        assert accel["vendor"] == "generic"
        assert accel["type"] == "cpu"
        assert "CPU" in accel["name"]
    clear_hardware_cache()


def test_system_info_simulated_linux():
    """Simulates Linux Ubuntu environment."""
    with patch("platform.system", return_value="Linux"), \
         patch("platform.release", return_value="6.5.0-generic"), \
         patch("platform.machine", return_value="x86_64"), \
         patch("shutil.which", return_value=None):
        
        friendly = get_os_friendly_name()
        assert "Linux" in friendly

        summary = get_system_summary()
        assert summary["is_linux"] is True
        assert summary["is_windows"] is False
        assert summary["is_mac"] is False


def test_security_cross_platform_blocked_commands(tmp_path):
    """Tests that destructive Linux/macOS commands and privilege escalation are blocked."""
    cwd = tmp_path

    # Destructive POSIX commands
    blocked_posix = [
        "rm -rf /",
        "rm -rf /*",
        "rm -fr /",
        "rm -rf ~",
        "chmod -R 777 /",
        "reboot",
        "poweroff",
        "init 0",
        "init 6",
        ":(){ :|:& };:",
        "dd if=/dev/zero of=/dev/sda",
    ]
    for cmd in blocked_posix:
        safe, reason = evaluate_command_safety(cmd, cwd=cwd, workspace_root=cwd)
        assert safe is False, f"Expected '{cmd}' to be blocked!"
        assert "blocked" in reason.lower() or "policy" in reason.lower()

    # Privilege escalation attempts on POSIX & Windows
    escalation_commands = [
        "sudo rm -rf test",
        "sudo apt install curl",
        "su -",
        "su root",
        "doas apt update",
        "pkexec bash",
        "runas /user:Administrator cmd",
    ]
    for cmd in escalation_commands:
        safe, reason = evaluate_command_safety(cmd, cwd=cwd, workspace_root=cwd)
        assert safe is False, f"Expected '{cmd}' to be blocked as privilege escalation!"
        assert "privilege escalation" in reason.lower() or "blocked" in reason.lower()


def test_ollama_executable_discovery_unix_mock(tmp_path):
    """Verifies that Ollama executable discovery finds macOS / Linux paths."""
    service = OllamaService()
    fake_ollama = tmp_path / "ollama"
    fake_ollama.write_text("#!/bin/sh\necho ollama")
    fake_ollama.chmod(0o755)

    with patch("shutil.which", return_value=str(fake_ollama)):
        found = service.find_ollama_executable()
        assert found == fake_ollama


def test_comfyui_find_python_executable_cross_platform():
    """Verifies ComfyUI finds virtualenv python or falls back to sys.executable."""
    service = ComfyUIService()
    py = service.find_python_executable()
    assert isinstance(py, str)
    assert len(py) > 0
    assert Path(py).name.lower().startswith("python")
