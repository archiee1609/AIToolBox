import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.models import SystemHardwareSpec
from app.services.model_recommendation_service import model_recommendation_service

client = TestClient(app)


def test_system_spec_analysis():
    spec = model_recommendation_service.analyze_system_specs()
    assert isinstance(spec, SystemHardwareSpec)
    assert spec.cpu_cores >= 1
    assert spec.ram_total_gb > 0
    assert spec.tier in ["ULTRA", "BALANCED", "ECO"]


def test_recommendations_on_simulated_ultra_gpu():
    mock_summary = {
        "os_platform": "Windows",
        "os_friendly": "Windows 11 Pro",
        "architecture": "AMD64",
        "cpu": {"processor": "AMD Ryzen 9 7950X", "logical_cores": 32, "physical_cores": 16},
        "memory": {"total_gb": 64.0, "available_gb": 48.0, "percent_used": 25.0},
        "accelerator": {
            "vendor": "nvidia",
            "type": "cuda",
            "name": "NVIDIA GeForce RTX 4090",
            "device": "cuda:0",
            "is_unified_memory": False,
            "vram_gb": 24.0,
            "details": "NVIDIA GeForce RTX 4090 (24.0 GB VRAM)"
        }
    }
    recs = model_recommendation_service.get_recommendations(sys_summary=mock_summary)
    assert recs.system_spec.tier == "ULTRA"
    assert recs.primary_recommendation is not None
    assert recs.primary_recommendation.parameter_size in ["14B", "32B"]
    assert recs.primary_recommendation.fit_score == "Perfect Match"
    assert "GPU" in recs.primary_recommendation.execution_mode


def test_recommendations_on_simulated_balanced_gpu():
    mock_summary = {
        "os_platform": "Windows",
        "os_friendly": "Windows 11 Home",
        "architecture": "AMD64",
        "cpu": {"processor": "Intel Core i7-13700H", "logical_cores": 20, "physical_cores": 14},
        "memory": {"total_gb": 16.0, "available_gb": 9.5, "percent_used": 40.0},
        "accelerator": {
            "vendor": "nvidia",
            "type": "cuda",
            "name": "NVIDIA GeForce RTX 4060",
            "device": "cuda:0",
            "is_unified_memory": False,
            "vram_gb": 8.0,
            "details": "NVIDIA GeForce RTX 4060 (8.0 GB VRAM)"
        }
    }
    recs = model_recommendation_service.get_recommendations(sys_summary=mock_summary)
    assert recs.system_spec.tier == "BALANCED"
    assert recs.primary_recommendation is not None
    assert recs.primary_recommendation.parameter_size in ["7B", "8B"]
    assert recs.primary_recommendation.fit_score == "Perfect Match"


def test_recommendations_on_simulated_apple_silicon_mac():
    mock_summary = {
        "os_platform": "Darwin",
        "os_friendly": "macOS Sequoia 15.1",
        "architecture": "arm64",
        "cpu": {"processor": "Apple M3 Pro", "logical_cores": 12, "physical_cores": 12},
        "memory": {"total_gb": 18.0, "available_gb": 11.0, "percent_used": 38.0},
        "accelerator": {
            "vendor": "apple",
            "type": "mps",
            "name": "Apple M3 Pro (Metal)",
            "device": "mps",
            "is_unified_memory": True,
            "vram_gb": 18.0,
            "details": "Apple Silicon Unified Memory Architecture (18.0 GB)"
        }
    }
    recs = model_recommendation_service.get_recommendations(sys_summary=mock_summary)
    assert recs.system_spec.is_unified_memory is True
    assert recs.primary_recommendation is not None
    # 7B and 14B models should show Unified High-Speed
    assert "Unified" in recs.primary_recommendation.execution_mode or "MPS" in recs.primary_recommendation.execution_mode


def test_recommendations_on_simulated_cpu_only():
    mock_summary = {
        "os_platform": "Linux",
        "os_friendly": "Ubuntu 24.04 LTS",
        "architecture": "x86_64",
        "cpu": {"processor": "Intel Core i5-1135G7", "logical_cores": 8, "physical_cores": 4},
        "memory": {"total_gb": 8.0, "available_gb": 4.2, "percent_used": 47.0},
        "accelerator": {
            "vendor": "generic",
            "type": "cpu",
            "name": "Multi-Threaded CPU",
            "device": "CPU",
            "is_unified_memory": False,
            "vram_gb": 0.0,
            "details": "Intel Core i5-1135G7 (8 threads, AVX2 enabled)"
        }
    }
    recs = model_recommendation_service.get_recommendations(sys_summary=mock_summary)
    assert recs.system_spec.tier == "ECO"
    assert recs.primary_recommendation is not None
    # On CPU 8GB RAM, lightweight 3B should be primary
    assert recs.primary_recommendation.parameter_size in ["3B", "3.8B"]
    assert "CPU" in recs.primary_recommendation.execution_mode


def test_installed_model_tag_matching():
    installed = ["llama3.2:latest", "gemma4:12b"]
    recs = model_recommendation_service.get_recommendations(installed_models=installed)
    llama_rec = next((r for r in recs.recommendations if "llama3.2" in r.tag), None)
    assert llama_rec is not None
    assert llama_rec.is_installed is True

    # Check uninstalled model
    qwen_rec = next((r for r in recs.recommendations if "qwen2.5:7b" in r.tag), None)
    if qwen_rec:
        assert qwen_rec.is_installed is False


def test_api_recommendations_endpoint():
    res = client.get("/api/ollama/recommendations")
    assert res.status_code == 200
    data = res.json()
    assert "system_spec" in data
    assert "recommendations" in data
    assert "primary_recommendation" in data
    assert len(data["recommendations"]) > 0
    assert "cpu_cores" in data["system_spec"]
    assert "tier" in data["system_spec"]
