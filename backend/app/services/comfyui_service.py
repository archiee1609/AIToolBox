import os
import sys
import re
import json
import uuid
import time
import shutil
import asyncio
import datetime
import subprocess
import signal
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.core.resource_balancer import get_balanced_comfyui_args, get_balanced_image_dimensions
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
            "sampler_name": "dpmpp_2m",
            "scheduler": "karras",
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

def parse_resolution_from_prompt(prompt: str, default_width: int = 512, default_height: int = 512) -> Tuple[int, int]:
    """
    Extracts target width and height from user prompt text.
    Handles:
    - Direct dimensions: 1024x768, 1024 x 768, 1024*768, 1920x1080, 512x512, width 1024 height 768
    - Aspect ratios: 16:9, 9:16, 4:3, 3:4, 21:9, 1:1, --ar 16:9
    - Common orientation keywords: landscape, portrait, wallpaper, widescreen, square
    
    Ensures dimensions are bounded between 256 and 8192 (up to 8K) and are multiples of 8 for VAE compatibility.
    """
    if not prompt:
        return (default_width, default_height)

    p_lower = prompt.lower()

    # 1. Direct dimensions: 7680x4320, 8192x8192, 3840x2160, 1920x1080, 1024x768, 512x512
    dim_match = re.search(r'\b(\d{3,5})\s*(?:[xX*×]|by)\s*(\d{3,5})\b', prompt)
    if not dim_match:
        # Also check "width: 1024, height: 768" or "w: 1024 h: 768"
        dim_match = re.search(r'(?:width|w)[:=\s]+(\d{3,5})[,\s]+(?:height|h)[:=\s]+(\d{3,5})', prompt, re.IGNORECASE)

    if dim_match:
        w = int(dim_match.group(1))
        h = int(dim_match.group(2))
        
        # Scale proportionally if either dimension exceeds 8192 (up to 8K)
        max_dim = 8192
        if w > max_dim or h > max_dim:
            scale = max_dim / max(w, h)
            w = int(w * scale)
            h = int(h * scale)
        
        w = max(256, min(8192, w))
        h = max(256, min(8192, h))
        w = (w // 8) * 8
        h = (h // 8) * 8
        return (w, h)

    # 2. Resolution Keywords (8K, 4K, 2K, 1080p, 720p)
    if re.search(r'\b(?:8k(?:\s*uhd)?|8-k|ultra\s*hd\s*8k)\b', p_lower):
        if any(k in p_lower for k in ["portrait", "vertical", "9:16", "3:4"]):
            return (4320, 7680)
        elif "square" in p_lower or "1:1" in p_lower:
            return (8192, 8192)
        return (7680, 4320)

    if re.search(r'\b(?:4k(?:\s*uhd)?|4-k|ultra\s*hd\s*4k)\b', p_lower):
        if any(k in p_lower for k in ["portrait", "vertical", "9:16", "3:4"]):
            return (2160, 3840)
        elif "square" in p_lower or "1:1" in p_lower:
            return (4096, 4096)
        return (3840, 2160)

    if re.search(r'\b(?:2k|1440p|qhd)\b', p_lower):
        if any(k in p_lower for k in ["portrait", "vertical", "9:16", "3:4"]):
            return (1440, 2560)
        elif "square" in p_lower or "1:1" in p_lower:
            return (2048, 2048)
        return (2560, 1440)

    if re.search(r'\b(?:1080p|fhd|full\s*hd)\b', p_lower):
        if any(k in p_lower for k in ["portrait", "vertical", "9:16", "3:4"]):
            return (1080, 1920)
        return (1920, 1080)

    if re.search(r'\b(?:720p|hd\s*720)\b', p_lower):
        if any(k in p_lower for k in ["portrait", "vertical", "9:16", "3:4"]):
            return (720, 1280)
        return (1280, 720)

    # 2. Aspect ratios: 16:9, 9:16, 4:3, 3:4, 21:9, 1:1, --ar 16:9
    ar_match = re.search(r'(?:--ar\s+|aspect\s+ratio\s*[:=]?\s*|\b)(\d{1,2})\s*[:/]\s*(\d{1,2})\b', prompt, re.IGNORECASE)
    if ar_match:
        ar_w = int(ar_match.group(1))
        ar_h = int(ar_match.group(2))
        if ar_w > 0 and ar_h > 0:
            ratio = ar_w / ar_h
            if abs(ratio - 16 / 9) < 0.05:
                return (896, 512)
            elif abs(ratio - 9 / 16) < 0.05:
                return (512, 896)
            elif abs(ratio - 4 / 3) < 0.05:
                return (768, 576)
            elif abs(ratio - 3 / 4) < 0.05:
                return (576, 768)
            elif abs(ratio - 21 / 9) < 0.05:
                return (1024, 448)
            elif abs(ratio - 1.0) < 0.05:
                return (512, 512)

    # 3. Descriptive orientation keywords
    p_lower = prompt.lower()
    if any(k in p_lower for k in ["wallpaper", "widescreen", "ultrawide", "cinematic", "horizontal", "landscape"]):
        return (768, 512)
    elif any(k in p_lower for k in ["portrait", "vertical", "phone wallpaper", "mobile wallpaper"]):
        return (512, 768)
    elif "square" in p_lower:
        return (512, 512)

    return (default_width, default_height)

STYLE_PRESETS: Dict[str, Dict[str, str]] = {
    "None": {
        "positive": "",
        "negative": ""
    },
    "Photorealistic": {
        "positive": "photorealistic, 8k uhd, highly detailed, professional photography, soft lighting, 35mm lens, sharp focus, masterpiece",
        "negative": "cartoon, 3d, illustration, drawing, painting, bad anatomy, deformed, blurry, lowres, watermark"
    },
    "Cinematic": {
        "positive": "cinematic film still, 35mm photograph, dramatic lighting, depth of field, high contrast, atmospheric, 8k resolution",
        "negative": "anime, cartoon, sketch, low quality, oversaturated, amateur, blurry"
    },
    "Cyberpunk": {
        "positive": "cyberpunk aesthetic, volumetric neon lighting, intricate tech details, reflections, ray tracing, dark futuristic mood, 8k",
        "negative": "pastoral, vintage, sepia, dull colors, low quality, blurry, deformed"
    },
    "Digital Art": {
        "positive": "stunning digital art, trending on artstation, highly detailed illustration, dynamic composition, vibrant color palette",
        "negative": "low quality, photo, amateur, messy sketch, deformed, blurry"
    },
    "Anime / Ghibli": {
        "positive": "anime masterpiece, studio ghibli aesthetic, vibrant colors, makoto shinkai lighting, clean lineart, high detail",
        "negative": "photorealistic, 3d render, gritty, ugly, bad anatomy, low quality"
    }
}

DEFAULT_NEGATIVE_PROMPT: str = (
    "worst quality, low quality, normal quality, lowres, bad anatomy, bad hands, missing fingers, "
    "extra digit, fewer digits, cropped, signature, watermark, username, blurry, artist name, duplicate, "
    "morbid, mutilated, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, mutation, "
    "deformed, ugly, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs"
)

def calculate_optimal_base_dimensions(target_w: int, target_h: int) -> Tuple[int, int, bool]:
    """
    Given target user resolution, calculates the optimal base generation resolution for SD 1.5
    to prevent multi-object tiling and distortion, and returns whether upscaling is needed.
    """
    total_pixels = target_w * target_h
    # SD 1.5 native budget is around 512x512 = 262,144 pixels (safe up to ~393,216 pixels, e.g. 768x512)
    if total_pixels <= 768 * 512:
        return (target_w, target_h, False)

    ratio = target_w / target_h
    # Target base pixel budget ~512*512 = 262,144
    target_area = 512 * 512
    base_w = int(round((target_area * ratio) ** 0.5 / 64.0) * 64)
    base_h = int(round((target_area / ratio) ** 0.5 / 64.0) * 64)
    
    # Bound base dimensions to SD 1.5 sweet spot
    base_w = max(384, min(768, base_w))
    base_h = max(384, min(768, base_h))
    base_w = (base_w // 8) * 8
    base_h = (base_h // 8) * 8
    
    return (base_w, base_h, True)

class ComfyUIService:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.comfyui_base_url).rstrip("/")
        self.comfy_dir = settings.base_dir / "ComfyUI"
        self.comfy_main = self.comfy_dir / "main.py"
        self.checkpoints_dir = self.comfy_dir / "models" / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.comfy_output_dir = self.comfy_dir / "output"
        self.comfy_output_dir.mkdir(parents=True, exist_ok=True)
        self._process: Optional[subprocess.Popen] = None
        self.download_state: Optional[Dict[str, Any]] = None

    async def sync_external_outputs(self) -> List[str]:
        """Scans ComfyUI output folder for completed renders and catalogs them into image_history if not present."""
        recovered = []
        if not self.comfy_output_dir.exists():
            return recovered
        
        try:
            png_files = sorted(self.comfy_output_dir.glob("AIToolBox_*.png"), key=lambda f: f.stat().st_mtime, reverse=True)
            for f in png_files:
                if f.stat().st_size < 1024:
                    continue
                # Check if already present in database
                row = await db.fetchone("SELECT id, image_filename FROM image_history WHERE image_filename LIKE ? OR image_filename = ?", (f"%{f.name}%", f.name))
                if not row:
                    job_id = str(uuid.uuid4())
                    local_filename = f"gen_{job_id[:8]}_{f.name}"
                    dest_path = settings.generated_images_dir / local_filename
                    shutil.copy2(f, dest_path)
                    now_str = datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                    await db.execute(
                        """
                        INSERT INTO image_history (id, prompt, negative_prompt, status, image_filename, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (job_id, f"Recovered render ({f.name})", "", "completed", local_filename, now_str)
                    )
                    recovered.append(local_filename)
        except Exception as ex:
            logger.warning(f"Error during ComfyUI output sync: {ex}")
        return recovered

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

    def find_python_executable(self) -> str:
        """
        Locates the appropriate Python interpreter for running ComfyUI across Windows, macOS, and Linux.
        Checks dedicated ComfyUI venvs, project virtualenv, and falls back to sys.executable.
        """
        is_win = sys.platform == "win32"
        venv_candidates = [
            self.comfy_dir / "venv" / ("Scripts/python.exe" if is_win else "bin/python"),
            settings.base_dir / ".venv" / ("Scripts/python.exe" if is_win else "bin/python"),
            self.comfy_dir / ".venv" / ("Scripts/python.exe" if is_win else "bin/python"),
        ]
        for candidate in venv_candidates:
            if candidate.is_file():
                return str(candidate)

        return sys.executable

    async def is_server_reachable(self) -> bool:
        """Checks if ComfyUI HTTP server responds on the configured port."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/system_stats")
                return res.status_code == 200
        except Exception:
            return False

    async def start_service(self) -> bool:
        """Launches the ComfyUI subprocess across Windows, macOS, and Linux if it's not already running."""
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

            python_exe = self.find_python_executable()
            balanced_flags = get_balanced_comfyui_args()
            cmd = [python_exe, str(self.comfy_main)] + balanced_flags

            log_dir = settings.base_dir / "data" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / "comfyui.log"
            log_file = open(log_path, "a", encoding="utf-8", errors="replace")
            log_file.write(f"\n--- ComfyUI session started at {datetime.datetime.now().isoformat()} with cmd: {' '.join(cmd)} ---\n")
            log_file.flush()

            popen_kwargs: Dict[str, Any] = {
                "cwd": str(self.comfy_dir),
                "stdout": log_file,
                "stderr": log_file,
                "env": env
            }

            # Cross-platform detachment
            if sys.platform == "win32":
                popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000
            else:
                popen_kwargs["start_new_session"] = True

            # Launch in background
            self._process = subprocess.Popen(
                cmd,
                **popen_kwargs
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
        """
        Stops the ComfyUI process across Windows, macOS, and Linux.
        On POSIX systems, terminates the entire process group to ensure child worker processes are killed.
        """
        if self._process and self._process.poll() is None:
            pid = self._process.pid
            try:
                if sys.platform != "win32":
                    try:
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

        # Style preset & quality prompt enhancement
        style_key = getattr(req, "style_preset", "None") or "None"
        preset = STYLE_PRESETS.get(style_key, STYLE_PRESETS["None"])

        pos_parts = [req.prompt.strip()]
        if preset.get("positive"):
            pos_parts.append(preset["positive"])
        if getattr(req, "enhance_prompt", True):
            p_lower = req.prompt.lower()
            if not any(k in p_lower for k in ["masterpiece", "8k", "highly detailed", "photorealistic"]):
                pos_parts.append("masterpiece, highly detailed, sharp focus, professional lighting, photorealistic")
        final_pos = ", ".join(pos_parts)

        neg_parts = []
        if req.negative_prompt and req.negative_prompt.strip():
            neg_parts.append(req.negative_prompt.strip())
        else:
            neg_parts.append(DEFAULT_NEGATIVE_PROMPT)
        if preset.get("negative"):
            neg_parts.append(preset["negative"])
        final_neg = ", ".join(neg_parts)

        workflow["6"]["inputs"]["text"] = final_pos
        workflow["7"]["inputs"]["text"] = final_neg

        # Auto-detect resolution from prompt (e.g. 1024x768, 16:9, landscape, portrait)
        parsed_w, parsed_h = parse_resolution_from_prompt(req.prompt, default_width=req.width, default_height=req.height)

        # Calculate optimal base resolution for SD 1.5 to prevent multi-object tiling and distortion
        base_w, base_h, needs_upscale = calculate_optimal_base_dimensions(parsed_w, parsed_h)

        workflow["5"]["inputs"]["width"] = base_w
        workflow["5"]["inputs"]["height"] = base_h

        # High-quality upscale if requested resolution exceeds native base
        if needs_upscale:
            workflow["10"] = {
                "class_type": "ImageScale",
                "inputs": {
                    "image": ["8", 0],
                    "upscale_method": "lanczos",
                    "width": parsed_w,
                    "height": parsed_h,
                    "crop": "disabled"
                }
            }
            workflow["9"]["inputs"]["images"] = ["10", 0]
        else:
            workflow["9"]["inputs"]["images"] = ["8", 0]

        # Sampler & Scheduler (default to dpmpp_2m + karras for dramatically higher detail)
        sampler_name = getattr(req, "sampler_name", None) or "dpmpp_2m"
        scheduler = getattr(req, "scheduler", None) or "karras"
        valid_samplers = {"dpmpp_2m", "euler_ancestral", "euler", "ddim", "dpmpp_sde", "uni_pc"}
        valid_schedulers = {"karras", "normal", "exponential", "simple", "sgm_uniform"}

        workflow["3"]["inputs"]["sampler_name"] = sampler_name if sampler_name in valid_samplers else "dpmpp_2m"
        workflow["3"]["inputs"]["scheduler"] = scheduler if scheduler in valid_schedulers else "karras"
        workflow["3"]["inputs"]["steps"] = max(12, req.steps or 20)
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

        # Auto-parse resolution from prompt if provided in text and apply load balancer memory bounds
        parsed_w, parsed_h = parse_resolution_from_prompt(req.prompt, default_width=req.width, default_height=req.height)
        safe_w, safe_h, _ = get_balanced_image_dimensions(parsed_w, parsed_h)
        req.width = safe_w
        req.height = safe_h

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

            # 5. Poll history for rendered output image (up to 360 seconds for CPU rendering)
            output_image_filename = None
            start_poll_time = time.time()
            render_error = None

            for poll_idx in range(360):
                try:
                    hist_res = await client.get(f"{self.base_url}/history/{prompt_id}", timeout=15.0)
                    if hist_res.status_code == 200:
                        hist_data = hist_res.json().get(prompt_id, {})
                        
                        # Check if ComfyUI reported an execution error
                        status_info = hist_data.get("status", {})
                        if status_info.get("status_str") == "error":
                            messages = status_info.get("messages", [])
                            render_error = f"ComfyUI engine reported execution error: {messages}"
                            logger.error(render_error)
                            break

                        outputs = hist_data.get("outputs", {})
                        for node_id, node_output in outputs.items():
                            images = node_output.get("images", [])
                            if images:
                                img_info = images[0]
                                src_filename = img_info.get("filename")
                                subfolder = img_info.get("subfolder", "")
                                img_type = img_info.get("type", "output")
                                local_filename = f"gen_{job_id[:8]}_{src_filename}"
                                dest_path = settings.generated_images_dir / local_filename

                                # 1. Try instantaneous direct filesystem copy from ComfyUI output directory
                                direct_path = (self.comfy_output_dir / subfolder / src_filename).resolve()
                                if direct_path.exists() and direct_path.stat().st_size > 1024:
                                    shutil.copy2(direct_path, dest_path)
                                    output_image_filename = local_filename
                                    break

                                # 2. Fallback: fetch via ComfyUI /view API
                                view_res = await client.get(
                                    f"{self.base_url}/view",
                                    params={"filename": src_filename, "subfolder": subfolder, "type": img_type},
                                    timeout=30.0
                                )
                                if view_res.status_code == 200 and len(view_res.content) > 0:
                                    dest_path.write_bytes(view_res.content)
                                    output_image_filename = local_filename
                                    break
                except Exception as ex:
                    logger.debug(f"History poll exception at tick {poll_idx}: {ex}")

                if output_image_filename:
                    break

                # 3. Direct filesystem detection fallback: inspect output folder for recently generated AIToolBox_*.png
                if poll_idx >= 5 and poll_idx % 4 == 0:
                    try:
                        recent_pngs = sorted(
                            [f for f in self.comfy_output_dir.glob("AIToolBox_*.png") if f.stat().st_mtime >= start_poll_time - 5.0],
                            key=lambda f: f.stat().st_mtime,
                            reverse=True
                        )
                        if recent_pngs:
                            latest_png = recent_pngs[0]
                            if latest_png.stat().st_size > 10000:
                                local_filename = f"gen_{job_id[:8]}_{latest_png.name}"
                                dest_path = settings.generated_images_dir / local_filename
                                shutil.copy2(latest_png, dest_path)
                                output_image_filename = local_filename
                                break
                    except Exception as fs_ex:
                        logger.debug(f"Direct filesystem poll exception: {fs_ex}")

                await asyncio.sleep(1.0)

            if not output_image_filename:
                err_msg = render_error or "Image generation was queued but timed out while waiting for output rendering on CPU."
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
