"""
Unit and Integration tests for Model Download Manager, Stop/Cancel functionality,
cross-page persistence, model deletion, and real-time telemetry.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.model_download_service import ModelDownloadManager, DownloadJob, parse_model_names
from app.services.ollama_service import ollama_service
from app.core.resource_balancer import get_live_telemetry, get_current_load_profile
from app.core.ui_components import render_winxp_progress_bar


@pytest.fixture
def client():
    return TestClient(app)


def test_download_job_data_structure():
    job = DownloadJob("llama3.2:1b")
    assert job.model_name == "llama3.2:1b"
    assert job.status == "downloading"
    assert job.percent == 0.0
    assert job.is_indeterminate is True
    assert job.stop_requested is False

    d = job.to_dict()
    assert d["model"] == "llama3.2:1b"
    assert d["status"] == "downloading"
    assert "started_at" in d


def test_model_download_manager_start_and_stop():
    mgr = ModelDownloadManager()
    mgr.dismiss_job()

    with patch.object(mgr, "_run_download_stream"):
        job = mgr.start_download("test-model:1b")
        assert job.model_name == "test-model:1b"
        assert job.status == "downloading"

        # Check queries
        active = mgr.get_active_job()
        assert active is not None
        assert active["model"] == "test-model:1b"

        # Stop download
        success = mgr.stop_download("test-model:1b")
        assert success is True
        assert job.status == "stopped"
        assert job.stop_requested is True

        # Stop again returns False (already stopped)
        assert mgr.stop_download("test-model:1b") is False

        # Cleanup
        mgr.dismiss_job("test-model:1b")
        assert mgr.get_job("test-model:1b") is None


def test_model_download_manager_chunk_processing():
    mgr = ModelDownloadManager()
    job = DownloadJob("qwen2.5:7b")

    # Indeterminate manifest chunk
    mgr._process_chunk_data(job, {"status": "pulling manifest"})
    assert job.status == "downloading"
    assert job.is_indeterminate is True
    assert job.detail == "pulling manifest"

    # Layer downloading chunk with percent
    mgr._process_chunk_data(job, {
        "status": "downloading layer",
        "completed": 500 * 1024 * 1024,
        "total": 1000 * 1024 * 1024
    })
    assert job.status == "downloading"
    assert job.is_indeterminate is False
    assert job.percent == 50.0
    assert "500.0 MB / 1000.0 MB" in job.detail

    # Success completion chunk
    mgr._process_chunk_data(job, {"status": "success"})
    assert job.status == "complete"
    assert job.percent == 100.0
    assert "successfully downloaded" in job.detail


def test_render_winxp_progress_bar_stopped_state():
    """Verify stopped state renders orange/amber styling and stop icon."""
    html_stopped = render_winxp_progress_bar(
        percent=42.0,
        status="stopped",
        detail="Download stopped by user."
    )
    assert "Status:" in html_stopped
    assert "Stopped" in html_stopped
    assert "⏹" in html_stopped
    assert "42.0%" in html_stopped
    assert "#f59e0b" in html_stopped  # Amber bar


def test_api_download_endpoints(client):
    """Test start, status, stop, jobs, and dismiss REST endpoints."""
    # Start download
    with patch("app.api.ollama.model_download_manager.start_download") as mock_start:
        mock_job = DownloadJob("deepseek-r1:1.5b")
        mock_start.return_value = mock_job
        res = client.post("/api/ollama/download/start", json={"name": "deepseek-r1:1.5b"})
        assert res.status_code == 200
        assert res.json()["status"] == "started"

    # Status
    res = client.get("/api/ollama/download/status")
    assert res.status_code == 200
    assert "job" in res.json()

    # Stop download
    with patch("app.api.ollama.model_download_manager.stop_download", return_value=True):
        res = client.post("/api/ollama/download/stop", json={"name": "deepseek-r1:1.5b"})
        assert res.status_code == 200
        assert res.json()["status"] == "stopped"

    # List jobs
    res = client.get("/api/ollama/download/jobs")
    assert res.status_code == 200
    assert "jobs" in res.json()

    # Dismiss job
    res = client.delete("/api/ollama/download/job?name=deepseek-r1:1.5b")
    assert res.status_code == 200
    assert res.json()["status"] == "dismissed"


def test_api_delete_model_endpoint(client):
    """Test delete model REST endpoint."""
    with patch.object(ollama_service, "delete_model") as mock_del:
        mock_del.return_value = {"status": "success", "message": "Model 'mock:7b' deleted."}
        res = client.delete("/api/ollama/models/mock:7b")
        assert res.status_code == 200
        assert res.json()["status"] == "success"


def test_parse_model_names():
    # Comma separated
    res = parse_model_names("qwen2.5:14b, llama3.2:latest, mistral:7b")
    assert res == ["qwen2.5:14b", "llama3.2:latest", "mistral:7b"]

    # Newlines and semicolons with extra whitespace
    res2 = parse_model_names("  qwen3.8:27b ;\n  phi4:14b \r\n gemma2:9b  ")
    assert res2 == ["qwen3.8:27b", "phi4:14b", "gemma2:9b"]

    # Deduplication and spaces
    res3 = parse_model_names("llama3.2:latest, llama3.2:latest, qwen2.5:14b")
    assert res3 == ["llama3.2:latest", "qwen2.5:14b"]

    # Empty
    assert parse_model_names("") == []
    assert parse_model_names("   ") == []


def test_model_download_manager_multiple_downloads():
    mgr = ModelDownloadManager()
    mgr.dismiss_job()

    with patch.object(mgr, "_run_download_stream"):
        jobs = mgr.start_multiple_downloads(["model-a:1b", "model-b:2b", "model-c:3b"])
        assert len(jobs) == 3
        assert [j.model_name for j in jobs] == ["model-a:1b", "model-b:2b", "model-c:3b"]

        active = mgr.get_active_jobs()
        assert len(active) == 3

        all_recent = mgr.get_all_active_or_recent_jobs()
        assert len(all_recent) == 3

        # Stop one
        mgr.stop_download("model-b:2b")
        active = mgr.get_active_jobs()
        assert len(active) == 2

        # Stop all remaining
        stopped_count = mgr.stop_all_downloads()
        assert stopped_count == 2
        assert len(mgr.get_active_jobs()) == 0

        # Dismiss all finished
        mgr.dismiss_all_finished()
        assert len(mgr.list_jobs()) == 0


def test_api_multiple_download_endpoints(client):
    # Start multiple downloads
    with patch("app.api.ollama.model_download_manager.start_multiple_downloads") as mock_starts:
        job1 = DownloadJob("model-1:7b")
        job2 = DownloadJob("model-2:14b")
        mock_starts.return_value = [job1, job2]

        res = client.post("/api/ollama/download/start-multiple", json={"models": ["model-1:7b", "model-2:14b"]})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "started"
        assert data["count"] == 2
        assert len(data["jobs"]) == 2

    # Stop all downloads
    with patch("app.api.ollama.model_download_manager.stop_all_downloads", return_value=2):
        res = client.post("/api/ollama/download/stop-all")
        assert res.status_code == 200
        assert res.json()["status"] == "stopped"
        assert res.json()["count"] == 2

    # Dismiss all finished
    with patch("app.api.ollama.model_download_manager.dismiss_all_finished"):
        res = client.delete("/api/ollama/download/jobs/finished")
        assert res.status_code == 200
        assert res.json()["status"] == "dismissed_finished"


def test_realtime_telemetry_force_refresh():
    """Verify get_live_telemetry produces live non-stale metrics."""
    t1 = get_live_telemetry(force_refresh=True)
    assert "cpu" in t1
    assert "memory" in t1
    assert "accelerator" in t1
    assert isinstance(t1["cpu"]["percent_used"], (int, float))
    assert isinstance(t1["memory"]["percent_used"], (int, float))
    assert isinstance(t1["accelerator"]["vram_percent_used"], (int, float))

    prof = get_current_load_profile(t1)
    assert "title" in prof
    assert "badge" in prof
    assert "optimal_threads" in prof
