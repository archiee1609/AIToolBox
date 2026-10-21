"""
Reusable UI component renderers and HTML helpers.
Contains Windows XP style progress bar and thinking badges.
"""

import html


def render_thinking_badge(phase: str = "thinking", details: str = "") -> str:
    """Renders animated thinking/processing/analysing status badge."""
    if phase == "analysing":
        text = details or "Analysing prompt & context..."
        return f'<div class="ai-thinking-box"><span class="ai-thinking-dots"><span class="ai-thinking-dot"></span><span class="ai-thinking-dot"></span><span class="ai-thinking-dot"></span></span><span class="ai-analysing-shimmer">{text}</span></div>'
    elif phase == "processing":
        text = details or "Processing workspace data..."
        return f'<div class="ai-thinking-box"><span class="ai-thinking-dots"><span class="ai-thinking-dot"></span><span class="ai-thinking-dot"></span><span class="ai-thinking-dot"></span></span><span class="ai-processing-text">{text}</span></div>'
    else:
        text = details or "Thinking..."
        return f'<div class="ai-thinking-box"><span class="ai-thinking-dots"><span class="ai-thinking-dot"></span><span class="ai-thinking-dot"></span><span class="ai-thinking-dot"></span></span><span>{text}</span></div>'


def render_winxp_progress_bar(
    percent: float = 0.0,
    status: str = "downloading",
    detail: str = "",
    is_indeterminate: bool = False
) -> str:
    """
    Renders an authentic Windows XP style segmented green progress bar.
    Displays:
    - Status: Downloading... (with animated or filled green blocks)
    - Status: Complete (Green Tick)
    """
    clamped_pct = max(0.0, min(100.0, float(percent or 0.0)))
    is_stopped = status.lower() in ["stopped", "paused", "cancelled"]
    is_complete = not is_stopped and (status.lower() == "complete" or clamped_pct >= 100.0)

    # Status header
    if is_complete:
        status_html = (
            '<div style="display:flex;align-items:center;gap:7px;">'
            '<span style="font-weight:700;color:#1e293b;font-size:0.9rem;">Status:</span>'
            '<span style="font-weight:800;color:#059669;font-size:0.92rem;">Complete</span>'
            '<span style="display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;background:#10b981;color:white;border-radius:50%;font-size:12px;font-weight:900;box-shadow:0 1px 3px rgba(16,185,129,0.4);">✔</span>'
            '</div>'
        )
        pct_label = '<span style="font-family:monospace;font-weight:800;color:#059669;font-size:0.85rem;">100.0%</span>'
    elif is_stopped:
        status_html = (
            '<div style="display:flex;align-items:center;gap:6px;">'
            '<span style="font-weight:700;color:#1e293b;font-size:0.9rem;">Status:</span>'
            '<span style="font-weight:700;color:#d97706;font-size:0.92rem;">Stopped</span>'
            '<span style="display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;background:#f59e0b;color:white;border-radius:50%;font-size:10px;font-weight:900;">⏹</span>'
            '</div>'
        )
        pct_label = f'<span style="font-family:monospace;font-weight:700;color:#d97706;font-size:0.85rem;">{clamped_pct:.1f}%</span>'
    else:
        status_html = (
            '<div style="display:flex;align-items:center;gap:6px;">'
            '<span style="font-weight:700;color:#1e293b;font-size:0.9rem;">Status:</span>'
            '<span style="font-weight:700;color:#0284c7;font-size:0.92rem;">Downloading...</span>'
            '</div>'
        )
        pct_label = f'<span style="font-family:monospace;font-weight:700;color:#334155;font-size:0.85rem;">{clamped_pct:.1f}%</span>'

    # Progress bar fill style (Windows XP segmented jelly blocks)
    # Segmented blocks: 8px colored brick, 2px white gap
    if is_stopped:
        fill_div = (
            f'<div style="width:{clamped_pct:.1f}%;height:100%;'
            f'background:repeating-linear-gradient(to right, #f59e0b 0px, #f59e0b 8px, #ffffff 8px, #ffffff 10px);'
            f'box-shadow:inset 0 2px 2px rgba(255,255,255,0.85), inset 0 -2px 2px rgba(120,60,0,0.5);'
            f'border-radius:1px;"></div>'
        )
    elif is_indeterminate and not is_complete:
        fill_div = (
            '<div style="width:100%;height:100%;'
            'background:repeating-linear-gradient(to right, #43be1a 0px, #43be1a 8px, #ffffff 8px, #ffffff 10px);'
            'box-shadow:inset 0 2px 2px rgba(255,255,255,0.85), inset 0 -2px 2px rgba(0,60,0,0.5);'
            'animation:winxp-marq 1.6s infinite linear;"></div>'
        )
    else:
        fill_div = (
            f'<div style="width:{clamped_pct:.1f}%;height:100%;'
            f'background:repeating-linear-gradient(to right, #43be1a 0px, #43be1a 8px, #ffffff 8px, #ffffff 10px);'
            f'box-shadow:inset 0 2px 2px rgba(255,255,255,0.85), inset 0 -2px 2px rgba(0,60,0,0.5);'
            f'border-radius:1px;transition:width 0.25s ease-out;"></div>'
        )

    detail_html = ""
    if detail:
        safe_detail = html.escape(str(detail))
        detail_html = f'<div style="font-size:0.75rem;color:#64748b;margin-top:5px;font-family:monospace;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{safe_detail}</div>'

    html_code = (
        f'<div style="background:#f8fafc;border:1px solid #cbd5e1;border-radius:6px;padding:10px 12px;margin:8px 0;box-shadow:0 1px 2px rgba(0,0,0,0.04);">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">'
        f'{status_html}'
        f'{pct_label}'
        f'</div>'
        f'<div style="width:100%;height:22px;background:#ffffff;border:2px solid #7f9db9;border-radius:3px;box-shadow:inset 1px 1px 2px rgba(0,0,0,0.3);padding:2px;box-sizing:border-box;overflow:hidden;">'
        f'{fill_div}'
        f'</div>'
        f'{detail_html}'
        f'</div>'
    )
    return html_code
