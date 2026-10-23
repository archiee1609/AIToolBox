"""
Document and Multi-file Processing Service.
Supports extracting text and metadata from PDFs, Word (.docx), source code, data tables, and images.
Allows uploading multiple files (up to 5 at once) for local LLM analysis (e.g. Resume vs JD).
"""

import io
import base64
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional


class HTMLDiagnosticParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: List[str] = []
        self.skip = False
        self.in_row = False
        self.row_cells: List[str] = []
        self.cell_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: Any):
        tl = tag.lower()
        if tl in ["style", "script", "head", "meta", "svg", "noscript", "link"]:
            self.skip = True
        elif not self.skip:
            if tl in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                self.parts.append("\n\n### ")
            elif tl in ["p", "div", "li", "br"]:
                self.parts.append("\n")
            elif tl == "tr":
                self.in_row = True
                self.row_cells = []
            elif tl in ["td", "th"]:
                self.cell_parts = []

    def handle_endtag(self, tag: str):
        tl = tag.lower()
        if tl in ["style", "script", "head", "meta", "svg", "noscript", "link"]:
            self.skip = False
        elif not self.skip:
            if tl in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                self.parts.append("\n")
            elif tl in ["td", "th"]:
                cell_text = " ".join("".join(self.cell_parts).split()).strip()
                if cell_text:
                    self.row_cells.append(cell_text)
                self.cell_parts = []
            elif tl == "tr":
                if self.row_cells:
                    self.parts.append("| " + " | ".join(self.row_cells) + " |\n")
                self.in_row = False
                self.row_cells = []
            elif tl == "table":
                self.parts.append("\n")

    def handle_data(self, data: str):
        if not self.skip and data:
            if self.in_row:
                self.cell_parts.append(data)
            else:
                self.parts.append(data)


def clean_html_document(raw_html: str, filename: str) -> str:
    """Parses HTML documents into structured text, stripping style/script tags and certificate dumps."""
    parser = HTMLDiagnosticParser()
    try:
        parser.feed(raw_html)
        raw_clean = "".join(parser.parts)
    except Exception:
        raw_clean = re.sub(r"<[^>]+>", " ", raw_html)

    lines = [re.sub(r"\s+", " ", l).strip() for l in raw_clean.split("\n")]
    clean_text = "\n".join([l for l in lines if l])

    # Omit raw certificate dumps if present (certutil dump in Windows WLAN reports)
    clean_text = re.sub(r"### Output for [\'\"]certutil.*?(?=###|\Z)", "", clean_text, flags=re.DOTALL)

    # For WLAN reports or lengthy network diagnostics, condense excessive packet heartbeat sessions
    if "wlan" in filename.lower() or "wlan report" in clean_text.lower():
        clean_text = re.sub(
            r"(### Wireless Sessions.*?\n)(?:.*)",
            r"\1[Note: Individual wireless heartbeat connection packets condensed to preserve model context]",
            clean_text,
            flags=re.DOTALL
        )

    # Cap document length to safe token budget (max 16,000 characters ~ 4,000 tokens)
    if len(clean_text) > 16000:
        head = clean_text[:10000]
        tail = clean_text[-5000:]
        clean_text = (
            f"{head}\n\n"
            f"[... Note: Middle {len(clean_text) - 15000} characters omitted to preserve optimal reasoning context. "
            f"Key system configuration, adapters, and disconnect diagnostics preserved ...]\n\n"
            f"{tail}"
        )
    return clean_text.strip()


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
        text = ""
        # Try pymupdf first, fallback to pypdf
        try:
            import pymupdf
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            pages = []
            for i, p in enumerate(doc):
                t = p.get_text().strip()
                if t:
                    pages.append(f"[Page {i+1}]\n{t}")
            text = "\n\n".join(pages).strip()
        except ImportError:
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                pages = []
                for i, p in enumerate(reader.pages):
                    t = p.extract_text() or ""
                    t = t.strip()
                    if t:
                        pages.append(f"[Page {i+1}]\n{t}")
                text = "\n\n".join(pages).strip()
            except ImportError:
                text = f"[PDF extraction requires 'pymupdf' or 'pypdf'. File: {filename} ({size_kb} KB)]"
            except Exception as e:
                text = f"[Error reading PDF {filename} with pypdf: {e}]"
        except Exception as e:
            text = f"[Error reading PDF {filename}: {e}]"

        return {
            "name": filename,
            "type": "document",
            "ext": ext,
            "size_kb": size_kb,
            "text": text or f"[PDF {filename} contains no extractable text]"
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
        except ImportError:
            text = f"[Word document extraction requires 'python-docx'. File: {filename} ({size_kb} KB)]"
        except Exception as e:
            text = f"[Error reading Word document {filename}: {e}]"
        return {
            "name": filename,
            "type": "document",
            "ext": ext,
            "size_kb": size_kb,
            "text": text or f"[Word document {filename} is empty]"
        }

    # 4. Excel / Spreadsheet Documents (.xlsx, .xls)
    elif ext in [".xlsx", ".xls"]:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            sheet_texts = []
            for sheet_name in wb.sheetnames[:5]:  # limit to first 5 sheets
                ws = wb[sheet_name]
                rows = []
                for row in ws.iter_rows(values_only=True):
                    row_vals = [str(v).strip() for v in row if v is not None and str(v).strip()]
                    if row_vals:
                        rows.append(" | ".join(row_vals))
                    if len(rows) >= 200:
                        rows.append("... [truncated remaining rows] ...")
                        break
                if rows:
                    sheet_texts.append(f"### Sheet: {sheet_name}\n" + "\n".join(rows))
            text = "\n\n".join(sheet_texts).strip()
        except ImportError:
            text = f"[Excel spreadsheet extraction requires 'openpyxl'. File: {filename} ({size_kb} KB)]"
        except Exception as e:
            text = f"[Error reading Spreadsheet {filename}: {e}]"
        return {
            "name": filename,
            "type": "document",
            "ext": ext,
            "size_kb": size_kb,
            "text": text or f"[Spreadsheet {filename} contains no rows]"
        }

    # 5. HTML / Web Diagnostic Reports (.html, .htm)
    elif ext in [".html", ".htm"]:
        try:
            raw_html = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                raw_html = file_bytes.decode("latin-1")
            except Exception as e:
                raw_html = f"[Error decoding HTML {filename}: {e}]"
        
        text = clean_html_document(raw_html, filename)
        return {
            "name": filename,
            "type": "document",
            "ext": ext,
            "size_kb": size_kb,
            "text": text or f"[HTML document {filename} contains no extractable text]"
        }

    # 6. Non-text Binary Files Protection (prevent dumping corrupt/null bytes to LLM)
    elif (
        ext in [".bin", ".exe", ".dll", ".so", ".dylib", ".zip", ".tar", ".gz", ".7z", ".rar", ".parquet", ".pkl", ".pickle", ".pyc", ".iso", ".dat"]
        or (b"\x00" in file_bytes[:8192])
    ):
        return {
            "name": filename,
            "type": "binary",
            "ext": ext,
            "size_kb": size_kb,
            "text": f"[Binary file: {filename} ({size_kb} KB) - binary contents omitted from prompt context]"
        }

    # 7. Text, Code, CSV, JSON, Markdown, Configs
    else:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
            except Exception as e:
                text = f"[Unable to decode text file {filename}: {e}]"
        
        # Enforce safe upper bound on raw text files to protect LLM context windows
        if len(text) > 20000:
            text = (
                f"{text[:14000]}\n\n"
                f"[... Note: Large text file ({size_kb} KB) condensed to preserve model reasoning context ...]\n\n"
                f"{text[-6000:]}"
            )

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
