# LOCAL AI WORKBENCH

[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Ollama](https://img.shields.io/badge/Ollama-Connected-black.svg)](https://ollama.com/)
[![Tests](https://img.shields.io/badge/Tests-55%20Passed-brightgreen.svg)]()

**Local AI Workbench** is a cross-platform, local-first workstation that delivers comprehensive AI capabilities across **Windows**, **macOS** (Apple Silicon M1/M2/M3/M4 & Intel), and **Linux** (Ubuntu, Debian, Fedora, Arch) through a single unified interface:

1. **⚡ Dynamic Resource Detection & Auto Load Balancing**: Real-time telemetry monitoring CPU load, host RAM, and GPU VRAM headroom. Automatically calculates optimal Ollama CPU thread allocation (preventing UI freezes), bounds safe context token limits, tunes prompt batching, and dynamically sets ComfyUI memory modes (`--highvram`, `--medvram`, `--lowvram`, or `--cpu`) to prevent Out-Of-Memory (OOM) crashes.
2. **All-in-One Power Studio (Flagship Interface)**: Unified power chat combining conversational AI, multi-file uploads (up to 5 documents simultaneously for resume vs JD or code comparison), in-chat image generation (`/image`), executive report generation (`/report`), coding assistance (`/code`), vision understanding, and tool execution in a single thread.
3. **🧠 Multi-AI Tool Memory Hub**: Import, manage, and toggle persistent memory snippets from **ChatGPT**, **Claude**, **Cursor**, **GitHub Copilot**, and **Gemini**. Active memories are automatically composed and injected into local Ollama system prompts.
4. **🎨 Auto-Starting ComfyUI Image Lab**: Native adapter for local ComfyUI. Automatically starts alongside the Ollama server with hardware-adaptive acceleration across all major GPU vendors (NVIDIA CUDA, AMD ROCm, Intel Arc XPU, Apple Silicon Metal MPS, or multi-threaded CPU).
5. **Hardware Discovery & Diagnostics Engine**: Dynamic hardware scanner discovering host OS, CPU threads, physical cores, system RAM, and GPU accelerator details across **NVIDIA**, **AMD**, **Intel**, **Apple Silicon**, and **Qualcomm Snapdragon** with hybrid memory overflow protection (`OLLAMA_FLASH_ATTENTION=false`).
6. **💡 Hardware-Aware LLM Recommendation & Downloader Engine**: Analyzes host CPU cores, RAM headroom, and dedicated/unified GPU VRAM to suggest optimal Ollama models to download across Daily Driver, Coding, Deep Reasoning, Lightweight, and Vision categories with 1-click batch installation and progress tracking.
7. **Report Generator Engine**: Generates executive summaries, codebase architecture audits, and test compliance reports with 1-click Markdown export and workspace saving.
8. **General-Purpose AI Chatbot**: Real-time streaming conversation with locally hosted Ollama models, conversation persistence, search, editing, and parameter tuning.
9. **AI Assistant with Practical Tools**: Sandboxed backend tool execution loop with Calculator, DateTime, File Read/Search, Document Summarizer, JSON Validator, File Creator, Test Runner, and Git status inspection.
10. **Vision Multimodal Studio**: Image-understanding workspace supporting visual inputs on compatible multimodal models (such as `llama3.2:latest` or `gemma4:12b`).
11. **Coding Agent**: Workspace inspection, unified diff computation, human-in-the-loop approval workflow, safe file patching, sandboxed test execution (`pytest`), and Git diff tracking.
12. **Native Streamlit Interface**: Clean, professional, pure light-mode Streamlit dashboard with dedicated tabs for All-in-One Studio, Memory Hub, ComfyUI Image Lab, Coding Agent, Vision, and Tools.
13. **🎙️ Voice & Audio Chat Studio**: Complete hands-free two-way conversational voice chat running 100% locally. Features an inline mic button in the chat prompt, a dedicated Voice & Audio Chat Studio navigation option, sub-millisecond silence pre-screening, universal PyAV audio resampling, and natural offline Text-to-Speech audio response playback.

---

## 🚀 Quick Start Guide

### Prerequisites
* **Operating System**: Windows 10/11, macOS 12+ (Apple Silicon or Intel), or Linux (Ubuntu 20.04+, Debian, Fedora, Arch).
* **Python**: Python 3.10+ (tested on Python 3.10, 3.11, 3.12, and 3.14).
* **Ollama**: Installed from [ollama.com](https://ollama.com) (or `brew install ollama` on macOS / `curl -fsSL https://ollama.com/install.sh | sh` on Linux).
* **Node.js 18+** & npm (optional, only required if compiling the React SPA).

---

### Installation & Launch

#### On macOS & Linux

1. **Automated Setup**:
   ```bash
   chmod +x scripts/*.sh
   ./scripts/install.sh
   ```

2. **Launch All-in-One Streamlit Studio (Recommended)**:
   ```bash
   ./scripts/start_streamlit.sh
   ```
   *The workbench automatically launches Ollama, starts ComfyUI (with Apple Silicon Metal or CUDA if available), and opens [http://127.0.0.1:8501](http://127.0.0.1:8501).*

3. **Launch FastAPI Backend & Web Interface**:
   ```bash
   ./scripts/start.sh
   ```

4. **Stop All Services**:
   ```bash
   ./scripts/stop.sh
   ```

---

#### On Windows

1. **Automated Setup**:
   ```cmd
   scripts\install.bat
   ```
   *Or via PowerShell:*
   ```powershell
   .\scripts\install.ps1
   ```

2. **Launch All-in-One Streamlit Studio (Recommended)**:
   ```cmd
   scripts\start_streamlit.bat
   ```
   *Or via PowerShell:*
   ```powershell
   .\scripts\start_streamlit.ps1
   ```
   *Or directly:*
   ```cmd
   python streamlit_app.py
   ```
   *The workbench opens automatically at [http://127.0.0.1:8501](http://127.0.0.1:8501).*

3. **Launch FastAPI Backend & Web Interface**:
   ```cmd
   scripts\start.bat
   ```
   *Or via PowerShell:*
   ```powershell
   .\scripts\start.ps1
   ```

4. **Stop All Services**:
   ```cmd
   scripts\stop.bat
   ```

---

## 🏗️ Project Architecture

```
AIToolBox/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI server entry point & lifespan
│   │   ├── core/
│   │   │   ├── config.py        # Centralized settings & path limits
│   │   │   ├── security.py      # Workspace sandboxing & traversal protection
│   │   │   ├── command_runner.py# Permission-controlled command executor
│   │   │   └── logging.py       # Redacting structured logger
│   │   ├── database/
│   │   │   ├── connection.py    # Thread-safe SQLite manager in WAL mode
│   │   │   └── migrations.py    # Automated schema initialization & migrations
│   │   ├── schemas/             # Pydantic models for request/response validation
│   │   ├── services/
│   │   │   ├── ollama_service.py # Live Ollama streaming client & capability discovery
│   │   │   ├── comfyui_service.py# Local ComfyUI adapter & graph builder
│   │   │   ├── tool_registry.py # Tool registration & permission loop
│   │   │   ├── coding_agent_service.py # Diff engine & code patcher
│   │   │   ├── workflow_service.py     # Structured workflow pipeline runner
│   │   │   └── backup_service.py       # Hot SQLite backup & validator
│   │   └── api/                 # Documented REST API endpoints
│   ├── tests/                   # Automated pytest suite (29 tests)
│   ├── requirements.txt         # Backend Python dependencies
│   └── run.py                   # Standalone Uvicorn runner
├── frontend/
│   ├── src/
│   │   ├── components/          # Sidebar, Header, DiffViewer
│   │   ├── pages/               # Chat, Tools, Vision, Image Lab, Coding, Automation, Diagnostics, Settings
│   │   ├── services/api.ts      # Typed frontend API client
│   │   ├── types/index.ts       # Shared TypeScript interfaces
│   │   ├── App.tsx              # Application shell & state manager
│   │   ├── main.tsx             # React DOM mount point
│   │   └── index.css            # Workstation styling & theme variables
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── data/
│   ├── workbench.db             # Local SQLite application database
│   └── backups/                 # Validated database backup snapshots
├── workspace/                   # Authorized directory for coding agent & file tools
├── generated_images/            # Saved local image generation output
├── scripts/
│   ├── install.sh / install.bat / install.ps1
│   ├── start_streamlit.sh / start_streamlit.bat / start_streamlit.ps1
│   ├── start.sh / start.bat / start.ps1
│   └── stop.sh / stop.bat / stop.ps1
├── docs/
│   ├── OLLAMA_GUIDE.md
│   ├── COMFYUI_GUIDE.md
│   ├── SECURITY_GUIDE.md
│   └── BACKUP_GUIDE.md
├── .env.example
├── .gitignore
└── README.md
```

---

## 🧪 Running Automated Tests

Run backend unit, security, and live integration tests:
```bash
python -m pytest backend/tests -v
```
All **55 automated tests** verify:
* Real-time resource discovery, load balancing, thread budgeting, and memory ceiling bounding.
* Cross-platform OS discovery (Windows, macOS Apple Silicon/Intel, Linux).
* Hardware accelerator detection across all vendors (NVIDIA, AMD ROCm, Intel Arc XPU, Qualcomm Snapdragon, Apple Silicon Metal, Multi-core CPU).
* Path traversal prevention, symlink resolution, and size limits.
* Destructive command blocking and privilege escalation rejection (both Windows and POSIX `sudo`/`su`/`doas`/`rm -rf`).
* Multi-file document upload processing and token budgeting (up to 5 files simultaneously).
* Live Ollama connectivity and model discovery.
* End-to-end chat completion and tool execution loop.
* Unified diff generation and change application.
* Structured workflow creation, dry-run validation, and step execution.
* SQLite schema migrations, CRUD, and online backup validation.

Verify frontend build:
```powershell
cd frontend
npm.cmd run build
```

---

## 🔒 Security Architecture Highlights

1. **Loopback Only (`127.0.0.1`)**: No open external ports or public internet exposure.
2. **Workspace Sandboxing**: File operations are strictly prohibited from escaping `AIToolBox/workspace`. Relative escapes (`../`) and null bytes are rejected.
3. **Controlled Command Runner**: All commands run in the workspace without elevated/admin privileges. Destructive system operations are blocked by policy.
4. **Zero Cloud Dependencies by Default**: Prompts, local files, and memories are never sent to external third parties.

---

## 📖 Additional Documentation
* [Ollama Integration Guide](docs/OLLAMA_GUIDE.md)
* [ComfyUI Image Generation Guide](docs/COMFYUI_GUIDE.md)
* [Security & Permissions Guide](docs/SECURITY_GUIDE.md)
* [Database Backup & Recovery Guide](docs/BACKUP_GUIDE.md)
