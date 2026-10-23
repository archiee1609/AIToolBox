"""
Cross-Platform System, Hardware, and Accelerator Discovery Utility.
Provides platform-aware detection of OS (Windows, macOS, Linux), Architecture (x86_64, arm64),
CPU, RAM, and GPU Acceleration across all major vendors:
- NVIDIA (GeForce RTX/GTX, Quadro, Tesla, A100, H100, etc.)
- AMD (Radeon RX, Radeon Pro, Instinct MI series, ROCm, Ryzen AI NPUs)
- Intel (Arc A-series/B-series, Iris Xe, Core Ultra AI Boost NPU, XPU)
- Apple Silicon (M1/M2/M3/M4 Base, Pro, Max, Ultra with Metal Performance Shaders)
- Qualcomm Snapdragon (Snapdragon X Elite, X Plus, 8cx, Adreno GPU, Hexagon NPU)
- Multi-threaded CPU execution fallback (with AVX-512, AVX2, or ARM NEON SIMD)
"""

import os
import sys
import platform
import subprocess
import shutil
import re
from typing import Dict, Any, List, Optional

try:
    import psutil
except ImportError:
    psutil = None

# Module-level caches
_CACHED_PROCESSOR_NAME: Optional[str] = None
_CACHED_DISPLAY_ADAPTERS: Optional[List[str]] = None
_CACHED_PRIMARY_ACCELERATOR: Optional[Dict[str, Any]] = None
_CACHED_ALL_HARDWARE: Optional[Dict[str, Any]] = None
_CACHED_SYSTEM_SUMMARY: Optional[Dict[str, Any]] = None


def clear_hardware_cache() -> None:
    """Clears hardware caches to force re-detection."""
    global _CACHED_PROCESSOR_NAME, _CACHED_DISPLAY_ADAPTERS, _CACHED_PRIMARY_ACCELERATOR, _CACHED_ALL_HARDWARE, _CACHED_SYSTEM_SUMMARY
    _CACHED_PROCESSOR_NAME = None
    _CACHED_DISPLAY_ADAPTERS = None
    _CACHED_PRIMARY_ACCELERATOR = None
    _CACHED_ALL_HARDWARE = None
    _CACHED_SYSTEM_SUMMARY = None


def get_os_friendly_name() -> str:
    """Returns a clean, human-readable OS name and version across Windows, macOS, and Linux."""
    sys_name = platform.system()
    if sys_name == "Windows":
        rel = platform.release()
        ver = platform.version()
        return f"Windows {rel} (Build {ver})"
    elif sys_name == "Darwin":
        mac_ver, _, _ = platform.mac_ver()
        if mac_ver:
            major = mac_ver.split(".")[0]
            names = {
                "15": "macOS Sequoia",
                "14": "macOS Sonoma",
                "13": "macOS Ventura",
                "12": "macOS Monterey",
                "11": "macOS Big Sur"
            }
            market = names.get(major, "macOS")
            return f"{market} {mac_ver}"
        return f"macOS {platform.release()}"
    elif sys_name == "Linux":
        try:
            if hasattr(platform, "freedesktop_os_release"):
                os_info = platform.freedesktop_os_release()
                pretty_name = os_info.get("PRETTY_NAME")
                if pretty_name:
                    return pretty_name
        except Exception:
            pass
        os_release = "/etc/os-release"
        if os.path.exists(os_release):
            try:
                with open(os_release, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            return line.split("=", 1)[1].strip().strip('"')
            except Exception:
                pass
        return f"Linux ({platform.release()})"
    return f"{sys_name} {platform.release()}"


def _get_processor_name() -> str:
    """Retrieves detailed processor name using fast OS native APIs."""
    global _CACHED_PROCESSOR_NAME
    if _CACHED_PROCESSOR_NAME:
        return _CACHED_PROCESSOR_NAME

    proc_name = platform.processor() or "Unknown Processor"

    # Windows: Read directly from Registry (instant, 0ms overhead)
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                if val and val.strip():
                    proc_name = val.strip()
        except Exception:
            pass

    # macOS: Query machdep.cpu.brand_string
    elif sys.platform == "darwin":
        try:
            brand = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True, timeout=1, stderr=subprocess.DEVNULL).strip()
            if brand:
                proc_name = brand
        except Exception:
            pass

    # Linux: Read /proc/cpuinfo model name
    elif sys.platform.startswith("linux"):
        try:
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if "model name" in line:
                            proc_name = line.split(":", 1)[1].strip()
                            break
                        elif "Hardware" in line:
                            proc_name = line.split(":", 1)[1].strip()
        except Exception:
            pass

    _CACHED_PROCESSOR_NAME = proc_name
    return proc_name


def get_cpu_info() -> Dict[str, Any]:
    """Detects CPU architecture, processor name, cores, and vendor hints."""
    arch = platform.machine()
    proc_name = _get_processor_name()

    physical_cores = os.cpu_count() or 1
    logical_cores = os.cpu_count() or 1
    if psutil:
        try:
            physical_cores = psutil.cpu_count(logical=False) or physical_cores
            logical_cores = psutil.cpu_count(logical=True) or logical_cores
        except Exception:
            pass

    proc_lower = proc_name.lower()
    is_arm64 = arch.lower() in ["arm64", "aarch64"]
    is_apple_silicon = platform.system() == "Darwin" and is_arm64
    is_snapdragon = any(k in proc_lower for k in ["snapdragon", "qualcomm", "oryon"]) or (is_arm64 and platform.system() == "Windows")
    is_amd_cpu = "amd" in proc_lower or "ryzen" in proc_lower
    is_intel_cpu = "intel" in proc_lower or "core" in proc_lower

    return {
        "architecture": arch,
        "is_apple_silicon": is_apple_silicon,
        "is_snapdragon": is_snapdragon,
        "is_arm64": is_arm64,
        "is_amd_cpu": is_amd_cpu,
        "is_intel_cpu": is_intel_cpu,
        "processor": proc_name,
        "physical_cores": physical_cores,
        "logical_cores": logical_cores
    }


def get_memory_info() -> Dict[str, Any]:
    """Returns system RAM metrics in GB."""
    if psutil:
        try:
            vm = psutil.virtual_memory()
            total_gb = round(vm.total / (1024 ** 3), 1)
            avail_gb = round(vm.available / (1024 ** 3), 1)
            percent_used = vm.percent
            return {
                "total_gb": total_gb,
                "available_gb": avail_gb,
                "percent_used": percent_used
            }
        except Exception:
            pass
    return {
        "total_gb": 0.0,
        "available_gb": 0.0,
        "percent_used": 0.0
    }


def _get_system_display_adapters() -> List[str]:
    """Queries display adapter names using instant OS APIs."""
    global _CACHED_DISPLAY_ADAPTERS
    if _CACHED_DISPLAY_ADAPTERS is not None:
        return _CACHED_DISPLAY_ADAPTERS

    adapters: List[str] = []

    # Windows: Read Display Class from Registry (instant, ~1ms, lists NVIDIA, AMD, Intel, Qualcomm)
    if sys.platform == "win32":
        try:
            import winreg
            key_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(k, i)
                        i += 1
                        if not subkey_name.isdigit():
                            continue
                        with winreg.OpenKey(k, subkey_name) as sub:
                            try:
                                desc, _ = winreg.QueryValueEx(sub, "DriverDesc")
                                if desc and desc not in adapters and "remote" not in desc.lower():
                                    adapters.append(desc.strip())
                            except Exception:
                                pass
                    except OSError:
                        break
        except Exception:
            pass

    # Linux: lspci query
    elif sys.platform.startswith("linux"):
        lspci = shutil.which("lspci")
        if lspci:
            try:
                out = subprocess.check_output([lspci], text=True, timeout=1, stderr=subprocess.DEVNULL)
                for line in out.splitlines():
                    if any(tag in line for tag in ["VGA compatible controller:", "3D controller:", "Display controller:"]):
                        parts = line.split(":", 2)
                        desc = parts[-1].strip() if len(parts) >= 3 else line
                        adapters.append(desc)
            except Exception:
                pass

    _CACHED_DISPLAY_ADAPTERS = adapters
    return adapters


def _detect_apple_silicon_accelerator() -> Optional[Dict[str, Any]]:
    """Detects Apple Silicon M-series Metal Performance Shaders (MPS) unified compute."""
    if platform.system() != "Darwin":
        return None
    arch = platform.machine()
    if arch not in ["arm64", "aarch64"]:
        return None

    proc_name = _get_processor_name()
    chip_name = proc_name if "apple" in proc_name.lower() else f"Apple Silicon ({arch.upper()})"

    mem = get_memory_info()
    ram_gb = mem.get("total_gb", 0.0)
    return {
        "vendor": "apple",
        "type": "mps",
        "name": f"Apple Silicon Metal ({chip_name})",
        "device": chip_name,
        "vram_gb": ram_gb,
        "is_unified_memory": True,
        "details": f"Apple Metal Performance Shaders (MPS) active with {ram_gb} GB Unified Memory on {chip_name}."
    }


def _detect_snapdragon_accelerator() -> Optional[Dict[str, Any]]:
    """Detects Qualcomm Snapdragon compute platforms, Adreno GPU, and Hexagon NPU."""
    cpu = get_cpu_info()
    proc_name = cpu.get("processor", "")
    proc_lower = proc_name.lower()
    adapters = _get_system_display_adapters()
    adapter_str = " ".join(adapters).lower()

    is_snapdragon = (
        "snapdragon" in proc_lower or "qualcomm" in proc_lower or "oryon" in proc_lower
        or "adreno" in adapter_str or "snapdragon" in adapter_str
    )

    if not is_snapdragon:
        return None

    model_name = "Snapdragon X Elite / X Plus"
    if "x elite" in proc_lower or "x elite" in adapter_str:
        model_name = "Snapdragon X Elite"
    elif "x plus" in proc_lower or "x plus" in adapter_str:
        model_name = "Snapdragon X Plus"
    elif "8cx" in proc_lower:
        model_name = "Snapdragon 8cx"
    elif proc_name and "unknown" not in proc_name.lower():
        model_name = proc_name

    mem = get_memory_info()
    ram_gb = mem.get("total_gb", 0.0)
    return {
        "vendor": "qualcomm",
        "type": "npu_gpu",
        "name": f"Qualcomm Snapdragon ({model_name})",
        "device": f"{model_name} (Adreno GPU & Hexagon NPU)",
        "vram_gb": ram_gb,
        "is_unified_memory": True,
        "details": f"{model_name} compute platform with Adreno GPU & Hexagon NPU ({ram_gb} GB Unified Memory)."
    }


def _detect_nvidia_accelerator() -> Optional[Dict[str, Any]]:
    """Detects any NVIDIA GPU (GeForce RTX/GTX, Quadro, Tesla, A100, H100, Blackwell)."""
    # 1. PyTorch CUDA check if torch is ALREADY loaded in sys.modules (0ms, honors active runtime and mocks)
    if "torch" in sys.modules:
        try:
            torch = sys.modules["torch"]
            if hasattr(torch, "cuda") and torch.cuda.is_available():
                if hasattr(torch, "version") and getattr(torch.version, "hip", None):
                    return None
                if hasattr(torch, "xpu") and torch.xpu.is_available() and not torch.cuda.is_available():
                    return None

                dev_name = torch.cuda.get_device_name(0)
                total_vram = 0.0
                try:
                    total_vram = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 1)
                except Exception:
                    pass
                return {
                    "vendor": "nvidia",
                    "type": "cuda",
                    "name": f"NVIDIA CUDA ({dev_name})",
                    "device": dev_name,
                    "vram_gb": total_vram,
                    "is_unified_memory": False,
                    "details": f"{dev_name} ({total_vram} GB Dedicated VRAM)"
                }
        except Exception:
            pass

    # 2. Fast nvidia-smi CLI check (~100ms, avoids heavy 4s torch import if torch is not compiled with CUDA)
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            output = subprocess.check_output(
                [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                text=True,
                timeout=1.5,
                creationflags=creationflags,
                stderr=subprocess.DEVNULL
            ).strip()
            if output:
                first_line = output.splitlines()[0]
                parts = [p.strip() for p in first_line.split(",")]
                gpu_name = parts[0]
                vram_mb = float(parts[1]) if len(parts) > 1 else 0.0
                vram_gb = round(vram_mb / 1024, 1)
                return {
                    "vendor": "nvidia",
                    "type": "cuda",
                    "name": f"NVIDIA CUDA ({gpu_name})",
                    "device": gpu_name,
                    "vram_gb": vram_gb,
                    "is_unified_memory": False,
                    "details": f"{gpu_name} ({vram_gb} GB VRAM detected via nvidia-smi)"
                }
        except Exception:
            pass

    # 3. Fast system adapter registry/lspci lookup
    adapters = _get_system_display_adapters()
    for name in adapters:
        name_lower = name.lower()
        if any(tag in name_lower for tag in ["nvidia", "geforce", "quadro", "tesla", "rtx", "gtx"]):
            return {
                "vendor": "nvidia",
                "type": "cuda",
                "name": f"NVIDIA ({name})",
                "device": name,
                "vram_gb": 0.0,
                "is_unified_memory": False,
                "details": f"{name} (NVIDIA GPU hardware detected)"
            }

    return None


def _detect_amd_accelerator() -> Optional[Dict[str, Any]]:
    """Detects AMD Radeon GPUs, Radeon Pro, Instinct, ROCm, or Ryzen AI NPUs."""
    # 1. PyTorch ROCm/HIP check
    try:
        import torch
        if torch.cuda.is_available() and hasattr(torch.version, "hip") and torch.version.hip:
            dev_name = torch.cuda.get_device_name(0)
            total_vram = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 1)
            return {
                "vendor": "amd",
                "type": "rocm",
                "name": f"AMD ROCm ({dev_name})",
                "device": dev_name,
                "vram_gb": total_vram,
                "is_unified_memory": False,
                "details": f"{dev_name} ({total_vram} GB Dedicated VRAM / ROCm active)"
            }
    except Exception:
        pass

    # 2. rocm-smi CLI
    rocm_smi = shutil.which("rocm-smi")
    if rocm_smi:
        try:
            out = subprocess.check_output([rocm_smi, "--showproductname"], text=True, timeout=1, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                if "Card series:" in line or "Card model:" in line:
                    dev_name = line.split(":", 1)[1].strip()
                    return {
                        "vendor": "amd",
                        "type": "rocm",
                        "name": f"AMD ROCm ({dev_name})",
                        "device": dev_name,
                        "vram_gb": 0.0,
                        "is_unified_memory": False,
                        "details": f"{dev_name} (AMD ROCm acceleration detected)"
                    }
        except Exception:
            pass

    # 3. System adapter registry/lspci lookup
    adapters = _get_system_display_adapters()
    for name in adapters:
        name_lower = name.lower()
        if "amd" in name_lower or "radeon" in name_lower:
            is_apu = any(k in name_lower for k in ["graphics", "vega", "780m", "890m", "680m"])
            return {
                "vendor": "amd",
                "type": "apu" if is_apu else "rocm",
                "name": f"AMD Radeon ({name})",
                "device": name,
                "vram_gb": 0.0,
                "is_unified_memory": is_apu,
                "details": f"{name} (AMD Radeon {'Integrated APU' if is_apu else 'Discrete GPU'})"
            }

    return None


def _detect_intel_accelerator() -> Optional[Dict[str, Any]]:
    """Detects Intel Arc GPUs (A770, A750, B580), Iris Xe, or Intel Core Ultra NPUs."""
    # 1. PyTorch XPU check (Intel Extension for PyTorch / PyTorch 2.4+ native XPU)
    try:
        import torch
        if hasattr(torch, "xpu") and torch.xpu.is_available():
            dev_name = torch.xpu.get_device_name(0)
            total_vram = round(torch.xpu.get_device_properties(0).total_memory / (1024 ** 3), 1)
            return {
                "vendor": "intel",
                "type": "xpu",
                "name": f"Intel XPU ({dev_name})",
                "device": dev_name,
                "vram_gb": total_vram,
                "is_unified_memory": False,
                "details": f"{dev_name} ({total_vram} GB VRAM / Intel oneAPI Level Zero active)"
            }
    except Exception:
        pass

    # 2. System adapter registry/lspci lookup
    adapters = _get_system_display_adapters()
    for name in adapters:
        name_lower = name.lower()
        if "intel" in name_lower and ("arc" in name_lower or "iris" in name_lower or "graphics" in name_lower or "uhd" in name_lower):
            is_arc = "arc" in name_lower
            return {
                "vendor": "intel",
                "type": "xpu" if is_arc else "integrated",
                "name": f"Intel Arc ({name})" if is_arc else f"Intel Graphics ({name})",
                "device": name,
                "vram_gb": 0.0,
                "is_unified_memory": not is_arc,
                "details": f"{name} (Intel {'Discrete Arc GPU' if is_arc else 'Graphics / NPU'})"
            }

    return None


def get_accelerator_info(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Dynamically discovers and selects the primary compute accelerator across all major hardware vendors:
    - Apple Silicon Metal (MPS) with Unified Memory (M1/M2/M3/M4)
    - Qualcomm Snapdragon (X Elite/X Plus with Adreno GPU & Hexagon NPU)
    - NVIDIA CUDA (GeForce RTX/GTX, Quadro, Tesla, A100, H100)
    - AMD Radeon / ROCm (RX 7000/6000, Radeon Pro, Instinct)
    - Intel Arc / XPU / Iris Xe (A770, A750, B580)
    - Multi-threaded CPU execution with detected SIMD extensions
    """
    global _CACHED_PRIMARY_ACCELERATOR
    if _CACHED_PRIMARY_ACCELERATOR is not None and not force_refresh:
        return _CACHED_PRIMARY_ACCELERATOR

    # 1. Check Apple Silicon Metal (MPS)
    apple = _detect_apple_silicon_accelerator()
    if apple:
        _CACHED_PRIMARY_ACCELERATOR = apple
        return apple

    # 2. Check Qualcomm Snapdragon Compute Platform (Adreno & Hexagon NPU)
    snapdragon = _detect_snapdragon_accelerator()
    if snapdragon:
        _CACHED_PRIMARY_ACCELERATOR = snapdragon
        return snapdragon

    # 3. Check NVIDIA GPUs
    nvidia = _detect_nvidia_accelerator()
    if nvidia:
        _CACHED_PRIMARY_ACCELERATOR = nvidia
        return nvidia

    # 4. Check AMD Radeon GPUs / ROCm
    amd = _detect_amd_accelerator()
    if amd:
        _CACHED_PRIMARY_ACCELERATOR = amd
        return amd

    # 5. Check Intel Arc GPUs / Iris Xe
    intel = _detect_intel_accelerator()
    if intel:
        _CACHED_PRIMARY_ACCELERATOR = intel
        return intel

    # 6. CPU Multi-threaded Fallback
    mem = get_memory_info()
    cpu = get_cpu_info()
    cores = cpu.get("logical_cores", 1)
    arch = cpu.get("architecture", "")
    fallback = {
        "vendor": "generic",
        "type": "cpu",
        "name": "Multi-threaded CPU Execution",
        "device": f"{cores}-Core CPU ({arch})",
        "vram_gb": 0.0,
        "is_unified_memory": False,
        "details": f"Running on {cores} CPU cores with {mem.get('total_gb', 0)} GB System RAM."
    }
    _CACHED_PRIMARY_ACCELERATOR = fallback
    return fallback


def get_all_detected_hardware(force_refresh: bool = False) -> Dict[str, Any]:
    """Scans and catalogs all video controllers, accelerators, and processors across all vendors."""
    global _CACHED_ALL_HARDWARE
    if _CACHED_ALL_HARDWARE is not None and not force_refresh:
        return _CACHED_ALL_HARDWARE

    primary = get_accelerator_info(force_refresh=force_refresh)
    adapters = _get_system_display_adapters()

    res = {
        "adapters": adapters,
        "apple_silicon": _detect_apple_silicon_accelerator(),
        "snapdragon": _detect_snapdragon_accelerator(),
        "nvidia": _detect_nvidia_accelerator(),
        "amd": _detect_amd_accelerator(),
        "intel": _detect_intel_accelerator(),
        "primary": primary
    }
    _CACHED_ALL_HARDWARE = res
    return res


def get_system_summary(force_refresh: bool = False) -> Dict[str, Any]:
    """Returns a complete summary dictionary of system, CPU, memory, and accelerator info (cached)."""
    global _CACHED_SYSTEM_SUMMARY
    if _CACHED_SYSTEM_SUMMARY is not None and not force_refresh:
        # Update dynamic memory metrics while keeping static hardware cached
        _CACHED_SYSTEM_SUMMARY["memory"] = get_memory_info()
        return _CACHED_SYSTEM_SUMMARY

    os_name = get_os_friendly_name()
    sys_name = platform.system()
    cpu = get_cpu_info()
    mem = get_memory_info()
    accel = get_accelerator_info(force_refresh=force_refresh)
    adapters = _get_system_display_adapters()

    summary = {
        "os_platform": sys_name,  # 'Windows', 'Darwin', 'Linux'
        "os_friendly": os_name,
        "architecture": cpu["architecture"],
        "cpu": cpu,
        "memory": mem,
        "accelerator": accel,
        "detected_adapters": adapters,
        "is_posix": os.name == "posix",
        "is_windows": sys_name == "Windows",
        "is_mac": sys_name == "Darwin",
        "is_linux": sys_name == "Linux"
    }
    _CACHED_SYSTEM_SUMMARY = summary
    return summary
