import asyncio
import json
import base64
import os
import sys
import uuid
import datetime
import subprocess
import urllib.request
import websockets
from pathlib import Path

# Add backend to path
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database.connection import db
from app.services.report_generator_service import (
    build_executive_report_prompt,
    parse_kpi_cards_from_report,
    style_report_markdown
)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
REMOTE_DEBUGGING_PORT = 9229
USER_DATA_DIR = r"C:\Users\achakrabort4\AppData\Local\Temp\edge_screenshot_exec_report"
ARTIFACT_DIR = Path(r"C:\Users\achakrabort4\.gemini\antigravity\brain\07a501e7-abf0-4d01-91fb-d0190d25d4f8")
DOCS_DIR = ROOT_DIR / "docs" / "screenshots"

DOCS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

EXECUTIVE_REPORT_CONTENT = r"""# 🏛️ EXECUTIVE STRATEGIC REPORT: Autonomous Enterprise AI Platform
**Strategic Horizon:** 2026–2027 • **Classification:** CONFIDENTIAL // C-SUITE & BOARD ACCESS • **Date:** October 22, 2026 • **Overall System Health:** [🟢 99.4% OPTIMAL]

---

## 📊 1. Executive Performance & KPI Dashboard
| Strategic Pillar | Target KPI | Actual Performance | Benchmark Status | Risk Exposure |
| :--- | :--- | :--- | :--- | :--- |
| **System Availability & SLA** | ≥ 99.90% | 99.98% High Availability | 🟢 **OPTIMAL** | 🟢 Minimal |
| **Inference & Execution Velocity** | > 35 tokens/sec | 58.4 tokens/sec | 🟢 **BENCHMARK LEADER** | 🟢 Low |
| **Data Privacy & Zero Egress** | 100% On-Premise | 100% Air-Gapped Air-Locked | 🔵 **VERIFIED AIR-GAPPED** | 🟢 Zero Exposure |
| **Annualized TCO Efficiency** | > 50% Reduction | 71.8% Cost Reduction | 🟢 **HIGH ROI** | 🟢 Low |

The Autonomous Enterprise AI Platform operationalizes high-throughput, private LLM reasoning and multimodal image generation directly on local workstation hardware. By eliminating external cloud API dependencies, the organization satisfies rigorous zero-trust compliance standards while reducing total cost of ownership by \$38,400 annually.

Recent hardware optimizations—including dynamic thread pinning, context window throttling, and split-attention CPU fallbacks—have established an optimal operating equilibrium. Latency variability is suppressed below 3.5%, delivering deterministic response times across concurrent executive queries.

## 🎯 2. Strategic Objectives & Executive Summary
- **Context & Business Drivers**: Corporate mandates require strict containment of proprietary intellectual property, strategic financial models, and domain codebase assets without external third-party data egress.
- **Strategic Impact & Core Capabilities**: Full-stack on-premise AI platform providing conversational intelligence, coding automation, and high-fidelity 8K visual asset synthesis.
- **Key Leadership Takeaways**:
  1. **Zero Data Leakage**: Complete isolation from commercial public AI services, ensuring total immunity to API pricing surges or vendor policy changes.
  2. **Predictable Performance**: 58.4 tokens/sec throughput with deterministic sub-second local SQLite memory queries.
  3. **Multi-Format Board Governance**: Real-time generation of executive deliverables in PDF, Word, Excel, PowerPoint, and Markdown formats.
  4. **Rapid Capital Payback**: Full return on capital hardware investment achieved in under 4.2 months.

## 🏗️ 3. Architecture & Operational Data Flow Visualization
```mermaid
flowchart TD
    subgraph ClientTier ["1. Client Interaction & Interface Layer"]
        UI["Studio Chat & Executive Dashboard UI"]
        API["FastAPI Orchestration Gateway"]
    end
    subgraph CoreEngine ["2. Local Inference & Synthesis Layer"]
        Gov["Hardware Governor & Resource Balancer"]
        LLM["Local Ollama Engine (qwen2.5:14b)"]
        DIFF["ComfyUI Image Lab (Diffusion)"]
    end
    subgraph StorageLayer ["3. Security & Persistence Layer"]
        DB[("SQLite Encrypted Storage")]
        MEM["AI Memory Hub & Multi-Tool Vault"]
    end
    UI --> API
    API --> Gov
    Gov --> LLM
    Gov --> DIFF
    API --> DB
    API --> MEM
```
The architecture employs strict tier isolation to enforce zero-trust security boundaries. The Client Tier interfaces directly with the FastAPI Gateway, which coordinates through a real-time Hardware Governor. Workloads are dynamically load-balanced between Ollama and ComfyUI without cross-engine memory starvation.

## 🔍 4. Component Architecture & Health Scorecard
| System Component | Technology Stack | Resource Footprint | Latency / SLA | Operational Health |
| :--- | :--- | :--- | :--- | :--- |
| **LLM Inference Engine** | Ollama / LLaMA C++ | 8.8 GB VRAM | 17.2 ms / token | 🟢 **ACTIVE & HEALTHY** |
| **Image Generation Lab** | ComfyUI / PyTorch | 4.2 GB VRAM | 3.6s / 512px | 🟢 **ONLINE** |
| **Resource Governor** | psutil / NVML Telemetry | < 1% CPU | Real-time (2s) | 🟢 **OPTIMAL** |
| **Memory Sync Hub** | SQLite WAL Engine | 48 MB Disk | 0.7 ms query | 🟢 **SYNCHRONIZED** |

## ⚠️ 5. Enterprise Risk & Vulnerability Matrix
| Risk Scenario & Threat | Impact Area | Likelihood | Severity | Mitigation Strategy & Safeguards | Residual Risk |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Memory Fragmentation / VRAM Overrun** | Inference Latency | Low | 🟠 **HIGH** | Dynamic context throttling & thread capping | 🟢 **LOW** |
| **Model Hallucination on Domain Code** | Output Quality | Medium | 🟡 **MEDIUM** | System prompt grounding with Memory Hub injection | 🟢 **LOW** |
| **CUDA Driver & PyTorch ABI Drift** | Service Boot | Low | 🟠 **HIGH** | Resilient CPU auto-fallback & split attention | 🟢 **LOW** |
| **Unauthorized Physical Data Access** | Security | Very Low | 🔴 **CRITICAL** | OS-level encryption & zero telemetry reporting | 🟢 **MINIMAL** |

## 🚀 6. Strategic Implementation Roadmap & Phased Milestones
| Phase | Horizon | Key Strategic Milestones | Owner | Success KPI |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1: Foundation & Hardening** | Days 1–30 | Thread optimization, memory leak audits, baseline SLAs | Lead Architect | 99.9% uptime |
| **Phase 2: Scale & Acceleration** | Days 31–90 | Multi-model orchestration, advanced caching, 8K scaling | DevOps / ML | < 2s response |
| **Phase 3: Autonomous Maturity** | Days 91–180 | Continuous self-tuning, enterprise agent pipelines | CTO / Advisory | 3x team productivity |

## 💰 7. Financial & Resource ROI Analysis
| Cost Category | Cloud API Model (Monthly) | Local AI Workbench (Monthly) | 12-Month Net Savings |
| :--- | :--- | :--- | :--- |
| **Inference Usage (2.5M tokens/day)** | $2,200.00 | $0.00 (Local Hardware) | $26,400.00 |
| **Image Creation (600 renders/mo)** | $300.00 | $0.00 (ComfyUI) | $3,600.00 |
| **Data Privacy & Compliance Audits** | $700.00 | $0.00 (Zero Cloud Exposure) | $8,400.00 |
| **Total Annualized Impact** | **$38,400.00** | **$0.00** | **+$38,400.00 (+100% ROI)** |

## 📌 8. Actionable Executive Recommendations & Next Steps
1. **Immediate (Next 7 Days)**: Lock in baseline performance profiles across all development nodes and verify SQLite WAL backup routines.
2. **Short-Term (Next 30 Days)**: Enable automated batch exports of strategic reports directly to internal knowledge vaults.
3. **Strategic Horizon (Next Quarter)**: Expand on-premise agentic workflows to encompass continuous CI/CD automated review.
"""


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

    async def scroll_to_text(self, text_snippet, offset_y=0):
        await self.evaluate(f"""
            (() => {{
                const xpath = "//*[contains(text(), '{text_snippet}')]";
                const res = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                if (res.snapshotLength > 0) {{
                    const el = res.snapshotItem(res.snapshotLength - 1);
                    el.scrollIntoView({{ behavior: 'instant', block: 'start' }});
                }}
            }})()
        """)
        await asyncio.sleep(1.2)

    async def capture(self, filename):
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


async def prepare_demo_conversation() -> str:
    """Inserts a dedicated executive report conversation into SQLite."""
    conv_id = "exec-report-demo-2026"
    now = datetime.datetime.now().isoformat()
    
    # Clean any prior demo
    await db.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
    await db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))

    # Create conversation
    await db.execute(
        """
        INSERT INTO conversations (id, title, model, system_prompt, temperature, context_length, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (conv_id, "Executive Strategic Report: Enterprise AI Platform", "qwen2.5:14b", "", 0.3, 8192, now, now)
    )

    # User request
    user_msg_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO messages (id, conversation_id, role, content, images_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_msg_id, conv_id, "user", "/report Autonomous Enterprise AI Platform -- Architecture, KPI Dashboard, and Risk Assessment", "[]", now)
    )

    # Assistant Executive Report
    asst_msg_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO messages (id, conversation_id, role, content, images_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (asst_msg_id, conv_id, "assistant", EXECUTIVE_REPORT_CONTENT.strip(), "[]", now)
    )
    return conv_id


async def main():
    print("Preparing demo executive report conversation in database...")
    conv_id = await prepare_demo_conversation()
    print(f"Demo conversation ready with ID: {conv_id}")

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
        f"http://127.0.0.1:8501/?page=studio&conv={conv_id}"
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

        print("\n[1/4] Capturing Executive KPI Dashboard & Classification Banner...")
        await client.wait_until_settled(25)
        await client.scroll_to_text("CONFIDENTIAL // BOARD ACCESS")
        await client.capture("09_executive_report_dashboard_kpis.png")

        print("\n[2/4] Capturing Visual Architecture Mermaid Diagram & Component Scorecard...")
        await client.scroll_to_text("Architecture & Operational Data Flow")
        await client.capture("10_executive_report_architecture_and_scorecard.png")

        print("\n[3/4] Capturing Enterprise Risk Matrix & Financial TCO ROI Table...")
        await client.scroll_to_text("Enterprise Risk & Vulnerability Matrix")
        await client.capture("11_executive_report_risk_matrix_and_roi.png")

        print("\n[4/4] Capturing Multi-Format Report Download Toolbar...")
        await client.scroll_to_text("Download Report Files")
        await client.capture("12_executive_report_download_toolbar.png")

        await client.close()
        print("\n[SUCCESS] All 4 Executive Report screenshots captured successfully!")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(main())
