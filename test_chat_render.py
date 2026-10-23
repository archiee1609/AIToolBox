import asyncio, json, subprocess, urllib.request, websockets, base64

async def test():
    EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    proc = subprocess.Popen([
        EDGE_PATH, "--headless=new", "--remote-debugging-port=9227",
        r"--user-data-dir=C:\Users\achakrabort4\AppData\Local\Temp\edge_clean_profile_nofre",
        "--no-first-run", "--no-default-browser-check", "--disable-fre", "--disable-sync",
        "--window-size=1680,1050", "--hide-scrollbars", "--disable-gpu",
        "http://127.0.0.1:8501/?page=studio&conv=818ecc2c-a4c2-4fc0-a91a-a13e5a8fcfd9"
    ])
    await asyncio.sleep(2)
    try:
        req = urllib.request.urlopen("http://127.0.0.1:9227/json")
        targets = json.loads(req.read().decode())
        print("Targets:", [(t.get("title"), t.get("url")) for t in targets])
        
        # Pick the 8501 target
        target = next((t for t in targets if "8501" in t.get("url", "")), targets[0])
        ws = await websockets.connect(target["webSocketDebuggerUrl"])
        
        async def eval_js(expr):
            await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == 1:
                    return msg.get("result", {}).get("result", {}).get("value")
        
        for i in range(25):
            await asyncio.sleep(1)
            is_running = await eval_js("Array.from(document.querySelectorAll('button')).some(b => b.innerText.includes('Stop'))")
            print(f"[{i}s] Is running: {is_running}")
            if is_running is False:
                break
        
        await asyncio.sleep(2)
        chat_info = await eval_js("""
            (() => {
                const h3 = Array.from(document.querySelectorAll('h3')).map(h => h.innerText);
                const msgs = document.querySelectorAll('[data-testid="stChatMessage"]');
                return {h3: h3, msgCount: msgs.length};
            })()
        """)
        print("Chat info:", chat_info)
        
        await ws.send(json.dumps({"id": 2, "method": "Page.captureScreenshot", "params": {"format": "png"}}))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 2:
                data = base64.b64decode(msg["result"]["data"])
                with open(r"C:\Users\achakrabort4\.gemini\antigravity\brain\07a501e7-abf0-4d01-91fb-d0190d25d4f8\01_studio_chat_test.png", "wb") as f:
                    f.write(data)
                print("Saved test screenshot!")
                break
        await ws.close()
    finally:
        proc.kill()

if __name__ == "__main__":
    asyncio.run(test())
