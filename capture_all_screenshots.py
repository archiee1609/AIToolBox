import asyncio
import json
import base64
import os
import sys
import subprocess
import urllib.request
import websockets
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
REMOTE_DEBUGGING_PORT = 9228
USER_DATA_DIR = r"C:\Users\achakrabort4\AppData\Local\Temp\edge_screenshot_all"
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

    async def wait_until_settled(self, max_seconds=30):
        print("  Waiting for Streamlit to finish executing...", end="", flush=True)
        # Wait a moment for run state to initiate if navigating
        await asyncio.sleep(1.0)
        for _ in range(max_seconds * 2):
            await asyncio.sleep(0.5)
            is_running = await self.evaluate("""
                (() => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    return buttons.some(b => b.innerText && b.innerText.includes('Stop'));
                })()
            """)
            if is_running is False:
                print(" Done!")
                await asyncio.sleep(1.5)
                return True
        print(" Timeout.")
        return False

    async def capture(self, filename, scroll_y=0):
        if scroll_y > 0:
            await self.evaluate(f"""
                (() => {{
                    const el = document.querySelector('[data-testid="stMain"]');
                    if (el) {{ el.scrollTop = {scroll_y}; }}
                    else {{ window.scrollTo(0, {scroll_y}); }}
                }})()
            """)
            await asyncio.sleep(1.0)
        else:
            await self.evaluate("""
                (() => {
                    const el = document.querySelector('[data-testid="stMain"]');
                    if (el) { el.scrollTop = 0; }
                    else { window.scrollTo(0, 0); }
                })()
            """)
            await asyncio.sleep(0.5)

        res = await self.send_cmd("Page.captureScreenshot", {
            "format": "png",
            "fromSurface": True,
            "captureBeyondViewport": False
        })
        data = base64.b64decode(res["data"])

        doc_path = DOCS_DIR / filename
        with open(doc_path, "wb") as f:
            f.write(data)

        artifact_path = ARTIFACT_DIR / filename
        with open(artifact_path, "wb") as f:
            f.write(data)

        print(f"  [+] Captured {filename} ({len(data)} bytes)")

    async def close(self):
        if self.ws:
            await self.ws.close()

async def main():
    cmd = [
        EDGE_PATH,
        "--headless=new",
        f"--remote-debugging-port={REMOTE_DEBUGGING_PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-fre",
        "--disable-sync",
        "--window-size=1680,1050",
        "--hide-scrollbars",
        "--disable-gpu",
        "http://127.0.0.1:8501"
    ]
    proc = subprocess.Popen(cmd)
    try:
        await asyncio.sleep(2.5)
        req = urllib.request.urlopen(f"http://127.0.0.1:{REMOTE_DEBUGGING_PORT}/json")
        targets = json.loads(req.read().decode())
        target = next((t for t in targets if "8501" in t.get("url", "")), targets[0])
        ws_url = target["webSocketDebuggerUrl"]

        client = CDPClient(ws_url)
        await client.connect()
        await client.send_cmd("Page.enable")
        await client.send_cmd("DOM.enable")

        # Set 1.25x DPI for crisp high-resolution screenshots
        await client.send_cmd("Emulation.setDeviceMetricsOverride", {
            "width": 1680,
            "height": 1050,
            "deviceScaleFactor": 1.25,
            "mobile": False
        })

        # -------------------------------------------------------------
        # 1. STUDIO CHAT (Active Conversation & Top Header)
        # -------------------------------------------------------------
        print("\n[1/8] Capturing Studio Chat (Active Conversation)...")
        await client.send_cmd("Page.navigate", {
            "url": "http://127.0.0.1:8501/?page=studio&conv=818ecc2c-a4c2-4fc0-a91a-a13e5a8fcfd9"
        })
        await client.wait_until_settled(25)
        await client.capture("01_studio_chat_conversation.png")

        # -------------------------------------------------------------
        # 2. STUDIO CHAT (Scrolled to Animated Prompt Box)
        # -------------------------------------------------------------
        print("\n[2/8] Capturing Studio Chat (Prompt Box & Controls)...")
        await client.capture("02_studio_chat_prompt_box.png", scroll_y=600)

        # -------------------------------------------------------------
        # 3. MORE - MODEL & INFERENCE (Parameters & Hardware Card)
        # -------------------------------------------------------------
        print("\n[3/8] Capturing Model & Inference Parameters...")
        await client.send_cmd("Page.navigate", {
            "url": "http://127.0.0.1:8501/?page=more&tab=model"
        })
        await client.wait_until_settled(20)
        await client.capture("03_model_inference_params.png")

        # -------------------------------------------------------------
        # 4. MORE - INSTALLED MODELS & XP DOWNLOADER
        # -------------------------------------------------------------
        print("\n[4/8] Capturing Installed Models & Downloader...")
        await client.capture("04_installed_models_and_downloader.png", scroll_y=650)

        # -------------------------------------------------------------
        # 5. MORE - REALTIME ENGINES & DIAGNOSTICS
        # -------------------------------------------------------------
        print("\n[5/8] Capturing Real-time Engines & Diagnostics...")
        await client.send_cmd("Page.navigate", {
            "url": "http://127.0.0.1:8501/?page=more&tab=diagnostics"
        })
        await client.wait_until_settled(20)
        # Let live fragment update
        await asyncio.sleep(2.0)
        await client.capture("05_realtime_engines_diagnostics.png")

        # -------------------------------------------------------------
        # 6. MORE - AI IMAGE GENERATION STUDIO (8K Presets & Prompt)
        # -------------------------------------------------------------
        print("\n[6/8] Capturing AI Image Generation Studio...")
        await client.send_cmd("Page.navigate", {
            "url": "http://127.0.0.1:8501/?page=more&tab=image"
        })
        await client.wait_until_settled(20)
        await client.capture("06_image_generation_studio.png")

        # -------------------------------------------------------------
        # 7. MORE - IMAGE CREATIONS GALLERY
        # -------------------------------------------------------------
        print("\n[7/8] Capturing Image Creations Gallery...")
        await client.capture("07_image_creations_gallery.png", scroll_y=550)

        # -------------------------------------------------------------
        # 8. MORE - AI TOOL MEMORY HUB
        # -------------------------------------------------------------
        print("\n[8/8] Capturing AI Tool Memory Hub...")
        await client.send_cmd("Page.navigate", {
            "url": "http://127.0.0.1:8501/?page=more&tab=memory"
        })
        await client.wait_until_settled(20)
        await client.capture("08_ai_memory_hub.png")

        await client.close()
        print("\n[SUCCESS] All 8 high-resolution screenshots generated successfully!")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(main())
