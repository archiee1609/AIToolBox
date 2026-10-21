import pytest
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    if "application/json" in res.headers.get("content-type", ""):
        data = res.json()
        assert data["app"] == "Local AI Workbench"
    else:
        assert "<html" in res.text.lower()

def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "ollama" in data
    assert "comfyui" in data
    assert "database" in data
    assert "workspace" in data

def test_tools_listing():
    res = client.get("/api/tools")
    assert res.status_code == 200
    tools = res.json()
    assert isinstance(tools, list)
    tool_names = [t["name"] for t in tools]
    assert "calculator" in tool_names
    assert "read_workspace_file" in tool_names
    assert "write_workspace_file" in tool_names

def test_conversation_crud():
    # Create conversation
    create_res = client.post("/api/chat/conversations", json={
        "title": "API Test Conversation",
        "model": "gemma4:12b",
        "system_prompt": "You are a test assistant."
    })
    assert create_res.status_code == 200
    conv = create_res.json()
    conv_id = conv["id"]
    assert conv["title"] == "API Test Conversation"

    # Fetch conversation
    get_res = client.get(f"/api/chat/conversations/{conv_id}")
    assert get_res.status_code == 200
    assert get_res.json()["conversation"]["id"] == conv_id

    # Update conversation
    patch_res = client.patch(f"/api/chat/conversations/{conv_id}", json={
        "title": "Updated Title"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Updated Title"

    # Delete conversation
    del_res = client.delete(f"/api/chat/conversations/{conv_id}")
    assert del_res.status_code == 200

def test_coding_workspace_tree():
    res = client.get("/api/coding/workspace/tree")
    assert res.status_code == 200
    data = res.json()
    assert "workspace_root" in data
    assert isinstance(data["files"], list)

def test_automation_workflows():
    res = client.get("/api/automation/workflows")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_settings_endpoint():
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "ollama_base_url" in data
    assert "workspace_root" in data

def test_ollama_pull_endpoint_validation():
    # Attempting to pull without a model name should return 400 Bad Request
    res = client.post("/api/ollama/pull", json={"name": ""})
    assert res.status_code == 400

def test_reports_endpoint_validation():
    # Attempting to generate a report without a title should return 422 Unprocessable Entity
    res = client.post("/api/reports/generate", json={})
    assert res.status_code == 422


def test_reports_export_endpoint():
    md_content = "# Quarterly Review\n\n## Performance\n- Speed: 100%\n- Reliability: 99.9%"
    
    # PDF export
    res_pdf = client.post("/api/reports/export", json={"markdown": md_content, "title": "Quarterly Review", "format": "pdf"})
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in res_pdf.headers["content-disposition"]
    assert len(res_pdf.content) > 500

    # Word export
    res_docx = client.post("/api/reports/export", json={"markdown": md_content, "title": "Quarterly Review", "format": "docx"})
    assert res_docx.status_code == 200
    assert "wordprocessingml" in res_docx.headers["content-type"]
    assert len(res_docx.content) > 500

    # Excel export
    res_xlsx = client.post("/api/reports/export", json={"markdown": md_content, "title": "Quarterly Review", "format": "xlsx"})
    assert res_xlsx.status_code == 200
    assert "spreadsheetml" in res_xlsx.headers["content-type"]
    assert len(res_xlsx.content) > 500

    # PPTX export
    res_pptx = client.post("/api/reports/export", json={"markdown": md_content, "title": "Quarterly Review", "format": "pptx"})
    assert res_pptx.status_code == 200
    assert "presentationml" in res_pptx.headers["content-type"]
    assert len(res_pptx.content) > 500

    # ZIP bundle export
    res_zip = client.post("/api/reports/export", json={"markdown": md_content, "title": "Quarterly Review", "format": "zip"})
    assert res_zip.status_code == 200
    assert res_zip.headers["content-type"] == "application/zip"
    assert len(res_zip.content) > 1000


def test_reports_bundle_endpoint():
    md_content = "# Architecture Audit\n\n## Findings\n- Low latency\n- Private offline execution"
    res = client.post("/api/reports/bundle", json={"markdown": md_content, "title": "Architecture Audit"})
    assert res.status_code == 200
    data = res.json()
    assert "formats" in data
    assert "pdf" in data["formats"]
    assert "docx" in data["formats"]
    assert "xlsx" in data["formats"]
    assert "pptx" in data["formats"]
    assert "zip" in data["formats"]
    assert data["formats"]["pdf"]["available"] is True

def test_parse_resolution_from_prompt():
    from app.services.comfyui_service import parse_resolution_from_prompt
    assert parse_resolution_from_prompt("A futuristic workstation 1024x768 with neon lights") == (1024, 768)
    assert parse_resolution_from_prompt("A workstation with 1024 x 768 resolution") == (1024, 768)
    assert parse_resolution_from_prompt("cyberpunk city width: 1024, height: 768") == (1024, 768)
    assert parse_resolution_from_prompt("mountain view, 16:9") == (896, 512)
    assert parse_resolution_from_prompt("robot portrait, 9:16") == (512, 896)
    assert parse_resolution_from_prompt("photo of a warrior, portrait") == (512, 768)
    assert parse_resolution_from_prompt("medieval castle landscape") == (768, 512)
    assert parse_resolution_from_prompt("cute kitten") == (512, 512)
    # 8K UHD and 8K direct dimensions
    assert parse_resolution_from_prompt("A majestic eagle in 8K UHD resolution") == (7680, 4320)
    assert parse_resolution_from_prompt("Sci-fi landscape 7680x4320 wallpaper") == (7680, 4320)
    assert parse_resolution_from_prompt("Anime character 8K portrait") == (4320, 7680)
    assert parse_resolution_from_prompt("Iconic logo 8192x8192") == (8192, 8192)
    # 4K UHD
    assert parse_resolution_from_prompt("Hyper-realistic jungle in 4K") == (3840, 2160)


def test_image_generate_request_supports_8k_and_4k():
    from app.schemas.image import ImageGenerateRequest
    # 4K portrait (from user report)
    req_4k = ImageGenerateRequest(prompt="random GTA V wallpaper", width=2160, height=3840)
    assert req_4k.width == 2160
    assert req_4k.height == 3840

    # 8K Ultra HD
    req_8k = ImageGenerateRequest(prompt="epic landscape", width=7680, height=4320)
    assert req_8k.width == 7680
    assert req_8k.height == 4320

    # 8K Full Square
    req_8k_sq = ImageGenerateRequest(prompt="square banner", width=8192, height=8192)
    assert req_8k_sq.width == 8192
    assert req_8k_sq.height == 8192


