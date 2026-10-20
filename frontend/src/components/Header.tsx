import React from 'react';
import {
  Sparkles,
  MessageSquare,
  Wrench,
  Image as ImageIcon,
  Eye,
  Code2,
  Workflow,
  Activity,
  Settings as SettingsIcon,
  ChevronDown,
  Plus,
  HardDrive,
  Shield,
  Bot,
  Brain
} from 'lucide-react';
import { ModelDetails } from '../types';

export type NavItem =
  | 'power'
  | 'chat'
  | 'memory'
  | 'image_lab'
  | 'coding'
  | 'vision'
  | 'tools'
  | 'automation'
  | 'diagnostics'
  | 'settings';

interface HeaderProps {
  activeTab: NavItem;
  setActiveTab: (tab: NavItem) => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  models: ModelDetails[];
  ollamaOnline: boolean;
  comfyOnline: boolean;
  workspacePath: string;
  onOpenModelManager?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  selectedModel,
  setSelectedModel,
  models,
  ollamaOnline,
  comfyOnline,
  workspacePath,
  onOpenModelManager
}) => {
  const navItems: Array<{ id: NavItem; label: string; icon: React.ReactNode; isFlagship?: boolean; badge?: string }> = [
    { id: 'power', label: 'All-in-One Studio', icon: <Sparkles size={15} />, isFlagship: true, badge: 'PRO' },
    { id: 'chat', label: 'Chat Only', icon: <MessageSquare size={15} /> },
    { id: 'memory', label: 'Memory Hub', icon: <Brain size={15} />, badge: 'AI TOOLS' },
    { id: 'image_lab', label: 'Image Lab', icon: <ImageIcon size={15} /> },
    { id: 'coding', label: 'Coding Agent', icon: <Code2 size={15} /> },
    { id: 'vision', label: 'Vision Multimodal', icon: <Eye size={15} /> },
    { id: 'tools', label: 'AI Tools', icon: <Wrench size={15} /> },
    { id: 'automation', label: 'Automation', icon: <Workflow size={15} /> },
    { id: 'diagnostics', label: 'Diagnostics', icon: <Activity size={15} /> },
    { id: 'settings', label: 'Settings', icon: <SettingsIcon size={15} /> }
  ];

  const folderName = workspacePath ? workspacePath.split('\\').pop() : 'workspace';

  return (
    <header className="bg-white/95 backdrop-blur-md border-b border-slate-200/80 select-none shrink-0 shadow-2xs z-30 sticky top-0">
      <div className="px-4 py-2.5 flex items-center justify-between gap-3">
        {/* Left: Brand Identity */}
        <div className="flex items-center gap-3 shrink-0">
          <div
            className="w-8.5 h-8.5 rounded-xl flex items-center justify-center text-white shadow-sm"
            style={{
              background: 'linear-gradient(135deg, #6366f1 0%, #4338ca 100%)'
            }}
          >
            <Sparkles size={18} />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-sm text-slate-900 tracking-tight">AI WORKBENCH</span>
              <span className="badge badge-success text-[10px] py-0.5 px-1.5 font-bold">
                Local-First
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-medium hidden sm:block">Private Workstation</p>
          </div>
        </div>

        {/* Center: Module Navigation Tabs */}
        <nav className="flex items-center gap-1 overflow-x-auto py-1 scrollbar-none max-w-[62vw]">
          {navItems.map(item => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition cursor-pointer whitespace-nowrap ${
                  isActive
                    ? 'bg-indigo-50/90 text-indigo-700 font-bold border border-indigo-200/90 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 border border-transparent'
                }`}
              >
                <span className={isActive ? 'text-indigo-600' : 'text-slate-400'}>{item.icon}</span>
                <span>{item.label}</span>
                {item.badge && (
                  <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded-md ${
                    isActive ? 'bg-indigo-200/60 text-indigo-800' : 'bg-slate-200/60 text-slate-600'
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Right: Model Selector & Live Status Pills */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Active Model Selector */}
          <div className="flex items-center gap-1.5 bg-slate-50/90 border border-slate-200/90 rounded-xl p-1 pr-1.5 shadow-2xs">
            <div className="pl-1.5 text-indigo-500">
              <Bot size={15} />
            </div>
            <div className="relative">
              <select
                value={selectedModel}
                onChange={e => setSelectedModel(e.target.value)}
                disabled={!ollamaOnline || models.length === 0}
                className="bg-transparent text-xs font-bold text-slate-800 pr-5 pl-1 py-0.5 outline-none cursor-pointer appearance-none max-w-[130px] truncate"
              >
                {models.length === 0 && <option value="">No models installed</option>}
                {models.map(m => (
                  <option key={m.name} value={m.name}>
                    {m.name} {m.is_preferred ? '★' : ''}
                  </option>
                ))}
              </select>
              <ChevronDown size={12} className="absolute right-0 top-1 text-slate-400 pointer-events-none" />
            </div>

            {onOpenModelManager && (
              <button
                onClick={onOpenModelManager}
                className="text-xs text-indigo-600 hover:text-indigo-800 font-bold px-1.5 py-0.5 rounded-lg hover:bg-indigo-50 transition flex items-center gap-0.5"
                title="Install or manage models"
              >
                <Plus size={12} />
                <span>Model</span>
              </button>
            )}
          </div>

          {/* Status Badges */}
          <div className="hidden lg:flex items-center gap-1.5 border-l border-slate-200/90 pl-2">
            {/* Ollama Status */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-2xs font-bold border shadow-2xs ${
                ollamaOnline
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200/80'
                  : 'bg-red-50 text-red-600 border-red-200/80'
              }`}
              title={ollamaOnline ? 'Ollama running on 127.0.0.1:11434' : 'Ollama is offline'}
            >
              <span className={`status-dot ${ollamaOnline ? 'status-dot-active' : 'status-dot-inactive'}`} />
              <span>Ollama</span>
            </div>

            {/* ComfyUI Status */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-2xs font-bold border shadow-2xs ${
                comfyOnline
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200/80'
                  : 'bg-amber-50 text-amber-700 border-amber-200/80'
              }`}
              title={comfyOnline ? 'ComfyUI active on 127.0.0.1:8188' : 'ComfyUI idle (auto-starts in Image Lab)'}
            >
              <span className={`status-dot ${comfyOnline ? 'status-dot-active' : 'status-dot-warning'}`} />
              <span>ComfyUI</span>
            </div>

            {/* Workspace Directory Pill */}
            <div
              className="hidden xl:flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-2xs font-mono font-medium text-slate-600 bg-slate-50 border border-slate-200/80"
              title={`Authorized Workspace: ${workspacePath}`}
            >
              <HardDrive size={12} className="text-slate-400" />
              <span>{folderName}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
