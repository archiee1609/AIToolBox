import asyncio
import json
import base64
import os
import subprocess
import urllib.request
import websockets
from pathlib import Path

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
REMOTE_DEBUGGING_PORT = 9225
USER_DATA_DIR = r"C:\Users\achakrabort4\AppData\Local\Temp\edge_screenshot_profile_clean"
ARTIFACT_DIR = Path(r"C:\Users\achakrabort4\.gemini\antigravity\brain\07a501e7-abf0-4d01-91fb-d0190d25d4f8")
DOCS_DIR = Path(r"C:\Users\achakrabort4\Documents\AIToolBox\docs\screenshots")

DOCS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

class CDPClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.msg_id = 0
        self.ws = None

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=100 * 1024 * 1024)

    async def send_cmd(self, method, params=None):
        self.msg_id += 1
        payload = {"id": self.msg_id, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(payload))
        while True:
            resp_raw = await self.ws.recv()
            resp = json.loads(resp_raw)
            if resp.get("id") == self.msg_id:
                return resp.get("result", {})

    async def evaluate(self, expr):
        res = await self.send_cmd("Runtime.evaluate", {
            "expression": expr,
            "awaitPromise": True,
            "returnByValue": True
        })
        return res.get("result", {}).get("value")

    async def wait_for_streamlit(self, max_seconds=20):
        print("Waiting for page render to settle...")
        for _ in range(max_seconds * 2):
            await asyncio.sleep(0.5)
            is_loading = await self.evaluate("""
                (() => {
                    const status = document.querySelector('[data-testid="stStatusWidget"]');
                    if (status && status.innerText.includes('Running')) return true;
                    const skeletons = document.querySelectorAll('[data-testid="stSkeleton"]');
                    if (skeletons.length > 0) return true;
                    const app = document.querySelector('[data-testid="stAppViewContainer"]');
                    if (!app) return true;
                    return false;
                })()
            """)
            if not is_loading:
                await asyncio.sleep(1.5)
                return True
        return False

    async def capture_screenshot(self, filename, scroll_y=0):
        if scroll_y > 0:
            await self.evaluate(f"window.scrollTo(0, {scroll_y});")
            await asyncio.sleep(0.8)
        else:
            await self.evaluate("window.scrollTo(0, 0);")
            await asyncio.sleep(0.5)

        result = await self.send_cmd("Page.captureScreenshot", {
            "format": "png",
            "fromSurface": True,
            "captureBeyondViewport": False
        })
        data = base64.b64decode(result["data"])
        
        doc_path = DOCS_DIR / filename
        with open(doc_path, "wb") as f:
            f.write(data)
            
        artifact_path = ARTIFACT_DIR / filename
        with open(artifact_path, "wb") as f:
            f.write(data)
            
        print(f"[+] Saved: {filename} ({len(data)} bytes)")

    async def close(self):
        if self.ws:
            await self.ws.close()

async def main():
    cmd = [
        EDGE_PATH,
        "--headless=new",
        f"--remote-debugging-port={REMOTE_DEBUGGING_PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--window-size=1680,1050",
        "--hide-scrollbars",
        "--disable-gpu",
        "about:blank"
    ]
    proc = subprocess.Popen(cmd)
    try:
        await asyncio.sleep(2)
        req = urllib.request.urlopen(f"http://127.0.0.1:{REMOTE_DEBUGGING_PORT}/json")
        targets = json.loads(req.read().decode())
        ws_url = targets[0]["webSocketDebuggerUrl"]

        client = CDPClient(ws_url)
        await client.connect()
        await client.send_cmd("Page.enable")
        await client.send_cmd("DOM.enable")

        # Set high device pixel ratio for crystal clear screenshots
        await client.send_cmd("Emulation.setDeviceMetricsOverride", {
            "width": 1680,
            "height": 1050,
            "deviceScaleFactor": 1.25,
            "mobile": False
        })

        # 1. Studio Chat with Active Conversation & Prompt Box
        print("\n--- Capturing Studio Chat ---")
        await client.send_cmd("Page.navigate", {"url": "http://127.0.0.1:8501/?page=studio&conv=818ecc2c-a4c2-4fc0-a91a-a13e5a8fcfd9"})
        await client.wait_for_streamlit(25)
        await asyncio.sleep(2)
        await client.capture_screenshot("01_studio_chat_active.png")

        # 2. More - Model & Inference (Top)
        print("\n--- Capturing Model & Inference ---")
        await client.send_cmd("Page.navigate", {"url": "http://127.0.0.1:8501/?page=more&tab=model"})
        await client.wait_for_streamlit(15)
        await asyncio.sleep(1)
        await client.capture_screenshot("02_model_inference_params.png")

        # 3. More - Installed Models & XP Style Downloader (Scrolled)
        print("\n--- Capturing Installed Models & Downloader ---")
        await client.capture_screenshot("03_installed_models_downloader.png", scroll_y=550)

        # 4. More - Engines & Real-time Diagnostics
        print("\n--- Capturing Engines & Diagnostics ---")
        await client.send_cmd("Page.navigate", {"url": "http://127.0.0.1:8501/?page=more&tab=diagnostics"})
        await client.wait_for_streamlit(15)
        await asyncio.sleep(2)
        await client.capture_screenshot("04_engines_diagnostics.png")

        # 5. More - Image Generation Studio (Prompt, 8K Presets, Controls)
        print("\n--- Capturing Image Generation Studio ---")
        await client.send_cmd("Page.navigate", {"url": "http://127.0.0.1:8501/?page=more&tab=image"})
        await client.wait_for_streamlit(15)
        await asyncio.sleep(2)
        await client.capture_screenshot("05_image_generation_studio.png")

        # 6. More - Image Generation Gallery (Scrolled)
        print("\n--- Capturing Image Generation Gallery ---")
        await client.capture_screenshot("06_image_generation_gallery.png", scroll_y=600)

        # 7. More - AI Memory Hub
        print("\n--- Capturing AI Memory Hub ---")
        await client.send_cmd("Page.navigate", {"url": "http://127.0.0.1:8501/?page=more&tab=memory"})
        await client.wait_for_streamlit(15)
        await asyncio.sleep(1)
        await client.capture_screenshot("07_ai_memory_hub.png")

        await client.close()
        print("\n[SUCCESS] All screenshots captured successfully!")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(main())
