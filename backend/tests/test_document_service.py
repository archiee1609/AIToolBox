import io
import pytest
from app.services.document_service import extract_file_data, process_uploaded_files


def test_extract_pdf():
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((50, 72), "John Doe Resume\nSkills: Python, Ollama, PyTorch")
    pdf_bytes = doc.tobytes()

    res = extract_file_data("resume.pdf", pdf_bytes)
    assert res["type"] == "document"
    assert "John Doe Resume" in res["text"]
    assert "Python, Ollama" in res["text"]
    assert res["size_kb"] > 0


def test_extract_docx():
    docx = pytest.importorskip("docx")
    d = docx.Document()
    d.add_paragraph("Job Description: Senior AI Engineer")
    tbl = d.add_table(rows=1, cols=2)
    tbl.rows[0].cells[0].text = "Experience"
    tbl.rows[0].cells[1].text = "5+ years in Python"
    buf = io.BytesIO()
    d.save(buf)

    res = extract_file_data("job_description.docx", buf.getvalue())
    assert res["type"] == "document"
    assert "Senior AI Engineer" in res["text"]
    assert "5+ years in Python" in res["text"]


def test_extract_text_and_code():
    code_bytes = b"def test_app():\n    return 'Hello World'\n"
    res = extract_file_data("test.py", code_bytes)
    assert res["type"] == "text"
    assert "def test_app" in res["text"]


def test_process_multiple_files_and_cap():
    class MockFile:
        def __init__(self, name, content):
            self.name = name
            self.content = content
        def getvalue(self):
            return self.content

    # Create 7 files
    files = [
        MockFile(f"file_{i}.txt", f"Content of file {i}".encode("utf-8"))
        for i in range(7)
    ]

    # Process with max_files=5
    result = process_uploaded_files(files, max_files=5)
    assert result["total_files"] == 5
    assert len(result["attached_file_pills"]) == 5
    assert "file_0.txt" in result["pills_summary"]
    assert "file_4.txt" in result["pills_summary"]
    assert "file_5.txt" not in result["pills_summary"]
    assert len(result["attached_docs_context"]) == 5
