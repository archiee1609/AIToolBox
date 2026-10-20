import asyncio
import base64
import io
import json
import os
import sys
import time
from pathlib import Path
from PIL import Image
import httpx

BASE_URL = "http://127.0.0.1:8000"

async def run_comprehensive_system_check():
    results = {}
    print("=" * 60)
    print("  LOCAL AI WORKBENCH - COMPREHENSIVE LIVE SYSTEM TEST")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Root & Frontend Static Serving
        print("\n[1/12] Testing Root & Frontend Static Serving...")
        try:
            r = await client.get(f"{BASE_URL}/")
            assert r.status_code == 200
            assert "<!DOCTYPE html>" in r.text
            assert "Local AI Workbench" in r.text
            print("  [PASS] Root endpoint correctly serves compiled React SPA index.html")
            results["root_frontend"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Root frontend failed: {e}")
            results["root_frontend"] = f"FAIL: {e}"

        # 2. System Health & Diagnostics
        print("\n[2/12] Testing /api/health and Diagnostics...")
        try:
            r = await client.get(f"{BASE_URL}/api/health")
            assert r.status_code == 200
            data = r.json()
            assert data["backend_status"] == "healthy"
            assert data["ollama"]["status"] == "healthy"
            assert "gemma4:12b" in data["installed_models"]
            assert "gpt-oss:latest" in data["installed_models"]
            assert data["database"]["status"] == "healthy"
            assert data["workspace"]["status"] == "healthy"
            print(f"  [PASS] Diagnostics: Ollama v{data['ollama']['details']['version']}, SQLite healthy, models: {data['installed_models']}")
            results["health_check"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Health check failed: {e}")
            results["health_check"] = f"FAIL: {e}"

        # 3. Model Discovery & Tags API
        print("\n[3/12] Testing /api/ollama/models Listing...")
        try:
            r = await client.get(f"{BASE_URL}/api/ollama/models")
            assert r.status_code == 200
            models = r.json()
            assert len(models) >= 2
            gemma = next(m for m in models if "gemma4" in m["name"])
            gpt = next(m for m in models if "gpt-oss" in m["name"])
            assert gemma["capabilities"]["image_understanding"] is True
            assert gemma["capabilities"]["tool_calling"] is True
            assert gpt["capabilities"]["image_understanding"] is False
            print(f"  [PASS] Discovered {len(models)} models with accurate capabilities.")
            results["model_discovery"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Model discovery failed: {e}")
            results["model_discovery"] = f"FAIL: {e}"

        # 4. Conversation Management (CRUD)
        print("\n[4/12] Testing Conversation Lifecycle (Create/Get/Patch/Delete)...")
        conv_id = None
        try:
            # Create
            r = await client.post(f"{BASE_URL}/api/chat/conversations", json={
                "title": "Automated Live Test Conversation",
                "model": "gemma4:12b",
                "temperature": 0.5,
                "context_length": 8192,
                "system_prompt": "You are a helpful assistant."
            })
            assert r.status_code == 200
            conv = r.json()
            conv_id = conv["id"]

            # Get
            r = await client.get(f"{BASE_URL}/api/chat/conversations/{conv_id}")
            assert r.status_code == 200
            assert r.json()["conversation"]["title"] == "Automated Live Test Conversation"

            # Update
            r = await client.patch(f"{BASE_URL}/api/chat/conversations/{conv_id}", json={
                "title": "Updated Live Test Title"
            })
            assert r.status_code == 200
            assert r.json()["title"] == "Updated Live Test Title"

            print(f"  [PASS] Conversation CRUD verified successfully (ID: {conv_id[:8]}...).")
            results["conversation_crud"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Conversation CRUD failed: {e}")
            results["conversation_crud"] = f"FAIL: {e}"

        # 5. Live Chat Streaming with Primary Model (gemma4:12b)
        print("\n[5/12] Testing Real-Time Streaming Chat with 'gemma4:12b'...")
        try:
            tokens_received = []
            async with client.stream("POST", f"{BASE_URL}/api/chat/completions", json={
                "conversation_id": conv_id,
                "message": "Respond with the single word 'VERIFIED' and nothing else.",
                "model": "gemma4:12b",
                "temperature": 0.0,
                "enable_tools": False,
                "stream": True
            }) as stream_res:
                assert stream_res.status_code == 200
                async for chunk in stream_res.aiter_text():
                    for line in chunk.split("\n"):
                        if line.startswith("data: "):
                            try:
                                d = json.loads(line[6:])
                                if d.get("type") == "token":
                                    tokens_received.append(d.get("content", ""))
                            except:
                                pass
            full_reply = "".join(tokens_received).strip()
            assert len(full_reply) > 0
            print(f"  [PASS] gemma4:12b generated streaming response: '{full_reply}'")
            results["chat_stream_gemma4"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Chat stream gemma4 failed: {e}")
            results["chat_stream_gemma4"] = f"FAIL: {e}"

        # 6. Model Switching & Inference with Secondary Model (gpt-oss:latest)
        print("\n[6/12] Testing Model Switching with 'gpt-oss:latest'...")
        try:
            tokens_gpt = []
            async with client.stream("POST", f"{BASE_URL}/api/chat/completions", json={
                "conversation_id": conv_id,
                "message": "Respond with the word 'CONFIRMED'.",
                "model": "gpt-oss:latest",
                "temperature": 0.0,
                "enable_tools": False,
                "stream": True
            }) as stream_res:
                assert stream_res.status_code == 200
                async for chunk in stream_res.aiter_text():
                    for line in chunk.split("\n"):
                        if line.startswith("data: "):
                            try:
                                d = json.loads(line[6:])
                                if d.get("type") == "token":
                                    tokens_gpt.append(d.get("content", ""))
                            except:
                                pass
            reply_gpt = "".join(tokens_gpt).strip()
            assert len(reply_gpt) > 0
            print(f"  [PASS] gpt-oss:latest generated response: '{reply_gpt}'")
            results["chat_stream_gpt_oss"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Model switching gpt-oss failed: {e}")
            results["chat_stream_gpt_oss"] = f"FAIL: {e}"

        # 7. Tool Registry & Tool Execution
        print("\n[7/12] Testing AI Tool Registry and Execution...")
        try:
            # Calculator
            calc_res = await client.post(f"{BASE_URL}/api/tools/execute", json={
                "tool_name": "calculator",
                "arguments": {"expression": "128 * 4 + 12"}
            })
            assert calc_res.status_code == 200
            assert calc_res.json()["result"]["result"] == 524

            # Write file in workspace
            write_res = await client.post(f"{BASE_URL}/api/tools/execute", json={
                "tool_name": "write_workspace_file",
                "arguments": {"path": "test_verification.txt", "content": "Workbench Live Test File"},
                "approved": True
            })
            assert write_res.status_code == 200
            assert write_res.json()["status"] == "success"

            # Read file back
            read_res = await client.post(f"{BASE_URL}/api/tools/execute", json={
                "tool_name": "read_workspace_file",
                "arguments": {"path": "test_verification.txt"}
            })
            assert read_res.status_code == 200
            assert "Workbench Live Test File" in read_res.json()["result"]["content"]

            print("  [PASS] Tools verified: calculator, write_workspace_file, read_workspace_file.")
            results["tools_execution"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Tool execution failed: {e}")
            results["tools_execution"] = f"FAIL: {e}"

        # 8. Vision & Multimodal Image Understanding
        print("\n[8/12] Testing Vision Analysis & Capability Handling...")
        try:
            # Create a tiny 64x64 valid red PNG in memory
            img = Image.new("RGB", (64, 64), color="red")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

            # Test with vision-capable model (gemma4:12b)
            v_res = await client.post(f"{BASE_URL}/api/vision/analyze", json={
                "image_data": img_b64,
                "prompt": "What primary color is this image? Reply in one word.",
                "model": "gemma4:12b"
            })
            assert v_res.status_code == 200
            v_data = v_res.json()
            assert v_data["capability_supported"] is True
            assert len(v_data["response"]) > 0
            print(f"  [PASS] Vision analysis with gemma4:12b: '{v_data['response'].strip()}'")

            # Test with non-vision model (gpt-oss:latest) - must return capability warning
            nv_res = await client.post(f"{BASE_URL}/api/vision/analyze", json={
                "image_data": img_b64,
                "prompt": "Color?",
                "model": "gpt-oss:latest"
            })
            assert nv_res.status_code == 200
            nv_data = nv_res.json()
            assert nv_data["capability_supported"] is False
            assert "does not support visual inputs" in nv_data["response"]
            print(f"  [PASS] Non-vision capability handling correctly warned user.")
            results["vision_multimodal"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Vision test failed: {e}")
            results["vision_multimodal"] = f"FAIL: {e}"

        # 9. Coding Agent Workspace, Unified Diff, & Patching
        print("\n[9/12] Testing Coding Agent Diff and Approval...")
        try:
            # 1. Tree
            tree_res = await client.get(f"{BASE_URL}/api/coding/workspace/tree")
            assert tree_res.status_code == 200
            assert "workspace_root" in tree_res.json()

            # 2. Compute Diff
            diff_res = await client.post(f"{BASE_URL}/api/coding/diff", json={
                "path": "test_verification.txt",
                "new_content": "Workbench Live Test File - Modified by Agent"
            })
            assert diff_res.status_code == 200
            diff_content = diff_res.json()["diff"]
            assert "+Workbench Live Test File - Modified by Agent" in diff_content

            # 3. Create Task & Apply Changes
            task_res = await client.post(f"{BASE_URL}/api/coding/tasks", json={
                "task_description": "Live Diff Update Verification"
            })
            task_id = task_res.json()["id"]

            apply_res = await client.post(f"{BASE_URL}/api/coding/tasks/{task_id}/apply", json={
                "approved": True,
                "file_changes": [{
                    "path": "test_verification.txt",
                    "content": "Workbench Live Test File - Modified by Agent"
                }]
            })
            assert apply_res.status_code == 200
            assert apply_res.json()["status"] == "applied"
            print("  [PASS] Coding agent workspace inspection, diff generation, and approved patching verified.")
            results["coding_agent"] = "PASS"
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"  [FAIL] Coding agent failed: {e}\n{tb}")
            results["coding_agent"] = f"FAIL: {e}"

        # 10. Workflow Automation Engine (Dry-Run & Execution)
        print("\n[10/12] Testing Automation Engine...")
        try:
            wf_res = await client.post(f"{BASE_URL}/api/automation/workflows", json={
                "name": "Live Test Pipeline",
                "description": "Reads test file and saves copy",
                "steps": [
                    {"id": "s1", "action_type": "read_files", "parameters": {"pattern": "test_verification.txt"}},
                    {"id": "s2", "action_type": "write_file", "parameters": {"output_path": "pipeline_output.txt"}}
                ]
            })
            wf = wf_res.json()
            wf_id = wf["id"]

            # Preview
            prev_res = await client.post(f"{BASE_URL}/api/automation/workflows/{wf_id}/preview")
            assert prev_res.status_code == 200
            assert prev_res.json()["valid"] is True

            # Run
            run_res = await client.post(f"{BASE_URL}/api/automation/workflows/{wf_id}/run", json={"confirmed": True})
            assert run_res.status_code == 200
            assert run_res.json()["status"] == "completed"

            # Clean up workflow
            await client.delete(f"{BASE_URL}/api/automation/workflows/{wf_id}")
            print("  [PASS] Workflow creation, dry-run preview, and execution verified.")
            results["workflow_automation"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Automation failed: {e}")
            results["workflow_automation"] = f"FAIL: {e}"

        # 11. ComfyUI Image Lab Offline Handling
        print("\n[11/12] Testing Image Lab ComfyUI Offline Status & Actionable Guide...")
        try:
            c_res = await client.get(f"{BASE_URL}/api/image_lab/status")
            assert c_res.status_code == 200
            c_data = c_res.json()
            # When ComfyUI is offline, must be unreachable with instructions
            if not c_data["is_reachable"]:
                assert "To enable local image generation" in c_data["actionable_instructions"]
                print("  [PASS] ComfyUI offline status honest and actionable instructions provided.")
            else:
                print("  [PASS] ComfyUI online and reachable.")
            results["image_lab_status"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Image lab test failed: {e}")
            results["image_lab_status"] = f"FAIL: {e}"

        # 12. Security Enforcement & Path Traversal Protection
        print("\n[12/12] Testing Security Sandbox & Path Traversal Rejection...")
        try:
            # Traversal attempt on file read
            bad_read = await client.post(f"{BASE_URL}/api/coding/workspace/read", json={
                "path": "../../Windows/System32/drivers/etc/hosts"
            })
            assert bad_read.status_code in [400, 403]

            # Null byte attempt
            bad_null = await client.post(f"{BASE_URL}/api/coding/workspace/read", json={
                "path": "test\0escape.txt"
            })
            assert bad_null.status_code in [400, 403]

            # Hot backup creation & validation
            backup_res = await client.post(f"{BASE_URL}/api/settings/backups")
            assert backup_res.status_code == 200
            b_data = backup_res.json()
            assert b_data["filename"].startswith("workbench_backup_")

            print("  [PASS] Path traversal rejected (403/400). Hot SQLite backup generated and verified.")
            results["security_and_backup"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Security check failed: {e}")
            results["security_and_backup"] = f"FAIL: {e}"

        # 13. Report Generation
        print("\n[13/14] Testing Executive Report Generation API...")
        try:
            report_res = await client.post(f"{BASE_URL}/api/reports/generate", json={
                "title": "Automated Live System Audit",
                "report_type": "executive_summary",
                "topic_description": "Validate report structure and synthesis capability.",
                "model": "gemma4:12b",
                "save_to_workspace": False
            })
            assert report_res.status_code == 200
            rep_data = report_res.json()
            assert rep_data["word_count"] > 20
            assert "Automated Live System Audit" in rep_data["title"]
            print(f"  [PASS] Report generated successfully ({rep_data['word_count']} words via {rep_data['model']}).")
            results["report_generation"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Report generation failed: {e}")
            results["report_generation"] = f"FAIL: {e}"

        # 14. Model Pull Provision API
        print("\n[14/14] Testing Model Pull Provision API...")
        try:
            # Validate empty model name is rejected
            bad_pull = await client.post(f"{BASE_URL}/api/ollama/pull", json={"name": ""})
            assert bad_pull.status_code == 400
            print("  [PASS] Model installation endpoint operational and validates model tags.")
            results["model_install_provision"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Model pull provision failed: {e}")
            results["model_install_provision"] = f"FAIL: {e}"

        # Clean up temporary test files in workspace
        for temp_name in ["test_verification.txt", "pipeline_output.txt"]:
            p = Path("workspace") / temp_name
            if p.exists():
                p.unlink()

        # Clean up conversation
        if conv_id:
            await client.delete(f"{BASE_URL}/api/chat/conversations/{conv_id}")

    print("\n" + "=" * 60)
    print("  LIVE SYSTEM TEST SUMMARY")
    print("=" * 60)
    all_pass = all(v == "PASS" for v in results.values())
    for name, res in results.items():
        print(f"  {name.ljust(25)}: {res}")
    print("=" * 60)
    print(f"  OVERALL RESULT: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
    print("=" * 60)
    return all_pass

if __name__ == "__main__":
    success = asyncio.run(run_comprehensive_system_check())
    sys.exit(0 if success else 1)
