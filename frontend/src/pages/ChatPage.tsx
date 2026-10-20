import React, { useState, useEffect, useRef } from 'react';
import {
  Plus,
  Send,
  Trash2,
  Search,
  Sliders,
  Copy,
  Check,
  Square,
  Paperclip,
  Wrench,
  Bot,
  User,
  AlertTriangle,
  Sparkles,
  RefreshCw,
  X
} from 'lucide-react';
import { api } from '../services/api';
import { Conversation, Message, ModelDetails } from '../types';
import { MarkdownRenderer } from '../components/MarkdownRenderer';

interface ChatPageProps {
  selectedModel: string;
  models: ModelDetails[];
  ollamaOnline: boolean;
}

export const ChatPage: React.FC<ChatPageProps> = ({ selectedModel, models, ollamaOnline }) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [toolStatus, setToolStatus] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [attachedImages, setAttachedImages] = useState<string[]>([]);
  const [temperature, setTemperature] = useState(0.7);
  const [contextLength, setContextLength] = useState(8192);
  const [systemPrompt, setSystemPrompt] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load conversations
  const loadConversations = async () => {
    try {
      const list = await api.listConversations();
      setConversations(list);
      if (list.length > 0 && !activeConvId) {
        setActiveConvId(list[0].id);
      }
    } catch (e) {
      console.error('Failed to load conversations', e);
    }
  };

  useEffect(() => {
    loadConversations();
  }, []);

  // Load active conversation messages
  useEffect(() => {
    if (!activeConvId) return;
    api.getConversation(activeConvId).then(res => {
      setMessages(res.messages);
      setTemperature(res.conversation.temperature || 0.7);
      setContextLength(res.conversation.context_length || 8192);
      setSystemPrompt(res.conversation.system_prompt || '');
    }).catch(console.error);
  }, [activeConvId]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Create new conversation
  const handleNewConversation = async () => {
    try {
      const conv = await api.createConversation({
        title: 'New Conversation',
        model: selectedModel || (models[0]?.name ?? 'gemma4:12b'),
        temperature,
        context_length: contextLength,
        system_prompt: systemPrompt
      });
      setConversations([conv, ...conversations]);
      setActiveConvId(conv.id);
      setMessages([]);
    } catch (e) {
      console.error('Failed to create conversation', e);
    }
  };

  // Delete conversation
  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    try {
      await api.deleteConversation(id);
      const remaining = conversations.filter(c => c.id !== id);
      setConversations(remaining);
      if (activeConvId === id) {
        setActiveConvId(remaining[0]?.id || null);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Handle image attachment
  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const file = files[0];
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setAttachedImages([...attachedImages, reader.result]);
      }
    };
    reader.readAsDataURL(file);
  };

  // Copy message
  const copyMessage = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Submit message
  const handleSendMessage = async () => {
    if ((!inputText.trim() && attachedImages.length === 0) || isGenerating) return;

    let convId = activeConvId;
    if (!convId) {
      const newConv = await api.createConversation({
        title: inputText.slice(0, 30) || 'New Conversation',
        model: selectedModel || (models[0]?.name ?? 'gemma4:12b'),
        temperature,
        context_length: contextLength,
        system_prompt: systemPrompt
      });
      convId = newConv.id;
      setActiveConvId(convId);
      setConversations([newConv, ...conversations]);
    }

    const currentInput = inputText;
    const currentImgs = [...attachedImages];
    setInputText('');
    setAttachedImages([]);
    setIsGenerating(true);
    setStreamingContent('');
    setToolStatus(null);

    // Optimistically add user message
    const tempUserMsg: Message = {
      id: Date.now().toString(),
      conversation_id: convId,
      role: 'user',
      content: currentInput,
      images: currentImgs,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('/api/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: convId,
          message: currentInput,
          images: currentImgs,
          model: selectedModel,
          temperature,
          context_length: contextLength,
          enable_tools: true,
          stream: true
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`Chat API error: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let accumulatedText = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.type === 'token') {
                  accumulatedText += data.content;
                  setStreamingContent(accumulatedText);
                } else if (data.type === 'tool_calls_requested') {
                  const names = data.tool_calls.map((t: any) => t.function?.name).join(', ');
                  setToolStatus(`Executing tool: ${names}`);
                } else if (data.type === 'tool_result') {
                  setToolStatus(`Tool '${data.tool_name}' completed.`);
                } else if (data.type === 'done') {
                  setIsGenerating(false);
                  setStreamingContent('');
                  setToolStatus(null);
                  api.getConversation(convId).then(r => setMessages(r.messages));
                } else if (data.type === 'error') {
                  console.error('Stream error:', data.error);
                  setIsGenerating(false);
                }
              } catch {
                // ignore chunk parse
              }
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error('Chat error:', err);
      }
    } finally {
      setIsGenerating(false);
      loadConversations();
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsGenerating(false);
      setToolStatus(null);
    }
  };

  const filteredConversations = conversations.filter(c =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex h-full overflow-hidden" style={{ backgroundColor: 'var(--bg-canvas)' }}>
      {/* Conversation Thread Sidebar */}
      <div
        className="flex flex-col border-r select-none"
        style={{
          width: '260px',
          backgroundColor: 'var(--bg-sidebar)',
          borderColor: 'var(--border-subtle)'
        }}
      >
        <div className="p-3 border-b border-subtle flex flex-col gap-2">
          <button
            onClick={handleNewConversation}
            className="btn btn-primary w-full py-2 flex items-center justify-center gap-2 text-xs font-semibold"
          >
            <Plus size={15} />
            <span>New Chat</span>
          </button>

          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-2.5 text-dim pointer-events-none" />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="input-text text-2xs pl-8 py-1.5 font-mono"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-1.5 flex flex-col gap-1">
          {filteredConversations.length === 0 ? (
            <div className="text-center text-2xs text-dim p-6">No conversations found.</div>
          ) : (
            filteredConversations.map(c => {
              const isActive = c.id === activeConvId;
              return (
                <div
                  key={c.id}
                  onClick={() => setActiveConvId(c.id)}
                  className={`group flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer transition text-xs ${
                    isActive
                      ? 'text-white font-medium shadow-sm'
                      : 'text-muted hover:text-main hover:bg-card'
                  }`}
                  style={
                    isActive
                      ? {
                          backgroundColor: 'var(--bg-card)',
                          border: '1px solid var(--border-main)',
                          color: '#ffffff'
                        }
                      : { border: '1px solid transparent' }
                  }
                >
                  <div className="truncate flex-1 pr-2">
                    <p className="truncate text-xs">{c.title}</p>
                    <span className="text-2xs text-dim font-mono">{c.model}</span>
                  </div>
                  <button
                    onClick={e => handleDeleteConversation(c.id, e)}
                    className="opacity-0 group-hover:opacity-100 text-dim hover:text-danger p-1 rounded transition"
                    title="Delete conversation"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Main Conversation Stream & Input */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Top Control Bar */}
        <div
          className="px-5 py-2.5 border-b border-subtle flex items-center justify-between text-xs"
          style={{ backgroundColor: 'var(--bg-panel)' }}
        >
          <div className="flex items-center gap-2">
            <div className="badge badge-accent font-mono text-2xs flex items-center gap-1.5">
              <Bot size={12} />
              <span>{selectedModel || 'Select Model'}</span>
            </div>
            {!ollamaOnline && (
              <span className="badge badge-warning text-2xs flex items-center gap-1">
                <AlertTriangle size={11} /> Ollama Offline
              </span>
            )}
          </div>

          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`btn btn-ghost text-xs py-1 px-2.5 flex items-center gap-1.5 ${
              showSettings ? 'text-accent bg-card' : ''
            }`}
          >
            <Sliders size={13} />
            <span>Parameters</span>
          </button>
        </div>

        {/* Configuration Drawer */}
        {showSettings && (
          <div
            className="p-4 border-b border-subtle flex flex-wrap gap-5 text-xs animate-in"
            style={{ backgroundColor: 'var(--bg-card)' }}
          >
            <div className="flex flex-col gap-1 w-44">
              <div className="flex justify-between text-2xs text-muted font-mono">
                <span>Temperature</span>
                <span className="text-main font-semibold">{temperature}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.5"
                step="0.05"
                value={temperature}
                onChange={e => setTemperature(parseFloat(e.target.value))}
                className="accent-indigo-500 cursor-pointer"
              />
            </div>

            <div className="flex flex-col gap-1 w-44">
              <label className="text-2xs text-muted font-mono">Context Window</label>
              <select
                value={contextLength}
                onChange={e => setContextLength(parseInt(e.target.value))}
                className="input-select text-2xs py-1 font-mono"
              >
                <option value={4096}>4,096 tokens</option>
                <option value={8192}>8,192 tokens</option>
                <option value={16384}>16,384 tokens</option>
                <option value={32768}>32,768 tokens</option>
                <option value={65536}>65,536 tokens</option>
              </select>
            </div>

            <div className="flex-1 min-w-[240px]">
              <label className="text-2xs text-muted font-mono">System Instructions</label>
              <input
                type="text"
                placeholder="Optional system prompt..."
                value={systemPrompt}
                onChange={e => setSystemPrompt(e.target.value)}
                className="input-text text-xs py-1"
              />
            </div>
          </div>
        )}

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-5">
          {messages.length === 0 && !streamingContent && (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-muted max-w-lg mx-auto">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center text-white mb-4 shadow-xl"
                style={{
                  background: 'linear-gradient(135deg, #6366f1 0%, #4338ca 100%)',
                  boxShadow: '0 4px 20px rgba(99, 102, 241, 0.35)'
                }}
              >
                <Sparkles size={26} />
              </div>
              <h3 className="text-base font-bold text-main mb-1.5">Welcome to Local AI Workbench</h3>
              <p className="text-xs text-muted leading-relaxed mb-6">
                Private, local-first intelligence running natively on your workstation. No cloud API keys or telemetry.
              </p>
              <div className="grid grid-cols-2 gap-2.5 w-full">
                <button
                  onClick={() => setInputText('How is this application architected and secured?')}
                  className="card p-3 text-left hover:border-accent transition cursor-pointer"
                >
                  <p className="text-xs font-semibold text-main mb-1">Architecture & Security</p>
                  <p className="text-2xs text-muted">Inspect local sandboxing and policies</p>
                </button>
                <button
                  onClick={() => setInputText('Use the calculator tool to compute 2^16 - 1.')}
                  className="card p-3 text-left hover:border-accent transition cursor-pointer"
                >
                  <p className="text-xs font-semibold text-main mb-1">Tool Calling</p>
                  <p className="text-2xs text-muted">Execute backend tools with safety checks</p>
                </button>
              </div>
            </div>
          )}

          {messages.map(msg => {
            const isUser = msg.role === 'user';
            return (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-3xl ${isUser ? 'ml-auto' : 'mr-auto'} w-full`}
              >
                {/* Avatar */}
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-white font-mono text-2xs ${
                    isUser
                      ? 'bg-slate-700 shadow-sm'
                      : 'bg-indigo-600 shadow-md'
                  }`}
                  style={!isUser ? { background: 'linear-gradient(135deg, #6366f1 0%, #4338ca 100%)' } : undefined}
                >
                  {isUser ? <User size={14} /> : <Bot size={14} />}
                </div>

                {/* Message Body */}
                <div
                  className={`flex-1 rounded-2xl p-4 shadow-sm ${
                    isUser
                      ? 'rounded-tr-none bg-gradient-to-r from-indigo-600 to-indigo-700 text-white'
                      : 'rounded-tl-none bg-white border border-slate-200'
                  }`}
                >
                  {/* Images attachments */}
                  {msg.images && msg.images.length > 0 && (
                    <div className="flex gap-2 mb-3">
                      {msg.images.map((img, i) => (
                        <img
                          key={i}
                          src={img.startsWith('data:') ? img : `data:image/jpeg;base64,${img}`}
                          alt="Attachment"
                          className="max-h-56 rounded-lg border object-contain bg-slate-900 border-slate-200"
                        />
                      ))}
                    </div>
                  )}

                  {/* Render content: user messages are text, assistant messages are rich markdown */}
                  {isUser ? (
                    <div className="text-xs leading-relaxed select-text font-sans text-white whitespace-pre-wrap">
                      {msg.content}
                    </div>
                  ) : (
                    <div className="text-xs leading-relaxed select-text font-sans text-slate-800">
                      <MarkdownRenderer content={msg.content} />
                    </div>
                  )}

                  {/* Message Footer */}
                  <div
                    className={`flex items-center justify-between mt-2.5 pt-2 border-t text-2xs font-mono ${
                      isUser ? 'border-indigo-500/40 text-indigo-200' : 'border-slate-100 text-slate-400'
                    }`}
                  >
                    <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    <button
                      onClick={() => copyMessage(msg.id, msg.content)}
                      className="hover:text-main transition flex items-center gap-1"
                      title="Copy response"
                    >
                      {copiedId === msg.id ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                      <span>{copiedId === msg.id ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}

          {/* Real-time Streaming Response */}
          {streamingContent && (
            <div className="flex gap-3 max-w-3xl mr-auto w-full">
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-white shadow-md"
                style={{ background: 'linear-gradient(135deg, #6366f1 0%, #4338ca 100%)' }}
              >
                <Bot size={14} />
              </div>
              <div
                className="flex-1 card rounded-xl rounded-tl-none p-3.5 border-accent"
                style={{ boxShadow: '0 0 20px var(--accent-glow)' }}
              >
                {toolStatus && (
                  <div className="badge badge-accent mb-2.5 font-mono text-2xs flex items-center gap-1.5 py-1 px-2.5">
                    <Wrench size={12} className="animate-spin" />
                    <span>{toolStatus}</span>
                  </div>
                )}
                <MarkdownRenderer content={streamingContent} />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Floating Docked Prompt Composer */}
        <div className="p-4 bg-gradient-to-t from-slate-50 via-slate-50 to-transparent select-none">
          <div className="bg-white p-3 rounded-2xl border border-slate-200 flex flex-col gap-2 max-w-3xl mx-auto shadow-floating focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-100 transition-all">
            {/* Attached Image Chips */}
            {attachedImages.length > 0 && (
              <div className="flex gap-2 px-2 pt-1">
                {attachedImages.map((img, idx) => (
                  <div key={idx} className="relative group">
                    <img src={img} alt="attachment" className="h-14 w-14 object-cover rounded-lg border border-subtle" />
                    <button
                      onClick={() => setAttachedImages(attachedImages.filter((_, i) => i !== idx))}
                      className="absolute -top-1.5 -right-1.5 bg-danger text-white rounded-full p-0.5 hover:scale-110 transition shadow-sm"
                    >
                      <X size={11} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Prompt Input Box */}
            <div className="flex items-end gap-2 px-1">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleImageUpload}
                accept="image/*"
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="btn btn-ghost p-2 rounded-lg text-muted hover:text-main"
                title="Attach image for multimodal understanding"
              >
                <Paperclip size={16} />
              </button>

              <textarea
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder={ollamaOnline ? "Ask anything... (Enter to send, Shift+Enter for newline)" : "Ollama is currently offline on http://127.0.0.1:11434"}
                disabled={!ollamaOnline && !inputText}
                rows={Math.min(5, Math.max(1, inputText.split('\n').length))}
                className="flex-1 bg-transparent border-0 outline-none text-xs text-main resize-none p-1.5 leading-relaxed font-sans placeholder-dim"
              />

              {isGenerating ? (
                <button
                  onClick={handleStop}
                  className="btn btn-danger py-1.5 px-3 rounded-lg flex items-center gap-1.5 text-xs font-semibold"
                  title="Stop generation"
                >
                  <Square size={12} />
                  <span>Stop</span>
                </button>
              ) : (
                <button
                  onClick={handleSendMessage}
                  disabled={!inputText.trim() && attachedImages.length === 0}
                  className="btn btn-primary p-2 rounded-lg"
                  title="Send message"
                >
                  <Send size={15} />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
