import os
import sys
import json
import shutil
import asyncio
import datetime
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.schemas.models import ModelDetails, ModelCapabilities, ModelOptions

PREFERRED_MODEL_HINTS = ["gpt-oss", "gemma4:12b"]

class OllamaService:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._process: Optional[subprocess.Popen] = None

    def find_ollama_executable(self) -> Optional[Path]:
        """Locates the Ollama executable on the system."""
        # 1. System PATH
        for binary_name in ["ollama", "ollama.exe"]:
            found = shutil.which(binary_name)
            if found:
                return Path(found)

        # 2. Windows standard installation locations
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidate = Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe"
            if candidate.exists():
                return candidate

        home_dir = Path.home()
        candidate = home_dir / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe"
        if candidate.exists():
            return candidate

        prog_files = os.environ.get("ProgramFiles")
        if prog_files:
            candidate = Path(prog_files) / "Ollama" / "ollama.exe"
            if candidate.exists():
                return candidate

        prog_files_x86 = os.environ.get("ProgramFiles(x86)")
        if prog_files_x86:
            candidate = Path(prog_files_x86) / "Ollama" / "ollama.exe"
            if candidate.exists():
                return candidate

        # 3. Unix standard locations
        for unix_path in [Path("/usr/local/bin/ollama"), Path("/usr/bin/ollama"), Path("/bin/ollama")]:
            if unix_path.exists():
                return unix_path

        return None

    async def is_server_reachable(self, timeout: float = 3.0) -> bool:
        """Quick check if Ollama server responds on base_url."""
        health = await self.check_health(timeout=timeout)
        return health.get("reachable", False)

    async def check_health(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Checks whether Ollama is reachable and returns its version."""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.get(f"{self.base_url}/api/version")
                if res.status_code == 200:
                    data = res.json()
                    return {"reachable": True, "version": data.get("version", "unknown"), "error": None}
                return {"reachable": False, "version": None, "error": f"HTTP {res.status_code}"}
        except Exception as e:
            return {"reachable": False, "version": None, "error": str(e)}

    async def start_service(self, timeout_seconds: int = 30) -> bool:
        """Launches the Ollama server in background if not already running."""
        if await self.is_server_reachable(timeout=2.0):
            logger.info("Ollama server is already running.")
            return True

        ollama_bin = self.find_ollama_executable()
        if not ollama_bin:
            logger.error("Ollama executable was not found on this system.")
            return False

        logger.info(f"Starting local Ollama server from {ollama_bin}...")
        try:
            log_dir = settings.base_dir / "data" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / "ollama.log"
            log_file = open(log_path, "a", encoding="utf-8", errors="replace")
            log_file.write(f"\n--- Ollama session started at {datetime.datetime.now().isoformat()} with {ollama_bin} serve ---\n")
            log_file.flush()

            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000  # CREATE_NO_WINDOW

            env = os.environ.copy()
            # Disable Flash Attention by default to prevent CUDA stack buffer overrun
            # (exit code 0xc0000409 / shared object initialization failed) when models
            # split between GPU VRAM and CPU system memory.
            env["OLLAMA_FLASH_ATTENTION"] = "false"

            self._process = subprocess.Popen(
                [str(ollama_bin), "serve"],
                stdout=log_file,
                stderr=log_file,
                creationflags=creationflags,
                env=env
            )

            # Wait for Ollama to complete GPU discovery and bind to port
            for sec in range(timeout_seconds):
                await asyncio.sleep(1.0)
                if await self.is_server_reachable(timeout=2.0):
                    logger.info(f"Ollama server started and verified reachable on {self.base_url} (in {sec+1}s).")
                    return True
                if self._process and self._process.poll() is not None:
                    logger.error(f"Ollama process exited prematurely with code {self._process.returncode}")
                    return False

            return await self.is_server_reachable(timeout=3.0)
        except Exception as e:
            logger.error(f"Failed to start Ollama process: {e}")
            return False

    async def stop_service(self) -> bool:
        """Stops the Ollama process if launched by this service."""
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()
            self._process = None
            return True
        return False

    async def ensure_running(self) -> bool:
        """Ensures Ollama is running, starting it if offline."""
        if await self.is_server_reachable(timeout=2.0):
            return True
        return await self.start_service()

    async def list_models(self) -> List[ModelDetails]:
        """Discovers all locally installed models from Ollama."""
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code != 200:
                    logger.error(f"Failed to fetch Ollama tags: HTTP {res.status_code}")
                    return []
                
                data = res.json()
                raw_models = data.get("models", [])
                result = []

                for m in raw_models:
                    name = m.get("name", "")
                    details = m.get("details", {})
                    caps_list = m.get("capabilities", [])
                    family = details.get("family", "")
                    families = details.get("families", []) or []

                    # Infer / detect capabilities accurately
                    # Check Ollama reported capabilities list first
                    has_vision = "vision" in caps_list or "clip" in family.lower() or any("clip" in f.lower() for f in families)
                    has_tools = "tools" in caps_list or True # Most modern models support tools, but Ollama tags tell us
                    has_thinking = "thinking" in caps_list

                    caps = ModelCapabilities(
                        text_generation=True,
                        streaming=True,
                        tool_calling=has_tools,
                        image_understanding=has_vision,
                        structured_output=True,
                        reasoning_controls=has_thinking
                    )

                    # Determine if matches preferred hints
                    is_preferred = any(hint.lower() in name.lower() for hint in PREFERRED_MODEL_HINTS)

                    details_obj = ModelDetails(
                        name=name,
                        model=m.get("model", name),
                        parameter_size=details.get("parameter_size"),
                        quantization_level=details.get("quantization_level"),
                        format=details.get("format"),
                        family=family,
                        context_length=details.get("context_length"),
                        capabilities=caps,
                        is_preferred=is_preferred,
                        modified_at=m.get("modified_at"),
                        size_bytes=m.get("size")
                    )
                    result.append(details_obj)

                return result
        except Exception as e:
            logger.error(f"Error querying Ollama models: {e}")
            return []

    async def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Queries /api/show for a specific model."""
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(f"{self.base_url}/api/show", json={"name": model_name})
                if res.status_code == 200:
                    return res.json()
                return None
        except Exception as e:
            logger.error(f"Error getting model info for {model_name}: {e}")
            return None

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        timeout: float = 120.0
    ) -> Dict[str, Any]:
        """Non-streaming chat request with timeout handling."""
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(f"{self.base_url}/api/chat", json=payload)
            if res.status_code != 200:
                raise RuntimeError(f"Ollama chat error HTTP {res.status_code}: {res.text}")
            return res.json()

    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 180.0
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming chat response generator yielding chunks."""
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if options:
            payload["options"] = options
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    raise RuntimeError(f"Ollama stream error HTTP {response.status_code}: {err_body.decode('utf-8', errors='replace')}")

                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            try:
                                yield json.loads(line)
                            except json.JSONDecodeError:
                                pass
                if buffer.strip():
                    try:
                        yield json.loads(buffer.strip())
                    except json.JSONDecodeError:
                        pass

    async def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        context_length: int = 8192,
        options: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 180.0
    ) -> AsyncGenerator[str, None]:
        """Convenience generator yielding stream text chunks directly."""
        opts = options or {"temperature": temperature, "num_ctx": context_length}
        async for chunk in self.stream_chat(model=model, messages=messages, options=opts, tools=tools, timeout=timeout):
            msg = chunk.get("message", {})
            token = msg.get("content", "")
            if token:
                yield token

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        images: Optional[List[str]] = None,
        temperature: float = 0.7,
        context_length: int = 8192,
        options: Optional[Dict[str, Any]] = None,
        timeout: float = 180.0
    ) -> Any:
        """Executes a completion prompt with optional image embeddings."""
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options or {"temperature": temperature, "num_ctx": context_length}
        }
        if system:
            payload["system"] = system
        if images:
            payload["images"] = images

        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(f"{self.base_url}/api/generate", json=payload)
            if res.status_code != 200:
                raise RuntimeError(f"Ollama generate error HTTP {res.status_code}: {res.text}")
            data = res.json()
            class GenerateResult:
                def __init__(self, raw: Dict[str, Any]):
                    self.raw = raw
                    self.response = raw.get("response", "")
                def __getitem__(self, item):
                    return self.raw[item]
                def get(self, item, default=None):
                    return self.raw.get(item, default)
            return GenerateResult(data)

    async def pull_model(
        self,
        model_name: str,
        timeout: float = 3600.0
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Pulls an Ollama model from the library, streaming progress."""
        payload = {"name": model_name, "stream": True}
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", f"{self.base_url}/api/pull", json=payload) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    raise RuntimeError(f"Ollama pull error HTTP {response.status_code}: {err_body.decode('utf-8', errors='replace')}")

                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                total = data.get("total")
                                completed = data.get("completed")
                                if total and completed and total > 0:
                                    data["percent"] = round((completed / total) * 100, 1)
                                yield data
                            except json.JSONDecodeError:
                                pass
                if buffer.strip():
                    try:
                        data = json.loads(buffer.strip())
                        total = data.get("total")
                        completed = data.get("completed")
                        if total and completed and total > 0:
                            data["percent"] = round((completed / total) * 100, 1)
                        yield data
                    except json.JSONDecodeError:
                        pass

    async def delete_model(self, model_name: str) -> Dict[str, Any]:
        """Deletes a model from Ollama."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.request("DELETE", f"{self.base_url}/api/delete", json={"name": model_name})
            if res.status_code != 200:
                raise RuntimeError(f"Failed to delete model: HTTP {res.status_code} {res.text}")
            return {"status": "success", "message": f"Model '{model_name}' successfully removed."}

ollama_service = OllamaService()
