import os
import sys
import json
import shutil
import asyncio
import datetime
import subprocess
import signal
from pathlib import Path
from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.core.resource_balancer import get_balanced_ollama_options
from app.schemas.models import ModelDetails, ModelCapabilities, ModelOptions

PREFERRED_MODEL_HINTS = ["gpt-oss", "gemma4:12b"]

class OllamaGenerateResponse(str):
    """
    Rich response from Ollama generate endpoint.
    Inherits from str so it acts natively as a string in print/format/markdown contexts,
    while also exposing `.response`, `.raw`, `.get()`, and dict-style indexing.
    """
    response: str
    raw: Dict[str, Any]

    def __new__(cls, content: str, raw: Optional[Dict[str, Any]] = None):
        instance = super().__new__(cls, content or "")
        instance.response = content or ""
        instance.raw = raw or {}
        return instance

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, str):
            return self.raw[item]
        return super().__getitem__(item)


class OllamaService:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._process: Optional[subprocess.Popen] = None

    def find_ollama_executable(self) -> Optional[Path]:
        """
        Locates the Ollama executable on the system across Windows, macOS, and Linux.
        Checks system PATH, platform-specific package managers (Homebrew), standard bundle paths,
        and standard installation directories.
        """
        # 1. System PATH
        for binary_name in ["ollama", "ollama.exe"]:
            found = shutil.which(binary_name)
            if found:
                return Path(found)

        # 2. macOS Locations (Homebrew Apple Silicon / Intel, App Bundle)
        mac_candidates = [
            Path("/opt/homebrew/bin/ollama"),                       # Homebrew (Apple Silicon)
            Path("/usr/local/bin/ollama"),                         # Homebrew (Intel)
            Path("/Applications/Ollama.app/Contents/Resources/ollama"),  # System App Bundle
            Path.home() / "Applications" / "Ollama.app" / "Contents" / "Resources" / "ollama", # User App Bundle
        ]
        for mac_path in mac_candidates:
            if mac_path.is_file() and os.access(mac_path, os.X_OK):
                return mac_path

        # 3. Linux Locations (Standard install curl script, snap, local bin)
        linux_candidates = [
            Path("/usr/local/bin/ollama"),
            Path("/usr/bin/ollama"),
            Path("/bin/ollama"),
            Path.home() / ".local" / "bin" / "ollama",
            Path("/var/lib/ollama/bin/ollama"),
            Path("/snap/bin/ollama"),
        ]
        for linux_path in linux_candidates:
            if linux_path.is_file() and os.access(linux_path, os.X_OK):
                return linux_path

        # 4. Windows Standard Locations
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidate = Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe"
            if candidate.is_file():
                return candidate

        home_dir = Path.home()
        candidate = home_dir / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe"
        if candidate.is_file():
            return candidate

        prog_files = os.environ.get("ProgramFiles")
        if prog_files:
            candidate = Path(prog_files) / "Ollama" / "ollama.exe"
            if candidate.is_file():
                return candidate

        prog_files_x86 = os.environ.get("ProgramFiles(x86)")
        if prog_files_x86:
            candidate = Path(prog_files_x86) / "Ollama" / "ollama.exe"
            if candidate.is_file():
                return candidate

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
        """Launches the Ollama server in background across Windows, macOS, and Linux if not already running."""
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

            popen_kwargs: Dict[str, Any] = {
                "stdout": log_file,
                "stderr": log_file,
            }

            # Cross-platform background process detachment
            if sys.platform == "win32":
                popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000  # CREATE_NO_WINDOW
            else:
                # POSIX (macOS & Linux): start in a new process group for clean daemonization
                popen_kwargs["start_new_session"] = True

            env = os.environ.copy()
            # Disable Flash Attention by default to prevent CUDA stack buffer overrun
            # (exit code 0xc0000409 / shared object initialization failed) when models
            # split between GPU VRAM and CPU system memory.
            env["OLLAMA_FLASH_ATTENTION"] = "false"
            popen_kwargs["env"] = env

            self._process = subprocess.Popen(
                [str(ollama_bin), "serve"],
                **popen_kwargs
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
        """
        Stops the Ollama process if launched by this service.
        On POSIX systems, terminates the entire process group to ensure child runners are stopped.
        """
        if self._process and self._process.poll() is None:
            pid = self._process.pid
            try:
                if sys.platform != "win32":
                    try:
                        # Kill the whole process group on POSIX
                        pgid = os.getpgid(pid)
                        os.killpg(pgid, signal.SIGTERM)
                    except Exception:
                        self._process.terminate()
                else:
                    self._process.terminate()

                self._process.wait(timeout=5)
            except Exception:
                try:
                    if sys.platform != "win32":
                        try:
                            pgid = os.getpgid(pid)
                            os.killpg(pgid, signal.SIGKILL)
                        except Exception:
                            self._process.kill()
                    else:
                        self._process.kill()
                except Exception:
                    pass
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
                if response.status_code == 200:
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
                    return

                err_body = await response.aread()
                err_text = err_body.decode("utf-8", errors="replace")

            # Fallback retry for transient CUDA / buffer overrun in streaming
            if "llama-server" in err_text or "0xc0000409" in err_text or "CUDA" in err_text or "buffer" in err_text:
                logger.warning(f"Ollama streaming server crash: {err_text}. Retrying with safe fallback options...")
                await asyncio.sleep(2.0)
                fallback_opts = dict(payload.get("options") or {})
                fallback_opts["num_ctx"] = min(fallback_opts.get("num_ctx", 4096), 4096)
                fallback_opts["num_thread"] = 4
                fallback_opts["num_batch"] = min(fallback_opts.get("num_batch", 256), 256)
                payload["options"] = fallback_opts

                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response2:
                    if response2.status_code == 200:
                        buffer = ""
                        async for chunk in response2.aiter_text():
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
                        return
                    err_body2 = await response2.aread()
                    err_text2 = err_body2.decode("utf-8", errors="replace")
                    if "CUDA" in err_text2 or "0xc0000409" in err_text2 or "llama-server" in err_text2:
                        await asyncio.sleep(2.0)
                        fallback_opts["num_gpu"] = 0
                        payload["options"] = fallback_opts
                        async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response3:
                            if response3.status_code == 200:
                                buffer = ""
                                async for chunk in response3.aiter_text():
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
                                return
                            err_body3 = await response3.aread()
                            err_text = err_body3.decode("utf-8", errors="replace")

            raise RuntimeError(f"Ollama stream error HTTP {response.status_code}: {err_text}")

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
        """Convenience generator yielding stream text chunks directly with dynamic load balancing."""
        balanced_opts = get_balanced_ollama_options(
            model_name=model,
            requested_context=context_length,
            requested_temperature=temperature
        )
        if options:
            balanced_opts.update(options)

        thinking_buffer: List[str] = []
        has_yielded_content = False

        async for chunk in self.stream_chat(model=model, messages=messages, options=balanced_opts, tools=tools, timeout=timeout):
            msg = chunk.get("message", {})
            token = msg.get("content", "")
            thinking_token = msg.get("thinking", "")
            if thinking_token:
                thinking_buffer.append(thinking_token)
            if token:
                has_yielded_content = True
                yield token

        # If model exhausted context or completed only in thinking mode without content,
        # fallback to yielding synthesized thinking output so the user NEVER receives a blank response!
        if not has_yielded_content and thinking_buffer:
            thought_text = "".join(thinking_buffer).strip()
            if thought_text:
                yield f"**Analysis & Findings (from Reasoning Engine):**\n\n{thought_text}"

    async def chat_stream_detailed(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        context_length: int = 8192,
        options: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 180.0
    ) -> AsyncGenerator[Dict[str, str], None]:
        """
        Yields detailed stream events:
        {"type": "thinking", "text": "..."}
        {"type": "content", "text": "..."}
        Guarantees that the caller can display live thinking animations and content.
        """
        balanced_opts = get_balanced_ollama_options(
            model_name=model,
            requested_context=context_length,
            requested_temperature=temperature
        )
        if options:
            balanced_opts.update(options)

        thinking_buffer: List[str] = []
        has_yielded_content = False

        async for chunk in self.stream_chat(model=model, messages=messages, options=balanced_opts, tools=tools, timeout=timeout):
            msg = chunk.get("message", {})
            token = msg.get("content", "")
            thinking_token = msg.get("thinking", "")
            if thinking_token:
                thinking_buffer.append(thinking_token)
                yield {"type": "thinking", "text": thinking_token}
            if token:
                has_yielded_content = True
                yield {"type": "content", "text": token}

        if not has_yielded_content and thinking_buffer:
            thought_text = "".join(thinking_buffer).strip()
            if thought_text:
                yield {"type": "content", "text": f"**Analysis & Findings (from Reasoning Engine):**\n\n{thought_text}"}

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
        """Executes a completion prompt with dynamic load balancing."""
        balanced_opts = get_balanced_ollama_options(
            model_name=model,
            requested_context=context_length,
            requested_temperature=temperature
        )
        if options:
            balanced_opts.update(options)

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": balanced_opts
        }
        if system:
            payload["system"] = system
        if images:
            payload["images"] = images

        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(f"{self.base_url}/api/generate", json=payload)
            if res.status_code == 200:
                data = res.json()
                resp_str = data.get("response", "")
                if not resp_str and data.get("thinking"):
                    resp_str = f"**Technical Diagnostic Findings (Reasoning):**\n\n{data['thinking']}"
                return OllamaGenerateResponse(resp_str, raw=data)

            err_text = res.text
            # Automatic resilient recovery for llama-server process crash / CUDA buffer overrun
            if res.status_code == 500 and ("llama-server" in err_text or "0xc0000409" in err_text or "CUDA" in err_text or "buffer" in err_text):
                logger.warning(f"Ollama llama-server error ({res.status_code}): {err_text}. Initiating safe fallback retry...")
                await asyncio.sleep(2.0)
                fallback_opts = dict(balanced_opts)
                fallback_opts["num_ctx"] = min(fallback_opts.get("num_ctx", 4096), 4096)
                fallback_opts["num_thread"] = 4
                fallback_opts["num_batch"] = min(fallback_opts.get("num_batch", 256), 256)
                payload["options"] = fallback_opts

                res2 = await client.post(f"{self.base_url}/api/generate", json=payload)
                if res2.status_code == 200:
                    data = res2.json()
                    resp_str = data.get("response", "")
                    if not resp_str and data.get("thinking"):
                        resp_str = f"**Technical Diagnostic Findings (Reasoning):**\n\n{data['thinking']}"
                    logger.info("Ollama generate recovered successfully via safe fallback parameters.")
                    return OllamaGenerateResponse(resp_str, raw=data)

                if "CUDA" in res2.text or "0xc0000409" in res2.text or "llama-server" in res2.text:
                    await asyncio.sleep(2.0)
                    fallback_opts["num_gpu"] = 0
                    payload["options"] = fallback_opts
                    res3 = await client.post(f"{self.base_url}/api/generate", json=payload)
                    if res3.status_code == 200:
                        data = res3.json()
                        resp_str = data.get("response", "")
                        if not resp_str and data.get("thinking"):
                            resp_str = f"**Technical Diagnostic Findings (Reasoning):**\n\n{data['thinking']}"
                        logger.info("Ollama generate recovered successfully via CPU fallback.")
                        return OllamaGenerateResponse(resp_str, raw=data)

            raise RuntimeError(f"Ollama generate error HTTP {res.status_code}: {res.text}")

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
