import os
import datetime
import subprocess
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import logger
from app.services.ollama_service import ollama_service
from app.services.coding_agent_service import coding_agent_service
from app.services.tool_registry import tool_registry

class ReportGenerateRequest(BaseModel):
    title: str = Field(..., description="Report title or main topic")
    report_type: str = Field(default="executive_summary", description="executive_summary, codebase_audit, test_audit, technical_research, or custom")
    topic_description: str = Field(default="", description="Detailed context, questions, or requirements for the report")
    model: Optional[str] = Field(default=None, description="Ollama model to use")
    save_to_workspace: bool = Field(default=False, description="Whether to write the generated report to a markdown file in workspace")
    output_filename: Optional[str] = Field(default=None, description="Optional custom filename e.g. executive_report.md")

class ReportGenerateResponse(BaseModel):
    title: str
    report_type: str
    model: str
    content: str
    word_count: int
    saved_path: Optional[str] = None
    created_at: str

class ReportService:
    async def generate_report(self, req: ReportGenerateRequest) -> ReportGenerateResponse:
        model_name = req.model or settings.default_model
        now = datetime.datetime.now().strftime("%B %d, %Y - %H:%M")
        
        # 1. Gather context depending on report type
        additional_context = ""
        
        if req.report_type == "codebase_audit":
            tree = await coding_agent_service.get_workspace_tree()
            file_names = [f.path for f in tree.files[:60]]
            git_status = await coding_agent_service.get_git_status()
            additional_context = (
                f"### Workspace Project Files ({len(tree.files)} total):\n"
                f"{json_dump_files(file_names)}\n\n"
                f"### Git Version Control Status:\n"
                f"Is Git: {git_status.is_git_repo}, Branch: {git_status.branch}, Clean: {git_status.clean}\n"
                f"Modified: {git_status.modified}, Untracked: {git_status.untracked}\n"
            )

        elif req.report_type == "test_audit":
            # Run test suite to gather real data
            test_res = await tool_registry.execute_tool("run_project_tests", {"test_path": "backend/tests"})
            test_output = test_res.result if test_res.status == "success" else test_res.error
            additional_context = f"### Test Suite Execution Output:\n```\n{str(test_output)[:3000]}\n```\n"

        # 2. Formulate high-quality system and user prompts
        if req.report_type in ["executive_summary", "executive"]:
            from app.services.report_generator_service import (
                EXECUTIVE_SYSTEM_PROMPT, build_executive_report_prompt, style_report_markdown
            )
            system_prompt = EXECUTIVE_SYSTEM_PROMPT
            user_prompt = build_executive_report_prompt(
                report_title=req.title,
                scope=f"{req.topic_description}\n\n{additional_context}".strip()
            )
        else:
            system_prompt = (
                "You are an elite enterprise analyst, technical architect, and principal researcher. "
                "You specialize in authoring high-density, authoritative, beautifully structured Markdown reports. "
                "Always include: Executive Summary, Clear Section Headers, Markdown Tables where relevant, "
                "Quantitative Assessment, Risk or Limitation Analysis, and Prioritized Actionable Recommendations. "
                "Do not output conversational greetings; output the report content directly."
            )

            user_prompt = f"""
# REQUEST: GENERATE FORMAL {req.report_type.upper().replace('_', ' ')} REPORT

**Report Title:** {req.title}
**Date:** {now}
**Context & Scope:**
{req.topic_description or "Provide a comprehensive, high-quality analysis."}

{additional_context}

Please structure the report with:
1. Executive Summary
2. Core Analysis & Findings (with structured data/tables if applicable)
3. Technical / Strategic Assessment
4. Risk & Mitigations Matrix
5. Prioritized Actionable Roadmap & Recommendations
"""

        # 3. Request LLM completion
        try:
            res = await ollama_service.chat(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                options={"temperature": 0.3}
            )
            content = res.get("message", {}).get("content", "").strip()
            if req.report_type in ["executive_summary", "executive"]:
                from app.services.report_generator_service import style_report_markdown
                content = style_report_markdown(content)
        except Exception as e:
            logger.error(f"Error generating report via LLM: {e}")
            raise RuntimeError(f"Report generation failed: {e}")

        # Compute word count
        word_count = len(content.split())

        # 4. Optional saving to workspace
        saved_path = None
        if req.save_to_workspace:
            clean_filename = req.output_filename or f"REPORT_{req.title.replace(' ', '_').upper()[:30]}.md"
            if not clean_filename.endswith(".md"):
                clean_filename += ".md"
            
            write_res = await tool_registry.execute_tool(
                "write_workspace_file",
                {"path": clean_filename, "content": f"# {req.title}\n*Generated on {now} via Local AI Workbench ({model_name})*\n\n{content}"},
                approved=True
            )
            if write_res.status == "success":
                saved_path = clean_filename

        return ReportGenerateResponse(
            title=req.title,
            report_type=req.report_type,
            model=model_name,
            content=content,
            word_count=word_count,
            saved_path=saved_path,
            created_at=datetime.datetime.now().isoformat()
        )

def json_dump_files(files: List[str]) -> str:
    return "\n".join(f"- {f}" for f in files)

report_service = ReportService()
