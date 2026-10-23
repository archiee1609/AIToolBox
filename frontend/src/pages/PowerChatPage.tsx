import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Square,
  Bot,
  User,
  Trash2,
  Edit2,
  Copy,
  Check,
  RefreshCw,
  Image as ImageIcon,
  FileText,
  FileCode,
  Terminal,
  Paperclip,
  Sparkles,
  Sliders,
  ChevronDown,
  X,
  Plus,
  Search,
  AlertTriangle,
  Download,
  Eye,
  CheckCircle,
  Folder,
  Layers,
  Wand2,
  ZoomIn,
  Brain,
  Mic,
  MicOff
} from 'lucide-react';
import { api } from '../services/api';
import {
  Conversation,
  Message,
  ModelDetails,
  ReportGenerateRequest
} from '../types';
import { MarkdownRenderer } from '../components/MarkdownRenderer';
import { DiffViewer } from '../components/DiffViewer';
import { ModelManagerModal } from '../components/ModelManagerModal';

interface PowerChatPageProps {
  selectedModel: string;
  setSelectedModel: (m: string) => void;
  models: ModelDetails[];
  onRefreshModels: () => Promise<void>;
}

type PowerMode = 'chat' | 'image' | 'report' | 'code';

export const PowerChatPage: React.FC<PowerChatPageProps> = ({
  selectedModel,
  setSelectedModel,
  models,
  onRefreshModels
}) => {
  // Conversations State
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const toggleVoiceInput = async () => {
    if (isListening) {
      if (recognitionRef.current) recognitionRef.current.stop();
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
      setIsListening(false);
      return;
    }

    setSpeechError(null);
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => setIsListening(true);
        recognition.onresult = (event: any) => {
          let interim = '';
          let final = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) final += event.results[i][0].transcript;
            else interim += event.results[i][0].transcript;
          }
          const spoken = final || interim;
          if (spoken) {
            setInputText(prev => (prev.trim() ? prev.trim() + ' ' : '') + spoken.trim());
          }
        };
        recognition.onerror = (event: any) => {
          setIsListening(false);
          if (event.error !== 'no-speech') setSpeechError(`Voice error: ${event.error}`);
        };
        recognition.onend = () => setIsListening(false);
        recognitionRef.current = recognition;
        recognition.start();
        return;
      } catch (err: any) {
        console.warn('SpeechRecognition failed, falling back to MediaRecorder:', err);
      }
    }

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        audioChunksRef.current = [];
        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunksRef.current.push(e.data);
        };
        mediaRecorder.onstop = async () => {
          const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          stream.getTracks().forEach(t => t.stop());
          try {
            const res = await api.transcribeAudio(blob);
            if (res.text) {
              setInputText(prev => (prev.trim() ? prev.trim() + ' ' : '') + res.text);
            } else if (res.is_silent) {
              setSpeechError('No speech detected in audio.');
            }
          } catch (e: any) {
            setSpeechError('Failed to transcribe audio.');
          }
        };
        mediaRecorder.start();
        mediaRecorderRef.current = mediaRecorder;
        setIsListening(true);
      } catch (err: any) {
        setSpeechError('Microphone access denied or unavailable.');
        setIsListening(false);
      }
    } else {
      setSpeechError('Microphone not supported in this browser.');
    }
  };
  const [isSearching, setIsSearching] = useState(false);

  // Composer State
  const [inputText, setInputText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [toolStatus, setToolStatus] = useState<string | null>(null);
  const [attachedImages, setAttachedImages] = useState<string[]>([]);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Current active mode
  const [activeMode, setActiveMode] = useState<PowerMode>('chat');

  // Generation options
  const [showConfig, setShowConfig] = useState(false);
  const [temperature, setTemperature] = useState(0.7);
  const [contextLength, setContextLength] = useState(8192);
  const [systemPrompt, setSystemPrompt] = useState(
    'You are Local AI Workbench, an all-in-one expert assistant capable of general reasoning, coding, writing formal reports, and analyzing data. Be precise, helpful, and structured.'
  );

  // Modals & Panels
  const [isModelManagerOpen, setIsModelManagerOpen] = useState(false);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [reportType, setReportType] = useState<'executive_summary' | 'codebase_audit' | 'test_audit' | 'technical_research'>('executive_summary');
  const [reportTitle, setReportTitle] = useState('Executive Architecture & Capability Report');
  const [reportPrompt, setReportPrompt] = useState('');
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);

  // Image Lab quick generation modal / zoom
  const [zoomedImage, setZoomedImage] = useState<string | null>(null);
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Model Capabilities
  const currentModelDetails = models.find(m => m.name === selectedModel);
  const supportsVision = currentModelDetails?.capabilities?.image_understanding ?? false;
  const visionModel = models.find(m => m.capabilities?.image_understanding)?.name || 'gemma4:12b';

  // Active Memories Synced Info
  const [activeMemoriesCount, setActiveMemoriesCount] = useState<number>(0);
  const [activeMemorySources, setActiveMemorySources] = useState<string[]>([]);

  // Load conversations & memory metadata
  const loadConversations = async () => {
    try {
      const [convs, mems] = await Promise.all([
        api.listConversations(),
        api.listMemories().catch(() => [])
      ]);
      setConversations(convs);
      if (convs.length > 0 && !activeConvId) {
        selectConversation(convs[0].id);
      }
      const active = mems.filter(m => m.enabled);
      setActiveMemoriesCount(active.length);
      const uniqueTools = Array.from(new Set(active.map(m => m.source_tool || 'custom')));
      setActiveMemorySources(uniqueTools);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, toolStatus]);

  const selectConversation = async (id: string) => {
    setActiveConvId(id);
    try {
      const data = await api.getConversation(id);
      setMessages(data.messages);
      if (data.conversation.model && models.some(m => m.name === data.conversation.model)) {
        setSelectedModel(data.conversation.model);
      }
      setTemperature(data.conversation.temperature ?? 0.7);
      setContextLength(data.conversation.context_length ?? 8192);
      setSystemPrompt(data.conversation.system_prompt ?? '');
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateNewConversation = async () => {
    try {
      const newConv = await api.createConversation({
        title: 'New Power Workspace',
        model: selectedModel || (models[0]?.name ?? 'gemma4:12b'),
        temperature,
        context_length: contextLength,
        system_prompt: systemPrompt
      });
      setConversations([newConv, ...conversations]);
      setActiveConvId(newConv.id);
      setMessages([]);
      setInputText('');
      setAttachedImages([]);
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    try {
      await api.deleteConversation(id);
      const remaining = conversations.filter(c => c.id !== id);
      setConversations(remaining);
      if (activeConvId === id) {
        if (remaining.length > 0) {
          selectConversation(remaining[0].id);
        } else {
          setActiveConvId(null);
          setMessages([]);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Image attachment
  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    for (let i = 0; i < files.length; i++) {
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === 'string') {
          setAttachedImages(prev => [...prev, reader.result as string]);
        }
      };
      reader.readAsDataURL(files[i]);
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData.items;
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        const file = items[i].getAsFile();
        if (file) {
          const reader = new FileReader();
          reader.onload = () => {
            if (typeof reader.result === 'string') {
              setAttachedImages(prev => [...prev, reader.result as string]);
            }
          };
          reader.readAsDataURL(file);
        }
      }
    }
  };

  // Dedicated Image Generation Command
  const handleInlineImageGenerate = async (promptText: string) => {
    if (!promptText.trim()) return;
    let convId = activeConvId;
    if (!convId) {
      const newConv = await api.createConversation({
        title: `Image: ${promptText.slice(0, 25)}`,
        model: selectedModel || (models[0]?.name ?? 'gemma4:12b')
      });
      convId = newConv.id;
      setActiveConvId(convId);
      setConversations([newConv, ...conversations]);
    }

    // Add user prompt to thread
    const userMsg: Message = {
      id: Date.now().toString(),
      conversation_id: convId,
      role: 'user',
      content: `/image ${promptText}`,
      images: [],
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);
    setIsGeneratingImage(true);
    setInputText('');

    try {
      const res = await api.generateImage({
        prompt: promptText,
        width: 1024,
        height: 1024,
        seed: Math.floor(Math.random() * 1000000)
      });

      let assistantText = '';
      const imgUrl = res.image_url || (res.image_filename ? `/api/image_lab/output/${res.image_filename}` : null);
      if ((res.status === 'success' || res.status === 'completed') && imgUrl) {
        assistantText = `### 🎨 Generated Image\n\n![${promptText}](${imgUrl})\n\n**Prompt:** *${promptText}*\n**Seed:** \`${res.seed || 'Auto'}\` • **Dimensions:** 1024x1024`;
      } else {
        assistantText = `### ⚠️ Image Generation Status\n\n${res.error || 'ComfyUI service is currently unreachable on http://127.0.0.1:8188.'}\n\n> [!NOTE]\n> Ensure ComfyUI has a checkpoint (.safetensors) in \`ComfyUI/models/checkpoints\`. You can manage and download checkpoints directly in the **Image Lab** tab.`;
      }

      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        conversation_id: convId,
        role: 'assistant',
        content: assistantText,
        images: [],
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (err: any) {
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        conversation_id: convId,
        role: 'assistant',
        content: `### ⚠️ Generation Failed\n\n${err.message}`,
        images: [],
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, botMsg]);
    } finally {
      setIsGeneratingImage(false);
    }
  };

  // Dedicated Report Generation
  const handleGenerateReportModal = async () => {
    if (!reportTitle.trim()) return;
    let convId = activeConvId;
    if (!convId) {
      const newConv = await api.createConversation({
        title: `Report: ${reportTitle.slice(0, 25)}`,
        model: selectedModel || (models[0]?.name ?? 'gemma4:12b')
      });
      convId = newConv.id;
      setActiveConvId(convId);
      setConversations([newConv, ...conversations]);
    }

    setIsGeneratingReport(true);
    setReportModalOpen(false);

    // Add user request to chat
    const userMsg: Message = {
      id: Date.now().toString(),
      conversation_id: convId,
      role: 'user',
      content: `/report [${reportType}] ${reportTitle}: ${reportPrompt}`,
      images: [],
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);

    try {
      const res = await api.generateReport({
        title: reportTitle,
        report_type: reportType,
        topic_description: reportPrompt,
        model: selectedModel,
        save_to_workspace: true
      });

      const reportText = `## 📄 ${res.title}\n*Report Type: ${res.report_type} • Word Count: ${res.word_count} • Saved to: \`${res.saved_path || 'In-Memory'}\`*\n\n---\n\n${res.content}`;

      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        conversation_id: convId,
        role: 'assistant',
        content: reportText,
        images: [],
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (err: any) {
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        conversation_id: convId,
        role: 'assistant',
        content: `### ⚠️ Report Generation Failed\n\n${err.message}`,
        images: [],
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, botMsg]);
    } finally {
      setIsGeneratingReport(false);
    }
  };

  // Dedicated Coding Task Command
  const handleInlineCodeCommand = async (taskInstruction: string) => {
    if (!taskInstruction.trim()) return;
    let convId = activeConvId;
    if (!convId) {
      const newConv = await api.createConversation({
        title: `Code: ${taskInstruction.slice(0, 25)}`,
        model: selectedModel || (models[0]?.name ?? 'gemma4:12b')
      });
      convId = newConv.id;
      setActiveConvId(convId);
      setConversations([newConv, ...conversations]);
    }

    const userMsg: Message = {
      id: Date.now().toString(),
      conversation_id: convId,
      role: 'user',
      content: `/code ${taskInstruction}`,
      images: [],
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);
    setInputText('');
    setToolStatus('Inspecting workspace and formulating coding plan...');

    try {
      const task = await api.createCodingTask(taskInstruction);
      let assistantText = `### 💻 Coding Task Initialized: [${task.id}]\n\n**Plan:**\n${task.plan || 'Inspecting files...'}\n\n`;
      if (task.diff_content) {
        assistantText += `\`\`\`diff\n${task.diff_content}\n\`\`\`\n\n> Go to the **Coding Agent** tab to inspect and approve patches.`;
      } else {
        assistantText += `*Workspace files inspected. Affected files: ${task.affected_files.join(', ') || 'Scanning workspace'}*`;
      }

      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        conversation_id: convId,
        role: 'assistant',
        content: assistantText,
        images: [],
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (err: any) {
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        conversation_id: convId,
        role: 'assistant',
        content: `### ⚠️ Coding Agent Error\n\n${err.message}`,
        images: [],
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, botMsg]);
    } finally {
      setToolStatus(null);
    }
  };

  // Main Message Send Handler (dispatches /image, /report, /code, or standard chat)
  const handleSendMessage = async () => {
    const trimmed = inputText.trim();
    if ((!trimmed && attachedImages.length === 0) || isGenerating) return;

    // Intercept slash commands
    if (trimmed.startsWith('/image ')) {
      return handleInlineImageGenerate(trimmed.slice(7));
    }
    if (trimmed.startsWith('/report ')) {
      setReportTitle(trimmed.slice(8));
      setReportModalOpen(true);
      return;
    }
    if (trimmed.startsWith('/code ')) {
      return handleInlineCodeCommand(trimmed.slice(6));
    }

    let convId = activeConvId;
    if (!convId) {
      const newConv = await api.createConversation({
        title: trimmed.slice(0, 30) || 'New Conversation',
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
                // ignore
              }
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        const errorMsg: Message = {
          id: (Date.now() + 1).toString(),
          conversation_id: convId,
          role: 'assistant',
          content: `⚠️ Request failed: ${err.message}`,
          images: [],
          created_at: new Date().toISOString()
        };
        setMessages(prev => [...prev, errorMsg]);
      }
    } finally {
      setIsGenerating(false);
      setStreamingContent('');
      setToolStatus(null);
    }
  };

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsGenerating(false);
    setStreamingContent('');
    setToolStatus(null);
  };

  const handleCopyMessage = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleExportReport = (content: string, title: string = 'report') => {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.toLowerCase().replace(/[^a-z0-9]/g, '_')}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div onPaste={handlePaste} className="flex h-full overflow-hidden bg-canvas">
      {/* Conversations Left Drawer */}
      <div className="w-64 border-r border-slate-200/90 flex flex-col bg-slate-50/80 overflow-hidden shrink-0">
        <div className="p-3 border-b border-slate-200/80 flex items-center justify-between gap-2">
          <button
            onClick={handleCreateNewConversation}
            className="btn btn-primary flex-1 text-xs py-2 px-3 flex items-center justify-center gap-1.5 font-bold shadow-xs hover:shadow-subtle"
          >
            <Plus size={14} />
            <span>New Chat</span>
          </button>
        </div>

        {/* Search */}
        <div className="p-2.5 border-b border-slate-200/80">
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search chat history..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full text-xs pl-8 pr-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition"
            />
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1.5">
          {conversations.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-400">
              No conversations yet. Start a new session.
            </div>
          ) : (
            conversations
              .filter(c => c.title.toLowerCase().includes(searchQuery.toLowerCase()))
              .map(c => {
                const isSelected = activeConvId === c.id;
                return (
                  <div
                    key={c.id}
                    onClick={() => selectConversation(c.id)}
                    className={`p-2.5 rounded-xl cursor-pointer border transition text-xs flex items-center justify-between group ${
                      isSelected
                        ? 'bg-white border-indigo-200 text-indigo-900 shadow-2xs font-semibold'
                        : 'bg-transparent border-transparent hover:bg-slate-100 text-slate-700'
                    }`}
                  >
                    <div className="flex flex-col min-w-0 pr-2">
                      <span className="truncate text-xs">{c.title}</span>
                      <span className="text-[10px] font-mono text-slate-400 truncate mt-0.5">
                        {c.model}
                      </span>
                    </div>
                    <button
                      onClick={e => handleDeleteConversation(c.id, e)}
                      title="Delete conversation"
                      className="text-slate-400 hover:text-red-600 opacity-0 group-hover:opacity-100 p-1 transition shrink-0"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                );
              })
          )}
        </div>
      </div>

      {/* Main Power Studio Workspace */}
      <div className="flex-1 flex flex-col h-full bg-slate-50/50 overflow-hidden min-w-0">
        {/* Power Studio Top Action Bar */}
        <div className="h-12 border-b border-slate-200/90 bg-white px-4 flex items-center justify-between gap-3 shrink-0 shadow-2xs">
          {/* Quick Capability Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto">
            <span className="text-[11px] font-mono uppercase text-slate-400 tracking-wider mr-1">Modes:</span>
            <button
              onClick={() => setActiveMode('chat')}
              className={`text-2xs px-3 py-1.5 rounded-xl border font-semibold flex items-center gap-1.5 transition ${
                activeMode === 'chat'
                  ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                  : 'bg-slate-50 text-slate-600 border-slate-200 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Bot size={13} />
              <span>AI Chat</span>
            </button>

            <button
              onClick={() => {
                setActiveMode('image');
                setInputText('/image a dramatic cyberpunk city with neon reflections in 8k');
              }}
              className={`text-2xs px-3 py-1.5 rounded-xl border font-semibold flex items-center gap-1.5 transition ${
                activeMode === 'image'
                  ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                  : 'bg-slate-50 text-slate-600 border-slate-200 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <ImageIcon size={13} />
              <span>Image Generator</span>
            </button>

            <button
              onClick={() => {
                setActiveMode('report');
                setReportModalOpen(true);
              }}
              className={`text-2xs px-3 py-1.5 rounded-xl border font-semibold flex items-center gap-1.5 transition ${
                activeMode === 'report'
                  ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                  : 'bg-slate-50 text-slate-600 border-slate-200 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <FileText size={13} />
              <span>Report Generator</span>
            </button>

            <button
              onClick={() => {
                setActiveMode('code');
                setInputText('/code analyze workspace files and add unit tests');
              }}
              className={`text-2xs px-3 py-1.5 rounded-xl border font-semibold flex items-center gap-1.5 transition ${
                activeMode === 'code'
                  ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                  : 'bg-slate-50 text-slate-600 border-slate-200 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <FileCode size={13} />
              <span>Coding Agent</span>
            </button>
          </div>

          {/* Model Selector & Live Memory Pill */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Active Memory Indicator */}
            {activeMemoriesCount > 0 && (
              <div
                className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-2xs font-semibold bg-emerald-50 border border-emerald-200 text-emerald-700 shadow-2xs cursor-default"
                title={`Active memories loaded from: ${activeMemorySources.join(', ')}`}
              >
                <Brain size={12} className="text-emerald-600" />
                <span>{activeMemoriesCount} {activeMemoriesCount === 1 ? 'Memory' : 'Memories'} Injected</span>
              </div>
            )}

            <div className="relative">
              <select
                value={selectedModel}
                onChange={e => setSelectedModel(e.target.value)}
                className="input-select text-2xs font-mono py-1 px-2.5 pr-7 bg-white border border-slate-200 text-slate-800 rounded-lg shadow-2xs font-semibold"
              >
                {models.map(m => (
                  <option key={m.name} value={m.name}>
                    {m.name} {m.capabilities.image_understanding ? '👁️' : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Model Manager / Install Provision Button */}
            <button
              onClick={() => setIsModelManagerOpen(true)}
              className="btn btn-secondary text-2xs py-1 px-2.5 flex items-center gap-1 font-semibold text-indigo-600 hover:border-indigo-300 shadow-2xs"
              title="Install or manage local LLM models"
            >
              <Download size={12} />
              <span>+ Install</span>
            </button>

            <button
              onClick={() => setShowConfig(!showConfig)}
              className={`btn btn-ghost text-2xs p-1.5 ${showConfig ? 'text-indigo-600 bg-indigo-50' : 'text-slate-400 hover:text-slate-700'}`}
              title="Model Inference Settings"
            >
              <Sliders size={14} />
            </button>
          </div>
        </div>

        {/* Inference Options Dropdown Panel */}
        {showConfig && (
          <div className="p-4 bg-panel border-b flex flex-wrap gap-4 text-xs font-mono">
            <div className="flex flex-col gap-1 min-w-[140px]">
              <span className="text-2xs text-muted">Temperature: {temperature}</span>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={temperature}
                onChange={e => setTemperature(parseFloat(e.target.value))}
                className="w-full accent-indigo-500 cursor-pointer"
              />
            </div>

            <div className="flex flex-col gap-1 min-w-[140px]">
              <span className="text-2xs text-muted">Context: {contextLength} tokens</span>
              <select
                value={contextLength}
                onChange={e => setContextLength(parseInt(e.target.value))}
                className="input-select text-2xs bg-card"
              >
                <option value={2048}>2,048</option>
                <option value={4096}>4,096</option>
                <option value={8192}>8,192</option>
                <option value={16384}>16,384</option>
                <option value={32768}>32,768</option>
              </select>
            </div>

            <div className="flex-1 flex flex-col gap-1 min-w-[200px]">
              <span className="text-2xs text-muted">System Instructions:</span>
              <input
                type="text"
                value={systemPrompt}
                onChange={e => setSystemPrompt(e.target.value)}
                className="input-text text-2xs"
              />
            </div>
          </div>
        )}

        {/* Multimodal Warning if attaching images with non-vision model */}
        {attachedImages.length > 0 && !supportsVision && (
          <div className="px-4 py-2 bg-warning-soft border-b border-warning/20 flex items-center justify-between text-2xs text-warning">
            <div className="flex items-center gap-2">
              <AlertTriangle size={14} />
              <span>
                The active model (<span className="font-mono font-semibold">{selectedModel}</span>) lacks vision understanding.
              </span>
            </div>
            {visionModel && (
              <button
                onClick={() => setSelectedModel(visionModel)}
                className="btn btn-secondary text-2xs py-0.5 px-2 font-semibold text-warning"
              >
                Switch to {visionModel}
              </button>
            )}
          </div>
        )}

        {/* Message Thread Scroll Area */}
        <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-5">
          {messages.length === 0 && !streamingContent && (
            <div className="my-auto max-w-2xl mx-auto flex flex-col items-center justify-center text-center gap-4 py-8">
              <div className="w-16 h-16 rounded-3xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shadow-xs">
                <Sparkles size={32} />
              </div>
              <div>
                <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">Local AI Power Workbench</h2>
                <p className="text-xs text-slate-500 mt-1 max-w-md leading-relaxed">
                  Your local-first, all-in-one workstation. Chat, generate images with ComfyUI, compile formal executive reports, and run coding tasks offline.
                </p>
              </div>

              {/* Memory integration pill */}
              {activeMemoriesCount > 0 ? (
                <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold shadow-2xs">
                  <Brain size={14} className="text-emerald-600" />
                  <span>{activeMemoriesCount} External AI Memories Active ({activeMemorySources.join(', ')})</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-100 border border-slate-200 text-slate-600 text-xs font-medium">
                  <Brain size={14} className="text-slate-400" />
                  <span>Tip: Import rules from ChatGPT, Claude, or Cursor in <strong>Memory Hub</strong></span>
                </div>
              )}

              {/* Quick Prompt Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full mt-2">
                <button
                  onClick={() => setInputText('Summarize key architectural patterns of this project and suggest improvements.')}
                  className="p-4 bg-white border border-slate-200 rounded-2xl text-left hover:border-indigo-300 hover:shadow-subtle hover:-translate-y-0.5 transition-all flex flex-col gap-1.5 group shadow-2xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800 group-hover:text-indigo-600 transition">🏗️ Architecture Review</span>
                    <span className="text-[10px] text-slate-400 font-mono">/review</span>
                  </div>
                  <span className="text-[11px] text-slate-500 leading-snug">Analyze code structure, modularity & security posture</span>
                </button>

                <button
                  onClick={() => {
                    setReportTitle('Local AI Engine Evaluation Report');
                    setReportModalOpen(true);
                  }}
                  className="p-4 bg-white border border-slate-200 rounded-2xl text-left hover:border-indigo-300 hover:shadow-subtle hover:-translate-y-0.5 transition-all flex flex-col gap-1.5 group shadow-2xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800 group-hover:text-indigo-600 transition">📄 Executive Report</span>
                    <span className="text-[10px] text-slate-400 font-mono">/report</span>
                  </div>
                  <span className="text-[11px] text-slate-500 leading-snug">Generate formal Markdown reports with executive summaries</span>
                </button>

                <button
                  onClick={() => setInputText('/image A photorealistic cyberpunk city at sunset, neon reflections in rain, 8k resolution')}
                  className="p-4 bg-white border border-slate-200 rounded-2xl text-left hover:border-indigo-300 hover:shadow-subtle hover:-translate-y-0.5 transition-all flex flex-col gap-1.5 group shadow-2xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800 group-hover:text-indigo-600 transition">🎨 ComfyUI Image Creation</span>
                    <span className="text-[10px] text-slate-400 font-mono">/image</span>
                  </div>
                  <span className="text-[11px] text-slate-500 leading-snug">Generate local images directly from chat with ComfyUI</span>
                </button>

                <button
                  onClick={() => setInputText('/code review git status and run tests')}
                  className="p-4 bg-white border border-slate-200 rounded-2xl text-left hover:border-indigo-300 hover:shadow-subtle hover:-translate-y-0.5 transition-all flex flex-col gap-1.5 group shadow-2xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800 group-hover:text-indigo-600 transition">💻 Coding & Diagnostics</span>
                    <span className="text-[10px] text-slate-400 font-mono">/code</span>
                  </div>
                  <span className="text-[11px] text-slate-500 leading-snug">Inspect workspace diffs, patch files, and execute pytest</span>
                </button>
              </div>
            </div>
          )}

          {/* Render Messages */}
          {messages.map(m => {
            const isUser = m.role === 'user';
            const isReport = m.content.startsWith('## 📄');
            return (
              <div
                key={m.id}
                className={`flex gap-3 max-w-4xl w-full ${isUser ? 'ml-auto justify-end' : 'mr-auto justify-start'}`}
              >
                {!isUser && (
                  <div className="w-8 h-8 rounded-xl bg-white border border-slate-200/90 flex items-center justify-center text-indigo-600 shrink-0 mt-1 shadow-xs font-bold">
                    <Bot size={16} />
                  </div>
                )}

                <div
                  className={`flex flex-col gap-2.5 max-w-[85%] ${
                    isUser
                      ? 'bg-gradient-to-r from-indigo-600 to-indigo-700 text-white p-4 rounded-2xl rounded-br-sm shadow-sm'
                      : isReport
                      ? 'bg-white border-2 border-indigo-200 shadow-sm p-5 rounded-2xl rounded-tl-sm'
                      : 'bg-white border border-slate-200/90 shadow-xs p-4.5 rounded-2xl rounded-tl-sm'
                  }`}
                >
                  {/* Assistant Header */}
                  {!isUser && (
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2 text-[11px] text-slate-500">
                      <div className="flex items-center gap-1.5 font-mono text-slate-700 font-semibold">
                        <Sparkles size={12} className="text-indigo-600" />
                        <span>{selectedModel}</span>
                      </div>
                      <span className="font-mono text-slate-400 text-[10px]">
                        {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  )}

                  {/* Attached images */}
                  {m.images && m.images.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-2">
                      {m.images.map((img, i) => (
                        <img
                          key={i}
                          src={img}
                          alt="Attachment"
                          onClick={() => setZoomedImage(img)}
                          className="w-24 h-24 object-cover rounded-xl border border-slate-200 cursor-pointer hover:opacity-90 transition shadow-2xs"
                        />
                      ))}
                    </div>
                  )}

                  {/* Content */}
                  <div className={`text-xs leading-relaxed select-text ${isUser ? 'whitespace-pre-wrap' : 'text-slate-800'}`}>
                    {isUser ? (
                      m.content
                    ) : (
                      <MarkdownRenderer content={m.content} />
                    )}
                  </div>

                  {/* User message timestamp */}
                  {isUser && (
                    <div className="text-[10px] text-indigo-200/80 font-mono text-right mt-0.5">
                      {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  )}

                  {/* Assistant Message Actions & Report Toolbar */}
                  {!isUser && (
                    <div className="flex items-center justify-between border-t border-slate-100 pt-2.5 mt-1 text-2xs text-slate-500">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleCopyMessage(m.id, m.content)}
                          className="hover:text-slate-900 flex items-center gap-1 transition px-1.5 py-0.5 rounded hover:bg-slate-100"
                        >
                          {copiedId === m.id ? (
                            <span className="text-emerald-600 flex items-center gap-1 font-semibold">
                              <Check size={11} /> Copied
                            </span>
                          ) : (
                            <span className="flex items-center gap-1">
                              <Copy size={11} /> Copy
                            </span>
                          )}
                        </button>

                        {isReport && (
                          <button
                            onClick={() => handleExportReport(m.content, 'Report')}
                            className="hover:text-indigo-600 flex items-center gap-1 font-semibold transition ml-2 px-1.5 py-0.5 rounded hover:bg-indigo-50 text-indigo-600"
                          >
                            <Download size={11} />
                            <span>Export .md</span>
                          </button>
                        )}
                      </div>

                      <span className="text-[10px] font-mono text-slate-400">
                        Local AI
                      </span>
                    </div>
                  )}
                </div>

                {isUser && (
                  <div className="w-8 h-8 rounded-xl bg-indigo-100 border border-indigo-200/90 flex items-center justify-center text-indigo-700 shrink-0 mt-1 shadow-2xs font-bold text-xs">
                    <User size={15} />
                  </div>
                )}
              </div>
            );
          })}

          {/* Streaming Assistant Response */}
          {isGenerating && streamingContent && (
            <div className="flex gap-3 max-w-4xl w-full mr-auto justify-start">
              <div className="w-8 h-8 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-indigo-600 shrink-0 mt-1 shadow-xs">
                <Bot size={16} className="animate-spin" />
              </div>
              <div className="bg-white border border-indigo-200/90 shadow-xs p-4.5 rounded-2xl rounded-tl-sm flex flex-col gap-2 max-w-[85%] w-full">
                <div className="text-xs text-slate-800 leading-relaxed select-text">
                  <MarkdownRenderer content={streamingContent} />
                </div>
              </div>
            </div>
          )}

          {/* Active Tool Status Pill */}
          {toolStatus && (
            <div className="self-center flex items-center gap-2 bg-white border border-indigo-200 rounded-full px-4 py-1.5 text-2xs font-mono text-indigo-600 shadow-sm animate-pulse">
              <Terminal size={12} />
              <span>{toolStatus}</span>
            </div>
          )}

          {isGeneratingImage && (
            <div className="self-center flex items-center gap-2 bg-white border border-amber-200 rounded-full px-4 py-1.5 text-2xs font-mono text-amber-700 shadow-sm animate-pulse">
              <ImageIcon size={12} />
              <span>Contacting ComfyUI engine to render image...</span>
            </div>
          )}

          {isGeneratingReport && (
            <div className="self-center flex items-center gap-2 bg-white border border-indigo-200 rounded-full px-4 py-1.5 text-2xs font-mono text-indigo-600 shadow-sm animate-pulse">
              <FileText size={12} />
              <span>Synthesizing formal executive report...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Composer Card Container */}
        <div className="p-4 bg-gradient-to-t from-slate-50 via-slate-50/80 to-transparent shrink-0">
          <div className="max-w-4xl mx-auto flex flex-col gap-2">
            {/* Attached Images Preview Row */}
            {attachedImages.length > 0 && (
              <div className="flex items-center gap-2 p-2 bg-white rounded-xl border border-slate-200 shadow-2xs overflow-x-auto">
                {attachedImages.map((img, idx) => (
                  <div key={idx} className="relative group w-14 h-14 rounded-lg overflow-hidden border border-slate-200 shrink-0 shadow-2xs">
                    <img src={img} alt="Attachment" className="w-full h-full object-cover" />
                    <button
                      onClick={() => setAttachedImages(attachedImages.filter((_, i) => i !== idx))}
                      className="absolute top-1 right-1 w-4 h-4 rounded-full bg-black/80 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition"
                    >
                      <X size={10} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Voice Listening Banner */}
            {isListening && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl mb-1.5 animate-pulse">
                <span className="w-2 h-2 rounded-full bg-rose-500 inline-block animate-ping" />
                <span className="font-medium">🎙️ Listening... Speak your prompt now (click microphone to finish)</span>
              </div>
            )}
            {speechError && (
              <div className="flex items-center justify-between px-3 py-1 bg-amber-50 border border-amber-200 text-amber-700 text-xs rounded-xl mb-1.5">
                <span>⚠️ {speechError}</span>
                <button onClick={() => setSpeechError(null)} className="text-amber-500 hover:text-amber-800"><X size={12} /></button>
              </div>
            )}

            {/* Main Floating Input Box */}
            <div className="bg-white border border-slate-200 rounded-2xl shadow-floating p-3 flex flex-col gap-2 focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-100 transition-all">
              <textarea
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder={
                  activeMode === 'image'
                    ? "Type image prompt e.g. 'A sleek mechanical robot in a cyber lab'..."
                    : activeMode === 'code'
                    ? "Type coding command e.g. 'inspect test files and add assertions'..."
                    : "Ask anything, type /image <prompt>, /report <topic>, or /code <task>..."
                }
                rows={2}
                className="w-full bg-transparent border-none outline-none text-xs text-slate-800 placeholder-slate-400 resize-none p-1 leading-relaxed"
              />

              {/* Bottom Composer Bar */}
              <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                <div className="flex items-center gap-1.5">
                  {/* Attach Image button */}
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    title="Attach image for vision inspection"
                    className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
                  >
                    <Paperclip size={15} />
                  </button>

                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleImageUpload}
                    accept="image/*"
                    multiple
                    className="hidden"
                  />

                  {/* Mode quick triggers */}
                  <button
                    type="button"
                    onClick={() => {
                      setInputText('/image ');
                    }}
                    title="Generate image via ComfyUI"
                    className="px-2 py-1 rounded-lg text-slate-500 hover:text-amber-700 hover:bg-amber-50 transition text-2xs flex items-center gap-1 font-mono border border-transparent hover:border-amber-200"
                  >
                    <ImageIcon size={13} className="text-amber-600" />
                    <span>/image</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setReportModalOpen(true)}
                    title="Generate structured Markdown report"
                    className="px-2 py-1 rounded-lg text-slate-500 hover:text-indigo-700 hover:bg-indigo-50 transition text-2xs flex items-center gap-1 font-mono border border-transparent hover:border-indigo-200"
                  >
                    <FileText size={13} className="text-indigo-600" />
                    <span>/report</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setInputText('/code ')}
                    title="Run coding agent task"
                    className="px-2 py-1 rounded-lg text-slate-500 hover:text-emerald-700 hover:bg-emerald-50 transition text-2xs flex items-center gap-1 font-mono border border-transparent hover:border-emerald-200"
                  >
                    <FileCode size={13} className="text-emerald-600" />
                    <span>/code</span>
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-400 hidden sm:inline font-mono">Shift+Enter for newline</span>

                  {/* Sleek Microphone Icon beside Send Button (Matching Image 2) */}
                  <button
                    type="button"
                    onClick={toggleVoiceInput}
                    title={isListening ? "Listening... Click to stop" : "Speak prompt (Voice Dictation)"}
                    className={`w-7 h-7 rounded-full flex items-center justify-center transition-all ${
                      isListening
                        ? 'bg-rose-100 text-rose-600 animate-pulse ring-2 ring-rose-400'
                        : 'text-slate-400 hover:text-indigo-600 hover:bg-slate-100'
                    }`}
                  >
                    {isListening ? <MicOff size={15} className="text-rose-600" /> : <Mic size={15} />}
                  </button>

                  {isGenerating ? (
                    <button
                      onClick={handleStopGeneration}
                      className="btn btn-danger text-xs py-1.5 px-3 flex items-center gap-1.5 font-semibold shadow-xs"
                    >
                      <Square size={13} />
                      <span>Stop</span>
                    </button>
                  ) : (
                    <button
                      onClick={handleSendMessage}
                      disabled={!inputText.trim() && attachedImages.length === 0}
                      className="btn btn-primary text-xs py-1.5 px-3.5 flex items-center gap-1.5 font-bold shadow-xs hover:shadow-subtle"
                    >
                      <Send size={13} />
                      <span>Send</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Model Manager / Installation Modal */}
      <ModelManagerModal
        isOpen={isModelManagerOpen}
        onClose={() => setIsModelManagerOpen(false)}
        models={models}
        selectedModel={selectedModel}
        onSelectModel={setSelectedModel}
        onRefreshModels={onRefreshModels}
      />

      {/* Report Generator Wizard Modal */}
      {reportModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="card max-w-lg w-full p-6 flex flex-col gap-4 bg-card shadow-2xl border">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2">
                <FileText size={18} className="text-accent" />
                <h3 className="text-sm font-bold text-main">Executive Report Generator</h3>
              </div>
              <button onClick={() => setReportModalOpen(false)} className="text-muted hover:text-main p-1">
                <X size={16} />
              </button>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-main">Report Format</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setReportType('executive_summary')}
                  className={`p-2.5 rounded-lg border text-left text-xs transition ${
                    reportType === 'executive_summary' ? 'border-accent bg-accent-soft text-main font-semibold' : 'border-subtle bg-panel text-muted'
                  }`}
                >
                  Executive Summary
                </button>
                <button
                  type="button"
                  onClick={() => setReportType('codebase_audit')}
                  className={`p-2.5 rounded-lg border text-left text-xs transition ${
                    reportType === 'codebase_audit' ? 'border-accent bg-accent-soft text-main font-semibold' : 'border-subtle bg-panel text-muted'
                  }`}
                >
                  Codebase Health Audit
                </button>
                <button
                  type="button"
                  onClick={() => setReportType('test_audit')}
                  className={`p-2.5 rounded-lg border text-left text-xs transition ${
                    reportType === 'test_audit' ? 'border-accent bg-accent-soft text-main font-semibold' : 'border-subtle bg-panel text-muted'
                  }`}
                >
                  Test & QA Compliance
                </button>
                <button
                  type="button"
                  onClick={() => setReportType('technical_research')}
                  className={`p-2.5 rounded-lg border text-left text-xs transition ${
                    reportType === 'technical_research' ? 'border-accent bg-accent-soft text-main font-semibold' : 'border-subtle bg-panel text-muted'
                  }`}
                >
                  Technical Research Deep-Dive
                </button>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-main">Report Title</label>
              <input
                type="text"
                value={reportTitle}
                onChange={e => setReportTitle(e.target.value)}
                className="input-text text-xs"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-main">Specific Objectives or Focus Areas</label>
              <textarea
                value={reportPrompt}
                onChange={e => setReportPrompt(e.target.value)}
                placeholder="e.g. Focus on offline security, Ollama model inference speeds, and enterprise readiness..."
                rows={3}
                className="input-textarea text-xs resize-none"
              />
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t">
              <button onClick={() => setReportModalOpen(false)} className="btn btn-secondary text-xs py-2 px-3">
                Cancel
              </button>
              <button
                onClick={handleGenerateReportModal}
                disabled={isGeneratingReport || !reportTitle.trim()}
                className="btn btn-primary text-xs py-2 px-4 font-semibold"
              >
                {isGeneratingReport ? 'Generating Report...' : 'Generate Report'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Lightbox Zoom Modal */}
      {zoomedImage && (
        <div
          onClick={() => setZoomedImage(null)}
          className="fixed inset-0 bg-black/90 backdrop-blur-md flex items-center justify-center p-6 z-50 cursor-pointer"
        >
          <div className="relative max-w-5xl max-h-[90vh]" onClick={e => e.stopPropagation()}>
            <img src={zoomedImage} alt="Zoom" className="max-h-[85vh] max-w-[90vw] object-contain rounded-xl shadow-2xl border" />
            <button
              onClick={() => setZoomedImage(null)}
              className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-card border flex items-center justify-center text-main hover:text-danger shadow-lg"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
