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
  Sun,
  Moon,
  ChevronDown,
  Download,
  Plus
} from 'lucide-react';
import { ModelDetails } from '../types';

export type NavItem =
  | 'power'
  | 'chat'
  | 'tools'
  | 'image_lab'
  | 'vision'
  | 'coding'
  | 'automation'
  | 'diagnostics'
  | 'settings';

interface SidebarProps {
  activeTab: NavItem;
  setActiveTab: (tab: NavItem) => void;
  theme: 'dark' | 'light';
  setTheme: (theme: 'dark' | 'light') => void;
  models: ModelDetails[];
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  ollamaOnline: boolean;
  comfyOnline: boolean;
  onOpenModelManager?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  theme,
  setTheme,
  models,
  selectedModel,
  setSelectedModel,
  ollamaOnline,
  comfyOnline,
  onOpenModelManager
}) => {
  const primaryNavItems: Array<{ id: NavItem; label: string; icon: React.ReactNode; isFlagship?: boolean }> = [
    { id: 'power', label: 'All-in-One Studio', icon: <Sparkles size={17} />, isFlagship: true },
    { id: 'chat', label: 'Chat Only', icon: <MessageSquare size={17} /> },
    { id: 'image_lab', label: 'Image Lab', icon: <ImageIcon size={17} /> },
    { id: 'coding', label: 'Coding Agent', icon: <Code2 size={17} /> },
    { id: 'vision', label: 'Vision Multimodal', icon: <Eye size={17} /> },
    { id: 'tools', label: 'AI Tools', icon: <Wrench size={17} /> },
    { id: 'automation', label: 'Automation', icon: <Workflow size={17} /> },
    { id: 'diagnostics', label: 'Diagnostics', icon: <Activity size={17} /> },
    { id: 'settings', label: 'Settings', icon: <SettingsIcon size={17} /> }
  ];

  return (
    <aside
      className="flex flex-col justify-between border-r select-none shrink-0"
      style={{
        width: '240px',
        backgroundColor: 'var(--bg-sidebar)',
        borderColor: 'var(--border-subtle)'
      }}
    >
      {/* Top Brand Header */}
      <div>
        <div className="px-4 py-3.5 border-b border-subtle flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold shadow-md"
              style={{
                background: 'linear-gradient(135deg, #6366f1 0%, #4338ca 100%)',
                boxShadow: '0 2px 10px rgba(99, 102, 241, 0.3)'
              }}
            >
              <Sparkles size={16} />
            </div>
            <div>
              <div className="text-xs font-bold tracking-tight text-main flex items-center gap-1.5">
                <span>AI WORKBENCH</span>
              </div>
              <p className="text-2xs font-mono text-dim tracking-wider">POWER WORKSTATION</p>
            </div>
          </div>

          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="p-1.5 rounded-md hover:bg-card text-muted hover:text-main transition"
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          >
            {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
          </button>
        </div>

        {/* Navigation Section */}
        <nav className="p-2 flex flex-col gap-1">
          <div className="px-2.5 py-1 text-2xs font-bold font-mono uppercase tracking-widest text-dim">
            Capabilities
          </div>
          {primaryNavItems.map(item => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition cursor-pointer text-left w-full ${
                  isActive
                    ? 'text-white font-semibold'
                    : 'text-muted hover:text-main hover:bg-card'
                }`}
                style={
                  isActive
                    ? {
                        background: item.isFlagship
                          ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.35) 0%, rgba(99, 102, 241, 0.18) 100%)'
                          : 'linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(99, 102, 241, 0.12) 100%)',
                        border: '1px solid rgba(99, 102, 241, 0.4)',
                        color: '#ffffff'
                      }
                    : { border: '1px solid transparent' }
                }
              >
                <span className={isActive ? 'text-indigo-400' : 'text-dim'}>{item.icon}</span>
                <span className="flex-1 truncate">{item.label}</span>
                {item.isFlagship && (
                  <span className="text-[9px] font-mono font-bold bg-indigo-500/30 text-indigo-300 px-1.5 py-0.5 rounded">
                    ALL-IN-1
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Service Cards */}
      <div className="p-2.5 border-t border-subtle flex flex-col gap-2">
        {/* Model Selector Card with Install Button */}
        <div
          className="p-2.5 rounded-lg border flex flex-col gap-1.5"
          style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex items-center justify-between text-2xs text-muted font-mono uppercase">
            <span className="font-semibold tracking-wider">Active Model</span>
            {onOpenModelManager && (
              <button
                onClick={onOpenModelManager}
                className="text-2xs text-accent hover:underline flex items-center gap-0.5 lowercase font-semibold"
                title="Install other LLM models"
              >
                <Plus size={10} />
                <span>install</span>
              </button>
            )}
          </div>

          <div className="relative">
            <select
              value={selectedModel}
              onChange={e => setSelectedModel(e.target.value)}
              disabled={!ollamaOnline || models.length === 0}
              className="input-select text-xs font-mono py-1 px-2 pr-6 appearance-none truncate cursor-pointer"
              style={{ backgroundColor: 'var(--bg-input)' }}
            >
              {models.length === 0 && <option value="">No models installed</option>}
              {models.map(m => (
                <option key={m.name} value={m.name}>
                  {m.name} {m.is_preferred ? '★' : ''}
                </option>
              ))}
            </select>
            <ChevronDown size={13} className="absolute right-2 top-2.5 text-dim pointer-events-none" />
          </div>
        </div>

        {/* Local Services Status Bar */}
        <div className="px-2 py-1 flex items-center justify-between text-2xs font-mono text-dim">
          <div className="flex items-center gap-1.5" title={ollamaOnline ? 'Ollama running on 127.0.0.1:11434' : 'Ollama is offline'}>
            <span className={`status-dot ${ollamaOnline ? 'status-dot-active' : 'status-dot-inactive'}`} />
            <span>Ollama</span>
          </div>
          <div className="flex items-center gap-1.5" title={comfyOnline ? 'ComfyUI running on 127.0.0.1:8188' : 'ComfyUI is offline'}>
            <span className={`status-dot ${comfyOnline ? 'status-dot-active' : 'status-dot-warning'}`} />
            <span>ComfyUI</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
