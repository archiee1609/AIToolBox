# LOCAL AI WORKBENCH

[![Python](https://img.shields.io/badge/Python-3.14%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20TypeScript-61dafb.svg)](https://react.dev/)
[![Ollama](https://img.shields.io/badge/Ollama-Connected-black.svg)](https://ollama.com/)
[![Tests](https://img.shields.io/badge/Tests-29%20Passed-brightgreen.svg)]()

**Local AI Workbench** is a Windows-first, local-first workstation that delivers comprehensive AI capabilities through a single unified interface:

1. **All-in-One Power Studio (Flagship Tab)**: Unified power chat combining conversational AI, in-chat image generation (`/image`), executive report generation (`/report`), coding assistance (`/code`), vision understanding, and tool execution in a single thread.
2. **LLM Model Installation & Management**: Built-in provision to discover, pull, and install any model from the Ollama library (`llama3.2`, `mistral`, `deepseek-r1:14b`, `qwen2.5-coder`, `phi4`, `llava`, etc.) with real-time SSE progress tracking.
3. **Report Generator Engine**: Generates executive summaries, codebase architecture audits, and test compliance reports with 1-click Markdown export and workspace saving.
4. **General-Purpose AI Chatbot**: Real-time streaming conversation with locally hosted Ollama models (`gemma4:12b`, `gpt-oss:latest`), conversation persistence, search, editing, and parameter tuning.
5. **AI Assistant with Practical Tools**: Sandboxed backend tool execution loop with Calculator, DateTime, File Read/Search, Document Summarizer, JSON Validator, File Creator, Test Runner, and Git status inspection.
6. **Local Image-Generation & Understanding Workspace**:
   - **Image Lab**: Native adapter for local ComfyUI instance with prompt graph submission, checkpoint selection, progress tracking, and local image gallery persistence.
   - **Vision**: Image-understanding workspace supporting visual inputs on compatible multimodal models (such as `gemma4:12b`).
7. **Coding Agent**: Workspace inspection, unified diff computation, human-in-the-loop approval workflow, safe file patching, sandboxed test execution (`pytest`), and Git diff tracking.
8. **Workflow Automation Engine**: Structured multi-step automation pipelines (read files, extract text, summarize with LLM, write output, run tests) with dry-run previews and execution audit trails.

---

## 🚀 Quick Start on Windows

### 1. Prerequisites
* **Windows 10 or 11**
* **Python 3.10+** (verified on Python 3.14.6)
* **Node.js 18+** & npm (verified on Node.js v24.18.0)
* **Ollama**: Installed and running on `http://127.0.0.1:11434` with your preferred models (e.g. `ollama run gemma4:12b` or `ollama run gpt-oss`).

### 2. Automated Installation
Run the Windows installation script:
```cmd
scripts\install.bat
```
*Or using PowerShell:*
```powershell
.\scripts\install.ps1
```

### 3. Launching the Application
Launch both backend services and open your browser:
```cmd
scripts\start.bat
```
*Or using PowerShell:*
```powershell
.\scripts\start.ps1
```
The Workbench will open at **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.

To stop running instances at any time:
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
│   ├── install.bat / install.ps1
│   ├── start.bat / start.ps1
│   └── stop.bat / stop.ps1
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
```powershell
python -m pytest backend/tests -v
```
All **29 automated tests** verify:
* Path traversal prevention, symlink resolution, and size limits.
* Destructive command blocking and privilege escalation rejection.
* Live Ollama connectivity and model discovery (`gemma4:12b`, `gpt-oss:latest`).
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
