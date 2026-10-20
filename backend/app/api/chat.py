import asyncio
import datetime
import json
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.logging import logger
from app.database.connection import db
from app.services.ollama_service import ollama_service
from app.services.tool_registry import tool_registry
from app.schemas.chat import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    MessageResponse,
    ChatCompletionRequest
)

router = APIRouter(prefix="/chat", tags=["Chat & Conversations"])

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations():
    rows = await db.fetchall(
        """
        SELECT c.*, COUNT(m.id) AS message_count
        FROM conversations c
        LEFT JOIN messages m ON c.id = m.conversation_id
        GROUP BY c.id
        ORDER BY c.updated_at DESC
        """
    )
    return [
        ConversationResponse(
            id=r["id"],
            title=r["title"],
            model=r["model"],
            system_prompt=r["system_prompt"] or "",
            temperature=r["temperature"] or 0.7,
            context_length=r["context_length"] or 8192,
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            message_count=r["message_count"]
        )
        for r in rows
    ]

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(req: ConversationCreate):
    conv_id = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()
    await db.execute(
        """
        INSERT INTO conversations (id, title, model, system_prompt, temperature, context_length, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            conv_id,
            req.title or "New Conversation",
            req.model,
            req.system_prompt or "",
            req.temperature if req.temperature is not None else 0.7,
            req.context_length if req.context_length is not None else 8192,
            now,
            now
        )
    )
    return ConversationResponse(
        id=conv_id,
        title=req.title or "New Conversation",
        model=req.model,
        system_prompt=req.system_prompt or "",
        temperature=req.temperature or 0.7,
        context_length=req.context_length or 8192,
        created_at=now,
        updated_at=now,
        message_count=0
    )

@router.get("/conversations/search")
async def search_conversations(q: str = Query(..., min_length=1)):
    search_param = f"%{q}%"
    rows = await db.fetchall(
        """
        SELECT DISTINCT c.id, c.title, c.model, c.updated_at, m.content AS matched_content
        FROM conversations c
        LEFT JOIN messages m ON c.id = m.conversation_id
        WHERE c.title LIKE ? OR m.content LIKE ?
        ORDER BY c.updated_at DESC LIMIT 20
        """,
        (search_param, search_param)
    )
    return rows

@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    conv = await db.fetchone("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    
    msgs = await db.fetchall(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,)
    )
    
    return {
        "conversation": dict(conv),
        "messages": [
            MessageResponse(
                id=m["id"],
                conversation_id=m["conversation_id"],
                role=m["role"],
                content=m["content"],
                images=json.loads(m["images_json"] or "[]"),
                tool_calls=json.loads(m["tool_calls_json"]) if m["tool_calls_json"] else None,
                tool_call_id=m["tool_call_id"],
                token_count=m["token_count"] or 0,
                created_at=m["created_at"]
            )
            for m in msgs
        ]
    }

@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(conversation_id: str, req: ConversationUpdate):
    conv = await db.fetchone("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    
    now = datetime.datetime.now().isoformat()
    new_title = req.title if req.title is not None else conv["title"]
    new_model = req.model if req.model is not None else conv["model"]
    new_sys = req.system_prompt if req.system_prompt is not None else conv["system_prompt"]
    new_temp = req.temperature if req.temperature is not None else conv["temperature"]
    new_ctx = req.context_length if req.context_length is not None else conv["context_length"]

    await db.execute(
        """
        UPDATE conversations
        SET title = ?, model = ?, system_prompt = ?, temperature = ?, context_length = ?, updated_at = ?
        WHERE id = ?
        """,
        (new_title, new_model, new_sys, new_temp, new_ctx, now, conversation_id)
    )

    return ConversationResponse(
        id=conversation_id,
        title=new_title,
        model=new_model,
        system_prompt=new_sys,
        temperature=new_temp,
        context_length=new_ctx,
        created_at=conv["created_at"],
        updated_at=now,
        message_count=0
    )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    conv = await db.fetchone("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    await db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    return {"deleted": True, "id": conversation_id}

@router.post("/completions")
async def chat_completions(req: ChatCompletionRequest):
    conv = await db.fetchone("SELECT * FROM conversations WHERE id = ?", (req.conversation_id,))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    model_name = req.model or conv["model"]
    now = datetime.datetime.now().isoformat()

    # 1. Save user message to database immediately to prevent loss
    user_msg_id = str(uuid.uuid4())
    clean_images = []
    for img in req.images or []:
        # If it's a data URL, strip prefix for Ollama
        if "," in img and "data:image" in img:
            clean_images.append(img.split(",", 1)[1])
        else:
            clean_images.append(img)

    await db.execute(
        """
        INSERT INTO messages (id, conversation_id, role, content, images_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_msg_id, req.conversation_id, "user", req.message, json.dumps(clean_images), now)
    )

    # Auto-title conversation if default title
    if conv["title"] == "New Conversation":
        new_title = req.message.strip().split("\n")[0][:40] or "Conversation"
        await db.execute("UPDATE conversations SET title = ? WHERE id = ?", (new_title, req.conversation_id))

    # 2. Build conversation history from database
    history_rows = await db.fetchall(
        "SELECT role, content, images_json, tool_calls_json FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (req.conversation_id,)
    )

    # Load active long-term memories and project workspace rules
    active_memories = await db.fetchall("SELECT key, content, source_tool, category FROM user_memories WHERE enabled = 1 ORDER BY updated_at DESC")
    ws_str = str(settings.workspace_root)
    proj_mem = await db.fetchone("SELECT instructions, context_summary FROM project_memory WHERE workspace_path = ?", (ws_str,))

    memory_prompt_sections = []
    if proj_mem:
        if proj_mem["instructions"]:
            memory_prompt_sections.append(f"### Project Workspace Rules:\n{proj_mem['instructions']}")
        if proj_mem["context_summary"]:
            memory_prompt_sections.append(f"### Workspace Context:\n{proj_mem['context_summary']}")

    if active_memories:
        mem_items = []
        for m in active_memories:
            src = m.get("source_tool", "AI").upper() if m.get("source_tool") else "AI"
            cat = f" ({m.get('category')})" if m.get("category") else ""
            mem_items.append(f"- [{src}{cat}] **{m['key']}**: {m['content']}")
        memory_prompt_sections.append("### Active Long-Term Memories & AI Tool Guidelines:\n" + "\n".join(mem_items))

    base_system = (conv["system_prompt"] or "").strip()
    if memory_prompt_sections:
        mem_block = "\n\n".join(memory_prompt_sections)
        if base_system:
            final_system = f"{base_system}\n\n---\n{mem_block}"
        else:
            final_system = mem_block
    else:
        final_system = base_system

    ollama_messages = []
    if final_system:
        ollama_messages.append({"role": "system", "content": final_system})

    for row in history_rows:
        msg_obj: Dict[str, Any] = {"role": row["role"], "content": row["content"]}
        imgs = json.loads(row["images_json"] or "[]")
        if imgs:
            msg_obj["images"] = imgs
        tool_calls = json.loads(row["tool_calls_json"] or "[]")
        if tool_calls:
            msg_obj["tool_calls"] = tool_calls
        ollama_messages.append(msg_obj)

    # 3. Determine available tools
    tools_schema = tool_registry.get_ollama_tools_schema() if req.enable_tools else None

    # 4. SSE Streaming Generator
    async def event_generator():
        assistant_msg_id = str(uuid.uuid4())
        full_content = ""
        current_messages = list(ollama_messages)
        iterations = 0
        max_iterations = settings.max_tool_iterations

        try:
            while iterations < max_iterations:
                iterations += 1
                stream_gen = ollama_service.stream_chat(
                    model=model_name,
                    messages=current_messages,
                    options={
                        "temperature": req.temperature or conv["temperature"] or 0.7,
                        "num_ctx": req.context_length or conv["context_length"] or 8192
                    },
                    tools=tools_schema
                )

                tool_calls_accumulator = []
                chunk_content = ""

                async for chunk in stream_gen:
                    msg = chunk.get("message", {})
                    token = msg.get("content", "")
                    if token:
                        chunk_content += token
                        full_content += token
                        payload = json.dumps({"type": "token", "content": token})
                        yield f"data: {payload}\n\n"

                    # Check for tool call
                    tool_calls = msg.get("tool_calls", [])
                    if tool_calls:
                        tool_calls_accumulator.extend(tool_calls)

                # Check if assistant requested tool execution
                if tool_calls_accumulator:
                    payload = json.dumps({
                        "type": "tool_calls_requested",
                        "tool_calls": tool_calls_accumulator
                    })
                    yield f"data: {payload}\n\n"

                    # Add assistant's message with tool calls to context
                    current_messages.append({
                        "role": "assistant",
                        "content": chunk_content,
                        "tool_calls": tool_calls_accumulator
                    })

                    # Execute each tool
                    for tc in tool_calls_accumulator:
                        func = tc.get("function", {})
                        t_name = func.get("name", "")
                        t_args = func.get("arguments", {})
                        
                        tool_res = await tool_registry.execute_tool(
                            name=t_name,
                            arguments=t_args,
                            conversation_id=req.conversation_id,
                            approved=True # Handled via tool registry policies
                        )

                        tool_output_payload = json.dumps({
                            "type": "tool_result",
                            "tool_name": t_name,
                            "result": tool_res.result,
                            "status": tool_res.status,
                            "error": tool_res.error
                        })
                        yield f"data: {tool_output_payload}\n\n"

                        # Feed tool result back to model as role: tool
                        current_messages.append({
                            "role": "tool",
                            "content": json.dumps(tool_res.result or tool_res.error or "completed")
                        })

                    # Loop continues so model can respond using tool result
                    continue

                # No tool calls, generation for this turn complete
                break

            # 5. Persist assistant response to DB
            now_res = datetime.datetime.now().isoformat()
            await db.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (assistant_msg_id, req.conversation_id, "assistant", full_content, now_res)
            )

            await db.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now_res, req.conversation_id)
            )

            done_payload = json.dumps({
                "type": "done",
                "message_id": assistant_msg_id,
                "content": full_content
            })
            yield f"data: {done_payload}\n\n"

        except Exception as e:
            logger.exception(f"Chat stream generation error: {e}")
            err_payload = json.dumps({
                "type": "error",
                "error": str(e),
                "partial_content": full_content
            })
            yield f"data: {err_payload}\n\n"
            # If we received any partial content, save it
            if full_content.strip():
                now_res = datetime.datetime.now().isoformat()
                await db.execute(
                    """
                    INSERT INTO messages (id, conversation_id, role, content, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (assistant_msg_id, req.conversation_id, "assistant", full_content + f"\n\n[Error: {str(e)}]", now_res)
                )

    return StreamingResponse(event_generator(), media_type="text/event-stream")
