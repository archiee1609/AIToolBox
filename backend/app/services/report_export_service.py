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
        "tables": [],
        "code_blocks": []
    }
    
    title_found = False
    in_table = False
    in_code_block = False
    code_lines: List[str] = []
    code_lang = ""
    current_table: List[List[str]] = []

    def flush_table():
        nonlocal in_table, current_table
        if in_table and current_table:
            current_section["tables"].append(current_table)
            current_table = []
            in_table = False

    for raw_line in lines:
        line = raw_line.strip()

        # Handle code block fence
        if line.startswith("```"):
            flush_table()
            if in_code_block:
                in_code_block = False
                current_section["code_blocks"].append({
                    "language": code_lang,
                    "content": "\n".join(code_lines)
                })
                code_lines = []
                code_lang = ""
            else:
                in_code_block = True
                code_lang = line[3:].strip()
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(raw_line)
            continue

        if not line:
            flush_table()
            continue

        # Detect divider lines
        if re.match(r'^(?:---|\*\*\*|___)$', line):
            flush_table()
            continue

        # Detect main title if not found yet
        if not title_found and (line.startswith("# ") or line.startswith("## 📄") or line.startswith("# 🏛️") or line.startswith("## ")):
            candidate = re.sub(r'^#+\s*(?:🏛️|📄)?\s*(?:EXECUTIVE\s*(?:STRATEGIC)?\s*REPORT:?)?\s*', '', line, flags=re.IGNORECASE).strip()
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
            if current_section["paragraphs"] or current_section["bullets"] or current_section["tables"] or current_section["code_blocks"] or current_section["heading"] != "Overview":
                sections.append(current_section)
                
            current_section = {
                "heading": heading_text,
                "level": level,
                "paragraphs": [],
                "bullets": [],
                "tables": [],
                "code_blocks": []
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
    if in_code_block and code_lines:
        current_section["code_blocks"].append({
            "language": code_lang,
            "content": "\n".join(code_lines)
        })

    if current_section["paragraphs"] or current_section["bullets"] or current_section["tables"] or current_section["code_blocks"] or not sections:
        sections.append(current_section)

    # Derive top KPI cards
    from app.services.report_generator_service import parse_kpi_cards_from_report
    kpis = parse_kpi_cards_from_report(markdown_text)

    return {
        "title": report_title,
        "date": datetime.datetime.now().strftime("%B %d, %Y"),
        "timestamp": datetime.datetime.now().isoformat(),
        "sections": sections,
        "kpis": kpis,
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
    meta_text = f"Generated by Local AI Workbench • {report_data.get('date', '')} • Classification: CONFIDENTIAL // BOARD LEVEL"
    story.append(Paragraph(meta_text, subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=10))

    # Executive KPI Dashboard Cards in PDF
    kpis = report_data.get("kpis", [])
    if kpis:
        kpi_table_data = [
            [Paragraph(f"<b>{k['title']}</b>", ParagraphStyle('KPITitle', parent=styles['Normal'], fontSize=7.5, textColor=colors.HexColor("#64748b"))) for k in kpis],
            [Paragraph(f"<b>{k['value']}</b>", ParagraphStyle('KPIVal', parent=styles['Normal'], fontSize=13, leading=15, textColor=primary_color)) for k in kpis],
            [Paragraph(f"<font color='{k['color']}'><b>{k['badge']}</b></font>", ParagraphStyle('KPIBadge', parent=styles['Normal'], fontSize=7)) for k in kpis]
        ]
        kpi_table = Table(kpi_table_data, colWidths=[500 / len(kpis)] * len(kpis))
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 10))

    # Sections
    for sec in report_data.get("sections", []):
        heading = html.escape(sec.get("heading", ""))
        level = sec.get("level", 1)
        h_style = h1_style if level <= 2 else h2_style
        story.append(Paragraph(heading, h_style))

        # Paragraphs
        for p in sec.get("paragraphs", []):
            safe_p = html.escape(p)
            safe_p = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', safe_p)
            safe_p = re.sub(r'\*(.+?)\*', r'<i>\1</i>', safe_p)
            story.append(Paragraph(safe_p, body_style))

        # Bullets
        for b in sec.get("bullets", []):
            safe_b = html.escape(b)
            safe_b = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', safe_b)
            story.append(Paragraph(f"• {safe_b}", bullet_style))

        # Code & Architecture blocks in PDF
        for cb in sec.get("code_blocks", []):
            cb_content = html.escape(cb.get("content", ""))
            cb_style = ParagraphStyle(
                'CodeBlockPDF',
                parent=styles['Normal'],
                fontName='Courier',
                fontSize=7.5,
                leading=10,
                textColor=colors.HexColor("#0f172a")
            )
            cb_table = Table([[Paragraph(cb_content.replace("\n", "<br/>"), cb_style)]], colWidths=[500])
            cb_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(Spacer(1, 4))
            story.append(cb_table)
            story.append(Spacer(1, 6))

        # Tables with color-coded badges
        for tbl in sec.get("tables", []):
            if not tbl or not tbl[0]:
                continue
            table_data = []
            for row_idx, row in enumerate(tbl):
                row_cells = []
                for cell in row:
                    safe_cell = html.escape(cell)
                    safe_cell = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', safe_cell)
                    u_cell = cell.upper()
                    if any(w in u_cell for w in ["OPTIMAL", "ACTIVE", "PASS", "EXCEEDING", "BENCHMARK LEADER", "LOW"]):
                        safe_cell = f'<font color="#15803d"><b>{safe_cell}</b></font>'
                    elif any(w in u_cell for w in ["CRITICAL", "FAIL", "IMMEDIATE"]):
                        safe_cell = f'<font color="#b91c1c"><b>{safe_cell}</b></font>'
                    elif any(w in u_cell for w in ["HIGH", "ELEVATED", "HIGH RISK", "HIGH ROI"]):
                        safe_cell = f'<font color="#c2410c"><b>{safe_cell}</b></font>'
                    elif any(w in u_cell for w in ["MEDIUM", "MODERATE", "ATTENTION", "NEEDS OPTIMIZATION"]):
                        safe_cell = f'<font color="#b45309"><b>{safe_cell}</b></font>'
                    elif any(w in u_cell for w in ["AIR-GAPPED", "VERIFIED", "STRATEGIC"]):
                        safe_cell = f'<font color="#0369a1"><b>{safe_cell}</b></font>'

                    cell_style = ParagraphStyle(
                        'TableCellStyle',
                        parent=styles['Normal'],
                        fontName='Helvetica-Bold' if row_idx == 0 else 'Helvetica',
                        fontSize=8,
                        leading=10,
                        textColor=primary_color if row_idx == 0 else text_color
                    )
                    row_cells.append(Paragraph(safe_cell, cell_style))
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
    sub_run = sub_p.add_run(f"Generated by Local AI Workbench • {report_data.get('date', '')} • CONFIDENTIAL // EXECUTIVE ACCESS")
    sub_run.font.name = 'Segoe UI'
    sub_run.font.size = Pt(9.5)
    sub_run.font.color.rgb = RGBColor(100, 116, 139)
    sub_p.paragraph_format.space_after = Pt(14)

    # Executive KPI Dashboard Table (if present)
    kpis = report_data.get("kpis", [])
    if kpis:
        kpi_h = doc.add_heading(level=2)
        kpi_h_run = kpi_h.add_run("📊 Executive Performance & KPI Dashboard")
        kpi_h_run.font.name = 'Segoe UI'
        kpi_h_run.font.bold = True
        kpi_h_run.font.size = Pt(13)
        kpi_h_run.font.color.rgb = RGBColor(79, 70, 229)
        kpi_h.paragraph_format.space_before = Pt(8)
        kpi_h.paragraph_format.space_after = Pt(4)

        kpi_table = doc.add_table(rows=len(kpis) + 1, cols=4)
        kpi_table.style = 'Light Shading Accent 1' if 'Light Shading Accent 1' in doc.styles else 'Table Grid'
        headers = ["Strategic Pillar", "Target KPI", "Actual Performance", "Status Badge"]
        for c_idx, h_text in enumerate(headers):
            cell_p = kpi_table.cell(0, c_idx).paragraphs[0]
            run = cell_p.add_run(h_text)
            run.font.name = 'Segoe UI'
            run.font.bold = True
            run.font.size = Pt(9.5)

        for r_idx, card in enumerate(kpis, start=1):
            vals = [card.get("title", ""), card.get("target", ""), card.get("value", ""), card.get("badge", "OPTIMAL")]
            for c_idx, val in enumerate(vals):
                cell_p = kpi_table.cell(r_idx, c_idx).paragraphs[0]
                run = cell_p.add_run(val)
                run.font.name = 'Segoe UI'
                run.font.size = Pt(9.5)
                if c_idx == 0 or c_idx == 3:
                    run.font.bold = True
        doc.add_paragraph().paragraph_format.space_after = Pt(12)

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

    # Executive KPI Dashboard Table (if present)
    kpis = report_data.get("kpis", [])
    current_row = 7
    if kpis:
        # Sub-header for KPIs
        ws1.merge_cells(f"A{current_row}:D{current_row}")
        kpi_title_cell = ws1[f"A{current_row}"]
        kpi_title_cell.value = "📊 EXECUTIVE PERFORMANCE & KPI DASHBOARD"
        kpi_title_cell.font = Font(name="Segoe UI", size=11, bold=True, color="1E293B")
        kpi_title_cell.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
        kpi_title_cell.alignment = Alignment(horizontal="left", vertical="center")
        ws1.row_dimensions[current_row].height = 22
        current_row += 1

        headers_kpi = ["Strategic Pillar", "Target KPI", "Actual Performance", "Status Badge"]
        for col_idx, h in enumerate(headers_kpi, 1):
            c = ws1.cell(row=current_row, column=col_idx, value=h)
            c.font = header_font
            c.fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
            c.alignment = Alignment(horizontal="left", vertical="center")
            c.border = thin_border
        ws1.row_dimensions[current_row].height = 22
        current_row += 1

        for card in kpis:
            ws1.cell(row=current_row, column=1, value=card.get("title", "")).font = bold_font
            ws1.cell(row=current_row, column=2, value=card.get("target", "")).font = body_font
            ws1.cell(row=current_row, column=3, value=card.get("value", "")).font = bold_font
            badge_cell = ws1.cell(row=current_row, column=4, value=card.get("badge", "OPTIMAL"))
            badge_cell.font = bold_font
            badge_cell.alignment = Alignment(horizontal="center", vertical="center")
            for c_i in range(1, 5):
                ws1.cell(row=current_row, column=c_i).border = thin_border
            current_row += 1
        current_row += 1

    # Sections summary table
    ws1.merge_cells(f"A{current_row}:D{current_row}")
    sec_title_cell = ws1[f"A{current_row}"]
    sec_title_cell.value = "📑 REPORT SECTIONS & ARCHITECTURE BREAKDOWN"
    sec_title_cell.font = Font(name="Segoe UI", size=11, bold=True, color="1E293B")
    sec_title_cell.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
    sec_title_cell.alignment = Alignment(horizontal="left", vertical="center")
    ws1.row_dimensions[current_row].height = 22
    current_row += 1

    headers_ws1 = ["Section #", "Heading", "Key Takeaways / Bullets", "Paragraph Count"]
    for col_idx, h in enumerate(headers_ws1, 1):
        c = ws1.cell(row=current_row, column=col_idx, value=h)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="left", vertical="center")
        c.border = thin_border
    ws1.row_dimensions[current_row].height = 24
    header_row_sec = current_row
    current_row += 1

    for idx, sec in enumerate(report_data.get("sections", []), 1):
        r = current_row
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
        current_row += 1

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
    """Generates a standalone, beautiful HTML report with CSS print media styling and interactive KPI/Mermaid visualizer."""
    title = html.escape(report_data.get("title", "Executive Report"))
    date_str = html.escape(report_data.get("date", ""))
    
    def apply_html_color_badges(text: str) -> str:
        s = html.escape(text)
        s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
        # Apply color-coded badges
        s = re.sub(
            r'🟢\s*(OPTIMAL|ACTIVE|LOW|EXCEEDING|ONLINE|SYNCHRONIZED|ACTIVE &amp; HEALTHY|BENCHMARK LEADER|MINIMAL|PASS)',
            r'<span class="badge badge-optimal">🟢 \1</span>',
            s, flags=re.IGNORECASE
        )
        s = re.sub(
            r'🔴\s*(CRITICAL|FAIL|IMMEDIATE ACTION|URGENT)',
            r'<span class="badge badge-critical">🔴 \1</span>',
            s, flags=re.IGNORECASE
        )
        s = re.sub(
            r'🟠\s*(HIGH|ELEVATED|HIGH RISK|HIGH ROI)',
            r'<span class="badge badge-high">🟠 \1</span>',
            s, flags=re.IGNORECASE
        )
        s = re.sub(
            r'🟡\s*(MEDIUM|MODERATE|ATTENTION|NEEDS OPTIMIZATION|ATTENTION NEEDED)',
            r'<span class="badge badge-medium">🟡 \1</span>',
            s, flags=re.IGNORECASE
        )
        s = re.sub(
            r'🔵\s*(STRATEGIC|VERIFIED|VERIFIED AIR-GAPPED|AIR-LOCKED|UNDER EVALUATION)',
            r'<span class="badge badge-strategic">🔵 \1</span>',
            s, flags=re.IGNORECASE
        )
        return s

    # KPI Grid HTML
    kpis = report_data.get("kpis", [])
    kpi_grid_html = ""
    if kpis:
        kpi_cards = []
        for k in kpis:
            c_title = html.escape(k.get("title", ""))
            c_val = html.escape(k.get("value", ""))
            c_target = html.escape(k.get("target", ""))
            c_badge = html.escape(k.get("badge", "OPTIMAL"))
            c_color = k.get("color", "#10b981")
            
            kpi_cards.append(f"""
            <div class="kpi-card" style="border-top-color: {c_color};">
              <div class="kpi-card-header">
                <span class="kpi-title">{c_title}</span>
                <span class="kpi-badge" style="color: {c_color}; border-color: {c_color}40; background: {c_color}15;">{c_badge}</span>
              </div>
              <div class="kpi-value">{c_val}</div>
              <div class="kpi-target">{c_target}</div>
            </div>
            """)
        kpi_grid_html = f"""
        <div class="dashboard-banner">
            <div class="dashboard-header-row">
                <span class="dashboard-title">📊 EXECUTIVE PERFORMANCE &amp; KPI DASHBOARD</span>
                <span class="confidential-pill">CONFIDENTIAL // BOARD LEVEL</span>
            </div>
            <div class="kpi-grid">
                {''.join(kpi_cards)}
            </div>
        </div>
        """

    sections_html = []
    has_mermaid = False
    for sec in report_data.get("sections", []):
        h = html.escape(sec.get("heading", ""))
        lvl = sec.get("level", 1)
        tag = f"h{min(lvl + 1, 4)}"
        
        sec_inner = [f"<{tag} class='section-heading'>{h}</{tag}>"]
        
        for p in sec.get("paragraphs", []):
            sec_inner.append(f"<p class='report-p'>{apply_html_color_badges(p)}</p>")
            
        if sec.get("bullets"):
            sec_inner.append("<ul class='report-ul'>")
            for b in sec.get("bullets", []):
                sec_inner.append(f"<li>{apply_html_color_badges(b)}</li>")
            sec_inner.append("</ul>")

        for tbl in sec.get("tables", []):
            if tbl and tbl[0]:
                sec_inner.append("<div class='table-wrapper'><table class='report-table'><thead><tr>")
                for c in tbl[0]:
                    sec_inner.append(f"<th>{apply_html_color_badges(c)}</th>")
                sec_inner.append("</tr></thead><tbody>")
                for row in tbl[1:]:
                    sec_inner.append("<tr>")
                    for c in row:
                        sec_inner.append(f"<td>{apply_html_color_badges(c)}</td>")
                    sec_inner.append("</tr>")
                sec_inner.append("</tbody></table></div>")

        for cb in sec.get("code_blocks", []):
            lang = cb.get("language", "").strip().lower()
            code_str = cb.get("content", "")
            if lang == "mermaid":
                has_mermaid = True
                sec_inner.append(f"<div class='mermaid-diagram-box'><div class='mermaid-title'>🏛️ Architecture Diagram</div><pre class='mermaid'>{html.escape(code_str)}</pre></div>")
            else:
                sec_inner.append(f"<pre class='report-code-block'><code>{html.escape(code_str)}</code></pre>")

        sections_html.append(f"<section class='report-section'>{''.join(sec_inner)}</section>")

    mermaid_script = """
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
  mermaid.initialize({ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' });
</script>
""" if has_mermaid else ""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{
    --primary: #0f172a;
    --accent: #4f46e5;
    --text: #334155;
    --bg-page: #f8fafc;
    --bg-card: #ffffff;
    --border: #e2e8f0;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: var(--text);
    background: var(--bg-page);
    margin: 0;
    padding: 2.5rem 1rem;
  }}
  .container {{
    max-width: 960px;
    margin: 0 auto;
    background: var(--bg-card);
    padding: 3rem;
    border-radius: 14px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.03);
    border: 1px solid var(--border);
  }}
  .header {{
    border-bottom: 2px solid var(--accent);
    padding-bottom: 1.25rem;
    margin-bottom: 1.75rem;
  }}
  .header h1 {{
    font-size: 2.3rem;
    color: var(--primary);
    margin: 0 0 0.5rem 0;
    font-weight: 800;
    letter-spacing: -0.02em;
  }}
  .meta {{
    font-size: 0.9rem;
    color: #64748b;
    display: flex;
    justify-content: space-between;
    font-weight: 500;
  }}
  .dashboard-banner {{
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 2rem;
  }}
  .dashboard-header-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }}
  .dashboard-title {{
    font-size: 0.85rem;
    font-weight: 800;
    color: #1e293b;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }}
  .confidential-pill {{
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 9999px;
    background: #e2e8f0;
    color: #475569;
    letter-spacing: 0.05em;
  }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 1rem;
  }}
  .kpi-card {{
    background: #ffffff;
    border: 1px solid var(--border);
    border-top: 3px solid #10b981;
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }}
  .kpi-card-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.5rem;
  }}
  .kpi-title {{
    font-size: 0.75rem;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    line-height: 1.2;
  }}
  .kpi-badge {{
    font-size: 0.68rem;
    font-weight: 800;
    padding: 1px 6px;
    border-radius: 9999px;
    border: 1px solid;
    white-space: nowrap;
  }}
  .kpi-value {{
    font-size: 1.7rem;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.1;
    margin-bottom: 0.25rem;
  }}
  .kpi-target {{
    font-size: 0.75rem;
    color: #94a3b8;
    font-weight: 500;
  }}
  .section-heading {{
    color: var(--accent);
    margin-top: 2.25rem;
    margin-bottom: 0.85rem;
    font-weight: 800;
    letter-spacing: -0.01em;
  }}
  .report-p {{
    margin-bottom: 0.9rem;
    font-size: 1.02rem;
    color: #334155;
  }}
  .report-ul {{
    padding-left: 1.5rem;
    margin-bottom: 1.25rem;
  }}
  .report-ul li {{
    margin-bottom: 0.45rem;
    font-size: 1.02rem;
  }}
  .table-wrapper {{
    overflow-x: auto;
    margin: 1.5rem 0;
    border-radius: 8px;
    border: 1px solid var(--border);
  }}
  .report-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.92rem;
  }}
  .report-table th, .report-table td {{
    padding: 0.75rem 0.9rem;
    border: 1px solid var(--border);
    text-align: left;
  }}
  .report-table th {{
    background: #f8fafc;
    color: var(--primary);
    font-weight: 700;
  }}
  .report-table tr:nth-child(even) td {{
    background: #fafbfc;
  }}
  .mermaid-diagram-box {{
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 1.25rem;
    margin: 1.5rem 0;
    text-align: center;
  }}
  .mermaid-title {{
    font-size: 0.85rem;
    font-weight: 700;
    color: #475569;
    text-transform: uppercase;
    margin-bottom: 1rem;
    text-align: left;
    letter-spacing: 0.04em;
  }}
  .report-code-block {{
    background: #1e293b;
    color: #f8fafc;
    padding: 1rem;
    border-radius: 8px;
    overflow-x: auto;
    font-family: Consolas, Monaco, "Courier New", monospace;
    font-size: 0.9rem;
  }}
  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 700;
    line-height: 1.2;
    white-space: nowrap;
  }}
  .badge-optimal {{ background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }}
  .badge-critical {{ background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }}
  .badge-high {{ background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }}
  .badge-medium {{ background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }}
  .badge-strategic {{ background: #f0f9ff; color: #0369a1; border: 1px solid #bae6fd; }}
  .footer {{
    margin-top: 3.5rem;
    padding-top: 1.25rem;
    border-top: 1px solid var(--border);
    font-size: 0.82rem;
    color: #94a3b8;
    display: flex;
    justify-content: space-between;
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
      <span>Generated by Local AI Workbench • Fully Air-Gapped</span>
      <span>{date_str}</span>
    </div>
  </div>
  {kpi_grid_html}
  {''.join(sections_html)}
  <div class="footer">
    <span>Synthesized privately on device • Local AI Workbench</span>
    <span>CONFIDENTIAL // EXECUTIVE ACCESS</span>
  </div>
</div>
{mermaid_script}
</body>
</html>"""
    return html_content.encode("utf-8")
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
