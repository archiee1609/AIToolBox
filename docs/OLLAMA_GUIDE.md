# Ollama Integration Guide

## Overview
Local AI Workbench connects to your locally installed Ollama instance running on `http://127.0.0.1:11434`.

The application dynamically discovers models via the `/api/tags` endpoint and queries `/api/show` for parameter sizes, quantization levels, context lengths, and supported capabilities.

---

## 1. Verifying Ollama Status
Ensure Ollama is running on your machine:
```powershell
ollama --version
```
To test API reachability:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version"
```

---

## 2. Installing Additional LLM Models Directly from the App
Local AI Workbench includes a built-in **Model Manager** to install and manage models directly without using the terminal:

1. Click the **`+ Install Models`** button in the top header, sidebar, or from within the **All-in-One Studio**.
2. **1-Click Popular Models**:
   - `llama3.2` (3B / Ultra-fast, lightweight everyday assistant)
   - `mistral` (7B / High precision reasoning & general tasks)
   - `deepseek-r1:14b` (14B / State-of-the-art chain-of-thought math & logic)
   - `qwen2.5-coder` (7B / Specialized coding & repository development)
   - `phi4` (14B / High-performance compact synthetic reasoning)
   - `llava` (7B / Vision & multimodal image understanding)
3. **Custom Model Input**: Enter any model tag from the [Ollama Library](https://ollama.com/library) (e.g. `gemma:2b`, `llama3:8b`, `codellama`).
4. **Live Download Progress**: The UI streams real-time SSE progress percentage, downloaded MB / total MB, and verification steps.
5. **Disk Management**: Inspect parameter size, quantization level, and disk space for each installed model. Delete unneeded models with one click.

---

## 3. Tested & Preferred Installed Models
The Workbench automatically recognizes your existing models:
* **`gemma4:12b`**:
  - Size: 11.9B parameters (`Q4_K_M` quantization)
  - Context Window: up to 262,144 tokens
  - Capabilities: Full text generation, Vision / visual input, Tool calling, Thinking / reasoning.
* **`gpt-oss:latest`**:
  - Size: 20.9B parameters (`MXFP4` quantization)
  - Context Window: up to 131,072 tokens
  - Capabilities: Text generation, Tool calling, Thinking.

---

## 4. Dynamic Model Switching
1. Open Local AI Workbench in your browser (`http://127.0.0.1:8000`).
2. The **Active Model** dropdown in the header and sidebar displays all installed models.
3. Select any installed model. The selection applies immediately to all subsequent chat prompts, reports, and agent tasks.
4. Model parameters (Temperature, Context Window, System Prompt) can be fine-tuned via the **Sliders** button in the chat header.

---

## 5. Vision & Multimodal Input
* If a model supports vision (e.g. `gemma4:12b`), you can attach images in **All-in-One Studio** or use the dedicated **Vision** workspace.
* If a text-only model (e.g. `gpt-oss:latest`) is selected, the application displays a friendly capability banner with a 1-click button to switch to a vision-capable model.
