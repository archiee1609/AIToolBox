"""
Hardware-Aware LLM Recommendation Engine.
Analyzes host system hardware specifications (CPU cores, physical cores, RAM headroom,
GPU accelerator vendor, dedicated/unified VRAM, and operational load profile)
to recommend the optimal Ollama models to download.
"""

from typing import Dict, Any, List, Optional, Tuple
from app.core.system_info import get_system_summary
from app.core.resource_balancer import get_current_load_profile, get_live_telemetry
from app.schemas.models import (
    SystemHardwareSpec,
    ModelRecommendation,
    ModelRecommendationsResponse
)

# Curated catalog of high-impact open weights models available on Ollama
CURATED_MODEL_CATALOG = [
    # --- Ultra-Lightweight (2B - 4B) ---
    {
        "tag": "llama3.2:latest",
        "name": "Llama 3.2 (3B)",
        "parameter_size": "3B",
        "download_size": "2.0 GB",
        "min_ram_gb": 4.0,
        "recommended_ram_gb": 6.0,
        "target_vram_gb": 3.0,
        "category": "lightweight",
        "category_label": "⚡ Ultra-Fast Everyday Assistant",
        "description": "Meta's ultra-compact, high-efficiency model. Near-instantaneous response times with minimal resource usage.",
        "strengths": ["Instant startup", "Ideal for CPU or battery operation", "Summaries & conversation"]
    },
    {
        "tag": "qwen2.5:3b",
        "name": "Qwen 2.5 (3B)",
        "parameter_size": "3B",
        "download_size": "1.9 GB",
        "min_ram_gb": 4.0,
        "recommended_ram_gb": 6.0,
        "target_vram_gb": 3.0,
        "category": "lightweight",
        "category_label": "⚡ Compact Multilingual & Logic",
        "description": "Alibaba's compact model with surprisingly strong coding, multi-turn reasoning, and multilingual support.",
        "strengths": ["Multilingual prowess", "Compact code generation", "Low memory footprint"]
    },
    {
        "tag": "phi3.5:latest",
        "name": "Phi-3.5 Mini (3.8B)",
        "parameter_size": "3.8B",
        "download_size": "2.2 GB",
        "min_ram_gb": 4.5,
        "recommended_ram_gb": 7.0,
        "target_vram_gb": 3.5,
        "category": "lightweight",
        "category_label": "⚡ Compact Synthetic Reasoning",
        "description": "Microsoft's lightweight synthetic reasoning model punching far above its weight class on logic benchmarks.",
        "strengths": ["Logical puzzles", "Math basics", "Extreme parameter efficiency"]
    },

    # --- Balanced (7B - 9B) ---
    {
        "tag": "qwen2.5:7b",
        "name": "Qwen 2.5 (7B)",
        "parameter_size": "7B",
        "download_size": "4.7 GB",
        "min_ram_gb": 8.0,
        "recommended_ram_gb": 12.0,
        "target_vram_gb": 6.0,
        "category": "daily_driver",
        "category_label": "🏆 Best Overall Daily Driver",
        "description": "The gold standard 7B open model. Outperforms many larger models on general knowledge, comprehension, and tools.",
        "strengths": ["Comprehensive knowledge", "Tool calling", "Exceptional general chat", "Flawless instruction following"]
    },
    {
        "tag": "qwen2.5-coder:7b",
        "name": "Qwen 2.5 Coder (7B)",
        "parameter_size": "7B",
        "download_size": "4.7 GB",
        "min_ram_gb": 8.0,
        "recommended_ram_gb": 12.0,
        "target_vram_gb": 6.0,
        "category": "coding",
        "category_label": "💻 Software Engineering & Code Agent",
        "description": "Trained on over 5.5 trillion tokens of code. Class-leading code generation, debugging, refactoring, and terminal commands.",
        "strengths": ["Python, TS, Rust, Go", "Diff & patch creation", "Terminal script generation", "Bug finding"]
    },
    {
        "tag": "mistral:7b",
        "name": "Mistral (7B)",
        "parameter_size": "7B",
        "download_size": "4.1 GB",
        "min_ram_gb": 8.0,
        "recommended_ram_gb": 12.0,
        "target_vram_gb": 5.5,
        "category": "daily_driver",
        "category_label": "🏆 Reliable General Assistant",
        "description": "Battle-tested, concise, and reliable instruction model with low latency and low hallucination rates.",
        "strengths": ["Concise prose", "Fast token throughput", "Low hallucination"]
    },
    {
        "tag": "deepseek-r1:7b",
        "name": "DeepSeek R1 Distill (7B)",
        "parameter_size": "7B",
        "download_size": "4.7 GB",
        "min_ram_gb": 8.0,
        "recommended_ram_gb": 12.0,
        "target_vram_gb": 6.0,
        "category": "reasoning",
        "category_label": "🧠 Deep Reasoning & Math (Chain-of-Thought)",
        "description": "State-of-the-art open reasoning model. Uses extended chain-of-thought scratchpad to solve complex logic, STEM, and math problems.",
        "strengths": ["Step-by-step thinking", "Math & logic puzzles", "Scientific analysis", "Clear derivations"]
    },
    {
        "tag": "gemma2:9b",
        "name": "Gemma 2 (9B)",
        "parameter_size": "9B",
        "download_size": "5.5 GB",
        "min_ram_gb": 10.0,
        "recommended_ram_gb": 16.0,
        "target_vram_gb": 7.5,
        "category": "daily_driver",
        "category_label": "🏆 High-Nuance Writing & Analysis",
        "description": "Google DeepMind's flagship 9B model featuring sliding window attention, high conversational nuance, and deep comprehension.",
        "strengths": ["Creative and technical writing", "Analytical summaries", "Nuanced dialogue"]
    },
    {
        "tag": "llava:7b",
        "name": "LLaVA (7B Vision)",
        "parameter_size": "7B",
        "download_size": "4.7 GB",
        "min_ram_gb": 8.0,
        "recommended_ram_gb": 12.0,
        "target_vram_gb": 6.5,
        "category": "vision",
        "category_label": "👁️ Multimodal Vision & Image Understanding",
        "description": "Multimodal visual reasoning engine capable of analyzing photos, technical diagrams, architectural flowcharts, and OCR documents.",
        "strengths": ["Visual Q&A", "Diagram analysis", "Document OCR", "UI screenshot inspection"]
    },

    # --- High-End Workstation (12B - 14B) ---
    {
        "tag": "qwen2.5:14b",
        "name": "Qwen 2.5 (14B)",
        "parameter_size": "14B",
        "download_size": "9.0 GB",
        "min_ram_gb": 14.0,
        "recommended_ram_gb": 20.0,
        "target_vram_gb": 11.0,
        "category": "daily_driver",
        "category_label": "🚀 High-End Workstation Powerhouse",
        "description": "Frontier-tier 14B intelligence rivaling larger proprietary models. Excellent for comprehensive research, coding, and synthesis.",
        "strengths": ["Deep reasoning", "Long-form drafting", "Complex tool chains", "Massive context retention"]
    },
    {
        "tag": "qwen2.5-coder:14b",
        "name": "Qwen 2.5 Coder (14B)",
        "parameter_size": "14B",
        "download_size": "9.0 GB",
        "min_ram_gb": 14.0,
        "recommended_ram_gb": 20.0,
        "target_vram_gb": 11.0,
        "category": "coding",
        "category_label": "💻 Advanced Multi-File Code Engineer",
        "description": "Top-ranked coding LLM in its weight class. Handles full repository refactoring, complex bug analysis, and system architecture.",
        "strengths": ["Full repo refactoring", "Complex test writing", "Architecture blueprints", "Multi-language mastery"]
    },
    {
        "tag": "deepseek-r1:14b",
        "name": "DeepSeek R1 Distill (14B)",
        "parameter_size": "14B",
        "download_size": "9.0 GB",
        "min_ram_gb": 14.0,
        "recommended_ram_gb": 20.0,
        "target_vram_gb": 11.0,
        "category": "reasoning",
        "category_label": "🧠 Elite Mathematics & Scientific Reasoning",
        "description": "Exceptional deep-thinking model fine-tuned on R1 reasoning outputs. Excels at competitive programming, mathematics, and logic proofs.",
        "strengths": ["Competitive STEM problems", "Deep reflective thinking", "Formal logic validation", "Complex algorithmic designs"]
    },
    {
        "tag": "phi4:14b",
        "name": "Phi-4 (14B)",
        "parameter_size": "14B",
        "download_size": "9.1 GB",
        "min_ram_gb": 14.0,
        "recommended_ram_gb": 20.0,
        "target_vram_gb": 11.0,
        "category": "reasoning",
        "category_label": "🧠 Microsoft Synthetic Logic & Research",
        "description": "Microsoft's state-of-the-art 14B model trained with synthetic curriculum learning for exceptional precision and reasoning.",
        "strengths": ["High precision output", "Academic research", "Synthetic reasoning benchmarks"]
    },
    {
        "tag": "gemma4:12b",
        "name": "Gemma 4 (12B Multimodal)",
        "parameter_size": "12B",
        "download_size": "6.6 GB",
        "min_ram_gb": 12.0,
        "recommended_ram_gb": 18.0,
        "target_vram_gb": 9.5,
        "category": "vision",
        "category_label": "👁️ Next-Gen Multimodal & Tool Agent",
        "description": "Google's versatile multimodal model delivering simultaneous vision comprehension, fast text reasoning, and tool execution.",
        "strengths": ["Vision + text in one model", "Tool calling", "Large context", "Efficient quantization"]
    },

    # --- Maximum Memory / Frontier (32B) ---
    {
        "tag": "qwen2.5:32b",
        "name": "Qwen 2.5 (32B)",
        "parameter_size": "32B",
        "download_size": "20.0 GB",
        "min_ram_gb": 28.0,
        "recommended_ram_gb": 36.0,
        "target_vram_gb": 22.0,
        "category": "daily_driver",
        "category_label": "🌌 Frontier Workstation Master",
        "description": "Frontier-level open weights model for extreme accuracy, complex reasoning, and professional workloads on high-VRAM rigs.",
        "strengths": ["Near-GPT-4o general performance", "Massive knowledge retrieval", "Zero-shot excellence"]
    }
]


class ModelRecommendationService:
    """
    Intelligent hardware-aware model recommendation service.
    """

    def analyze_system_specs(self, sys_summary: Optional[Dict[str, Any]] = None) -> SystemHardwareSpec:
        """Extracts and standardizes system hardware specification."""
        summary = sys_summary or get_system_summary()
        accel = summary.get("accelerator", {})
        cpu = summary.get("cpu", {})
        mem = summary.get("memory", {})
        accel_copy = dict(accel)
        accel_copy["total_vram_gb"] = accel.get("vram_gb", accel.get("total_vram_gb", 0.0))
        accel_copy["free_vram_gb"] = accel.get("vram_gb", accel.get("free_vram_gb", 0.0))
        sim_tele = {"accelerator": accel_copy, "cpu": cpu, "memory": mem} if sys_summary is not None else None
        profile = get_current_load_profile(sim_tele)

        return SystemHardwareSpec(
            os_name=summary.get("os_friendly", "Operating System"),
            cpu_name=cpu.get("processor", "Multi-Core CPU"),
            cpu_cores=cpu.get("logical_cores", 4),
            ram_total_gb=mem.get("total_gb", 16.0),
            ram_available_gb=mem.get("available_gb", 8.0),
            gpu_vendor=accel.get("vendor", "generic"),
            gpu_name=accel.get("name", "Integrated Graphics"),
            vram_gb=accel.get("vram_gb", 0.0),
            is_unified_memory=accel.get("is_unified_memory", False),
            tier=profile.get("tier", "BALANCED"),
            tier_badge=profile.get("badge", "⚖️ Balanced"),
            tier_description=profile.get("description", "")
        )

    def evaluate_model_fit(
        self,
        model_meta: Dict[str, Any],
        spec: SystemHardwareSpec
    ) -> Tuple[str, str, str, str, bool]:
        """
        Evaluates fit score, execution mode, and personalized reason for a given model.
        Returns: (fit_score, fit_badge, execution_mode, reason, is_compatible)
        """
        target_vram = model_meta.get("target_vram_gb", 6.0)
        min_ram = model_meta.get("min_ram_gb", 8.0)
        param_size = model_meta.get("parameter_size", "7B")

        # 1. Apple Silicon or Qualcomm Unified Memory Architecture
        if spec.is_unified_memory or spec.gpu_vendor in ["apple", "qualcomm"]:
            # On Apple Silicon Metal, memory is shared between CPU and GPU with high memory bandwidth
            if spec.ram_total_gb >= min_ram * 1.5:
                fit_score = "Perfect Match"
                fit_badge = "🟢 Perfect Fit"
                exec_mode = "Unified High-Speed (MPS)"
                reason = (
                    f"Fits comfortably inside your {spec.ram_total_gb:.0f} GB unified memory on {spec.os_name}. "
                    f"Apple Silicon Metal Performance Shaders provide direct high-bandwidth GPU acceleration with zero PCIe bottlenecks."
                )
                return fit_score, fit_badge, exec_mode, reason, True
            elif spec.ram_total_gb >= min_ram:
                fit_score = "Great Fit"
                fit_badge = "🔵 Great Fit"
                exec_mode = "Unified Memory (MPS)"
                reason = (
                    f"Runs well within your {spec.ram_total_gb:.0f} GB unified memory. "
                    f"Metal Shaders will accelerate inference smoothly with sufficient headroom for system apps."
                )
                return fit_score, fit_badge, exec_mode, reason, True
            elif spec.ram_total_gb >= min_ram * 0.8:
                fit_score = "Tight Fit"
                fit_badge = "🟡 Tight Memory"
                exec_mode = "Unified (Memory Constrained)"
                reason = (
                    f"Will run on your {spec.ram_total_gb:.0f} GB Mac, but close other heavy applications "
                    f"to avoid unified memory swapping."
                )
                return fit_score, fit_badge, exec_mode, reason, True
            else:
                return "Too Heavy", "🔴 Too Heavy", "OOM Risk", "Model exceeds safe limits for your unified RAM capacity.", False

        # 2. Discrete Dedicated GPU (NVIDIA CUDA, AMD ROCm, Intel Arc XPU)
        if spec.vram_gb >= 2.0 and spec.gpu_vendor in ["nvidia", "amd", "intel"]:
            if spec.vram_gb >= target_vram + 0.5:
                fit_score = "Perfect Match"
                fit_badge = "🟢 100% GPU VRAM"
                exec_mode = f"100% GPU ({spec.gpu_name})"
                reason = (
                    f"Loads 100% into your {spec.vram_gb:.1f} GB VRAM on {spec.gpu_name}. "
                    f"Zero system RAM offloading ensures blazingly fast inference with maximal tokens/sec."
                )
                return fit_score, fit_badge, exec_mode, reason, True
            elif spec.vram_gb >= target_vram * 0.75 and spec.ram_total_gb >= min_ram:
                fit_score = "Great Fit"
                fit_badge = "🔵 GPU Accelerated"
                exec_mode = "GPU Accelerated (Tight VRAM)"
                reason = (
                    f"Fits in your {spec.vram_gb:.1f} GB VRAM with compact context caching. "
                    f"Delivers full GPU acceleration with excellent responsiveness."
                )
                return fit_score, fit_badge, exec_mode, reason, True
            elif spec.ram_total_gb >= min_ram:
                fit_score = "Supported"
                fit_badge = "🟡 Split GPU/CPU"
                exec_mode = "Hybrid GPU + RAM Offload"
                reason = (
                    f"Layers will split between your {spec.vram_gb:.1f} GB VRAM and {spec.ram_total_gb:.0f} GB system RAM. "
                    f"Hardware load balancer will prevent OOM crashes."
                )
                return fit_score, fit_badge, exec_mode, reason, True
            else:
                return "Too Heavy", "🔴 Too Heavy", "OOM Risk", "Model exceeds available VRAM and system RAM headroom.", False

        # 3. CPU-Only Execution or Low-VRAM Fallback
        if spec.ram_total_gb >= min_ram:
            if param_size in ["2B", "3B", "3.8B"]:
                fit_score = "Perfect Match"
                fit_badge = "🟢 CPU Fast"
                exec_mode = f"Multi-Threaded CPU ({spec.cpu_cores} threads)"
                reason = (
                    f"Specially tuned for CPU execution on your {spec.cpu_cores}-thread processor and {spec.ram_total_gb:.0f} GB RAM. "
                    f"Generates prompt responses quickly without high memory consumption or freezing background apps."
                )
                return fit_score, fit_badge, exec_mode, reason, True
            elif param_size in ["7B", "8B", "9B"] and spec.ram_total_gb >= 15.0:
                fit_score = "Supported"
                fit_badge = "🟡 CPU Heavy"
                exec_mode = f"CPU Execution ({spec.cpu_cores} threads)"
                reason = (
                    f"Supported by your {spec.ram_total_gb:.0f} GB RAM. CPU token generation will be steady "
                    f"(~8-15 tokens/sec across {spec.cpu_cores} cores)."
                )
                return fit_score, fit_badge, exec_mode, reason, True
            else:
                return "Too Heavy", "🔴 Too Heavy", "Slow on CPU", "A 14B+ model runs sluggishly on CPU without dedicated GPU acceleration.", False
        else:
            return "Too Heavy", "🔴 Insufficient RAM", "Exceeds Capacity", "Requires more system RAM than currently available.", False

    def get_recommendations(
        self,
        sys_summary: Optional[Dict[str, Any]] = None,
        installed_models: Optional[List[str]] = None
    ) -> ModelRecommendationsResponse:
        """
        Calculates and returns ranked, categorized LLM download suggestions based on system specifications.
        """
        spec = self.analyze_system_specs(sys_summary)
        installed_set = {m.lower().strip() for m in (installed_models or [])}

        evaluated: List[ModelRecommendation] = []

        for item in CURATED_MODEL_CATALOG:
            fit_score, fit_badge, exec_mode, reason, is_compat = self.evaluate_model_fit(item, spec)
            if not is_compat:
                continue

            tag = item["tag"]
            # Check if tag or base tag matches installed models
            is_installed = any(
                tag.lower() == inst or
                tag.lower().split(":")[0] == inst.split(":")[0] and ("latest" in tag or "latest" in inst)
                for inst in installed_set
            )

            rec = ModelRecommendation(
                tag=tag,
                name=item["name"],
                category=item["category"],
                category_label=item["category_label"],
                parameter_size=item["parameter_size"],
                download_size=item["download_size"],
                min_ram_gb=item["min_ram_gb"],
                recommended_ram_gb=item["recommended_ram_gb"],
                fit_score=fit_score,
                fit_badge=fit_badge,
                execution_mode=exec_mode,
                description=item["description"],
                reason=reason,
                is_installed=is_installed,
                is_primary=False
            )
            evaluated.append(rec)

        # Determine Primary Recommendation (#1 single best fit for this machine)
        primary: Optional[ModelRecommendation] = None

        if spec.tier == "ULTRA":
            # Prefer 14B Qwen or DeepSeek if fits 100% GPU
            preferred_tags = ["qwen2.5:14b", "deepseek-r1:14b", "qwen2.5-coder:14b", "qwen2.5:7b"]
        elif spec.tier == "BALANCED":
            # Prefer 7B Qwen or Mistral
            preferred_tags = ["qwen2.5:7b", "mistral:7b", "qwen2.5-coder:7b", "deepseek-r1:7b", "llama3.2:latest"]
        else:
            # ECO / CPU / Low-RAM: Prefer lightweight 3B
            preferred_tags = ["llama3.2:latest", "qwen2.5:3b", "phi3.5:latest", "mistral:7b"]

        for pt in preferred_tags:
            match = next((r for r in evaluated if r.tag == pt), None)
            if match:
                match.is_primary = True
                primary = match
                break

        if not primary and evaluated:
            evaluated[0].is_primary = True
            primary = evaluated[0]

        # Order recommendations: primary first, then best fit daily driver, coding, reasoning, vision, lightweight
        category_order = ["daily_driver", "coding", "reasoning", "vision", "lightweight"]
        ranked = sorted(
            evaluated,
            key=lambda x: (
                0 if x.is_primary else 1,
                0 if x.fit_score == "Perfect Match" else (1 if x.fit_score == "Great Fit" else 2),
                category_order.index(x.category) if x.category in category_order else 9
            )
        )

        return ModelRecommendationsResponse(
            system_spec=spec,
            primary_recommendation=primary,
            recommendations=ranked,
            installed_tags=list(installed_set)
        )


model_recommendation_service = ModelRecommendationService()
