import asyncio, json, websockets, urllib.request

async def test():
    req = urllib.request.urlopen('http://127.0.0.1:9222/json')
    targets = json.loads(req.read().decode())
    ws = await websockets.connect(targets[0]['webSocketDebuggerUrl'])
    async def eval_js(js):
        await ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
        while True:
            r = await ws.recv()
            data = json.loads(r)
            if data.get('id') == 1:
                return data['result']['result'].get('value')
    
    tabs = await eval_js("""
        Array.from(document.querySelectorAll('button[role="tab"], [data-baseweb="tab"], [data-testid="stTab"], div[role="tab"]')).map(b => ({
            tag: b.tagName,
            text: b.innerText,
            role: b.getAttribute('role'),
            classes: b.className,
            ariaSelected: b.getAttribute('aria-selected')
        }))
    """)
    print('Tabs found:', tabs)
    await ws.close()

if __name__ == '__main__':
    asyncio.run(test())
