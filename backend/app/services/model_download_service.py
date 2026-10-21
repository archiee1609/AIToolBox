"""
Thread-safe Background Model Download Manager.
Allows asynchronous model pulls from Ollama that persist across Streamlit page/tab switches,
supports real-time progress tracking, pause/stop/cancel functionality, and multi-job tracking.
"""

import threading
import time
import json
import logging
from typing import Dict, Any, Optional, List
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class DownloadJob:
    """Represents a background model download task."""

    def __init__(self, model_name: str):
        self.model_name = model_name.strip()
        self.status = "downloading"  # "downloading", "complete", "stopped", "error"
        self.percent = 0.0
        self.completed = 0
        self.total = 0
        self.detail = f"Initiating download for '{self.model_name}'..."
        self.is_indeterminate = True
        self.error: Optional[str] = None
        self.stop_requested = False
        self.started_at = time.time()
        self.finished_at: Optional[float] = None
        self._thread: Optional[threading.Thread] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "status": self.status,
            "percent": self.percent,
            "completed": self.completed,
            "total": self.total,
            "detail": self.detail,
            "is_indeterminate": self.is_indeterminate,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class ModelDownloadManager:
    """
    Singleton service managing Ollama model pulls in independent daemon threads.
    Downloads persist independently of Streamlit's script reruns or page navigation.
    """
    _instance: Optional["ModelDownloadManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._jobs = {}
                cls._instance._job_lock = threading.Lock()
            return cls._instance

    def start_download(self, model_name: str, base_url: Optional[str] = None) -> DownloadJob:
        """Starts a background download job if not already running."""
        name = model_name.strip()
        url = base_url or settings.ollama_base_url
        with self._job_lock:
            existing = self._jobs.get(name)
            if existing and existing.status == "downloading":
                return existing

            job = DownloadJob(name)
            self._jobs[name] = job

            t = threading.Thread(
                target=self._run_download_stream,
                args=(job, url),
                daemon=True,
                name=f"ModelDownload-{name}"
            )
            job._thread = t
            t.start()
            return job

    def stop_download(self, model_name: str) -> bool:
        """Signals an active download to stop and aborts the connection."""
        name = model_name.strip()
        with self._job_lock:
            job = self._jobs.get(name)
            if job and job.status == "downloading":
                job.stop_requested = True
                job.status = "stopped"
                job.detail = f"Download of '{name}' cancelled by user."
                job.finished_at = time.time()
                return True
            return False

    def get_job(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Returns the dictionary representation of a specific download job."""
        with self._job_lock:
            job = self._jobs.get(model_name.strip())
            return job.to_dict() if job else None

    def get_active_job(self) -> Optional[Dict[str, Any]]:
        """Returns the most recent active downloading job if any."""
        with self._job_lock:
            for job in reversed(list(self._jobs.values())):
                if job.status == "downloading":
                    return job.to_dict()
            return None

    def get_active_or_latest_job(self) -> Optional[Dict[str, Any]]:
        """Returns active downloading job if present; otherwise the most recent finished job."""
        with self._job_lock:
            for job in reversed(list(self._jobs.values())):
                if job.status == "downloading":
                    return job.to_dict()
            if self._jobs:
                latest = list(self._jobs.values())[-1]
                return latest.to_dict()
            return None

    def list_jobs(self) -> List[Dict[str, Any]]:
        """Lists all known download jobs."""
        with self._job_lock:
            return [j.to_dict() for j in self._jobs.values()]

    def dismiss_job(self, model_name: Optional[str] = None):
        """Clears a completed/stopped job record."""
        with self._job_lock:
            if model_name:
                self._jobs.pop(model_name.strip(), None)
            else:
                self._jobs.clear()

    def _run_download_stream(self, job: DownloadJob, base_url: str):
        endpoint = f"{base_url.rstrip('/')}/api/pull"
        payload = {"name": job.model_name, "stream": True}

        try:
            with httpx.Client(timeout=httpx.Timeout(3600.0, connect=30.0)) as client:
                with client.stream("POST", endpoint, json=payload) as response:
                    if response.status_code != 200:
                        err_text = response.read().decode("utf-8", errors="replace")
                        job.status = "error"
                        job.error = f"HTTP {response.status_code}: {err_text}"
                        job.detail = f"Failed to download: {job.error}"
                        job.finished_at = time.time()
                        return

                    buffer = ""
                    for chunk in response.iter_text():
                        if job.stop_requested:
                            job.status = "stopped"
                            job.detail = f"Download of '{job.model_name}' stopped by user."
                            job.finished_at = time.time()
                            return

                        buffer += chunk
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                self._process_chunk_data(job, data)
                                if job.status == "complete":
                                    return
                            except json.JSONDecodeError:
                                pass

                    if buffer.strip() and not job.stop_requested:
                        try:
                            data = json.loads(buffer.strip())
                            self._process_chunk_data(job, data)
                        except json.JSONDecodeError:
                            pass

        except Exception as e:
            if not job.stop_requested:
                job.status = "error"
                job.error = str(e)
                job.detail = f"Download error: {str(e)}"
                job.finished_at = time.time()
        finally:
            if job.status == "downloading":
                if not job.stop_requested:
                    job.status = "complete"
                    job.percent = 100.0
                    job.detail = f"Model '{job.model_name}' download complete."
                job.finished_at = time.time()

    def _process_chunk_data(self, job: DownloadJob, data: Dict[str, Any]):
        st_val = data.get("status", "downloading")
        completed = data.get("completed", 0)
        total = data.get("total", 0)

        job.completed = completed
        job.total = total

        if total and completed and total > 0:
            job.percent = round((completed / total) * 100, 1)
            job.is_indeterminate = False
            comp_mb = round(completed / (1024 * 1024), 1)
            tot_mb = round(total / (1024 * 1024), 1)
            job.detail = f"{st_val} ({comp_mb} MB / {tot_mb} MB)"
        else:
            job.is_indeterminate = (st_val != "success")
            job.detail = st_val

        if st_val == "success":
            job.status = "complete"
            job.percent = 100.0
            job.detail = f"Model '{job.model_name}' successfully downloaded and registered."
            job.finished_at = time.time()


model_download_manager = ModelDownloadManager()
