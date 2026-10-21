#!/usr/bin/env bash
# ========================================================
#       LOCAL AI WORKBENCH - INSTALLATION SCRIPT
#       Supports macOS (Apple Silicon & Intel) & Linux
# ========================================================

set -e

# Determine repository root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

echo "========================================================"
echo "       LOCAL AI WORKBENCH - INSTALLATION SCRIPT         "
echo "========================================================"
echo ""

# 1. Detect Operating System
OS_TYPE="$(uname -s)"
case "${OS_TYPE}" in
    Darwin*)  PLATFORM="macOS" ;;
    Linux*)   PLATFORM="Linux" ;;
    *)        PLATFORM="Unknown (${OS_TYPE})" ;;
esac
echo "[*] Detected Platform: ${PLATFORM} ($(uname -m))"
echo ""

# 2. Check Python installation
echo "[1/4] Checking Python 3 installation..."
PYTHON_BIN=""
for cmd in python3 python; do
    if command -v "${cmd}" >/dev/null 2>&1; then
        PY_VER=$("${cmd}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        PY_MAJOR=$("${cmd}" -c 'import sys; print(sys.version_info.major)')
        PY_MINOR=$("${cmd}" -c 'import sys; print(sys.version_info.minor)')
        if [ "${PY_MAJOR}" -eq 3 ] && [ "${PY_MINOR}" -ge 10 ]; then
            PYTHON_BIN="${cmd}"
            echo "[+] Found compatible Python: $("${cmd}" --version) (${PYTHON_BIN})"
            break
        fi
    fi
done

if [ -z "${PYTHON_BIN}" ]; then
    echo "[ERROR] Python 3.10+ is required but was not found."
    if [ "${PLATFORM}" = "macOS" ]; then
        echo "Install via Homebrew: brew install python@3.11"
    else
        echo "Install via apt: sudo apt update && sudo apt install -y python3 python3-pip python3-venv"
    fi
    exit 1
fi

# 3. Setup Virtual Environment (Recommended for isolation)
VENV_DIR="${ROOT_DIR}/.venv"
if [ ! -d "${VENV_DIR}" ]; then
    echo "[*] Creating Python virtual environment in .venv..."
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

# Activate virtualenv
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
echo "[+] Active Python environment: $(which python)"

# 4. Install Backend Dependencies
echo ""
echo "[2/4] Installing backend Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -r "${ROOT_DIR}/backend/requirements.txt"

# 5. Check Node.js and Frontend Build
echo ""
echo "[3/4] Checking Node.js for Web UI..."
if command -v npm >/dev/null 2>&1 && [ -f "${ROOT_DIR}/frontend/package.json" ]; then
    echo "[*] Building frontend assets..."
    cd "${ROOT_DIR}/frontend"
    npm install --no-audit --no-fund
    npm run build || echo "[!] Notice: Frontend build skipped or had warnings."
    cd "${ROOT_DIR}"
else
    echo "[i] Node.js/npm not found or optional. Streamlit UI (streamlit_app.py) is ready to use directly!"
fi

# 6. Check Ollama Installation
echo ""
echo "[4/4] Verifying Ollama installation..."
if command -v ollama >/dev/null 2>&1 || [ -f "/opt/homebrew/bin/ollama" ] || [ -f "/usr/local/bin/ollama" ] || [ -f "/Applications/Ollama.app/Contents/Resources/ollama" ]; then
    echo "[+] Ollama is detected on this system!"
else
    echo "[!] Ollama was not found in your PATH."
    if [ "${PLATFORM}" = "macOS" ]; then
        echo "    Install Ollama for macOS:"
        echo "    1. Download from https://ollama.com/download/mac"
        echo "    or run: brew install ollama"
    else
        echo "    Install Ollama for Linux:"
        echo "    curl -fsSL https://ollama.com/install.sh | sh"
    fi
fi

echo ""
echo "========================================================"
echo "               INSTALLATION COMPLETE!                   "
echo "========================================================"
echo "To start the application, run:"
echo "  ./scripts/start_streamlit.sh   (for All-in-One Studio UI)"
echo "  or: ./scripts/start.sh         (for FastAPI + Web UI)"
echo "========================================================"
