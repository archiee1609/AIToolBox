from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class MessageCreate(BaseModel):
    role: str
    content: str
    images: Optional[List[str]] = Field(default_factory=list) # base64 or paths
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    images: List[str] = Field(default_factory=list)
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    token_count: int = 0
    created_at: str

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    model: str
    system_prompt: Optional[str] = ""
    temperature: Optional[float] = 0.7
    context_length: Optional[int] = 8192

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    context_length: Optional[int] = None

class ConversationResponse(BaseModel):
    id: str
    title: str
    model: str
    system_prompt: str
    temperature: float
    context_length: int
    created_at: str
    updated_at: str
    message_count: Optional[int] = 0

class ChatCompletionRequest(BaseModel):
    conversation_id: str
    message: str
    images: Optional[List[str]] = Field(default_factory=list)
    model: Optional[str] = None
    temperature: Optional[float] = None
    context_length: Optional[int] = None
    enable_tools: bool = True
    stream: bool = True
