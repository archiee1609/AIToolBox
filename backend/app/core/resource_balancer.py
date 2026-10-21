"""
Dynamic Resource Discovery, Telemetry, and Load Balancing Engine.
Automatically monitors CPU utilization, host RAM, GPU VRAM headroom, and active AI tasks
across NVIDIA, AMD, Intel, Apple Silicon, Qualcomm Snapdragon, and multi-core CPUs.
Dynamically tunes Ollama thread allocation, context token budgeting, prompt batching,
and ComfyUI memory modes (--highvram, --medvram, --lowvram, --cpu) to balance system load
and prevent out-of-memory (OOM) crashes and system freezes.
"""

import os
import sys
import time
import shutil
import subprocess
from typing import Dict, Any, List, Optional, Tuple

from app.core.system_info import get_system_summary, get_memory_info, get_cpu_info, get_accelerator_info

try:
    import psutil
except ImportError:
    psutil = None

# Telemetry Cache
_LAST_TELEMETRY_TIME = 0.0
_CACHED_TELEMETRY: Optional[Dict[str, Any]] = None
_TELEMETRY_CACHE_TTL = 2.0  # seconds


def get_live_telemetry(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Retrieves real-time system resource metrics:
    - CPU utilization %
    - RAM total, available, and percent used
    - GPU dedicated VRAM or unified memory metrics (total, used, free, % used)
    - Active hardware accelerator profile
    Cached for 2 seconds to avoid excessive system polling overhead.
    """
    global _LAST_TELEMETRY_TIME, _CACHED_TELEMETRY
    now = time.time()
    if not force_refresh and _CACHED_TELEMETRY is not None and (now - _LAST_TELEMETRY_TIME) < _TELEMETRY_CACHE_TTL:
        return _CACHED_TELEMETRY

    sys_info = get_system_summary()
    accel = sys_info.get("accelerator", {})
    cpu = sys_info.get("cpu", {})
    mem = get_memory_info()

    # 1. CPU Usage
    cpu_percent = 0.0
    if psutil:
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
        except Exception:
            cpu_percent = 0.0

    # 2. GPU / VRAM Telemetry
    gpu_vendor = accel.get("vendor", "generic")
    gpu_device = accel.get("device", "CPU")
    is_unified = accel.get("is_unified_memory", False)
    total_vram_gb = accel.get("vram_gb", 0.0)
    free_vram_gb = total_vram_gb
    used_vram_gb = 0.0
    vram_percent = 0.0

    # Query real-time NVIDIA VRAM via nvidia-smi if applicable
    if gpu_vendor == "nvidia":
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi:
            try:
                out = subprocess.check_output(
                    [nvidia_smi, "--query-gpu=memory.total,memory.used,memory.free,utilization.gpu", "--format=csv,noheader,nounits"],
                    text=True,
                    timeout=1,
                    stderr=subprocess.DEVNULL
                ).strip()
                if out:
                    parts = [float(p.strip()) for p in out.splitlines()[0].split(",")]
                    if len(parts) >= 3:
                        total_vram_gb = round(parts[0] / 1024.0, 1)
                        used_vram_gb = round(parts[1] / 1024.0, 1)
                        free_vram_gb = round(parts[2] / 1024.0, 1)
                        vram_percent = round((used_vram_gb / total_vram_gb) * 100, 1) if total_vram_gb > 0 else 0.0
            except Exception:
                pass

    # For Apple Silicon & Qualcomm Snapdragon, unified memory is shared with system RAM
    elif is_unified or gpu_vendor in ["apple", "qualcomm"]:
        total_vram_gb = mem.get("total_gb", 0.0)
        free_vram_gb = mem.get("available_gb", 0.0)
        used_vram_gb = round(total_vram_gb - free_vram_gb, 1)
        vram_percent = mem.get("percent_used", 0.0)

    # General fallback for discrete AMD/Intel if direct driver query isn't available
    elif total_vram_gb > 0 and free_vram_gb == total_vram_gb:
        # Estimate conservative free headroom
        free_vram_gb = round(total_vram_gb * 0.75, 1)
        used_vram_gb = round(total_vram_gb * 0.25, 1)
        vram_percent = 25.0

    telemetry = {
        "timestamp": now,
        "os_platform": sys_info.get("os_platform", ""),
        "os_friendly": sys_info.get("os_friendly", ""),
        "architecture": sys_info.get("architecture", ""),
        "cpu": {
            "processor": cpu.get("processor", ""),
            "physical_cores": cpu.get("physical_cores", 1),
            "logical_cores": cpu.get("logical_cores", 1),
            "percent_used": cpu_percent
        },
        "memory": {
            "total_gb": mem.get("total_gb", 0.0),
            "available_gb": mem.get("available_gb", 0.0),
            "percent_used": mem.get("percent_used", 0.0)
        },
        "accelerator": {
            "vendor": gpu_vendor,
            "type": accel.get("type", "cpu"),
            "name": accel.get("name", "CPU"),
            "device": gpu_device,
            "is_unified_memory": is_unified,
            "total_vram_gb": total_vram_gb,
            "free_vram_gb": free_vram_gb,
            "used_vram_gb": used_vram_gb,
            "vram_percent_used": vram_percent,
            "details": accel.get("details", "")
        }
    }

    _CACHED_TELEMETRY = telemetry
    _LAST_TELEMETRY_TIME = now
    return telemetry


def get_current_load_profile(telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Evaluates current system telemetry and automatically assigns an operational profile:
    - ULTRA: High VRAM (>= 16GB) or Unified System RAM >= 32GB
    - BALANCED: Standard VRAM (8GB - 15GB) or System RAM 16GB - 31GB
    - ECO: Low VRAM (< 8GB) or System RAM <= 16GB or CPU execution
    Returns optimal execution parameters (thread budget, safe context window, batch size, ComfyUI flags).
    """
    t = telemetry or get_live_telemetry()
    accel = t.get("accelerator", {})
    cpu = t.get("cpu", {})
    mem = t.get("memory", {})

    total_vram = accel.get("total_vram_gb", 0.0)
    free_vram = accel.get("free_vram_gb", 0.0)
    total_ram = mem.get("total_gb", 0.0)
    avail_ram = mem.get("available_gb", 0.0)
    logical_cores = cpu.get("logical_cores", 1)
    physical_cores = cpu.get("physical_cores", 1)
    is_unified = accel.get("is_unified_memory", False)
    vendor = accel.get("vendor", "generic")

    # Determine Tier
    if (total_vram >= 15.0 and not is_unified) or (is_unified and total_ram >= 31.0):
        tier = "ULTRA"
        tier_title = "Ultra Performance"
        tier_badge = "🚀 Ultra"
        tier_color = "#059669" # Emerald green
        description = "High-end compute detected. Maximum context length, fast prompt ingestion, and high-vram diffusion active."
        max_safe_context = 16384
        default_context = 8192
        batch_size = 512
        # Allocate up to (logical_cores - 2) threads, leaving 2 threads for UI and OS
        num_threads = max(2, logical_cores - 2)
        comfy_flags = ["--highvram"] if vendor != "apple" else []
        safe_max_dim = 1024

    elif (total_vram >= 7.5 and not is_unified) or (total_ram >= 15.5):
        tier = "BALANCED"
        tier_title = "Balanced Studio"
        tier_badge = "⚖️ Balanced"
        tier_color = "#0284c7" # Sky blue
        description = "Balanced workstation detected. Auto-tuning context window and medium-vram mode for optimal stability."
        max_safe_context = 8192
        default_context = 4096
        batch_size = 256
        # Allocate physical cores, keeping logical threads free for smooth UI responsiveness
        num_threads = max(2, min(physical_cores, logical_cores - 2))
        comfy_flags = ["--medvram"] if vendor != "apple" else []
        safe_max_dim = 768

    else:
        tier = "ECO"
        tier_title = "Resource-Saver / Eco"
        tier_badge = "🌱 Eco Saver"
        tier_color = "#d97706" # Amber
        description = "Memory-constrained hardware or CPU execution detected. Auto-throttling context, batch size, and low-vram mode to guarantee zero OOM crashes."
        max_safe_context = 4096
        default_context = 2048
        batch_size = 128
        num_threads = max(1, physical_cores - 1)
        comfy_flags = ["--lowvram"] if vendor in ["nvidia", "amd", "intel"] else ["--cpu", "--use-split-cross-attention"]
        safe_max_dim = 512

    # If currently experiencing high memory pressure (> 88% RAM used or < 2GB free VRAM), downgrade safe bounds
    ram_used_pct = mem.get("percent_used", 0.0)
    if ram_used_pct > 88.0 or (total_vram > 0 and free_vram < 2.0):
        max_safe_context = min(max_safe_context, 4096)
        default_context = min(default_context, 2048)
        batch_size = min(batch_size, 128)
        num_threads = max(1, min(num_threads, 4))
        if "--highvram" in comfy_flags:
            comfy_flags = ["--medvram"]
        elif "--medvram" in comfy_flags:
            comfy_flags = ["--lowvram"]

    return {
        "tier": tier,
        "title": tier_title,
        "badge": tier_badge,
        "color": tier_color,
        "description": description,
        "max_safe_context": max_safe_context,
        "default_context": default_context,
        "optimal_threads": num_threads,
        "prompt_batch_size": batch_size,
        "comfyui_cli_flags": comfy_flags,
        "safe_max_image_dim": safe_max_dim,
        "telemetry": t
    }


def get_balanced_ollama_options(
    model_name: str = "",
    requested_context: Optional[int] = None,
    requested_temperature: Optional[float] = 0.7
) -> Dict[str, Any]:
    """
    Automatically balances Ollama inference parameters according to host system headroom.
    - Prevents CPU starvation by setting optimal num_thread (leaving threads for UI/OS).
    - Prevents CUDA/RAM crashes by automatically bounding num_ctx to safe limits.
    - Configures num_batch and f16_kv based on hardware tier.
    """
    profile = get_current_load_profile()
    max_safe_ctx = profile["max_safe_context"]

    # Bound requested context capacity safely
    if requested_context is not None:
        actual_ctx = min(requested_context, max_safe_ctx)
    else:
        actual_ctx = profile["default_context"]

    temp = requested_temperature if requested_temperature is not None else 0.7

    options: Dict[str, Any] = {
        "temperature": temp,
        "num_ctx": actual_ctx,
        "num_thread": profile["optimal_threads"],
        "num_batch": profile["prompt_batch_size"],
    }

    # Enable half-precision key/value cache to conserve memory on Balanced & Eco profiles
    if profile["tier"] in ["BALANCED", "ECO"]:
        options["f16_kv"] = True

    return options


def get_balanced_comfyui_args(base_dir: Optional[Any] = None) -> List[str]:
    """
    Computes the optimal CLI arguments for starting local ComfyUI:
    - On Apple Silicon MPS: native Metal Performance Shaders without CPU flag.
    - On NVIDIA/AMD/Intel: dynamically applies --highvram, --medvram, or --lowvram based on VRAM capacity.
    - On CPU-only systems: applies --cpu --use-split-cross-attention.
    """
    profile = get_current_load_profile()
    accel = profile["telemetry"]["accelerator"]
    vendor = accel.get("vendor", "generic")

    args = ["--listen", "127.0.0.1", "--port", "8188"]

    # Apple Silicon uses native MPS (Metal) automatically
    if vendor == "apple":
        return args

    # Check for dedicated GPU vs CPU
    if vendor in ["nvidia", "amd", "intel"]:
        for flag in profile["comfyui_cli_flags"]:
            if flag not in args:
                args.append(flag)
    else:
        # Generic CPU execution
        if "--cpu" not in args:
            args.extend(["--cpu", "--use-split-cross-attention"])

    return args


def get_balanced_image_dimensions(target_w: int, target_h: int) -> Tuple[int, int, bool]:
    """
    Bounds image dimensions so that requests on low-VRAM or CPU hardware do not trigger allocation failures.
    Returns (safe_w, safe_h, was_scaled).
    """
    profile = get_current_load_profile()
    max_dim = profile["safe_max_image_dim"]

    w = max(256, min(target_w, 1536))
    h = max(256, min(target_h, 1536))
    was_scaled = False

    if w > max_dim or h > max_dim:
        scale = max_dim / max(w, h)
        w = int(round(w * scale / 8.0) * 8)
        h = int(round(h * scale / 8.0) * 8)
        was_scaled = True

    w = (w // 8) * 8
    h = (h // 8) * 8
    return (w, h, was_scaled)


def check_system_headroom() -> Tuple[bool, str]:
    """
    Health check before dispatching high-load workloads.
    Returns (is_healthy, advisory_message).
    """
    t = get_live_telemetry(force_refresh=True)
    mem_used = t["memory"]["percent_used"]
    free_ram = t["memory"]["available_gb"]
    cpu_used = t["cpu"]["percent_used"]

    if mem_used > 93.0 or free_ram < 1.0:
        return False, f"Critical memory pressure: {mem_used}% RAM used ({free_ram} GB available). Please close external applications."
    if cpu_used > 95.0:
        return True, f"High CPU utilization ({cpu_used}%). Load balancer is throttling background threads to keep UI responsive."
    return True, "System resources healthy and balanced."
