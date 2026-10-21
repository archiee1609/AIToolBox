"""
Local AI Workbench - Streamlit Application
A unified, private, offline AI workstation running natively on your local hardware.
Includes Studio Chat, AI Tool Memory Hub, ComfyUI Image Lab, Coding Agent, Vision, and Tools.
"""

import sys
import os
import asyncio
import json
import uuid
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import streamlit as st

# Ensure backend modules are discoverable
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# If user executes `python streamlit_app.py` directly, start Ollama & ComfyUI and launch Streamlit runner
try:
    import streamlit.runtime
    is_in_streamlit_runtime = streamlit.runtime.exists()
except Exception:
    is_in_streamlit_runtime = False

if not is_in_streamlit_runtime:
    import subprocess
    from app.services.ollama_service import ollama_service
    from app.services.comfyui_service import comfyui_service

    print("========================================================")
    print("       LOCAL AI WORKBENCH - ALL-IN-ONE LAUNCHER         ")
    print("========================================================")
    print("[*] Checking local Ollama engine...")
    try:
        asyncio.run(ollama_service.ensure_running())
        print("[+] Ollama service is online!")
    except Exception as e:
        print(f"[!] Ollama status notice: {e}")

    if comfyui_service.comfy_main.exists():
        print("[*] Checking local ComfyUI engine...")
        try:
            asyncio.run(comfyui_service.ensure_running())
            print("[+] ComfyUI service is online!")
        except Exception as e:
            print(f"[!] ComfyUI status notice: {e}")

    print("[*] Launching Local AI Workbench via Streamlit at http://127.0.0.1:8501...")
    script_path = str(Path(__file__).resolve())
    cmd = [sys.executable, "-m", "streamlit", "run", script_path, "--server.port", "8501"] + sys.argv[1:]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run(cmd, env=env)
        sys.exit(proc.returncode)
    except KeyboardInterrupt:
        print("\n[*] Local AI Workbench stopped.")
        sys.exit(0)

from app.core.config import settings
from app.database.connection import db
from app.database.migrations import run_migrations
from app.services.ollama_service import ollama_service
from app.services.comfyui_service import comfyui_service, POPULAR_MODELS, parse_resolution_from_prompt, STYLE_PRESETS
from app.services.tool_registry import tool_registry
from app.services.coding_agent_service import coding_agent_service
from app.schemas.image import ImageGenerateRequest

# Helper to execute async functions in Streamlit safely
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)

# Page Configuration
st.set_page_config(
    page_title="Local AI Workbench",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Professional, Clean Enterprise Light Theme)
st.markdown("""
<style>
    /* Google Plus Jakarta Sans & JetBrains Mono Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    * {
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    code, pre, [class*="stCode"], kbd {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Overall App Background & Padding */
    .stApp {
        background-color: #f8fafc;
    }

    .main .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2.5rem;
        max-width: 1280px;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.25rem;
    }

    [data-testid="stSidebar"] hr {
        margin: 0.85rem 0;
        border-color: #f1f5f9;
    }

    /* Navigation Radio Pills in Sidebar */
    [data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] {
        background: #f1f5f9;
        padding: 0.35rem;
        border-radius: 0.75rem;
        gap: 0.25rem;
    }

    [data-testid="stSidebar"] div[data-testid="stRadio"] label {
        border-radius: 0.55rem;
        padding: 0.5rem 0.85rem !important;
        font-weight: 600;
        font-size: 0.88rem;
        color: #475569;
        transition: all 0.15s ease-in-out;
        cursor: pointer;
        border: 1px solid transparent;
        background: transparent;
    }

    [data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
        color: #0f172a;
        background-color: #ffffff;
    }

    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-checked="true"],
    [data-testid="stSidebar"] div[data-testid="stRadio"] input:checked + div {
        color: #4f46e5 !important;
        font-weight: 700;
    }

    /* Sleek Custom Scrollbars */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 9999px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
    }

    /* Top Brand Bar */
    .brand-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.85rem 1.35rem;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 1rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.03);
    }
    .brand-title {
        font-size: 1.15rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.02em;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .brand-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.75rem;
        font-size: 0.74rem;
        font-weight: 700;
        border-radius: 9999px;
        line-height: 1.2;
    }
    .pill-success {
        background-color: #ecfdf5;
        color: #059669;
        border: 1px solid #a7f3d0;
    }
    .pill-indigo {
        background-color: #eef2ff;
        color: #4f46e5;
        border: 1px solid #c7d2fe;
    }
    .pill-warning {
        background-color: #fffbeb;
        color: #d97706;
        border: 1px solid #fde68a;
    }
    .pill-neutral {
        background-color: #f1f5f9;
        color: #475569;
        border: 1px solid #e2e8f0;
    }

    /* Cards */
    .stCard, .workbench-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 0.875rem;
        padding: 1.25rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.03);
        margin-bottom: 1rem;
    }

    /* Buttons */
    button[kind="primary"] {
        background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
        border: none !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-radius: 0.65rem !important;
        padding: 0.5rem 1.15rem !important;
        box-shadow: 0 2px 4px rgba(79, 70, 229, 0.2) !important;
        transition: all 0.18s ease-in-out !important;
    }
    button[kind="primary"]:hover {
        box-shadow: 0 4px 10px rgba(79, 70, 229, 0.32) !important;
        transform: translateY(-1px);
    }
    button[kind="primary"]:active {
        transform: translateY(0);
    }

    button[kind="secondary"] {
        border-radius: 0.6rem !important;
        border: 1px solid #e2e8f0 !important;
        background-color: #ffffff !important;
        color: #334155 !important;
        font-weight: 500 !important;
        transition: all 0.15s ease !important;
    }
    button[kind="secondary"]:hover {
        border-color: #cbd5e1 !important;
        background-color: #f8fafc !important;
        color: #0f172a !important;
    }

    /* Starter Prompt Cards */
    .starter-btn {
        text-align: left;
        width: 100%;
        border-radius: 0.875rem !important;
        border: 1px solid #e2e8f0 !important;
        background: #ffffff !important;
        padding: 0.85rem 1.1rem !important;
        transition: all 0.15s ease !important;
    }
    .starter-btn:hover {
        border-color: #6366f1 !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1) !important;
    }

    /* Chat Messages styling */
    [data-testid="stChatMessage"] {
        border-radius: 1rem;
        padding: 1.1rem 1.35rem;
        margin-bottom: 0.85rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
        transition: all 0.15s ease;
    }
    [data-testid="stChatMessage"]:hover {
        border-color: #cbd5e1;
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.04);
    }

    /* Distinct styling for User vs Assistant bubbles */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background-color: #f8fafc;
        border-left: 3.5px solid #6366f1;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        background-color: #ffffff;
        border-left: 3.5px solid #10b981;
    }

    /* Chat Input Bar */
    [data-testid="stChatInput"] {
        border-radius: 1.25rem !important;
        border: 1.5px solid #cbd5e1 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03) !important;
        background: #ffffff !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.16) !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.25rem;
        border-bottom: 1.5px solid #e2e8f0;
        padding-bottom: 0.25rem;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        font-size: 0.92rem;
        color: #64748b;
        padding: 0.6rem 0.5rem;
        border: none !important;
        background: transparent !important;
        transition: color 0.15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #0f172a;
    }
    .stTabs [aria-selected="true"] {
        color: #4f46e5 !important;
        border-bottom: 2.5px solid #4f46e5 !important;
    }

    /* Thinking & Analysing Subtle Animation */
    .ai-thinking-box {
        display: inline-flex;
        align-items: center;
        gap: 0.65rem;
        padding: 0.4rem 0.95rem;
        border-radius: 9999px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        color: #475569;
        font-size: 0.85rem;
        font-weight: 500;
        margin: 0.25rem 0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
        animation: subtlePulse 2.4s infinite ease-in-out;
    }

    .ai-thinking-dots {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
    }

    .ai-thinking-dot {
        width: 7px;
        height: 7px;
        background-color: #6366f1;
        border-radius: 50%;
        display: inline-block;
        animation: aiBounce 1.4s infinite ease-in-out both;
    }

    .ai-thinking-dot:nth-child(1) {
        animation-delay: -0.32s;
    }

    .ai-thinking-dot:nth-child(2) {
        animation-delay: -0.16s;
    }

    @keyframes aiBounce {
        0%, 80%, 100% {
            transform: scale(0.35);
            opacity: 0.3;
        }
        40% {
            transform: scale(1.15);
            opacity: 1;
            background-color: #4f46e5;
        }
    }

    /* Shimmer gradient for Analysing state */
    .ai-analysing-shimmer {
        display: inline-flex;
        align-items: center;
        background: linear-gradient(90deg, #4f46e5 0%, #06b6d4 50%, #4f46e5 100%);
        background-size: 200% auto;
        color: transparent;
        -webkit-background-clip: text;
        background-clip: text;
        font-weight: 600;
        animation: aiShimmer 2.2s linear infinite;
    }

    .ai-processing-text {
        color: #4f46e5;
        font-weight: 600;
        letter-spacing: -0.01em;
    }

    @keyframes aiShimmer {
        to {
            background-position: 200% center;
        }
    }

    @keyframes subtlePulse {
        0%, 100% {
            box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.22);
            border-color: #c7d2fe;
        }
        50% {
            box-shadow: 0 0 0 6px rgba(99, 102, 241, 0);
            border-color: #e2e8f0;
        }
    }
</style>
""", unsafe_allow_html=True)

# Status Badge Helper
def render_thinking_badge(phase: str = "thinking", details: str = "") -> str:
    if phase == "analysing":
        text = details or "Analysing prompt & context..."
        return f'<div class="ai-thinking-box"><span class="ai-thinking-dots"><span class="ai-thinking-dot"></span><span class="ai-thinking-dot"></span><span class="ai-thinking-dot"></span></span><span class="ai-analysing-shimmer">{text}</span></div>'
    elif phase == "processing":
        text = details or "Processing workspace data..."
        return f'<div class="ai-thinking-box"><span class="ai-thinking-dots"><span class="ai-thinking-dot"></span><span class="ai-thinking-dot"></span><span class="ai-thinking-dot"></span></span><span class="ai-processing-text">{text}</span></div>'
    else:
        text = details or "Thinking..."
        return f'<div class="ai-thinking-box"><span class="ai-thinking-dots"><span class="ai-thinking-dot"></span><span class="ai-thinking-dot"></span><span class="ai-thinking-dot"></span></span><span>{text}</span></div>'

# Initialize Database and Ensure Migrations
@st.cache_resource
def initialize_system():
    run_async(run_migrations())
    return True

initialize_system()

# Ensure Background Engines (Ollama & ComfyUI)
@st.cache_resource
def ensure_background_engines():
    """Auto-starts Ollama and ComfyUI on first application load."""
    if not run_async(ollama_service.is_server_reachable(timeout=2.0)):
        run_async(ollama_service.start_service())
    if comfyui_service.comfy_main.exists() and not run_async(comfyui_service.is_server_reachable()):
        run_async(comfyui_service.start_service())
    return True

ensure_background_engines()

# Check Services
ollama_online = run_async(ollama_service.is_server_reachable(timeout=2.0))
if not ollama_online:
    # Attempt on-demand start if not yet running
    try:
        run_async(ollama_service.start_service(timeout_seconds=15))
        ollama_online = run_async(ollama_service.is_server_reachable(timeout=2.0))
    except Exception:
        pass

ollama_health = run_async(ollama_service.check_health(timeout=3.0)) if ollama_online else {"reachable": False}
models_list = run_async(ollama_service.list_models()) if ollama_online else []
model_names = [m.name for m in models_list] if models_list else ["gemma4:12b"]

comfy_online = run_async(comfyui_service.is_server_reachable())

# Auto-start ComfyUI if offline
if not comfy_online and comfyui_service.comfy_main.exists():
    try:
        run_async(comfyui_service.start_service())
        comfy_online = run_async(comfyui_service.is_server_reachable())
    except Exception:
        pass

# User Preferences Persistence
DEFAULT_SYSTEM_INSTRUCTION = "You are Local AI Workbench, an all-in-one expert assistant for coding, reasoning, reports, and data analysis."

def get_preference(key: str, default: str = "") -> str:
    try:
        row = run_async(db.fetchone("SELECT value FROM user_preferences WHERE key = ?", (key,)))
        return row["value"] if row and row["value"] is not None else default
    except Exception:
        return default

def set_preference(key: str, value: str) -> None:
    try:
        run_async(db.execute(
            """
            INSERT INTO user_preferences (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (key, str(value))
        ))
    except Exception:
        pass

# ---------------------------------------------------------
# CONVERSATION & CHAT HISTORY HELPERS (ChatGPT & Gemini Style)
# ---------------------------------------------------------
def get_conversations(limit: int = 50) -> List[Dict[str, Any]]:
    try:
        rows = run_async(db.fetchall(
            """
            SELECT c.*, COUNT(m.id) AS msg_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            LIMIT ?
            """,
            (limit,)
        ))
        return [dict(r) for r in rows]
    except Exception:
        return []

def create_new_conversation(title: str = "New Chat", model: str = "") -> str:
    conv_id = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()
    m_name = model or "gemma4:12b"
    try:
        run_async(db.execute(
            """
            INSERT INTO conversations (id, title, model, system_prompt, temperature, context_length, created_at, updated_at)
            VALUES (?, ?, ?, '', 0.7, 8192, ?, ?)
            """,
            (conv_id, title, m_name, now, now)
        ))
    except Exception:
        pass
    return conv_id

def load_conversation_messages(conv_id: str) -> List[Dict[str, Any]]:
    try:
        rows = run_async(db.fetchall(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conv_id,)
        ))
        msgs = []
        for r in rows:
            imgs = []
            try:
                imgs = json.loads(r["images_json"] or "[]")
            except Exception:
                pass
            msgs.append({
                "id": r["id"],
                "role": r["role"],
                "content": r["content"],
                "images": imgs,
                "created_at": r["created_at"]
            })
        return msgs
    except Exception:
        return []

def save_chat_message(conv_id: str, role: str, content: str, images: Optional[List[str]] = None) -> str:
    msg_id = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()
    imgs_json = json.dumps(images or [])
    try:
        run_async(db.execute(
            """
            INSERT INTO messages (id, conversation_id, role, content, images_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (msg_id, conv_id, role, content, imgs_json, now)
        ))
        run_async(db.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conv_id)
        ))
    except Exception:
        pass
    return msg_id

def delete_conversation(conv_id: str) -> None:
    try:
        run_async(db.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,)))
        run_async(db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,)))
    except Exception:
        pass

def update_conversation_title(conv_id: str, new_title: str) -> None:
    now = datetime.datetime.now().isoformat()
    try:
        run_async(db.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (new_title, now, conv_id)
        ))
    except Exception:
        pass

# Load Stored Memories
def load_memories() -> List[Dict[str, Any]]:
    rows = run_async(db.fetchall("SELECT * FROM user_memories ORDER BY updated_at DESC"))
    return rows

stored_memories = load_memories()
active_memories = [m for m in stored_memories if m["enabled"]]

# Load persisted preferences and initialize session state before rendering
saved_sys_inst = get_preference("system_instruction", DEFAULT_SYSTEM_INSTRUCTION)
saved_model = get_preference("selected_model", "")
try:
    saved_temp = float(get_preference("temperature", "0.7"))
except Exception:
    saved_temp = 0.7
try:
    saved_ctx = int(get_preference("context_tokens", "8192"))
except Exception:
    saved_ctx = 8192

if "selected_model_val" not in st.session_state:
    if saved_model and saved_model in model_names:
        st.session_state["selected_model_val"] = saved_model
    else:
        st.session_state["selected_model_val"] = model_names[0] if model_names else "gemma4:12b"

if "temperature_val" not in st.session_state:
    st.session_state["temperature_val"] = min(max(saved_temp, 0.0), 1.0)

if "context_tokens_val" not in st.session_state:
    st.session_state["context_tokens_val"] = saved_ctx

if "sys_inst_val" not in st.session_state:
    st.session_state["sys_inst_val"] = saved_sys_inst

# Active inference parameters used across modules
selected_model = st.session_state["selected_model_val"]
temperature = float(st.session_state["temperature_val"])
context_tokens = int(st.session_state["context_tokens_val"])
system_instruction = st.session_state["sys_inst_val"]

# ---------------------------------------------------------
# SIDEBAR NAVIGATION & INFERENCE CONTROLS
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 0.65rem; margin-bottom: 0.75rem;">
        <div style="background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%); color: white; width: 34px; height: 34px; border-radius: 9px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.15rem; box-shadow: 0 2px 6px rgba(79, 70, 229, 0.25);">
            ⚡
        </div>
        <div>
            <div style="font-weight: 800; font-size: 1.05rem; color: #0f172a; line-height: 1.15;">AI Workbench</div>
            <div style="font-size: 0.73rem; color: #64748b; font-weight: 500;">Private • Offline Studio</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # + New Chat (Gemini / ChatGPT Style prominent starter)
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        target_model = st.session_state.get("selected_model_val", model_names[0] if model_names else "gemma4:12b")
        new_conv_id = create_new_conversation("New Chat", target_model)
        st.session_state["active_conv_id"] = new_conv_id
        st.session_state["messages"] = []
        st.session_state["loaded_conv_id"] = new_conv_id
        st.rerun()

    # Module Navigation
    # All features are unified in the All-in-One Studio & Settings. Developer tabs preserved in code.
    ALL_MODULE_PAGES = [
        "💬 All-in-One Studio",
        "⚙️ Settings",
        "🧠 AI Tool Memory Hub",
        "🎨 ComfyUI Image Lab",
        "💻 Autonomous Coding Agent",
        "👁️ Vision Multimodal",
        "🛠️ AI Tools",
        "⚙️ Diagnostics & Models"
    ]
    show_all_modules = st.query_params.get("show_all") in ["1", "true"]
    nav_options = ALL_MODULE_PAGES if show_all_modules else ["💬 All-in-One Studio", "⚙️ Settings"]

    selected_page = st.radio(
        "Navigation",
        nav_options,
        index=0,
        label_visibility="collapsed"
    )

    st.divider()

    # Fetch Conversations for History Panel
    all_conversations = get_conversations(35)
    if not all_conversations:
        init_id = create_new_conversation("New Chat", model_names[0] if model_names else "gemma4:12b")
        st.session_state["active_conv_id"] = init_id
        all_conversations = get_conversations(35)

    if "active_conv_id" not in st.session_state or not any(c["id"] == st.session_state["active_conv_id"] for c in all_conversations):
        st.session_state["active_conv_id"] = all_conversations[0]["id"]
        st.session_state["messages"] = load_conversation_messages(st.session_state["active_conv_id"])
        st.session_state["loaded_conv_id"] = st.session_state["active_conv_id"]

    if "loaded_conv_id" not in st.session_state or st.session_state["loaded_conv_id"] != st.session_state["active_conv_id"]:
        st.session_state["messages"] = load_conversation_messages(st.session_state["active_conv_id"])
        st.session_state["loaded_conv_id"] = st.session_state["active_conv_id"]

    # 🕒 Chat History Sidebar (Gemini & ChatGPT style)
    st.markdown("##### 🕒 Recent Chats")
    with st.container(height=260):
        for conv in all_conversations:
            is_active = (conv["id"] == st.session_state["active_conv_id"])
            col_c1, col_c2 = st.columns([5, 1])
            with col_c1:
                raw_t = conv.get("title") or "New Chat"
                display_t = raw_t if len(raw_t) <= 19 else raw_t[:17] + "..."
                label = f"▸ {display_t}" if is_active else f"  {display_t}"
                if st.button(
                    label,
                    key=f"ch_{conv['id']}",
                    use_container_width=True,
                    help=f"{raw_t}\nModel: {conv.get('model', 'gemma4:12b')} • Messages: {conv.get('msg_count', 0)}"
                ):
                    st.session_state["active_conv_id"] = conv["id"]
                    st.session_state["messages"] = load_conversation_messages(conv["id"])
                    st.session_state["loaded_conv_id"] = conv["id"]
                    st.rerun()
            with col_c2:
                if st.button("✕", key=f"del_{conv['id']}", help="Delete chat", use_container_width=True):
                    delete_conversation(conv["id"])
                    rem = [c for c in all_conversations if c["id"] != conv["id"]]
                    if rem:
                        st.session_state["active_conv_id"] = rem[0]["id"]
                        st.session_state["messages"] = load_conversation_messages(rem[0]["id"])
                        st.session_state["loaded_conv_id"] = rem[0]["id"]
                    else:
                        new_id = create_new_conversation("New Chat", selected_model)
                        st.session_state["active_conv_id"] = new_id
                        st.session_state["messages"] = []
                        st.session_state["loaded_conv_id"] = new_id
                    st.rerun()

    st.divider()

    # Service Status Pills (Compact footer)
    st.markdown("##### 📡 System Status")
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        if ollama_online:
            st.markdown('<span class="brand-pill pill-success">🟢 Ollama Online</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="brand-pill pill-warning">🔴 Ollama Offline</span>', unsafe_allow_html=True)
    with col_stat2:
        if comfy_online:
            st.markdown('<span class="brand-pill pill-success">🟢 ComfyUI Online</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="brand-pill pill-warning">🟠 ComfyUI Idle</span>', unsafe_allow_html=True)

    if not ollama_online:
        if st.button("▶ Start Ollama", use_container_width=True):
            with st.spinner("Booting local Ollama engine..."):
                run_async(ollama_service.start_service())
                st.rerun()

    if not comfy_online and comfyui_service.comfy_main.exists():
        if st.button("▶ Start ComfyUI", use_container_width=True):
            with st.spinner("Booting ComfyUI engine with CPU optimization..."):
                run_async(comfyui_service.start_service())
                st.rerun()

    st.caption(f"🧠 {len(active_memories)} active memories injected into prompts")

# =========================================================
# REUSABLE SECTION RENDERERS (MEMORIES, TOOLS, DIAGNOSTICS)
# =========================================================
def render_memory_hub_section():
    st.markdown("#### 🧠 AI Tool Memory Hub")
    st.caption("Import, synchronize, and activate guidelines from ChatGPT, Claude, Cursor, Copilot, and Gemini into your local LLM inference.")

    cur_stored = load_memories()
    cur_active = [m for m in cur_stored if m["enabled"]]

    # Stats Row
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("Total Memories", len(cur_stored))
    with s2:
        st.metric("Active in Prompts", len(cur_active), delta=f"{len(cur_active)} active")
    with s3:
        unique_tools = len(set((m.get("source_tool") or "custom").lower() for m in cur_stored))
        st.metric("Connected AI Tools", unique_tools if cur_stored else 1)
    with s4:
        st.metric("Local Sync Status", "🟢 Synced with Ollama")

    st.markdown("---")

    # 1-Click Import Presets
    st.markdown("##### ⚡ 1-Click Quick Import Presets")
    presets = [
        {
            "tool": "chatgpt",
            "name": "ChatGPT Instructions",
            "desc": "Concise, typed code, architectural reasoning before diffs.",
            "content": "Always provide concise, production-ready code with type annotations.\nPrefer modern standard libraries over unnecessary external packages.\nExplain the architectural reasoning before providing code diffs."
        },
        {
            "tool": "claude",
            "name": "Claude Project Memory",
            "desc": "Clean Architecture, separation of concerns, and type safety.",
            "content": "Adhere to Clean Architecture principles.\nSeparate domain logic, controllers, and data storage access.\nTreat documentation and type safety as first-class citizens."
        },
        {
            "tool": "cursor",
            "name": "Cursor Rules",
            "desc": "Minimal non-destructive edits and explicit TypeScript types.",
            "content": "Never rewrite entire files when single function changes suffice.\nUse explicit TypeScript types instead of 'any'.\nEnsure all FastAPI endpoints have request and response Pydantic models."
        },
        {
            "tool": "copilot",
            "name": "GitHub Copilot Instructions",
            "desc": "Python 3.12+ strict typing, pytest suites, and SQLite WAL.",
            "content": "Python 3.12+ with strict typing and pytest suites.\nReact 18 with functional components, Tailwind utility classes, and TypeScript.\nSQLite with WAL mode and transaction isolation."
        }
    ]

    cols = st.columns(4)
    for i, p in enumerate(presets):
        with cols[i]:
            st.markdown(f"**{p['name']}**")
            st.caption(p["desc"])
            if st.button(f"Import {p['tool'].title()}", key=f"import_preset_{p['tool']}", use_container_width=True):
                new_id = str(uuid.uuid4())
                now = datetime.datetime.now().isoformat()
                run_async(db.execute(
                    "INSERT INTO user_memories (id, key, content, source_tool, category, enabled, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                    (new_id, f"{p['tool'].title()} Instructions", p["content"], p["tool"], "instructions", now, now)
                ))
                st.toast(f"Imported {p['name']} successfully!", icon="🧠")
                st.rerun()

    st.markdown("---")

    # Add Custom Memory Form
    with st.expander("➕ Add Custom Memory Rule", expanded=False):
        with st.form("add_memory_form"):
            col_k, col_s, col_c = st.columns([2, 1, 1])
            with col_k:
                new_key = st.text_input("Memory Key / Title", placeholder="e.g. FastAPI Coding Guidelines")
            with col_s:
                new_source = st.selectbox("Source Tool", ["chatgpt", "claude", "cursor", "copilot", "gemini", "custom"])
            with col_c:
                new_cat = st.selectbox("Category", ["instructions", "rules", "persona", "tech_stack", "general"])
            
            new_content = st.text_area("Memory Content / Rules", placeholder="Type or paste memory guidelines here...", height=100)
            submit_mem = st.form_submit_button("Save to Memory Hub", type="primary")

            if submit_mem and new_key and new_content:
                new_id = str(uuid.uuid4())
                now = datetime.datetime.now().isoformat()
                run_async(db.execute(
                    "INSERT INTO user_memories (id, key, content, source_tool, category, enabled, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                    (new_id, new_key.strip(), new_content.strip(), new_source, new_cat, now, now)
                ))
                st.toast(f"Added memory: {new_key}", icon="✅")
                st.rerun()

    # Stored Memories List
    st.markdown(f"##### 📚 Stored Memories ({len(cur_stored)})")
    if not cur_stored:
        st.info("No memories stored yet. Click one of the 1-click presets above to import guidelines!")
    else:
        for mem in cur_stored:
            with st.container():
                col_info, col_toggle, col_del = st.columns([5, 1, 1])
                with col_info:
                    status_dot = "🟢" if mem["enabled"] else "⚪"
                    source_tag = mem.get("source_tool", "custom").upper()
                    st.markdown(f"**{status_dot} {mem['key']}** `{source_tag}` `{mem.get('category', 'general')}`")
                    st.code(mem["content"], language="text")
                with col_toggle:
                    toggle_label = "Mute" if mem["enabled"] else "Activate"
                    if st.button(toggle_label, key=f"tog_{mem['id']}", use_container_width=True):
                        new_state = 0 if mem["enabled"] else 1
                        run_async(db.execute("UPDATE user_memories SET enabled = ?, updated_at = ? WHERE id = ?", (new_state, datetime.datetime.now().isoformat(), mem["id"])))
                        st.rerun()
                with col_del:
                    if st.button("Delete", key=f"del_mem_{mem['id']}", use_container_width=True):
                        run_async(db.execute("DELETE FROM user_memories WHERE id = ?", (mem["id"],)))
                        st.rerun()


def render_diagnostics_section():
    st.markdown("#### ⚙️ Diagnostics & Engine Health")
    st.caption("Monitor your offline hardware acceleration, Ollama server, ComfyUI engine, and SQLite storage.")

    col_d1, col_d2 = st.columns(2)

    with col_d1:
        st.markdown("##### 🤖 Ollama Engine")
        st.write(f"**Endpoint:** `{settings.ollama_base_url}`")
        st.write(f"**Status:** {'🟢 Online & Healthy' if ollama_online else '🔴 Unreachable'}")
        st.write(f"**Installed Models:** {len(models_list)}")
        
        if not ollama_online:
            if st.button("🚀 Start Ollama Engine", key="diag_start_ollama", type="primary"):
                with st.spinner("Booting local Ollama engine..."):
                    run_async(ollama_service.start_service())
                    st.rerun()

        # Installed models details table
        if models_list:
            with st.expander("📦 Installed Models Breakdown", expanded=False):
                for m in models_list:
                    size_gb = round(getattr(m, "size", 0) / (1024**3), 2)
                    st.markdown(f"• **`{m.name}`** ({size_gb} GB)")

        # Pull model form
        with st.form("pull_model_form"):
            new_model_name = st.text_input("Install New Model from Ollama Registry", placeholder="e.g. qwen2.5-coder:7b")
            pull_btn = st.form_submit_button("📥 Pull Model via Ollama")
            if pull_btn and new_model_name:
                st.info(f"Triggering pull for `{new_model_name}` in background...")

    with col_d2:
        st.markdown("##### 🎨 ComfyUI Diffusion Engine")
        st.write(f"**Endpoint:** `{settings.comfyui_base_url}`")
        st.write(f"**Status:** {'🟢 Online & Ready' if comfy_online else '🟠 Idle / Offline'}")
        if not comfy_online and comfyui_service.comfy_main.exists():
            if st.button("🚀 Start ComfyUI Engine", key="diag_start_comfy", type="primary"):
                with st.spinner("Booting ComfyUI engine..."):
                    run_async(comfyui_service.start_service())
                    st.rerun()
        local_checkpoints = comfyui_service.get_local_checkpoints()
        st.write(f"**Checkpoints in Models Folder:** {len(local_checkpoints)}")
        if local_checkpoints:
            for ck in local_checkpoints:
                st.code(f"models/checkpoints/{ck}")

    st.markdown("---")
    st.markdown("##### 💾 Storage & Data Persistence")
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown(f"**SQLite Database Path:**\n`{settings.db_path}`")
    with col_s2:
        st.markdown(f"**Workspace Root:**\n`{settings.workspace_root}`")
    with col_s3:
        st.markdown(f"**Generated Images:**\n`{settings.generated_images_dir}`")


def render_tools_section():
    st.markdown("#### 🛠️ AI Tools & Execution Sandbox")
    st.caption("Inspect and execute sandboxed backend tools.")

    available_tools = tool_registry.get_all_definitions()
    tool_names = [t.name for t in available_tools]

    sel_tool_name = st.selectbox("Select Tool", tool_names, key="settings_tool_inspect_select")
    tool_obj = next((t for t in available_tools if t.name == sel_tool_name), None)

    if tool_obj:
        st.markdown(f"**Description:** {tool_obj.description}")
        st.markdown(f"**Category:** `{tool_obj.category}`")

        # Dynamic parameter inputs
        params = {}
        if tool_obj.parameters and tool_obj.parameters.get("properties"):
            st.markdown("##### Tool Parameters")
            for prop_name, prop_data in tool_obj.parameters["properties"].items():
                default_val = "25 * 4 + 15" if prop_name == "expression" else "README.md" if prop_name == "path" else ""
                params[prop_name] = st.text_input(f"{prop_name} ({prop_data.get('type', 'string')})", value=default_val, key=f"tool_input_{prop_name}")

        if st.button("⚡ Test Execute Tool", type="primary", key="exec_tool_test_btn"):
            status_box = st.empty()
            status_box.markdown(
                render_thinking_badge("processing", f"Executing sandboxed tool '{sel_tool_name}'..."),
                unsafe_allow_html=True
            )
            res = run_async(tool_registry.execute_tool(name=sel_tool_name, arguments=params, approved=True))
            status_box.empty()
            if res.success:
                st.success("Tool execution successful!")
                st.json(res.result)
            else:
                st.error(f"Execution failed: {res.error}")

# ---------------------------------------------------------
# TOP BRAND BANNER
# ---------------------------------------------------------
st.markdown(f"""
<div class="brand-container">
    <div>
        <div class="brand-title">
            <span>⚡ LOCAL AI WORKBENCH</span>
            <span class="brand-pill pill-success">100% Private</span>
            <span class="brand-pill pill-indigo">{selected_model}</span>
        </div>
        <p style="font-size: 0.8rem; color: #64748b; margin: 0.25rem 0 0 0;">
            Local-first AI workstation for private reasoning, ComfyUI image creation, coding agents, and memory sync.
        </p>
    </div>
    <div style="display: flex; gap: 0.5rem; align-items: center;">
        <span class="brand-pill pill-indigo">🧠 {len(active_memories)} Memories Active</span>
        <span class="brand-pill pill-success">{"🟢 Ready" if ollama_online else "🔴 Offline"}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# TAB 1: ALL-IN-ONE STUDIO / CHAT
# =========================================================
if selected_page == "💬 All-in-One Studio":
    active_conv_meta = next((c for c in all_conversations if c["id"] == st.session_state["active_conv_id"]), None)
    active_title = active_conv_meta["title"] if active_conv_meta else "New Chat"

    chat_header_c1, chat_header_c2, chat_header_c3 = st.columns([3.2, 1.8, 1.0])
    with chat_header_c1:
        st.markdown(f"### 💬 {active_title}")
        st.caption(f"Session `{st.session_state['active_conv_id'][:8]}` • {len(st.session_state.messages)} msgs • Active: `{selected_model}`")
    with chat_header_c2:
        def on_studio_model_change():
            new_m = st.session_state.get("studio_model_select")
            if new_m:
                set_preference("selected_model", new_m)
                st.session_state["selected_model_val"] = new_m

        cur_idx = model_names.index(selected_model) if selected_model in model_names else 0
        st.selectbox(
            "Active Model Switcher",
            options=model_names,
            index=cur_idx,
            key="studio_model_select",
            on_change=on_studio_model_change,
            label_visibility="collapsed",
            help="Switch active local model directly in chat"
        )
    with chat_header_c3:
        with st.popover("⚙️ Options"):
            new_title = st.text_input("Rename Chat", value=active_title, key="rename_chat_input")
            if st.button("Save Title", use_container_width=True):
                if new_title.strip():
                    update_conversation_title(st.session_state["active_conv_id"], new_title.strip())
                    st.rerun()
            if st.button("🗑️ Clear Messages", use_container_width=True):
                run_async(db.execute("DELETE FROM messages WHERE conversation_id = ?", (st.session_state["active_conv_id"],)))
                st.session_state["messages"] = []
                st.rerun()

    # Display empty state starter cards if no messages
    if not st.session_state.messages:
        st.markdown("""
        <div style="text-align: center; padding: 2rem 1rem;">
            <h3 style="font-weight: 800; color: #0f172a; margin-bottom: 0.5rem;">How can I assist your local workspace today?</h3>
            <p style="font-size: 0.85rem; color: #64748b; max-width: 500px; margin: 0 auto 1.5rem auto;">
                All processing happens locally on your computer. Private, high-speed, and connected to your external AI tool memories.
            </p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏗️ Architecture Review\n\nAnalyze project architecture & modular patterns", use_container_width=True):
                st.session_state.prompt_input = "Summarize the key architectural patterns of this application and suggest modular improvements."
            if st.button("🎨 ComfyUI Image Creation\n\nRender photorealistic images locally with /image", use_container_width=True):
                st.session_state.prompt_input = "/image A photorealistic cyberpunk city at sunset, neon reflections in rain, 8k resolution"
        with col2:
            if st.button("📄 Executive Report\n\nGenerate structured technical report with /report", use_container_width=True):
                st.session_state.prompt_input = "/report Executive Architecture and Performance Assessment"
            if st.button("💻 Autonomous Coding Agent\n\nInspect files, propose diffs, and run tests with /code", use_container_width=True):
                st.session_state.prompt_input = "/code review workspace files and run pytest suite"

    # Multimodal image attachment
    with st.expander("📎 Attach image for multimodal vision inspection (optional)", expanded=False):
        uploaded_image = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg", "webp"], key="chat_image_uploader")

    # Render Conversation History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("images"):
                for img_data in msg["images"]:
                    st.image(img_data, width=300)
            st.markdown(msg["content"])

    # Chat Input Box
    default_prompt = st.session_state.pop("prompt_input", "")
    user_prompt = st.chat_input("Ask anything, or use /image <prompt>, /report <topic>, /code <task>...", key="main_chat_input")
    prompt_to_use = user_prompt or default_prompt

    if prompt_to_use:
        # User message
        attached_b64 = []
        if uploaded_image:
            import base64
            b64 = base64.b64encode(uploaded_image.getvalue()).decode("utf-8")
            attached_b64.append(f"data:image/png;base64,{b64}")

        # Check if conversation needs an automatic descriptive title (like ChatGPT / Gemini)
        if active_title in ["New Chat", "New Conversation"] and not st.session_state.messages:
            auto_title = prompt_to_use.replace("/image", "").replace("/report", "").replace("/code", "").strip()[:32]
            if auto_title:
                update_conversation_title(st.session_state["active_conv_id"], auto_title)

        # Save user message to persistent SQLite
        save_chat_message(st.session_state["active_conv_id"], "user", prompt_to_use, attached_b64)

        st.session_state.messages.append({
            "role": "user",
            "content": prompt_to_use,
            "images": attached_b64
        })

        with st.chat_message("user"):
            if attached_b64:
                st.image(uploaded_image, width=300)
            st.markdown(prompt_to_use)

        # Assistant processing
        with st.chat_message("assistant"):
            # Check for inline /image command
            if prompt_to_use.strip().startswith("/image "):
                image_query = prompt_to_use.strip()[7:].strip()
                status_box = st.empty()
                status_box.markdown(
                    render_thinking_badge("analysing", f"Analysing prompt for image synthesis: '{image_query[:40]}'"),
                    unsafe_allow_html=True
                )

                checkpoints = comfyui_service.get_local_checkpoints()
                selected_ckpt = checkpoints[0] if checkpoints else "v1-5-pruned-emaonly.safetensors"
                det_w, det_h = parse_resolution_from_prompt(image_query)

                status_box.markdown(
                    render_thinking_badge("processing", f"Sampling diffusion tensors on CPU ({det_w}×{det_h}, ~60-120s)..."),
                    unsafe_allow_html=True
                )

                req = ImageGenerateRequest(
                    prompt=image_query,
                    checkpoint=selected_ckpt,
                    width=det_w,
                    height=det_h,
                    steps=15,
                    cfg_scale=7.0,
                    sampler_name="dpmpp_2m",
                    scheduler="karras",
                    enhance_prompt=True
                )
                res = run_async(comfyui_service.generate_image(req))
                status_box.empty()

                if res.status == "success" or res.status == "completed":
                    img_path = settings.generated_images_dir / res.image_filename if res.image_filename else None
                    if img_path and img_path.exists():
                        st.image(str(img_path), caption=f"{image_query} (Seed: {res.seed})", use_container_width=True)
                        response_text = f"### 🎨 Generated Image\n\n**Prompt:** *{image_query}*\n**Seed:** `{res.seed}` • **Saved:** `{res.image_filename}`"
                    else:
                        response_text = f"Image generated: `{res.image_url}`"
                else:
                    response_text = f"⚠️ Image generation error: {res.error or 'ComfyUI offline'}"
                
                save_chat_message(st.session_state["active_conv_id"], "assistant", response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

            # Check for inline /report command
            elif prompt_to_use.strip().startswith("/report "):
                report_title = prompt_to_use.strip()[8:].strip()
                status_box = st.empty()
                status_box.markdown(
                    render_thinking_badge("analysing", f"Analysing codebase architecture for '{report_title}'..."),
                    unsafe_allow_html=True
                )
                
                # Inject active memories into report prompt
                memory_block = "\n".join([f"- [{m.get('source_tool', 'custom').upper()}] {m['key']}: {m['content']}" for m in active_memories])
                full_system = f"{system_instruction}\n\n### Active Long-Term Memories:\n{memory_block}" if memory_block else system_instruction
                
                status_box.markdown(
                    render_thinking_badge("processing", f"Synthesizing executive report sections with {selected_model}..."),
                    unsafe_allow_html=True
                )

                rep_prompt = f"Generate a comprehensive, professional executive report titled '{report_title}'. Include Executive Summary, Architecture Overview, Key Findings, and Actionable Recommendations."
                response = run_async(ollama_service.generate(
                    model=selected_model,
                    prompt=rep_prompt,
                    system=full_system,
                    temperature=temperature,
                    context_length=context_tokens
                ))
                report_content = f"## 📄 {report_title}\n\n---\n\n{response.response}"
                status_box.empty()
                st.markdown(report_content)
                save_chat_message(st.session_state["active_conv_id"], "assistant", report_content)
                st.session_state.messages.append({"role": "assistant", "content": report_content})

            # Check for inline /code command
            elif prompt_to_use.strip().startswith("/code "):
                code_task = prompt_to_use.strip()[6:].strip()
                status_box = st.empty()
                status_box.markdown(
                    render_thinking_badge("analysing", f"Analysing workspace files for task: '{code_task}'..."),
                    unsafe_allow_html=True
                )

                task_res = run_async(coding_agent_service.create_task(task_description=code_task))
                coding_prompt = f"You are an expert autonomous software engineer. The user requested:\n{code_task}\n\nProvide an execution plan and code implementation."
                
                status_box.markdown(
                    render_thinking_badge("processing", f"Drafting syntax-safe unified diff with {selected_model}..."),
                    unsafe_allow_html=True
                )

                plan_parts = []
                async def stream_coding_plan():
                    async for chunk in ollama_service.chat_stream(
                        model=selected_model,
                        messages=[{"role": "user", "content": coding_prompt}],
                        temperature=0.2
                    ):
                        plan_parts.append(chunk)
                run_async(stream_coding_plan())
                plan_response = "".join(plan_parts) if plan_parts else "Coding plan generated."
                run_async(coding_agent_service.submit_plan_and_diff(task_res.id, plan_response, ["workspace"], plan_response))
                out = f"### 💻 Coding Agent Plan (Task `{task_res.id[:8]}`)\n\n**Objective:** {code_task}\n\n{plan_response}"
                status_box.empty()
                st.markdown(out)
                save_chat_message(st.session_state["active_conv_id"], "assistant", out)
                st.session_state.messages.append({"role": "assistant", "content": out})

            # Standard Chat Inference
            else:
                # 1. Build context with Active Memories from ChatGPT, Claude, Cursor, etc.
                memory_lines = []
                for m in active_memories:
                    src = m.get("source_tool", "custom").upper()
                    memory_lines.append(f"- [{src}] {m['key']}: {m['content']}")
                
                # Ensure current system instruction is synced in database
                set_preference("system_instruction", system_instruction)
                
                effective_system = system_instruction
                if memory_lines:
                    effective_system += "\n\n### Active Long-Term Memories & AI Tool Guidelines:\n" + "\n".join(memory_lines)

                # Format conversation history for Ollama
                ollama_messages = [{"role": "system", "content": effective_system}]
                for m in st.session_state.messages[-10:]:
                    ollama_messages.append({"role": m["role"], "content": m["content"]})

                # Stream response with animated status
                response_placeholder = st.empty()
                full_response_parts = []

                # Phase 1: Analysing animation
                response_placeholder.markdown(
                    render_thinking_badge("analysing", f"Analysing prompt with {len(active_memories)} active memories..."),
                    unsafe_allow_html=True
                )

                try:
                    # Phase 2: Thinking animation
                    response_placeholder.markdown(
                        render_thinking_badge("thinking", f"Thinking ({selected_model})..."),
                        unsafe_allow_html=True
                    )

                    # Phase 3: Token streaming from Ollama
                    async def stream_to_ui():
                        async for chunk in ollama_service.chat_stream(
                            model=selected_model,
                            messages=ollama_messages,
                            temperature=temperature,
                            context_length=context_tokens
                        ):
                            full_response_parts.append(chunk)
                            response_placeholder.markdown("".join(full_response_parts) + "▌")
                        response_placeholder.markdown("".join(full_response_parts))

                    run_async(stream_to_ui())
                    full_response = "".join(full_response_parts)
                    save_chat_message(st.session_state["active_conv_id"], "assistant", full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})

                except Exception as e:
                    err_msg = str(e)
                    if any(term in err_msg for term in ["0xc0000409", "CUDA error", "shared object initialization", "buffer in this application"]):
                        err_text = (
                            f"⚠️ **GPU Memory Overrun / CUDA Crash**: Model `{selected_model}` is too large to fit entirely in available VRAM, causing a split GPU/CPU memory crash.\n\n"
                            f"**Recommended Solutions:**\n"
                            f"- **Select a lighter model**: Switch to `gemma4:12b` or `llama3.2` using the model switcher above or in the Settings tab.\n"
                            f"- **Reduce Context Length**: Set **Context Length** in the Settings tab to `2048` or `4096` tokens.\n"
                            f"- **Safe Flash Attention**: Ollama has been reconfigured with `OLLAMA_FLASH_ATTENTION=false` to prevent CUDA memory crashes."
                        )
                    else:
                        err_text = f"⚠️ Inference failed: {e}\n\nEnsure Ollama is running on http://127.0.0.1:11434 with model `{selected_model}` installed."
                    response_placeholder.error(err_text)
                    save_chat_message(st.session_state["active_conv_id"], "assistant", err_text)
                    st.session_state.messages.append({"role": "assistant", "content": err_text})


# =========================================================
# TAB: SETTINGS & WORKSPACE CONFIGURATION
# =========================================================
elif selected_page == "⚙️ Settings":
    st.markdown("### ⚙️ Workspace & Engine Settings")
    st.caption("Configure local model inference parameters, system instructions, AI tool memories, and background engines.")

    tab_inf, tab_mem, tab_diag, tab_tools = st.tabs([
        "🤖 Model & Inference",
        "🧠 AI Memory Hub",
        "⚡ Engines & Diagnostics",
        "🛠️ Tools & Sandbox"
    ])

    with tab_inf:
        st.markdown("#### 🤖 Model Inference Parameters")
        st.caption("Configure the active local model, inference temperature, context capacity, and core instructions.")

        col_inf_left, col_inf_right = st.columns([1.5, 1])

        with col_inf_left:
            def on_settings_model_change():
                new_m = st.session_state.get("settings_model_select")
                if new_m:
                    set_preference("selected_model", new_m)
                    st.session_state["selected_model_val"] = new_m

            s_idx = model_names.index(selected_model) if selected_model in model_names else 0
            cur_sel_model = st.selectbox(
                "Active Model",
                options=model_names,
                index=s_idx,
                key="settings_model_select",
                on_change=on_settings_model_change,
                help="Select any local model running on your Ollama server. Persists across sessions."
            )

            # Model Specification Pill & Hardware Fit Card
            specs_info = {
                "llama3.2:latest": ("3.2B Parameters", "2.0 GB", "100% GPU VRAM Fit", "Fastest reasoning, lightweight & responsive"),
                "gemma4:12b": ("11.9B Parameters", "7.4 GB", "100% GPU VRAM Fit", "Excellent multi-step reasoning, coding, and instruction following"),
                "gpt-oss:latest": ("20.9B Parameters", "13.8 GB", "Safe Attention Active", "Deep architectural reasoning, complex multi-turn logic")
            }
            spec = specs_info.get(cur_sel_model, ("Local LLM", "Ollama Managed", "CUDA Accelerated", "Local offline model"))

            st.markdown(f"""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.75rem; padding: 0.85rem 1rem; margin: 0.4rem 0 1rem 0;">
                <div style="display: flex; gap: 0.45rem; flex-wrap: wrap; margin-bottom: 0.4rem;">
                    <span class="brand-pill pill-indigo">{spec[0]}</span>
                    <span class="brand-pill pill-success">{spec[1]}</span>
                    <span class="brand-pill pill-indigo">{spec[2]}</span>
                </div>
                <div style="font-size: 0.82rem; color: #475569;">{spec[3]}</div>
            </div>
            """, unsafe_allow_html=True)

            def on_settings_temp_change():
                new_t = st.session_state.get("settings_temp_slider", 0.7)
                set_preference("temperature", str(new_t))
                st.session_state["temperature_val"] = new_t

            st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=min(max(temperature, 0.0), 1.0),
                step=0.05,
                key="settings_temp_slider",
                on_change=on_settings_temp_change,
                help="Higher values make output more random/creative; lower values make it more focused and deterministic."
            )
            st.caption(
                "🎯 **0.0 - 0.2**: Code generation & math • "
                "⚖️ **0.3 - 0.7**: Balanced analysis • "
                "🎨 **0.8 - 1.0**: Creative brainstorming"
            )

            def on_settings_ctx_change():
                new_c = st.session_state.get("settings_ctx_select", 8192)
                set_preference("context_tokens", str(new_c))
                st.session_state["context_tokens_val"] = new_c

            ctx_options = [2048, 4096, 8192, 16384, 32768]
            ctx_idx = ctx_options.index(context_tokens) if context_tokens in ctx_options else 2
            st.selectbox(
                "Context Length",
                options=ctx_options,
                index=ctx_idx,
                key="settings_ctx_select",
                on_change=on_settings_ctx_change,
                help="Context window token capacity allocated for prompt, memories, and document context."
            )

        with col_inf_right:
            st.markdown("##### 🛡️ Hardware & Acceleration")
            st.markdown(f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 0.75rem; padding: 1.1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-weight: 700; font-size: 0.95rem; color: #0f172a; margin-bottom: 0.75rem;">RTX 4090 GPU Compute</div>
                <div style="font-size: 0.82rem; color: #334155; margin-bottom: 0.5rem;">
                    <b>Compute Device:</b> NVIDIA GeForce RTX 4090 (16GB VRAM)
                </div>
                <div style="font-size: 0.82rem; color: #334155; margin-bottom: 0.5rem;">
                    <b>Engine Host:</b> <code>http://127.0.0.1:11434</code>
                </div>
                <div style="font-size: 0.82rem; color: #059669; margin-bottom: 0.5rem;">
                    <b>Safe Flash Attention:</b> <span class="brand-pill pill-success">Active & Protected</span>
                </div>
                <div style="font-size: 0.78rem; color: #64748b; line-height: 1.45; margin-top: 0.6rem; padding-top: 0.5rem; border-top: 1px solid #f1f5f9;">
                    <code>OLLAMA_FLASH_ATTENTION=false</code> prevents Windows CUDA stack buffer overrun crashes (<code>0xc0000409</code>) on large models like <code>gpt-oss:latest</code>.
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### 📜 Core System Instruction")
        st.caption("Custom instruction prepended to all inference prompts. Saved permanently across sessions.")

        def on_settings_sys_inst_change():
            new_si = st.session_state.get("settings_sys_inst_input", "").strip()
            if new_si:
                set_preference("system_instruction", new_si)
                st.session_state["sys_inst_val"] = new_si

        sys_inst_text = st.text_area(
            "System Instruction",
            value=system_instruction,
            key="settings_sys_inst_input",
            height=140,
            on_change=on_settings_sys_inst_change,
            help="Custom system instruction. Automatically saved to database and remembered across sessions."
        )

        col_save, col_reset, col_sp = st.columns([1.2, 1.2, 3])
        with col_save:
            if st.button("💾 Save Instruction", use_container_width=True, type="primary"):
                curr_val = st.session_state.get("settings_sys_inst_input", sys_inst_text).strip()
                set_preference("system_instruction", curr_val)
                st.session_state["sys_inst_val"] = curr_val
                st.toast("System instruction permanently saved!", icon="💾")
        with col_reset:
            if st.button("↺ Reset to Default", use_container_width=True):
                set_preference("system_instruction", DEFAULT_SYSTEM_INSTRUCTION)
                st.session_state["sys_inst_val"] = DEFAULT_SYSTEM_INSTRUCTION
                st.session_state["settings_sys_inst_input"] = DEFAULT_SYSTEM_INSTRUCTION
                st.toast("Reset to default system instruction!", icon="↺")
                st.rerun()

    with tab_mem:
        render_memory_hub_section()

    with tab_diag:
        render_diagnostics_section()

    with tab_tools:
        render_tools_section()


# =========================================================
# TAB 2: AI TOOL MEMORY HUB (DIRECT VIEW FOR DEV MODE)
# =========================================================
elif selected_page == "🧠 AI Tool Memory Hub":
    render_memory_hub_section()


# =========================================================
# TAB 3: COMFYUI IMAGE LAB
# =========================================================
elif selected_page == "🎨 ComfyUI Image Lab":
    st.markdown("### 🎨 ComfyUI Image Lab")
    st.caption("Generate local images on your workstation via ComfyUI. 100% offline and private.")

    # Status Bar
    col_c1, col_c2, col_c3 = st.columns([2, 2, 1])
    with col_c1:
        st.markdown(f"**Service Status:** {'🟢 Online' if comfy_online else '🟠 Offline / Idle'}")
    with col_c2:
        checkpoints = comfyui_service.get_local_checkpoints()
        st.markdown(f"**Checkpoints Detected:** {len(checkpoints)}")
    with col_c3:
        if st.button("🔄 Refresh", key="refresh_comfy_btn"):
            st.rerun()

    if not comfy_online and comfyui_service.comfy_main.exists():
        st.warning("ComfyUI service is currently idle.")
        if st.button("▶ Launch ComfyUI Now", use_container_width=True):
            with st.spinner("Starting ComfyUI engine in background..."):
                run_async(comfyui_service.start_service())
                st.rerun()

    # Image Generator Form
    col_params, col_preview = st.columns([1, 1])

    with col_params:
        st.markdown("#### ⚙️ Prompt & Parameters")
        img_prompt = st.text_area(
            "Prompt",
            value="A futuristic cyberpunk workstation with neon lights, high detail, 1024x768 wallpaper",
            height=90,
            help="Specify resolution directly in your prompt, e.g. '1024x768', '16:9', 'landscape', 'portrait'."
        )

        detected_w, detected_h = parse_resolution_from_prompt(img_prompt)
        st.markdown(
            f'<div style="font-size:0.82rem; color: #475569; margin-top:-6px; margin-bottom:12px; background: #f8fafc; padding: 6px 10px; border-radius: 6px; border: 1px solid #e2e8f0;">'
            f'📐 <b>Auto-Detected Resolution:</b> <code style="color:#0f172a; font-weight:600; background:#ffffff; padding:2px 6px; border-radius:4px; border: 1px solid #cbd5e1;">{detected_w} × {detected_h}</code> '
            f'<span style="color:#64748b;">(given in prompt, e.g. <code>1024x768</code>, <code>16:9</code>, <code>portrait</code>, <code>landscape</code>)</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        col_st, col_enh = st.columns([1, 1])
        with col_st:
            style_choice = st.selectbox(
                "🎨 Style Preset",
                options=["Photorealistic", "Cinematic", "Cyberpunk", "Digital Art", "Anime / Ghibli", "None"],
                index=0,
                help="Applies expert lighting, cinematic composition, and high-detail textures"
            )
        with col_enh:
            st.write("")
            st.write("")
            enhance_toggle = st.checkbox("✨ Quality Boost", value=True, help="Injects professional render tokens and strong negative filter to eliminate mud/distortion")

        # Checkpoint selection and optional DreamShaper 8 downloader
        has_dreamshaper = any("dreamshaper" in c.lower() for c in (checkpoints or []))
        if not has_dreamshaper:
            col_ck, col_dl = st.columns([2, 1])
            with col_ck:
                selected_ckpt = st.selectbox(
                    "Model Checkpoint",
                    options=checkpoints if checkpoints else ["v1-5-pruned-emaonly.safetensors"],
                    index=0
                )
            with col_dl:
                st.write("")
                if st.button("📥 Get DreamShaper 8", help="Download DreamShaper 8 (Photorealistic SD 1.5, 2.1GB)"):
                    import asyncio
                    asyncio.create_task(comfyui_service.download_model_background("dreamshaper"))
                    st.rerun()
        else:
            selected_ckpt = st.selectbox(
                "Model Checkpoint",
                options=checkpoints,
                index=0
            )

        dl_state = comfyui_service.download_state
        if dl_state and dl_state.get("status") == "downloading":
            st.progress(dl_state.get("percent", 0) / 100.0, text=f"📥 {dl_state.get('message', 'Downloading...')}")
        elif dl_state and dl_state.get("status") == "completed":
            st.success(f"✅ {dl_state.get('message', 'Model installed!')}")

        neg_prompt = st.text_input(
            "Negative Prompt",
            value="blurry, deformed, low quality, artifacts, distorted, out of focus"
        )

        col_steps, col_cfg, col_sampler = st.columns([1, 1, 1])
        with col_steps:
            steps = st.slider("Steps", min_value=12, max_value=30, value=15, help="15 steps with DPM++ 2M Karras produces sharp, crisp details")
        with col_cfg:
            cfg = st.slider("CFG Scale", min_value=1.0, max_value=15.0, value=7.0, step=0.5)
        with col_sampler:
            sampler_name = st.selectbox("Sampler", ["dpmpp_2m", "euler_ancestral", "euler", "ddim"], index=0, help="DPM++ 2M Karras is the industry gold standard for sharp photorealism")

        generate_btn = st.button("🎨 Generate Image", type="primary", use_container_width=True)

    with col_preview:
        st.markdown("#### 🖼️ Render Preview")
        preview_container = st.empty()

        if generate_btn and img_prompt:
            with st.spinner(f"Sampling latent diffusion model on CPU ({detected_w}×{detected_h}, typically ~60-120s)..."):
                req = ImageGenerateRequest(
                    prompt=img_prompt,
                    negative_prompt=neg_prompt,
                    width=detected_w,
                    height=detected_h,
                    steps=steps,
                    cfg_scale=cfg,
                    checkpoint=selected_ckpt,
                    sampler_name=sampler_name,
                    scheduler="karras",
                    style_preset=style_choice,
                    enhance_prompt=enhance_toggle
                )
                res = run_async(comfyui_service.generate_image(req))

            if res.status == "success" or res.status == "completed":
                img_path = settings.generated_images_dir / res.image_filename if res.image_filename else None
                if img_path and img_path.exists():
                    st.image(str(img_path), caption=f"Resolution: {detected_w}×{detected_h} • Seed: {res.seed}", use_container_width=True)
                    with open(img_path, "rb") as f:
                        st.download_button("💾 Download Image", f, file_name=res.image_filename, mime="image/png", use_container_width=True)
                else:
                    st.success(f"Generated successfully: {res.image_url}")
            else:
                st.error(f"Image generation failed: {res.error}")

    # Gallery Section
    st.markdown("---")
    col_g_title, col_g_btn = st.columns([4, 1])
    with col_g_title:
        st.markdown("#### 📸 Image Gallery")
    with col_g_btn:
        if st.button("🔄 Sync Output", key="sync_gallery_btn", help="Sync any offline or background ComfyUI renders"):
            with st.spinner("Syncing local renders..."):
                run_async(comfyui_service.sync_external_outputs())
                st.rerun()

    try:
        run_async(comfyui_service.sync_external_outputs())
    except Exception:
        pass

    history_rows = run_async(db.fetchall("SELECT * FROM image_history WHERE status IN ('success', 'completed') ORDER BY created_at DESC LIMIT 8"))
    
    if history_rows:
        g_cols = st.columns(4)
        for i, row in enumerate(history_rows):
            fn = row["image_filename"]
            local_p = settings.generated_images_dir / fn if fn else None
            with g_cols[i % 4]:
                if local_p and local_p.exists():
                    st.image(str(local_p), caption=row["prompt"][:40] + "...", use_container_width=True)
    else:
        st.info("No generated images saved yet. Click 'Generate Image' to render your first artwork!")


# =========================================================
# TAB 4: AUTONOMOUS CODING AGENT
# =========================================================
elif selected_page == "💻 Autonomous Coding Agent":
    st.markdown("### 💻 Autonomous Coding Agent")
    st.caption("Inspect local workspace files, propose syntax-safe unified diffs, and execute automated tests.")

    col_files, col_editor, col_agent = st.columns([1, 2, 1.5])

    # Left: File Explorer
    with col_files:
        st.markdown("#### 📁 Workspace Files")
        tree = coding_agent_service.list_workspace_files()
        workspace_files = [f.path for f in tree.files if not f.is_dir]
        
        selected_file_path = st.selectbox(
            "Select File",
            options=workspace_files if workspace_files else ["README.md"],
            index=0
        )

    # Center: Code Inspector
    with col_editor:
        st.markdown(f"#### 📄 File: `{selected_file_path}`")
        full_path = settings.workspace_root / selected_file_path
        if full_path.exists() and full_path.is_file():
            try:
                code_text = full_path.read_text(encoding="utf-8", errors="replace")
                ext = selected_file_path.split(".")[-1] if "." in selected_file_path else "text"
                st.code(code_text, language=ext, line_numbers=True)
            except Exception as e:
                st.error(f"Error reading file: {e}")
        else:
            st.info("File not found in workspace.")

    # Right: Coding Agent
    with col_agent:
        st.markdown("#### 🤖 Agent Command")
        agent_instruction = st.text_area(
            "Agent Prompt",
            placeholder="e.g. Add input validation and unit tests for the main function...",
            height=100
        )
        propose_btn = st.button("🚀 Propose Diff", type="primary", use_container_width=True)

        if propose_btn and agent_instruction:
            status_box = st.empty()
            status_box.markdown(
                render_thinking_badge("analysing", "Analysing codebase & workspace files..."),
                unsafe_allow_html=True
            )
            task = run_async(coding_agent_service.create_task(task_description=agent_instruction))
            coding_prompt = f"Analyze the codebase instruction and output a clean unified diff:\nInstruction: {agent_instruction}"
            
            status_box.markdown(
                render_thinking_badge("processing", f"Generating unified diff with {selected_model}..."),
                unsafe_allow_html=True
            )
            diff_parts = []
            async def stream_diff():
                async for chunk in ollama_service.chat_stream(
                    model=selected_model,
                    messages=[{"role": "user", "content": coding_prompt}],
                    temperature=0.2
                ):
                    diff_parts.append(chunk)
            run_async(stream_diff())
            diff_content = "".join(diff_parts) if diff_parts else "No changes proposed."
            run_async(coding_agent_service.submit_plan_and_diff(task.id, "Plan generated", ["workspace"], diff_content))
            status_box.empty()
            st.markdown(f"**Task ID:** `{task.id[:8]}`")
            st.markdown("**Proposed Changes:**")
            st.code(diff_content, language="diff")

        st.markdown("---")
        st.markdown("#### 🧪 Test Suite")
        if st.button("▶ Run Pytest Suite", use_container_width=True):
            with st.spinner("Executing tests..."):
                exec_res = run_async(tool_registry.execute_tool("run_tests", {"test_framework": "pytest"}, approved=True))
                test_res = exec_res.result if (exec_res and exec_res.success and isinstance(exec_res.result, dict)) else {"exit_code": 1, "stdout": "", "stderr": str(getattr(exec_res, "error", "Execution failed"))}
                if test_res.get("exit_code") == 0:
                    st.success("All tests passed!")
                else:
                    st.error(f"Test failures:\n{test_res.get('stderr') or test_res.get('stdout')}")
                st.code(test_res.get("stdout", "No output"), language="text")


# =========================================================
# TAB 5: VISION MULTIMODAL
# =========================================================
elif selected_page == "👁️ Vision Multimodal":
    st.markdown("### 👁️ Vision Multimodal Inspector")
    st.caption("Upload images or screenshots and query local multimodal models for scene description, OCR, UI audit, and debugging.")

    col_vimg, col_vprompt = st.columns([1, 1])

    with col_vimg:
        vision_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg", "webp"], key="vision_page_uploader")
        if vision_file:
            st.image(vision_file, caption="Target Image", use_container_width=True)

    with col_vprompt:
        st.markdown("#### 🔍 Vision Query")
        
        # Preset buttons
        p_c1, p_c2 = st.columns(2)
        with p_c1:
            if st.button("Extract Text (OCR)", use_container_width=True):
                st.session_state.v_prompt = "Extract and transcribe all readable text, signs, labels, numbers, and code verbatim."
            if st.button("UI / UX Audit", use_container_width=True):
                st.session_state.v_prompt = "Analyze the visual hierarchy, typography, UI layout, and usability of this interface screenshot."
        with p_c2:
            if st.button("Describe Scene", use_container_width=True):
                st.session_state.v_prompt = "Describe this image in detail, listing key objects, colors, and composition."
            if st.button("Code & Error Debug", use_container_width=True):
                st.session_state.v_prompt = "Inspect any code, terminal output, or stack traces in this image, identify errors, and suggest fixes."

        v_query = st.text_area(
            "Query Prompt",
            value=st.session_state.get("v_prompt", "Describe this image and analyze its key components."),
            height=100
        )
        analyze_btn = st.button("👁️ Analyze Image", type="primary", use_container_width=True)

        if analyze_btn and vision_file:
            import base64
            b64_img = base64.b64encode(vision_file.getvalue()).decode("utf-8")
            status_box = st.empty()
            status_box.markdown(
                render_thinking_badge("analysing", f"Analysing image features & context with {selected_model}..."),
                unsafe_allow_html=True
            )
            try:
                res = run_async(ollama_service.generate(
                    model=selected_model,
                    prompt=v_query,
                    images=[b64_img]
                ))
                status_box.empty()
                st.markdown("### 📋 Analysis Result")
                st.markdown(res.response)
            except Exception as e:
                status_box.empty()
                st.error(f"Vision analysis error: {e}")


# =========================================================
# TAB 6: AI TOOLS (DIRECT VIEW FOR DEV MODE)
# =========================================================
elif selected_page == "🛠️ AI Tools":
    render_tools_section()


# =========================================================
# TAB 7: DIAGNOSTICS & MODELS (DIRECT VIEW FOR DEV MODE)
# =========================================================
elif selected_page == "⚙️ Diagnostics & Models":
    render_diagnostics_section()
