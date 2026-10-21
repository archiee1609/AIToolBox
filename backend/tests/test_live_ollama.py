import pytest
from app.services.ollama_service import ollama_service

@pytest.mark.asyncio
async def test_live_ollama_model_discovery():
    await ollama_service.ensure_running()
    health = await ollama_service.check_health()
    assert health["reachable"] is True
    assert health["version"] is not None

    models = await ollama_service.list_models()
    assert len(models) >= 1
    model_names = [m.name for m in models]
    assert any("gemma4" in n or "gpt-oss" in n for n in model_names)

@pytest.mark.asyncio
async def test_live_ollama_chat_completion():
    models = await ollama_service.list_models()
    target_model = models[0].name
    
    res = await ollama_service.chat(
        model=target_model,
        messages=[{"role": "user", "content": "Respond with only the number 42."}],
        options={"temperature": 0.0}
    )
    content = res.get("message", {}).get("content", "")
    assert len(content.strip()) > 0
