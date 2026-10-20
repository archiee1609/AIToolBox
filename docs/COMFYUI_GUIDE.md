# ComfyUI Image Generation Integration Guide

## Overview
Local AI Workbench integrates with local image generation backends via an adapter architecture. ComfyUI is the primary supported engine, defaulting to:
```
http://127.0.0.1:8188
```

---

## 1. Prerequisites & Installation
1. Clone or download ComfyUI from GitHub:
   ```bash
   git clone https://github.com/comfyanonymous/ComfyUI.git
   cd ComfyUI
   ```
2. Install ComfyUI dependencies into your Python environment:
   ```bash
   pip install -r requirements.txt
   ```
3. Place a compatible checkpoint (e.g., SD 1.5, SDXL, or Flux `.safetensors`) into:
   ```
   ComfyUI/models/checkpoints/
   ```

---

## 2. Launching ComfyUI for Workbench
Start ComfyUI on loopback port 8188:
```powershell
python main.py --listen 127.0.0.1 --port 8188
```

---

## 3. Workflow Architecture
When you submit a prompt in **Image Lab**, the backend adapter:
1. Validates prompt parameters (positive prompt, negative prompt, width, height, seed, steps, CFG scale).
2. Translates parameters into a standard node graph compatible with ComfyUI's `/prompt` API.
3. Submits the prompt graph and client ID to `POST /prompt`.
4. Polls `/history/{prompt_id}` until tensors are rendered and saved by the `SaveImage` node.
5. Downloads the resulting image from `/view` and saves it permanently to `generated_images/` on disk.
6. Records generation metadata in the SQLite `image_history` table and renders the preview in the gallery.

---

## 4. Offline Fallback Behavior
If ComfyUI is not running or unreachable:
* The application clearly displays an "Offline" status card in the Image Lab.
* Actionable setup steps and download links are shown.
* The chatbot, coding agent, automation pipelines, and vision workspaces continue to operate without interference.
