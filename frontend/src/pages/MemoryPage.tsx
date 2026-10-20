import React, { useState, useEffect } from 'react';
import {
  Brain,
  Plus,
  Trash2,
  Edit2,
  Check,
  Copy,
  Folder,
  Save,
  Search,
  Sparkles,
  Download,
  Upload,
  CheckCircle,
  ToggleLeft,
  ToggleRight,
  Layers,
  FileCode,
  Tag,
  BookOpen,
  Filter,
  X,
  ExternalLink
} from 'lucide-react';
import { api } from '../services/api';
import { MemoryItem, ProjectMemoryItem } from '../types';

interface ToolPreset {
  source: string;
  name: string;
  badgeColor: string;
  bgLight: string;
  borderColor: string;
  description: string;
  defaultKey: string;
  defaultCategory: string;
  sampleContent: string;
}

const AI_TOOL_PRESETS: ToolPreset[] = [
  {
    source: 'chatgpt',
    name: 'ChatGPT Instructions',
    badgeColor: 'text-emerald-700 bg-emerald-50 border-emerald-200',
    bgLight: 'bg-emerald-50/40',
    borderColor: 'border-emerald-200',
    description: 'Custom instructions, personal preferences & response style from ChatGPT.',
    defaultKey: 'chatgpt_custom_instructions',
    defaultCategory: 'instructions',
    sampleContent: `Always provide concise, production-ready code with type annotations.\nPrefer modern standard libraries over unnecessary external packages.\nExplain the architectural reasoning before providing code diffs.`
  },
  {
    source: 'claude',
    name: 'Claude Project Memory',
    badgeColor: 'text-amber-800 bg-amber-50 border-amber-200',
    bgLight: 'bg-amber-50/40',
    borderColor: 'border-amber-200',
    description: 'Project knowledge, guidelines, artifact rules & domain depth from Claude.',
    defaultKey: 'claude_project_guidelines',
    defaultCategory: 'rules',
    sampleContent: `Adhere to Clean Architecture principles.\nSeparate domain logic, controllers, and data storage access.\nTreat documentation and type safety as first-class citizens.`
  },
  {
    source: 'cursor',
    name: 'Cursor Rules (.cursorrules)',
    badgeColor: 'text-purple-700 bg-purple-50 border-purple-200',
    bgLight: 'bg-purple-50/40',
    borderColor: 'border-purple-200',
    description: 'Editor-level coding standards, linting directives & framework conventions.',
    defaultKey: 'cursor_coding_rules',
    defaultCategory: 'rules',
    sampleContent: `Never rewrite entire files when single function changes suffice.\nUse explicit TypeScript types instead of 'any'.\nEnsure all FastAPI endpoints have request and response Pydantic models.`
  },
  {
    source: 'copilot',
    name: 'GitHub Copilot Instructions',
    badgeColor: 'text-blue-700 bg-blue-50 border-blue-200',
    bgLight: 'bg-blue-50/40',
    borderColor: 'border-blue-200',
    description: 'Repository-specific conventions from .github/copilot-instructions.md.',
    defaultKey: 'copilot_repo_instructions',
    defaultCategory: 'tech_stack',
    sampleContent: `Python 3.12+ with strict typing and pytest suites.\nReact 18 with functional components, Tailwind utility classes, and TypeScript.\nSQLite with WAL mode and transaction isolation.`
  },
  {
    source: 'gemini',
    name: 'Gemini System Rules',
    badgeColor: 'text-sky-700 bg-sky-50 border-sky-200',
    bgLight: 'bg-sky-50/40',
    borderColor: 'border-sky-200',
    description: 'Prompt templates, multimodal guidelines & research parameters from Gemini.',
    defaultKey: 'gemini_multimodal_persona',
    defaultCategory: 'persona',
    sampleContent: `Analyze visual diagrams methodically before generating text explanations.\nMaintain neutral, technically rigorous tone with step-by-step reasoning.`
  },
  {
    source: 'custom',
    name: 'Custom Domain Knowledge',
    badgeColor: 'text-indigo-700 bg-indigo-50 border-indigo-200',
    bgLight: 'bg-indigo-50/40',
    borderColor: 'border-indigo-200',
    description: 'Custom notes, API keys specifications, schema definitions & personal style.',
    defaultKey: 'personal_workflow_rules',
    defaultCategory: 'general',
    sampleContent: `Always write clear commit messages.\nWhen running scripts on Windows, verify PowerShell compatibility.`
  }
];

export const MemoryPage: React.FC = () => {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [projectContext, setProjectContext] = useState<ProjectMemoryItem | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSourceFilter, setSelectedSourceFilter] = useState<string>('all');
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<string>('all');

  // Modal / Form States
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [editingMemory, setEditingMemory] = useState<MemoryItem | null>(null);

  // Form Fields
  const [formKey, setFormKey] = useState('');
  const [formContent, setFormContent] = useState('');
  const [formSource, setFormSource] = useState('chatgpt');
  const [formCategory, setFormCategory] = useState('instructions');

  // Import Text Form
  const [importSource, setImportSource] = useState('chatgpt');
  const [importKey, setImportKey] = useState('');
  const [importRawText, setImportRawText] = useState('');

  // Status message
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [m, p] = await Promise.all([api.listMemories(), api.getProjectContext()]);
      setMemories(m);
      setProjectContext(p);
    } catch (e) {
      console.error('Error loading memories:', e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const showNotification = (msg: string) => {
    setStatusMsg(msg);
    setTimeout(() => setStatusMsg(null), 3000);
  };

  const handleOpenAddModal = (preset?: ToolPreset) => {
    if (preset) {
      setFormKey(preset.defaultKey);
      setFormContent(preset.sampleContent);
      setFormSource(preset.source);
      setFormCategory(preset.defaultCategory);
    } else {
      setFormKey('');
      setFormContent('');
      setFormSource('chatgpt');
      setFormCategory('instructions');
    }
    setEditingMemory(null);
    setIsAddModalOpen(true);
  };

  const handleOpenEditModal = (mem: MemoryItem) => {
    setEditingMemory(mem);
    setFormKey(mem.key);
    setFormContent(mem.content);
    setFormSource(mem.source_tool || 'custom');
    setFormCategory(mem.category || 'general');
    setIsAddModalOpen(true);
  };

  const handleSaveMemory = async () => {
    if (!formKey.trim() || !formContent.trim()) return;

    try {
      if (editingMemory) {
        await api.updateMemory(editingMemory.id, {
          key: formKey.trim(),
          content: formContent.trim(),
          source_tool: formSource,
          category: formCategory,
          enabled: editingMemory.enabled
        });
        showNotification('Memory updated successfully.');
      } else {
        await api.createMemory({
          key: formKey.trim(),
          content: formContent.trim(),
          source_tool: formSource,
          category: formCategory,
          enabled: true
        });
        showNotification('New memory added to local AI context.');
      }
      setIsAddModalOpen(false);
      loadData();
    } catch (e: any) {
      alert(`Error saving memory: ${e.message}`);
    }
  };

  const handleToggle = async (mem: MemoryItem) => {
    try {
      await api.toggleMemory(mem.id);
      setMemories(prev =>
        prev.map(item => (item.id === mem.id ? { ...item, enabled: !item.enabled } : item))
      );
      showNotification(mem.enabled ? 'Memory deactivated in prompts.' : 'Memory activated in prompts.');
    } catch (e: any) {
      alert(`Error toggling memory: ${e.message}`);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this memory entry?')) return;
    try {
      await api.deleteMemory(id);
      setMemories(prev => prev.filter(m => m.id !== id));
      showNotification('Memory entry removed.');
    } catch (e: any) {
      alert(`Error deleting memory: ${e.message}`);
    }
  };

  const handleCopyContent = (content: string, id: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleSaveProjectContext = async () => {
    if (!projectContext) return;
    try {
      await api.updateProjectContext(projectContext.instructions, projectContext.context_summary);
      showNotification('Project workspace rules saved.');
    } catch (e: any) {
      alert(`Error saving project context: ${e.message}`);
    }
  };

  const handleImportSubmit = async () => {
    if (!importRawText.trim()) return;
    try {
      await api.importMemories([
        {
          key: importKey.trim() || `${importSource}_imported_memory`,
          content: importRawText.trim(),
          source_tool: importSource,
          category: 'instructions'
        }
      ]);
      setIsImportModalOpen(false);
      setImportRawText('');
      setImportKey('');
      showNotification('Imported memory successfully integrated!');
      loadData();
    } catch (e: any) {
      alert(`Error importing memory: ${e.message}`);
    }
  };

  const getSourceBadge = (source?: string) => {
    const s = (source || 'custom').toLowerCase();
    const preset = AI_TOOL_PRESETS.find(p => p.source === s) || AI_TOOL_PRESETS[5];
    return (
      <span className={`badge text-2xs font-semibold ${preset.badgeColor} uppercase tracking-wider`}>
        {s}
      </span>
    );
  };

  // Filtered list
  const filteredMemories = memories.filter(m => {
    const matchesSearch =
      m.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (m.source_tool && m.source_tool.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesSource =
      selectedSourceFilter === 'all' || (m.source_tool || 'custom').toLowerCase() === selectedSourceFilter;

    const matchesCategory =
      selectedCategoryFilter === 'all' || (m.category || 'general').toLowerCase() === selectedCategoryFilter;

    return matchesSearch && matchesSource && matchesCategory;
  });

  const activeCount = memories.filter(m => m.enabled).length;

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto p-6 gap-6 bg-slate-50 font-sans">
      <div className="max-w-6xl mx-auto w-full flex flex-col gap-6">

        {/* Top Hero Banner */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-5 relative overflow-hidden">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shadow-xs shrink-0">
              <Brain size={26} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-slate-900 tracking-tight">AI Tool Memory Hub</h1>
                <span className="badge badge-success text-[10px] py-0.5 px-2 font-semibold">
                  Synced with Ollama
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
                Import and organize long-term memory, system instructions, and custom rules from{' '}
                <strong className="text-slate-700">ChatGPT, Claude, Cursor, Copilot, and Gemini</strong>.
                Active memories automatically enrich every chat conversation and coding agent task on your local machine.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            <button
              onClick={() => setIsImportModalOpen(true)}
              className="btn btn-secondary text-xs py-2 px-3.5 flex items-center gap-1.5 shadow-xs font-semibold"
            >
              <Upload size={14} />
              <span>Import AI Tool</span>
            </button>
            <button
              onClick={() => handleOpenAddModal()}
              className="btn btn-primary text-xs py-2 px-4 flex items-center gap-1.5 shadow-md font-bold"
            >
              <Plus size={15} />
              <span>Add Memory</span>
            </button>
          </div>
        </div>

        {/* Status Notification Toast */}
        {statusMsg && (
          <div className="bg-indigo-600 text-white text-xs font-semibold py-2.5 px-4 rounded-xl shadow-lg flex items-center justify-between animate-fadeIn">
            <div className="flex items-center gap-2">
              <CheckCircle size={16} />
              <span>{statusMsg}</span>
            </div>
            <button onClick={() => setStatusMsg(null)} className="text-indigo-200 hover:text-white">
              <X size={14} />
            </button>
          </div>
        )}

        {/* Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col gap-1">
            <span className="text-2xs font-bold text-slate-400 uppercase tracking-wider">Total Stored</span>
            <span className="text-2xl font-bold text-slate-900">{memories.length}</span>
            <span className="text-[11px] text-slate-500">Cross-tool memory units</span>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col gap-1">
            <span className="text-2xs font-bold text-slate-400 uppercase tracking-wider">Active in Prompts</span>
            <span className="text-2xl font-bold text-emerald-600">{activeCount}</span>
            <span className="text-[11px] text-emerald-600 font-medium">Currently injected into LLM</span>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col gap-1">
            <span className="text-2xs font-bold text-slate-400 uppercase tracking-wider">Connected Tools</span>
            <span className="text-2xl font-bold text-indigo-600">
              {new Set(memories.map(m => (m.source_tool || 'custom').toLowerCase())).size || 1}
            </span>
            <span className="text-[11px] text-slate-500">ChatGPT, Claude, Cursor, etc.</span>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col gap-1">
            <span className="text-2xs font-bold text-slate-400 uppercase tracking-wider">Workspace Context</span>
            <span className="text-2xl font-bold text-slate-800">
              {projectContext?.instructions ? 'Configured' : 'Default'}
            </span>
            <span className="text-[11px] text-slate-500">Local repository guidelines</span>
          </div>
        </div>

        {/* Quick Tool Integrations Presets */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-indigo-600" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                Quick Integration Presets from External AI Tools
              </h2>
            </div>
            <span className="text-2xs text-slate-400">Click any preset to import template</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {AI_TOOL_PRESETS.map(preset => (
              <div
                key={preset.source}
                onClick={() => handleOpenAddModal(preset)}
                className={`p-3.5 rounded-xl border border-slate-200 hover:${preset.borderColor} ${preset.bgLight} transition cursor-pointer flex flex-col justify-between gap-2.5 group shadow-2xs hover:shadow-sm`}
              >
                <div className="flex items-center justify-between">
                  <span className={`badge text-2xs font-semibold ${preset.badgeColor}`}>
                    {preset.name}
                  </span>
                  <Plus size={14} className="text-slate-400 group-hover:text-indigo-600 transition" />
                </div>
                <p className="text-xs text-slate-600 leading-snug">{preset.description}</p>
                <div className="flex items-center text-2xs font-semibold text-indigo-600 group-hover:translate-x-0.5 transition">
                  <span>Import Template</span>
                  <span className="ml-1">→</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Project Workspace Guidelines Editor */}
        {projectContext && (
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col gap-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <div className="flex items-center gap-2">
                <Folder size={16} className="text-indigo-600" />
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                  Current Workspace Rules & Tech Stack Context
                </h2>
              </div>
              <button
                onClick={handleSaveProjectContext}
                className="btn btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5 font-semibold text-indigo-600 hover:border-indigo-300"
              >
                <Save size={13} />
                <span>Save Workspace Rules</span>
              </button>
            </div>

            <p className="text-xs text-slate-500 leading-relaxed">
              These guidelines are loaded automatically for every conversation, vision query, and coding agent task inside{' '}
              <code className="bg-slate-100 px-1 py-0.5 rounded font-mono text-slate-700">{projectContext.workspace_path}</code>.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-700">Project Coding Standards & Constraints</label>
                <textarea
                  value={projectContext.instructions}
                  onChange={e => setProjectContext({ ...projectContext, instructions: e.target.value })}
                  placeholder="e.g. Always write clean Python 3.12 code, write comprehensive docstrings, and maintain unit tests..."
                  rows={4}
                  className="input-textarea text-xs resize-none font-mono"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-700">Tech Stack & Architectural Notes</label>
                <textarea
                  value={projectContext.context_summary}
                  onChange={e => setProjectContext({ ...projectContext, context_summary: e.target.value })}
                  placeholder="e.g. FastAPI backend on 127.0.0.1:8000, React 18 frontend, SQLite with WAL mode, Ollama on port 11434..."
                  rows={4}
                  className="input-textarea text-xs resize-none font-mono"
                />
              </div>
            </div>
          </div>
        )}

        {/* Stored Memory List & Filter Bar */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col gap-4">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <BookOpen size={16} className="text-indigo-600" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                All Memory Entries ({filteredMemories.length})
              </h2>
            </div>

            {/* Filter & Search Bar */}
            <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
              {/* Search */}
              <div className="relative flex-1 md:w-60">
                <Search size={13} className="absolute left-2.5 top-2.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search memories..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="input-text text-xs pl-8 py-1.5"
                />
              </div>

              {/* Source Filter */}
              <select
                value={selectedSourceFilter}
                onChange={e => setSelectedSourceFilter(e.target.value)}
                className="input-select text-xs py-1.5 px-2.5 w-auto"
              >
                <option value="all">All Tools</option>
                <option value="chatgpt">ChatGPT</option>
                <option value="claude">Claude</option>
                <option value="cursor">Cursor</option>
                <option value="copilot">Copilot</option>
                <option value="gemini">Gemini</option>
                <option value="custom">Custom</option>
              </select>

              {/* Category Filter */}
              <select
                value={selectedCategoryFilter}
                onChange={e => setSelectedCategoryFilter(e.target.value)}
                className="input-select text-xs py-1.5 px-2.5 w-auto"
              >
                <option value="all">All Categories</option>
                <option value="instructions">Instructions</option>
                <option value="rules">Rules</option>
                <option value="persona">Persona</option>
                <option value="tech_stack">Tech Stack</option>
                <option value="general">General</option>
              </select>
            </div>
          </div>

          {/* Memory Cards Grid */}
          {filteredMemories.length === 0 ? (
            <div className="p-12 text-center flex flex-col items-center justify-center gap-3">
              <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                <Brain size={24} />
              </div>
              <p className="text-xs text-slate-500 font-medium">No memory entries match your criteria.</p>
              <button
                onClick={() => handleOpenAddModal()}
                className="btn btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
              >
                <Plus size={13} />
                <span>Create New Memory</span>
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredMemories.map(mem => (
                <div
                  key={mem.id}
                  className={`border rounded-xl p-4.5 transition flex flex-col justify-between gap-3 shadow-2xs hover:shadow-sm ${
                    mem.enabled
                      ? 'bg-white border-slate-200'
                      : 'bg-slate-50/60 border-slate-200/60 opacity-70'
                  }`}
                >
                  {/* Card Header */}
                  <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
                    <div className="flex items-center gap-2 min-w-0">
                      {getSourceBadge(mem.source_tool)}
                      <span className="text-xs font-bold text-slate-900 truncate">{mem.key}</span>
                      {mem.category && (
                        <span className="badge badge-neutral text-[10px] py-0 px-1.5 text-slate-500">
                          {mem.category}
                        </span>
                      )}
                    </div>

                    {/* Quick Active Toggle */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        onClick={() => handleToggle(mem)}
                        className={`text-2xs font-bold px-2 py-0.5 rounded-full flex items-center gap-1 transition ${
                          mem.enabled
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100'
                            : 'bg-slate-100 text-slate-500 border border-slate-200 hover:bg-slate-200'
                        }`}
                        title={mem.enabled ? 'Active: Injected into AI prompts' : 'Disabled: Not injected'}
                      >
                        <span className={`status-dot ${mem.enabled ? 'status-dot-active' : 'status-dot-inactive'}`} />
                        <span>{mem.enabled ? 'Active' : 'Disabled'}</span>
                      </button>
                    </div>
                  </div>

                  {/* Content Body */}
                  <div className="bg-slate-50/80 border border-slate-100 rounded-lg p-3 max-h-36 overflow-y-auto">
                    <p className="text-xs text-slate-700 whitespace-pre-wrap leading-relaxed font-mono">
                      {mem.content}
                    </p>
                  </div>

                  {/* Card Footer / Actions */}
                  <div className="flex items-center justify-between text-2xs text-slate-400 pt-1">
                    <span>Updated {new Date(mem.updated_at).toLocaleDateString()}</span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleCopyContent(mem.content, mem.id)}
                        className="btn btn-ghost text-2xs py-1 px-2 flex items-center gap-1 text-slate-500 hover:text-slate-800"
                        title="Copy content"
                      >
                        {copiedId === mem.id ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                        <span>{copiedId === mem.id ? 'Copied' : 'Copy'}</span>
                      </button>

                      <button
                        onClick={() => handleOpenEditModal(mem)}
                        className="btn btn-ghost text-2xs py-1 px-2 flex items-center gap-1 text-slate-500 hover:text-slate-800"
                        title="Edit memory"
                      >
                        <Edit2 size={12} />
                        <span>Edit</span>
                      </button>

                      <button
                        onClick={() => handleDelete(mem.id)}
                        className="btn btn-ghost text-2xs py-1 px-2 flex items-center gap-1 text-red-500 hover:text-red-700 hover:bg-red-50"
                        title="Delete memory"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Add / Edit Memory Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Brain size={18} className="text-indigo-600" />
                <h3 className="text-sm font-bold text-slate-900">
                  {editingMemory ? 'Edit Memory Entry' : 'Add Memory from AI Tool'}
                </h3>
              </div>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X size={18} />
              </button>
            </div>

            <div className="flex flex-col gap-3.5">
              {/* Tool Source Selection */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-800">Source AI Tool</label>
                <div className="grid grid-cols-3 gap-1.5">
                  {['chatgpt', 'claude', 'cursor', 'copilot', 'gemini', 'custom'].map(src => (
                    <button
                      key={src}
                      type="button"
                      onClick={() => setFormSource(src)}
                      className={`btn text-xs py-1.5 capitalize ${
                        formSource === src ? 'btn-primary' : 'btn-secondary'
                      }`}
                    >
                      {src}
                    </button>
                  ))}
                </div>
              </div>

              {/* Category & Key */}
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-slate-800">Key / Identifier</label>
                  <input
                    type="text"
                    value={formKey}
                    onChange={e => setFormKey(e.target.value)}
                    placeholder="e.g. coding_style_rules"
                    className="input-text text-xs font-mono"
                  />
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-slate-800">Category</label>
                  <select
                    value={formCategory}
                    onChange={e => setFormCategory(e.target.value)}
                    className="input-select text-xs"
                  >
                    <option value="instructions">Instructions</option>
                    <option value="rules">Rules</option>
                    <option value="persona">Persona</option>
                    <option value="tech_stack">Tech Stack</option>
                    <option value="general">General</option>
                  </select>
                </div>
              </div>

              {/* Memory Content */}
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-800">
                  Instruction / Memory Content
                </label>
                <textarea
                  value={formContent}
                  onChange={e => setFormContent(e.target.value)}
                  rows={6}
                  placeholder="Paste rules, system prompt, or instructions from your other AI tools here..."
                  className="input-textarea text-xs font-mono resize-none leading-relaxed"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setIsAddModalOpen(false)}
                className="btn btn-secondary text-xs py-2 px-4"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveMemory}
                disabled={!formKey.trim() || !formContent.trim()}
                className="btn btn-primary text-xs py-2 px-5 font-bold"
              >
                {editingMemory ? 'Update Memory' : 'Save Memory'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import Modal */}
      {isImportModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Upload size={18} className="text-indigo-600" />
                <h3 className="text-sm font-bold text-slate-900">Import Memory from AI Tools</h3>
              </div>
              <button
                onClick={() => setIsImportModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X size={18} />
              </button>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Quickly paste your custom instructions, system prompts, or rules exported from ChatGPT, Claude, Cursor, or Copilot.
            </p>

            <div className="flex flex-col gap-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-slate-800">Source Tool</label>
                  <select
                    value={importSource}
                    onChange={e => setImportSource(e.target.value)}
                    className="input-select text-xs"
                  >
                    <option value="chatgpt">ChatGPT (Custom Instructions)</option>
                    <option value="claude">Claude (Project Knowledge)</option>
                    <option value="cursor">Cursor (.cursorrules)</option>
                    <option value="copilot">GitHub Copilot (.github)</option>
                    <option value="gemini">Gemini Prompt</option>
                    <option value="custom">Raw Document</option>
                  </select>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-slate-800">Label / Name</label>
                  <input
                    type="text"
                    value={importKey}
                    onChange={e => setImportKey(e.target.value)}
                    placeholder="e.g. chatgpt_profile"
                    className="input-text text-xs"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-800">Raw Text or Rules</label>
                <textarea
                  value={importRawText}
                  onChange={e => setImportRawText(e.target.value)}
                  rows={7}
                  placeholder="Paste text exported from your AI tool here..."
                  className="input-textarea text-xs font-mono resize-none leading-relaxed"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setIsImportModalOpen(false)}
                className="btn btn-secondary text-xs py-2 px-4"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleImportSubmit}
                disabled={!importRawText.trim()}
                className="btn btn-primary text-xs py-2 px-5 font-bold"
              >
                Import Memory
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
