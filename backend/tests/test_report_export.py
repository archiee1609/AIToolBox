import pytest
from app.services.report_export_service import (
    parse_markdown_report,
    generate_pdf_bytes,
    generate_docx_bytes,
    generate_xlsx_bytes,
    generate_pptx_bytes,
    generate_html_bytes,
    export_report_bundle,
    sanitize_filename
)

SAMPLE_REPORT_MD = """## 📄 Executive Architecture & Performance Assessment

---

# Executive Summary
The Local AI Workbench architecture delivers low-latency private AI execution on local client hardware.

# System Architecture
The system consists of three interconnected layers:
- Core FastAPI REST Backend
- Dynamic Hardware Governor & Load Balancer
- Streamlit All-in-One Studio UI

# Performance Metrics
| Component | Metric | Target | Status |
| --- | --- | --- | --- |
| Ollama Inference | 45 tokens/sec | > 30 tps | Optimal |
| ComfyUI Generation | 4.2 sec/image | < 6 sec | Optimal |
| Database Operations | 1.2 ms | < 5 ms | Optimal |

# Actionable Recommendations
1. Scale context memory automatically according to dynamic VRAM headroom.
2. Enable multi-vendor hardware acceleration for NVIDIA, AMD, Intel, and Apple Silicon.
3. Provide one-click multi-format exports for executive review.
"""


def test_sanitize_filename():
    assert sanitize_filename("Report: Top 10 Features?") == "Report_Top_10_Features"
    assert sanitize_filename("## 📄 Quarterly Analysis") == "Quarterly_Analysis"


def test_parse_markdown_report():
    data = parse_markdown_report(SAMPLE_REPORT_MD)
    assert data["title"] == "Executive Architecture & Performance Assessment"
    assert len(data["sections"]) >= 4
    
    # Check tables parsed
    perf_sec = next((s for s in data["sections"] if s["heading"] == "Performance Metrics"), None)
    assert perf_sec is not None
    assert len(perf_sec["tables"]) == 1
    assert len(perf_sec["tables"][0]) >= 3


def test_generate_pdf_bytes():
    data = parse_markdown_report(SAMPLE_REPORT_MD)
    pdf = generate_pdf_bytes(data)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 500
    assert pdf.startswith(b"%PDF")


def test_generate_docx_bytes():
    data = parse_markdown_report(SAMPLE_REPORT_MD)
    docx = generate_docx_bytes(data)
    assert isinstance(docx, bytes)
    assert len(docx) > 500
    # ZIP signature for docx
    assert docx.startswith(b"PK")


def test_generate_xlsx_bytes():
    data = parse_markdown_report(SAMPLE_REPORT_MD)
    xlsx = generate_xlsx_bytes(data)
    assert isinstance(xlsx, bytes)
    assert len(xlsx) > 500
    # ZIP signature for xlsx
    assert xlsx.startswith(b"PK")


def test_generate_pptx_bytes():
    data = parse_markdown_report(SAMPLE_REPORT_MD)
    pptx = generate_pptx_bytes(data)
    assert isinstance(pptx, bytes)
    assert len(pptx) > 500
    # ZIP signature for pptx
    assert pptx.startswith(b"PK")


def test_generate_html_bytes():
    data = parse_markdown_report(SAMPLE_REPORT_MD)
    html_b = generate_html_bytes(data)
    assert isinstance(html_b, bytes)
    assert b"Executive Architecture" in html_b
    assert b"<table class='report-table'>" in html_b


def test_export_report_bundle():
    bundle = export_report_bundle(SAMPLE_REPORT_MD)
    for fmt in ["pdf", "docx", "xlsx", "pptx", "md", "html"]:
        assert fmt in bundle
        assert "bytes" in bundle[fmt]
        assert len(bundle[fmt]["bytes"]) > 0
        assert "filename" in bundle[fmt]
        assert bundle[fmt]["filename"].endswith(f".{fmt}")
