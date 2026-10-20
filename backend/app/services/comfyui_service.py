import os
import sys
import json
import uuid
import asyncio
import datetime
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.database.connection import db
from app.schemas.image import ComfyUIStatusResponse, ImageGenerateRequest, ImageGenerateResponse

DEFAULT_COMFYUI_WORKFLOW = {
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "cfg": 7.0,
            "denoise": 1.0,
            "latent_image": ["5", 0],
            "model": ["4", 0],
            "negative": ["7", 0],
            "positive": ["6", 0],
            "sampler_name": "euler",
            "scheduler": "normal",
            "seed": 42,
            "steps": 20
        }
    },
    "4": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": "v1-5-pruned-emaonly.safetensors"
        }
    },
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "batch_size": 1,
            "height": 512,
            "width": 512
        }
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": ["4", 1],
            "text": "beautiful landscape"
        }
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": ["4", 1],
            "text": "ugly, blurry, low quality"
        }
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["3", 0],
            "vae": ["4", 2]
        }
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "AIToolBox",
            "images": ["8", 0]
        }
    }
}

POPULAR_MODELS = {
    "sd15": {
        "name": "Stable Diffusion v1.5",
        "filename": "v1-5-pruned-emaonly.safetensors",
        "url": "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors",
        "size": "4.27 GB"
    },
    "sdturbo": {
        "name": "SD-Turbo (Ultra-Fast 1-Step)",
        "filename": "sd_turbo.safetensors",
        "url": "https://huggingface.co/stabilityai/sd-turbo/resolve/main/sd_turbo.safetensors",
        "size": "2.4 GB"
    },
    "dreamshaper": {
        "name": "DreamShaper 8 (Artistic & General)",
        "filename": "DreamShaper_8_pruned.safetensors",
        "url": "https://huggingface.co/Lykon/DreamShaper/resolve/main/DreamShaper_8_pruned.safetensors",
        "size": "2.1 GB"
    }
}

class ComfyUIService:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.comfyui_base_url).rstrip("/")
        self.comfy_dir = settings.base_dir / "ComfyUI"
        self.comfy_main = self.comfy_dir / "main.py"
        self.checkpoints_dir = self.comfy_dir / "models" / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self._process: Optional[subprocess.Popen] = None
        self.download_state: Optional[Dict[str, Any]] = None

    def get_local_checkpoints(self) -> List[str]:
        """Lists checkpoint files present in ComfyUI/models/checkpoints/ directory."""
        if not self.checkpoints_dir.exists():
            return []
        valid_exts = {".safetensors", ".ckpt", ".pt", ".bin"}
        files = []
        for f in self.checkpoints_dir.iterdir():
            if f.is_file() and f.suffix.lower() in valid_exts and f.stat().st_size > 1024 * 1024:
                files.append(f.name)
        return sorted(files)

    async def is_server_reachable(self) -> bool:
        """Checks if ComfyUI HTTP server responds on the configured port."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/system_stats")
                return res.status_code == 200
        except Exception:
            return False

    async def start_service(self) -> bool:
        """Launches the ComfyUI subprocess if it's not already running."""
        if await self.is_server_reachable():
            logger.info("ComfyUI is already running.")
            return True

        if not self.comfy_main.exists():
            logger.error(f"ComfyUI main.py not found at {self.comfy_main}")
            return False

        logger.info(f"Starting local ComfyUI from {self.comfy_dir}...")
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"

            # Detect CUDA support; if absent or uncompiled, fall back to CPU mode
            has_cuda = False
            try:
                import torch
                has_cuda = bool(torch.cuda.is_available())
            except Exception:
                has_cuda = False

            cmd = [sys.executable, str(self.comfy_main), "--listen", "127.0.0.1", "--port", "8188"]
            if not has_cuda:
                cmd.extend(["--cpu", "--use-split-cross-attention"])

            log_dir = settings.base_dir / "data" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / "comfyui.log"
            log_file = open(log_path, "a", encoding="utf-8", errors="replace")
            log_file.write(f"\n--- ComfyUI session started at {datetime.datetime.now().isoformat()} with cmd: {' '.join(cmd)} ---\n")
            log_file.flush()

            # Launch in background
            self._process = subprocess.Popen(
                cmd,
                cwd=str(self.comfy_dir),
                stdout=log_file,
                stderr=log_file,
                env=env
            )

            # Wait up to 15 seconds for ComfyUI to load extensions and bind port
            for _ in range(15):
                await asyncio.sleep(1.0)
                if await self.is_server_reachable():
                    logger.info("ComfyUI launched and verified reachable on http://127.0.0.1:8188.")
                    return True
                if self._process.poll() is not None:
                    logger.error(f"ComfyUI process exited prematurely with code {self._process.returncode}")
                    return False

            # Still booting in background
            return self._process.poll() is None
        except Exception as e:
            logger.error(f"Failed to start ComfyUI process: {e}")
            return False

    async def stop_service(self) -> bool:
        """Stops the ComfyUI process."""
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
        """Ensures ComfyUI is online, starting it if installed and currently offline."""
        if await self.is_server_reachable():
            return True
        if self.comfy_main.exists():
            return await self.start_service()
        return False

    async def check_status(self) -> ComfyUIStatusResponse:
        """Inspects whether ComfyUI is running, lists models, and returns actionable guidance."""
        is_installed = self.comfy_main.exists()
        local_ckpts = self.get_local_checkpoints()

        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                res = await client.get(f"{self.base_url}/system_stats")
                if res.status_code == 200:
                    data = res.json()
                    queue_res = await client.get(f"{self.base_url}/queue")
                    queue_count = 0
                    if queue_res.status_code == 200:
                        q_data = queue_res.json()
                        queue_count = len(q_data.get("queue_running", [])) + len(q_data.get("queue_pending", []))

                    # Fetch active checkpoints reported by ComfyUI API
                    api_checkpoints = []
                    try:
                        obj_res = await client.get(f"{self.base_url}/object_info/CheckpointLoaderSimple")
                        if obj_res.status_code == 200:
                            ckpt_info = obj_res.json().get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
                            if isinstance(ckpt_info, list):
                                api_checkpoints = ckpt_info
                    except Exception:
                        pass

                    # Union of local files and API reported files
                    all_ckpts = sorted(list(set(api_checkpoints + local_ckpts)))

                    return ComfyUIStatusResponse(
                        is_reachable=True,
                        is_installed=is_installed,
                        service_url=self.base_url,
                        version=data.get("system", {}).get("comfyui_version", "Running"),
                        queue_remaining=queue_count,
                        available_checkpoints=all_ckpts,
                        actionable_instructions=None,
                        download_progress=self.download_state
                    )
        except Exception:
            pass

        instructions = ""
        if is_installed:
            instructions = (
                f"ComfyUI is detected locally at {self.comfy_dir}.\n"
                "The service is currently idle. You can click 'Start ComfyUI' to boot it up instantly."
            )
        else:
            instructions = (
                f"ComfyUI folder was not found at {self.comfy_dir}.\n"
                "Please place the ComfyUI repository folder into the AIToolBox root directory."
            )

        return ComfyUIStatusResponse(
            is_reachable=False,
            is_installed=is_installed,
            service_url=self.base_url,
            queue_remaining=0,
            available_checkpoints=local_ckpts,
            actionable_instructions=instructions,
            download_progress=self.download_state
        )

    async def download_model_background(self, model_key: str):
        """Asynchronously downloads a checkpoint model to ComfyUI/models/checkpoints/ with progress tracking."""
        model_info = POPULAR_MODELS.get(model_key, POPULAR_MODELS["sd15"])
        dest_file = self.checkpoints_dir / model_info["filename"]

        if dest_file.exists() and dest_file.stat().st_size > 1024 * 1024:
            self.download_state = {
                "status": "completed",
                "model_key": model_key,
                "filename": model_info["filename"],
                "percent": 100,
                "message": f"Model {model_info['filename']} is already downloaded."
            }
            return

        self.download_state = {
            "status": "downloading",
            "model_key": model_key,
            "filename": model_info["filename"],
            "percent": 0,
            "downloaded_bytes": 0,
            "total_bytes": 0,
            "message": f"Connecting to download {model_info['name']}..."
        }

        temp_file = dest_file.with_suffix(".tmp")
        try:
            async with httpx.AsyncClient(timeout=3600.0, follow_redirects=True) as client:
                async with client.stream("GET", model_info["url"]) as response:
                    if response.status_code != 200:
                        self.download_state = {
                            "status": "failed",
                            "model_key": model_key,
                            "filename": model_info["filename"],
                            "message": f"Download failed with HTTP {response.status_code}"
                        }
                        return

                    total_bytes = int(response.headers.get("content-length", 0))
                    self.download_state["total_bytes"] = total_bytes
                    downloaded = 0

                    with open(temp_file, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=1024 * 512):
                            f.write(chunk)
                            downloaded += len(chunk)
                            percent = round((downloaded / total_bytes) * 100, 1) if total_bytes > 0 else 0
                            self.download_state["downloaded_bytes"] = downloaded
                            self.download_state["percent"] = percent
                            self.download_state["message"] = f"Downloading {model_info['name']}: {percent}% ({downloaded // (1024*1024)}MB / {total_bytes // (1024*1024)}MB)"

            # Rename temp to final
            if temp_file.exists():
                temp_file.rename(dest_file)

            self.download_state = {
                "status": "completed",
                "model_key": model_key,
                "filename": model_info["filename"],
                "percent": 100,
                "message": f"Successfully installed {model_info['filename']}!"
            }
        except Exception as e:
            logger.error(f"Model download error: {e}")
            self.download_state = {
                "status": "failed",
                "model_key": model_key,
                "filename": model_info["filename"],
                "message": f"Download error: {str(e)}"
            }
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

    def build_workflow(self, req: ImageGenerateRequest, chosen_checkpoint: str) -> Dict[str, Any]:
        """Constructs a validated ComfyUI prompt graph with custom parameters and selected checkpoint."""
        workflow = json.loads(json.dumps(DEFAULT_COMFYUI_WORKFLOW))

        # Checkpoint
        workflow["4"]["inputs"]["ckpt_name"] = chosen_checkpoint

        # Positive & Negative prompts
        workflow["6"]["inputs"]["text"] = req.prompt
        workflow["7"]["inputs"]["text"] = req.negative_prompt or ""

        # Dimensions
        workflow["5"]["inputs"]["width"] = req.width
        workflow["5"]["inputs"]["height"] = req.height

        # Sampling parameters
        workflow["3"]["inputs"]["steps"] = req.steps or 20
        workflow["3"]["inputs"]["cfg"] = req.cfg_scale or 7.0

        # Seed
        seed = req.seed if req.seed is not None and req.seed >= 0 else int(datetime.datetime.now().timestamp() * 1000) % (2**31)
        workflow["3"]["inputs"]["seed"] = seed

        return workflow

    async def generate_image(self, req: ImageGenerateRequest) -> ImageGenerateResponse:
        """Ensures ComfyUI is running, builds prompt graph, tracks rendering, and saves image."""
        job_id = str(uuid.uuid4())
        now = datetime.datetime.now().isoformat()

        # 1. Ensure ComfyUI service is running
        is_running = await self.ensure_running()
        if not is_running:
            err_msg = (
                f"Cannot generate image: ComfyUI service is offline at {self.base_url}. "
                "Click 'Start ComfyUI' in the Image Lab to launch it."
            )
            await db.execute(
                """
                INSERT INTO image_history (id, prompt, negative_prompt, status, error, image_filename, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, req.prompt, req.negative_prompt, "failed", err_msg, "", now)
            )
            return ImageGenerateResponse(
                id=job_id,
                status="failed",
                prompt=req.prompt,
                error=err_msg,
                created_at=now
            )

        # 2. Check for available checkpoints
        status = await self.check_status()
        available = status.available_checkpoints
        chosen_ckpt = None

        if req.checkpoint and req.checkpoint in available:
            chosen_ckpt = req.checkpoint
        elif available:
            chosen_ckpt = available[0]

        if not chosen_ckpt:
            err_msg = (
                "No model checkpoint (.safetensors) found in ComfyUI/models/checkpoints/. "
                "Please place a model checkpoint (e.g., Stable Diffusion 1.5 or SD-Turbo) into "
                f"'{self.checkpoints_dir}' or click 'Download SD 1.5' in Image Lab."
            )
            await db.execute(
                """
                INSERT INTO image_history (id, prompt, negative_prompt, status, error, image_filename, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, req.prompt, req.negative_prompt, "failed", err_msg, "", now)
            )
            return ImageGenerateResponse(
                id=job_id,
                status="failed",
                prompt=req.prompt,
                error=err_msg,
                created_at=now
            )

        # 3. Build workflow graph
        workflow = self.build_workflow(req, chosen_ckpt)
        seed_used = workflow["3"]["inputs"]["seed"]
        client_id = str(uuid.uuid4())

        # 4. Submit prompt to ComfyUI
        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                prompt_res = await client.post(
                    f"{self.base_url}/prompt",
                    json={"prompt": workflow, "client_id": client_id}
                )
            except Exception as e:
                err_msg = f"Failed to submit generation prompt to ComfyUI: {e}"
                return ImageGenerateResponse(id=job_id, status="failed", prompt=req.prompt, error=err_msg, created_at=now)

            if prompt_res.status_code != 200:
                err_msg = f"ComfyUI prompt submission rejected: {prompt_res.text}"
                await db.execute(
                    """
                    INSERT INTO image_history (id, prompt, negative_prompt, status, error, image_filename, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (job_id, req.prompt, req.negative_prompt, "failed", err_msg, "", now)
                )
                return ImageGenerateResponse(
                    id=job_id,
                    status="failed",
                    prompt=req.prompt,
                    error=err_msg,
                    created_at=now
                )

            data = prompt_res.json()
            prompt_id = data.get("prompt_id")

            # 5. Poll history for rendered output image
            output_image_filename = None
            for _ in range(90): # Poll for up to 90 seconds
                try:
                    hist_res = await client.get(f"{self.base_url}/history/{prompt_id}")
                    if hist_res.status_code == 200:
                        hist_data = hist_res.json().get(prompt_id, {})
                        outputs = hist_data.get("outputs", {})
                        for node_id, node_output in outputs.items():
                            images = node_output.get("images", [])
                            if images:
                                img_info = images[0]
                                src_filename = img_info.get("filename")
                                subfolder = img_info.get("subfolder", "")
                                img_type = img_info.get("type", "output")

                                # Fetch image binary from ComfyUI view API
                                view_res = await client.get(
                                    f"{self.base_url}/view",
                                    params={"filename": src_filename, "subfolder": subfolder, "type": img_type}
                                )
                                if view_res.status_code == 200:
                                    local_filename = f"gen_{job_id[:8]}_{src_filename}"
                                    dest_path = settings.generated_images_dir / local_filename
                                    dest_path.write_bytes(view_res.content)
                                    output_image_filename = local_filename
                                    break
                except Exception:
                    pass

                if output_image_filename:
                    break
                await asyncio.sleep(1.0)

            if not output_image_filename:
                err_msg = "Image generation was queued but timed out while waiting for output rendering."
                await db.execute(
                    """
                    INSERT INTO image_history (id, prompt, negative_prompt, status, error, image_filename, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (job_id, req.prompt, req.negative_prompt, "failed", err_msg, "", now)
                )
                return ImageGenerateResponse(
                    id=job_id,
                    status="failed",
                    prompt=req.prompt,
                    error=err_msg,
                    created_at=now
                )

            # 6. Record success in SQLite
            await db.execute(
                """
                INSERT INTO image_history (id, prompt, negative_prompt, seed, width, height, image_filename, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, req.prompt, req.negative_prompt, seed_used, req.width, req.height, output_image_filename, "completed", now)
            )

            return ImageGenerateResponse(
                id=job_id,
                status="completed",
                prompt=req.prompt,
                image_filename=output_image_filename,
                image_url=f"/api/image_lab/output/{output_image_filename}",
                seed=seed_used,
                created_at=now
            )

comfyui_service = ComfyUIService()
