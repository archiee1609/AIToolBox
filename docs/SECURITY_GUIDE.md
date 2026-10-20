# Security & Permission Controls Guide

## Architectural Security Principles
Local AI Workbench is built on a "local-first, security-in-depth" architecture. All security decisions and file boundaries are enforced strictly by the backend authority, never trusted to AI prompts or frontend logic alone.

---

## 1. Loopback Network Binding
* The application server binds exclusively to `127.0.0.1`.
* It does not expose administrative ports, static file directories, or SQLite databases to the local area network (LAN) or external internet by default.
* Cross-Origin Resource Sharing (CORS) is restricted to loopback origins.

---

## 2. Workspace Sandboxing & Path Traversal Prevention
* File operations (read, write, search, diff, patch) are strictly confined to the authorized workspace root:
  ```
  AIToolBox/workspace/
  ```
* All incoming paths undergo canonical resolution using `os.path.realpath` and `Path.resolve()`.
* The security manager enforces:
  - Strict prefix checking against the resolved workspace root.
  - Rejection of parent directory traversal attempts (`../` or `..\\`).
  - Detection and rejection of null-byte poison attacks (`\0`).
  - Validation of maximum file size limits (default 25MB) to protect against denial-of-service / memory exhaustion.

---

## 3. Centralized Controlled Command Runner
Model-generated terminal commands or scripts are never executed arbitrarily or with elevated permissions.
All commands pass through `run_command_safely`:
* **Non-elevated**: The process never runs with Administrator / RunAs privileges.
* **Workspace CWD**: Commands can only execute with a working directory strictly inside the authorized workspace.
* **Command Blocklist**: Automatically detects and blocks dangerous system commands (e.g. `format`, `diskpart`, `bcdedit`, `shutdown`, `reg delete`, `takeown`, `icacls`, fork bombs).
* **Execution Timeouts**: Enforces hard execution timeouts (default 60s) to prevent runaway or hanging processes.
* **Audit Trail**: Every executed command, working directory, exit code, stdout, stderr, and duration is logged to `command_audit_log` in SQLite.

---

## 4. Privacy & External Network Access
* By default, `enable_web_search` is set to `False`.
* Private local documents, source code, and prompts are never sent to external cloud APIs or third-party search engines without explicit user enablement in Settings.
