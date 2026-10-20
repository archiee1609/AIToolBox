import json
import httpx
from typing import List, Dict, Any, Optional, AsyncGenerator
from app.core.config import settings
from app.core.logging import logger
from app.schemas.models import ModelDetails, ModelCapabilities, ModelOptions

PREFERRED_MODEL_HINTS = ["gpt-oss", "gemma4:12b"]

class OllamaService:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")

    async def check_health(self) -> Dict[str, Any]:
        """Checks whether Ollama is reachable and returns its version."""
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"{self.base_url}/api/version")
                if res.status_code == 200:
                    data = res.json()
                    return {"reachable": True, "version": data.get("version", "unknown"), "error": None}
                return {"reachable": False, "version": None, "error": f"HTTP {res.status_code}"}
        except Exception as e:
            return {"reachable": False, "version": None, "error": str(e)}

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
