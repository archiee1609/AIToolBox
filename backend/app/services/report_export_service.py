"""
Report Export Service.
Parses generated markdown reports and compiles downloadable artifacts in multiple formats:
- PDF (.pdf) via reportlab
- Microsoft Word (.docx) via python-docx
- Microsoft Excel (.xlsx) via openpyxl (Summary & Data sheets, table parsing)
- Microsoft PowerPoint (.pptx) via python-pptx (16:9 widescreen presentation slides)
- Markdown (.md) raw text
- Standalone HTML (.html) print-ready styled document
"""

import io
import re
import html
import datetime
from typing import Dict, Any, List, Optional, Tuple


def sanitize_filename(title: str, max_length: int = 50) -> str:
    """Creates a filesystem-safe filename from report title."""
    clean = re.sub(r'[\\/*?:"<>|#📄\r\n\t]', '', title).strip()
    clean = re.sub(r'\s+', '_', clean)
    if not clean:
        clean = "Executive_Report"
    return clean[:max_length]


def parse_markdown_report(markdown_text: str, default_title: str = "Executive Report") -> Dict[str, Any]:
    """
    Parses a markdown report into a structured object:
    - title
    - subtitle
    - date
    - sections: list of dicts with heading, level, paragraphs, bullets, tables
    """
    lines = markdown_text.splitlines()
    report_title = default_title
    sections: List[Dict[str, Any]] = []
    
    current_section: Dict[str, Any] = {
        "heading": "Overview",
        "level": 1,
        "paragraphs": [],
        "bullets": [],
        "tables": []
    }
    
    title_found = False
    in_table = False
    current_table: List[List[str]] = []

    def flush_table():
        nonlocal in_table, current_table
        if in_table and current_table:
            current_section["tables"].append(current_table)
            current_table = []
            in_table = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_table()
            continue

        # Detect divider lines
        if re.match(r'^(?:---|\*\*\*|___)$', line):
            flush_table()
            continue

        # Detect main title if not found yet
        if not title_found and (line.startswith("# ") or line.startswith("## 📄") or line.startswith("## ")):
            candidate = re.sub(r'^#+\s*(?:📄\s*)?', '', line).strip()
            if candidate:
                report_title = candidate
                title_found = True
                continue

        # Detect markdown table line
        if line.startswith("|") and line.endswith("|"):
            # Skip separator line like |---|---|
            if re.match(r'^\|[\s\-:|]+\|$', line):
                in_table = True
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            current_table.append(cells)
            in_table = True
            continue
        else:
            flush_table()

        # Detect Section Headings (#, ##, ###, ####)
        heading_match = re.match(r'^(#{1,4})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            
            # Flush current section if it has content
            if current_section["paragraphs"] or current_section["bullets"] or current_section["tables"] or current_section["heading"] != "Overview":
                sections.append(current_section)
                
            current_section = {
                "heading": heading_text,
                "level": level,
                "paragraphs": [],
                "bullets": [],
                "tables": []
            }
            continue

        # Detect Bullet points (- *, 1. 2.)
        bullet_match = re.match(r'^(?:[\-\*•]|\d+\.)\s+(.+)$', line)
        if bullet_match:
            current_section["bullets"].append(bullet_match.group(1).strip())
            continue

        # Otherwise standard paragraph text
        current_section["paragraphs"].append(line)

    flush_table()
    if current_section["paragraphs"] or current_section["bullets"] or current_section["tables"] or not sections:
        sections.append(current_section)

    return {
        "title": report_title,
        "date": datetime.datetime.now().strftime("%B %d, %Y"),
        "timestamp": datetime.datetime.now().isoformat(),
        "sections": sections,
        "raw_markdown": markdown_text
    }


def generate_pdf_bytes(report_data: Dict[str, Any]) -> bytes:
    """Generates an executive, styled PDF report using reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom color palette
    primary_color = colors.HexColor("#1e293b")  # Dark slate
    accent_color = colors.HexColor("#4f46e5")   # Indigo
    text_color = colors.HexColor("#334155")     # Slate text
    light_bg = colors.HexColor("#f8fafc")

    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'ReportSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        'Heading1Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=accent_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=text_color,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=text_color,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=4
    )

    story = []

    # Title & Subtitle Banner
    safe_title = html.escape(report_data.get("title", "Executive Report"))
    story.append(Paragraph(safe_title, title_style))
    meta_text = f"Generated by Local AI Workbench • {report_data.get('date', '')}"
    story.append(Paragraph(meta_text, subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=14))

    # Sections
    for sec in report_data.get("sections", []):
        heading = html.escape(sec.get("heading", ""))
        level = sec.get("level", 1)
        h_style = h1_style if level <= 2 else h2_style
        story.append(Paragraph(heading, h_style))

        # Paragraphs
        for p in sec.get("paragraphs", []):
            safe_p = html.escape(p)
            # Support basic bold markup like **bold**
            safe_p = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', safe_p)
            safe_p = re.sub(r'\*(.+?)\*', r'<i>\1</i>', safe_p)
            story.append(Paragraph(safe_p, body_style))

        # Bullets
        for b in sec.get("bullets", []):
            safe_b = html.escape(b)
            safe_b = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', safe_b)
            story.append(Paragraph(f"• {safe_b}", bullet_style))

        # Tables
        for tbl in sec.get("tables", []):
            if not tbl or not tbl[0]:
                continue
            table_data = []
            for row in tbl:
                row_cells = [Paragraph(html.escape(cell), body_style) for cell in row]
                table_data.append(row_cells)
            
            t = Table(table_data, colWidths=[500 / len(tbl[0])] * len(tbl[0]))
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), light_bg),
                ('TEXTCOLOR', (0, 0), (-1, 0), primary_color),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            story.append(Spacer(1, 4))
            story.append(t)
            story.append(Spacer(1, 6))

        story.append(Spacer(1, 6))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_docx_bytes(report_data: Dict[str, Any]) -> bytes:
    """Generates a professional Microsoft Word (.docx) document."""
    import docx
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = docx.Document()

    # Set standard margins
    for s in doc.sections:
        s.top_margin = Inches(0.8)
        s.bottom_margin = Inches(0.8)
        s.left_margin = Inches(0.8)
        s.right_margin = Inches(0.8)

    # Document Title
    title = report_data.get("title", "Executive Report")
    title_p = doc.add_heading(level=0)
    title_run = title_p.add_run(title)
    title_run.font.name = 'Segoe UI'
    title_run.font.size = Pt(22)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(30, 41, 59)

    # Subtitle / Metadata
    sub_p = doc.add_paragraph()
    sub_run = sub_p.add_run(f"Generated by Local AI Workbench • {report_data.get('date', '')}")
    sub_run.font.name = 'Segoe UI'
    sub_run.font.size = Pt(9.5)
    sub_run.font.color.rgb = RGBColor(100, 116, 139)
    sub_p.paragraph_format.space_after = Pt(14)

    # Sections
    for sec in report_data.get("sections", []):
        heading = sec.get("heading", "")
        level = sec.get("level", 1)
        h = doc.add_heading(level=min(level, 3))
        h_run = h.add_run(heading)
        h_run.font.name = 'Segoe UI'
        h_run.font.bold = True
        if level <= 1:
            h_run.font.color.rgb = RGBColor(79, 70, 229)  # Indigo
            h_run.font.size = Pt(14)
        else:
            h_run.font.color.rgb = RGBColor(30, 41, 59)
            h_run.font.size = Pt(12)
        h.paragraph_format.space_before = Pt(12)
        h.paragraph_format.space_after = Pt(4)

        # Paragraphs
        for p in sec.get("paragraphs", []):
            para = doc.add_paragraph()
            para.paragraph_format.space_after = Pt(4)
            para.paragraph_format.line_spacing = 1.15
            # Basic bold formatting **word**
            parts = re.split(r'(\*\*.*?\*\*)', p)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    r = para.add_run(part[2:-2])
                    r.bold = True
                else:
                    r = para.add_run(part)
                r.font.name = 'Segoe UI'
                r.font.size = Pt(10.5)
                r.font.color.rgb = RGBColor(51, 65, 85)

        # Bullets
        for b in sec.get("bullets", []):
            bp = doc.add_paragraph(style='List Bullet')
            bp.paragraph_format.space_after = Pt(2)
            parts = re.split(r'(\*\*.*?\*\*)', b)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    r = bp.add_run(part[2:-2])
                    r.bold = True
                else:
                    r = bp.add_run(part)
                r.font.name = 'Segoe UI'
                r.font.size = Pt(10)
                r.font.color.rgb = RGBColor(51, 65, 85)

        # Tables
        for tbl in sec.get("tables", []):
            if not tbl or not tbl[0]:
                continue
            table = doc.add_table(rows=len(tbl), cols=len(tbl[0]))
            table.style = 'Light Shading Accent 1' if 'Light Shading Accent 1' in doc.styles else 'Table Grid'
            for r_idx, row in enumerate(tbl):
                for c_idx, cell in enumerate(row):
                    cell_p = table.cell(r_idx, c_idx).paragraphs[0]
                    c_run = cell_p.add_run(cell)
                    c_run.font.name = 'Segoe UI'
                    c_run.font.size = Pt(9.5)
                    if r_idx == 0:
                        c_run.bold = True
            doc.add_paragraph()

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def generate_xlsx_bytes(report_data: Dict[str, Any]) -> bytes:
    """Generates an executive Microsoft Excel (.xlsx) workbook with Overview and Detailed Breakdown."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()

    # Style definitions
    title_font = Font(name="Segoe UI", size=15, bold=True, color="FFFFFF")
    title_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")

    meta_font = Font(name="Segoe UI", size=10, italic=True, color="475569")
    bold_font = Font(name="Segoe UI", size=10, bold=True, color="1E293B")
    body_font = Font(name="Segoe UI", size=10, color="334155")
    
    thin_border = Border(
        left=Side(style='thin', color="CBD5E1"),
        right=Side(style='thin', color="CBD5E1"),
        top=Side(style='thin', color="CBD5E1"),
        bottom=Side(style='thin', color="CBD5E1")
    )
    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    # Sheet 1: Executive Overview
    ws1 = wb.active
    ws1.title = "Executive Overview"
    ws1.views.sheetView[0].showGridLines = True

    # Title Banner
    ws1.merge_cells("A1:D1")
    cell_a1 = ws1["A1"]
    cell_a1.value = report_data.get("title", "Executive Report")
    cell_a1.font = title_font
    cell_a1.fill = title_fill
    cell_a1.alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[1].height = 36

    # Metadata
    ws1["A3"] = "Generated At:"
    ws1["A3"].font = bold_font
    ws1["B3"] = report_data.get("date", "")
    ws1["B3"].font = body_font

    ws1["A4"] = "Platform:"
    ws1["A4"].font = bold_font
    ws1["B4"] = "Local AI Workbench"
    ws1["B4"].font = body_font

    ws1["A5"] = "Total Sections:"
    ws1["A5"].font = bold_font
    ws1["B5"] = len(report_data.get("sections", []))
    ws1["B5"].font = body_font

    # Sections summary table
    headers_ws1 = ["Section #", "Heading", "Key Takeaways / Bullets", "Paragraph Count"]
    for col_idx, h in enumerate(headers_ws1, 1):
        c = ws1.cell(row=7, column=col_idx, value=h)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="left", vertical="center")
        c.border = thin_border
    ws1.row_dimensions[7].height = 24

    for idx, sec in enumerate(report_data.get("sections", []), 1):
        r = 7 + idx
        ws1.cell(row=r, column=1, value=idx).font = bold_font
        ws1.cell(row=r, column=2, value=sec.get("heading", "")).font = bold_font
        ws1.cell(row=r, column=3, value=len(sec.get("bullets", []))).font = body_font
        ws1.cell(row=r, column=4, value=len(sec.get("paragraphs", []))).font = body_font
        
        fill_to_use = zebra_fill if idx % 2 == 0 else PatternFill(fill_type=None)
        for c_i in range(1, 5):
            cell = ws1.cell(row=r, column=c_i)
            cell.border = thin_border
            if fill_to_use.fill_type:
                cell.fill = fill_to_use

    # Sheet 2: Detailed Content Breakdown
    ws2 = wb.create_sheet(title="Detailed Content")
    ws2.views.sheetView[0].showGridLines = True
    
    headers_ws2 = ["Section", "Item Type", "Content Details"]
    for col_idx, h in enumerate(headers_ws2, 1):
        c = ws2.cell(row=1, column=col_idx, value=h)
        c.font = header_font
        c.fill = header_fill
        c.border = thin_border
    ws2.row_dimensions[1].height = 24

    row_cursor = 2
    for sec in report_data.get("sections", []):
        sec_title = sec.get("heading", "")
        # Add paragraphs
        for p in sec.get("paragraphs", []):
            ws2.cell(row=row_cursor, column=1, value=sec_title).font = bold_font
            ws2.cell(row=row_cursor, column=2, value="Paragraph").font = meta_font
            ws2.cell(row=row_cursor, column=3, value=p).font = body_font
            for c_i in range(1, 4):
                ws2.cell(row=row_cursor, column=c_i).border = thin_border
            row_cursor += 1
            
        # Add bullets
        for b in sec.get("bullets", []):
            ws2.cell(row=row_cursor, column=1, value=sec_title).font = bold_font
            ws2.cell(row=row_cursor, column=2, value="Key Point").font = meta_font
            ws2.cell(row=row_cursor, column=3, value=b).font = body_font
            for c_i in range(1, 4):
                ws2.cell(row=row_cursor, column=c_i).border = thin_border
            row_cursor += 1

    # Auto-fit column widths
    for sheet in [ws1, ws2]:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 14), 70)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def generate_pptx_bytes(report_data: Dict[str, Any]) -> bytes:
    """Generates a modern 16:9 widescreen PowerPoint presentation (.pptx)."""
    import pptx
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    prs = pptx.Presentation()
    # Configure 16:9 widescreen dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    # Theme colors
    bg_dark = RGBColor(15, 23, 42)      # Slate 900
    accent_color = RGBColor(99, 102, 241) # Indigo 500
    text_white = RGBColor(255, 255, 255)
    text_dark = RGBColor(30, 41, 59)
    text_muted = RGBColor(100, 116, 139)
    card_bg = RGBColor(248, 250, 252)

    # 1. Slide 1: Modern Title Slide (Dark Theme)
    slide1 = prs.slides.add_slide(blank_layout)
    bg1 = slide1.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)  # MSO_SHAPE.RECTANGLE
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = bg_dark
    bg1.line.fill.background()

    # Title box
    tb = slide1.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(11.0), Inches(2.5))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p_title = tf.paragraphs[0]
    p_title.text = report_data.get("title", "Executive Technical Report")
    p_title.font.name = "Segoe UI"
    p_title.font.size = Pt(40)
    p_title.font.bold = True
    p_title.font.color.rgb = text_white

    p_sub = tf.add_paragraph()
    p_sub.text = f"Local AI Workbench • {report_data.get('date', '')}"
    p_sub.font.name = "Segoe UI"
    p_sub.font.size = Pt(18)
    p_sub.font.color.rgb = accent_color
    p_sub.space_before = Pt(16)

    # 2. Subsequent Slides: One or more slides per Section
    for sec in report_data.get("sections", []):
        heading = sec.get("heading", "Executive Section")
        bullets = sec.get("bullets", [])
        paragraphs = sec.get("paragraphs", [])

        # Gather content items
        items = bullets if bullets else paragraphs
        if not items:
            items = ["Section content synthesized by Local AI Workbench."]

        # Split into chunks of max 5 items per slide
        chunk_size = 5
        chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

        for part_idx, chunk in enumerate(chunks):
            slide = prs.slides.add_slide(blank_layout)
            
            # Subtle top accent bar
            bar = slide.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(0.12))
            bar.fill.solid()
            bar.fill.fore_color.rgb = accent_color
            bar.line.fill.background()

            # Slide Header
            header_box = slide.shapes.add_textbox(Inches(1.0), Inches(0.6), Inches(11.3), Inches(1.0))
            h_tf = header_box.text_frame
            h_tf.word_wrap = True
            h_p = h_tf.paragraphs[0]
            display_heading = heading if len(chunks) == 1 else f"{heading} (Part {part_idx + 1})"
            h_p.text = display_heading
            h_p.font.name = "Segoe UI"
            h_p.font.size = Pt(28)
            h_p.font.bold = True
            h_p.font.color.rgb = text_dark

            # Content Card Container
            card = slide.shapes.add_shape(1, Inches(1.0), Inches(1.8), Inches(11.33), Inches(4.8))
            card.fill.solid()
            card.fill.fore_color.rgb = card_bg
            card.line.color.rgb = RGBColor(226, 232, 240)

            # Bullet List Frame
            content_box = slide.shapes.add_textbox(Inches(1.4), Inches(2.0), Inches(10.5), Inches(4.3))
            c_tf = content_box.text_frame
            c_tf.word_wrap = True

            for item_idx, item in enumerate(chunk):
                p_item = c_tf.paragraphs[0] if item_idx == 0 else c_tf.add_paragraph()
                p_item.text = f"•  {item}"
                p_item.font.name = "Segoe UI"
                p_item.font.size = Pt(17)
                p_item.font.color.rgb = text_dark
                p_item.space_before = Pt(14) if item_idx > 0 else Pt(0)
                p_item.line_spacing = 1.25

            # Slide Footer
            footer_box = slide.shapes.add_textbox(Inches(1.0), Inches(6.8), Inches(11.3), Inches(0.5))
            f_tf = footer_box.text_frame
            f_p = f_tf.paragraphs[0]
            f_p.text = f"Local AI Workbench  |  {report_data.get('title', '')}"
            f_p.font.name = "Segoe UI"
            f_p.font.size = Pt(10)
            f_p.font.color.rgb = text_muted

    buffer = io.BytesIO()
    prs.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def generate_html_bytes(report_data: Dict[str, Any]) -> bytes:
    """Generates a standalone, beautiful HTML report with CSS print media styling."""
    title = html.escape(report_data.get("title", "Executive Report"))
    date_str = html.escape(report_data.get("date", ""))
    
    sections_html = []
    for sec in report_data.get("sections", []):
        h = html.escape(sec.get("heading", ""))
        lvl = sec.get("level", 1)
        tag = f"h{min(lvl + 1, 4)}"
        
        sec_inner = [f"<{tag} class='section-heading'>{h}</{tag}>"]
        
        for p in sec.get("paragraphs", []):
            sp = html.escape(p)
            sp = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', sp)
            sec_inner.append(f"<p class='report-p'>{sp}</p>")
            
        if sec.get("bullets"):
            sec_inner.append("<ul class='report-ul'>")
            for b in sec.get("bullets", []):
                sb = html.escape(b)
                sb = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', sb)
                sec_inner.append(f"<li>{sb}</li>")
            sec_inner.append("</ul>")

        for tbl in sec.get("tables", []):
            if tbl and tbl[0]:
                sec_inner.append("<div class='table-wrapper'><table class='report-table'><thead><tr>")
                for c in tbl[0]:
                    sec_inner.append(f"<th>{html.escape(c)}</th>")
                sec_inner.append("</tr></thead><tbody>")
                for row in tbl[1:]:
                    sec_inner.append("<tr>")
                    for c in row:
                        sec_inner.append(f"<td>{html.escape(c)}</td>")
                    sec_inner.append("</tr>")
                sec_inner.append("</tbody></table></div>")

        sections_html.append(f"<section class='report-section'>{''.join(sec_inner)}</section>")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{
    --primary: #1e293b;
    --accent: #4f46e5;
    --text: #334155;
    --bg-card: #ffffff;
    --border: #e2e8f0;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: var(--text);
    background: #f8fafc;
    margin: 0;
    padding: 2.5rem 1rem;
  }}
  .container {{
    max-width: 860px;
    margin: 0 auto;
    background: var(--bg-card);
    padding: 3rem;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    border: 1px solid var(--border);
  }}
  .header {{
    border-bottom: 2px solid var(--accent);
    padding-bottom: 1.25rem;
    margin-bottom: 2rem;
  }}
  .header h1 {{
    font-size: 2.2rem;
    color: var(--primary);
    margin: 0 0 0.5rem 0;
    font-weight: 800;
  }}
  .meta {{
    font-size: 0.9rem;
    color: #64748b;
    display: flex;
    justify-content: space-between;
  }}
  .section-heading {{
    color: var(--accent);
    margin-top: 2rem;
    margin-bottom: 0.75rem;
    font-weight: 700;
  }}
  .report-p {{
    margin-bottom: 0.85rem;
  }}
  .report-ul {{
    padding-left: 1.5rem;
    margin-bottom: 1.25rem;
  }}
  .report-ul li {{
    margin-bottom: 0.4rem;
  }}
  .table-wrapper {{
    overflow-x: auto;
    margin: 1.25rem 0;
  }}
  .report-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.95rem;
  }}
  .report-table th, .report-table td {{
    padding: 0.65rem 0.85rem;
    border: 1px solid var(--border);
    text-align: left;
  }}
  .report-table th {{
    background: #f1f5f9;
    color: var(--primary);
    font-weight: 600;
  }}
  .footer {{
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
    font-size: 0.8rem;
    color: #94a3b8;
    text-align: center;
  }}
  @media print {{
    body {{ background: #fff; padding: 0; }}
    .container {{ box-shadow: none; border: none; padding: 0; }}
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>{title}</h1>
    <div class="meta">
      <span>Generated by Local AI Workbench</span>
      <span>{date_str}</span>
    </div>
  </div>
  {''.join(sections_html)}
  <div class="footer">
    Synthesized privately on device • Local AI Workbench
  </div>
</div>
</body>
</html>"""
    return html_content.encode("utf-8")


def export_report_bundle(markdown_text: str, default_title: str = "Executive Report") -> Dict[str, Dict[str, Any]]:
    """
    Compiles all supported downloadable file formats from markdown report text.
    Returns dictionary with format keys: 'pdf', 'docx', 'xlsx', 'pptx', 'md', 'html'.
    """
    parsed = parse_markdown_report(markdown_text, default_title)
    safe_name = sanitize_filename(parsed["title"])

    bundle: Dict[str, Dict[str, Any]] = {}

    # 1. PDF
    try:
        pdf_bytes = generate_pdf_bytes(parsed)
        bundle["pdf"] = {
            "name": "PDF Document",
            "filename": f"{safe_name}.pdf",
            "bytes": pdf_bytes,
            "mime": "application/pdf",
            "icon": "📕",
            "size_kb": round(len(pdf_bytes) / 1024, 1)
        }
    except Exception as e:
        bundle["pdf"] = {"error": str(e), "name": "PDF Document", "icon": "📕"}

    # 2. Word (.docx)
    try:
        docx_bytes = generate_docx_bytes(parsed)
        bundle["docx"] = {
            "name": "Word Document",
            "filename": f"{safe_name}.docx",
            "bytes": docx_bytes,
            "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "icon": "📘",
            "size_kb": round(len(docx_bytes) / 1024, 1)
        }
    except Exception as e:
        bundle["docx"] = {"error": str(e), "name": "Word Document", "icon": "📘"}

    # 3. Excel (.xlsx)
    try:
        xlsx_bytes = generate_xlsx_bytes(parsed)
        bundle["xlsx"] = {
            "name": "Excel Spreadsheet",
            "filename": f"{safe_name}.xlsx",
            "bytes": xlsx_bytes,
            "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "icon": "📊",
            "size_kb": round(len(xlsx_bytes) / 1024, 1)
        }
    except Exception as e:
        bundle["xlsx"] = {"error": str(e), "name": "Excel Spreadsheet", "icon": "📊"}

    # 4. PowerPoint (.pptx)
    try:
        pptx_bytes = generate_pptx_bytes(parsed)
        bundle["pptx"] = {
            "name": "PowerPoint Slides",
            "filename": f"{safe_name}.pptx",
            "bytes": pptx_bytes,
            "mime": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "icon": "📙",
            "size_kb": round(len(pptx_bytes) / 1024, 1)
        }
    except Exception as e:
        bundle["pptx"] = {"error": str(e), "name": "PowerPoint Slides", "icon": "📙"}

    # 5. Markdown (.md)
    md_bytes = markdown_text.encode("utf-8")
    bundle["md"] = {
        "name": "Markdown Source",
        "filename": f"{safe_name}.md",
        "bytes": md_bytes,
        "mime": "text/markdown",
        "icon": "📝",
        "size_kb": round(len(md_bytes) / 1024, 1)
    }

    # 6. HTML (.html)
    try:
        html_bytes = generate_html_bytes(parsed)
        bundle["html"] = {
            "name": "Web / Print HTML",
            "filename": f"{safe_name}.html",
            "bytes": html_bytes,
            "mime": "text/html",
            "icon": "🌐",
            "size_kb": round(len(html_bytes) / 1024, 1)
        }
    except Exception as e:
        bundle["html"] = {"error": str(e), "name": "Web HTML", "icon": "🌐"}

    # 7. Complete ZIP Archive (All Formats in one click)
    try:
        import zipfile
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fmt_key in ["pdf", "docx", "xlsx", "pptx", "md", "html"]:
                b_item = bundle.get(fmt_key)
                if b_item and "bytes" in b_item:
                    zf.writestr(b_item["filename"], b_item["bytes"])
        zip_bytes = zip_buf.getvalue()
        bundle["zip"] = {
            "name": "All Formats (.zip)",
            "filename": f"{safe_name}_Complete_Bundle.zip",
            "bytes": zip_bytes,
            "mime": "application/zip",
            "icon": "📦",
            "size_kb": round(len(zip_bytes) / 1024, 1)
        }
    except Exception as e:
        bundle["zip"] = {"error": str(e), "name": "All Formats (.zip)", "icon": "📦"}

    return bundle
