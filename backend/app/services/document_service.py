"""
Document and Multi-file Processing Service.
Supports extracting text and metadata from PDFs, Word (.docx), source code, data tables, and images.
Allows uploading multiple files (up to 5 at once) for local LLM analysis (e.g. Resume vs JD).
"""

import io
import base64
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional


def extract_file_data(filename: str, file_bytes: bytes) -> Dict[str, Any]:
    """
    Extracts text content or image encoding from uploaded files.
    Supports PDF, DOCX, Code, CSV, JSON, Markdown, and Images.
    """
    ext = Path(filename).suffix.lower()
    size_kb = round(len(file_bytes) / 1024, 1)

    # 1. Image Files (Vision / Multimodal)
    if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]:
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        mime = "image/png" if ext == ".png" else "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/webp" if ext == ".webp" else "image/png"
        return {
            "name": filename,
            "type": "image",
            "ext": ext,
            "size_kb": size_kb,
            "data_uri": f"data:{mime};base64,{b64}",
            "raw_b64": b64,
            "text": ""
        }

    # 2. PDF Documents
    elif ext == ".pdf":
        try:
            import pymupdf
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            pages = []
            for i, p in enumerate(doc):
                t = p.get_text().strip()
                if t:
                    pages.append(f"[Page {i+1}]\n{t}")
            text = "\n\n".join(pages).strip()
        except Exception as e:
            text = f"[Error reading PDF {filename}: {e}]"
        return {
            "name": filename,
            "type": "document",
            "ext": ext,
            "size_kb": size_kb,
            "text": text
        }

    # 3. Microsoft Word Documents (.docx / .doc)
    elif ext in [".docx", ".doc"]:
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            parts = [p.text for p in doc.paragraphs if p.text.strip()]
            for tbl in doc.tables:
                for row in tbl.rows:
                    row_t = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                    if row_t:
                        parts.append(row_t)
            text = "\n".join(parts).strip()
        except Exception as e:
            text = f"[Error reading Word document {filename}: {e}]"
        return {
            "name": filename,
            "type": "document",
            "ext": ext,
            "size_kb": size_kb,
            "text": text
        }

    # 4. Text, Code, CSV, JSON, Markdown, Configs
    else:
        try:
            text = file_bytes.decode("utf-8")
        except Exception:
            text = file_bytes.decode("latin-1", errors="replace")
        return {
            "name": filename,
            "type": "text",
            "ext": ext,
            "size_kb": size_kb,
            "text": text
        }


def process_uploaded_files(files_list: List[Any], max_files: int = 5) -> Dict[str, Any]:
    """
    Processes up to max_files uploaded files.
    Returns structured data for chat rendering, persistent saving, and LLM context.
    """
    capped_files = files_list[:max_files]
    processed = []
    attached_images_b64 = []
    raw_images_b64 = []
    attached_docs_context = []
    attached_file_pills = []

    for f in capped_files:
        fname = getattr(f, "name", "file")
        if hasattr(f, "getvalue"):
            fbytes = f.getvalue()
        elif hasattr(f, "read"):
            fbytes = f.read()
        elif isinstance(f, bytes):
            fbytes = f
        else:
            fbytes = b""

        fdata = extract_file_data(fname, fbytes)
        processed.append(fdata)

        if fdata["type"] == "image":
            attached_images_b64.append(fdata["data_uri"])
            raw_images_b64.append(fdata["raw_b64"])
            attached_file_pills.append(f"🖼️ `{fdata['name']}` ({fdata['size_kb']} KB)")
        else:
            doc_text = fdata["text"]
            attached_docs_context.append(
                f"--- START OF ATTACHED FILE: {fdata['name']} (Size: {fdata['size_kb']} KB) ---\n"
                f"{doc_text}\n"
                f"--- END OF ATTACHED FILE: {fdata['name']} ---"
            )
            attached_file_pills.append(f"📄 `{fdata['name']}` ({fdata['size_kb']} KB)")

    pills_summary = ""
    if attached_file_pills:
        pills_str = " • ".join(attached_file_pills)
        pills_summary = f"📎 **Attached Files ({len(attached_file_pills)}/{max_files}):** {pills_str}"

    collapsible_html = ""
    if attached_docs_context:
        collapsible_html = (
            f"\n\n<details><summary>📄 <i>View attached document contents ({len(attached_docs_context)} file(s))</i></summary>\n\n"
            + "\n\n".join(attached_docs_context)
            + "\n\n</details>"
        )

    context_prompt_block = ""
    if attached_docs_context:
        context_prompt_block = (
            f"### Attached Context Documents ({len(attached_docs_context)} file(s)):\n\n"
            + "\n\n".join(attached_docs_context)
            + "\n\n---\n"
        )

    return {
        "processed_files": processed,
        "attached_images_b64": attached_images_b64,
        "raw_images_b64": raw_images_b64,
        "attached_docs_context": attached_docs_context,
        "attached_file_pills": attached_file_pills,
        "pills_summary": pills_summary,
        "collapsible_html": collapsible_html,
        "context_prompt_block": context_prompt_block,
        "total_files": len(processed)
    }
