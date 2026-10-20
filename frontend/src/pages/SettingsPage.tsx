import React, { useState, useEffect } from 'react';
import {
  Settings as SettingsIcon,
  Save,
  Database,
  Download,
  RotateCcw,
  Plus,
  Trash2,
  HardDrive,
  Shield,
  FileText,
  CheckCircle,
  AlertTriangle,
  Sun,
  Moon,
  Folder,
  Brain,
  Sliders,
  Check
} from 'lucide-react';
import { api } from '../services/api';
import { SystemSettings, BackupItem, MemoryItem, ProjectMemoryItem, ModelDetails } from '../types';

interface SettingsPageProps {
  theme: 'dark' | 'light';
  setTheme: (t: 'dark' | 'light') => void;
  models: ModelDetails[];
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ theme, setTheme, models }) => {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [backups, setBackups] = useState<BackupItem[]>([]);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [projectContext, setProjectContext] = useState<ProjectMemoryItem | null>(null);

  // New Memory form
  const [newMemKey, setNewMemKey] = useState('');
  const [newMemContent, setNewMemContent] = useState('');

  // Status feedback
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [isBackingUp, setIsBackingUp] = useState(false);

  const loadAll = async () => {
    try {
      const [s, b, m, p] = await Promise.all([
        api.getSettings(),
        api.listBackups(),
        api.listMemories(),
        api.getProjectContext()
      ]);
      setSettings(s);
      setBackups(b);
      setMemories(m);
      setProjectContext(p);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleSaveSettings = async () => {
    if (!settings) return;
    try {
      const updated = await api.updateSettings(settings);
      setSettings(updated);
      setSaveStatus('System settings updated successfully.');
      setTimeout(() => setSaveStatus(null), 3500);
    } catch (e: any) {
      alert(`Error saving settings: ${e.message}`);
    }
  };

  const handleCreateBackup = async () => {
    setIsBackingUp(true);
    try {
      await api.createBackup();
      const updatedBackups = await api.listBackups();
      setBackups(updatedBackups);
      setSaveStatus('Hot database backup snapshot created.');
      setTimeout(() => setSaveStatus(null), 3500);
    } catch (e: any) {
      alert(`Backup failed: ${e.message}`);
    } finally {
      setIsBackingUp(false);
    }
  };

  const handleRestoreBackup = async (filename: string) => {
    if (!confirm(`CAUTION: Restoring '${filename}' will overwrite the active SQLite database. An emergency pre-restore snapshot will be saved automatically. Continue?`)) {
      return;
    }
    try {
      await api.restoreBackup(filename, true);
      alert('Database restored successfully! Reloading application...');
      window.location.reload();
    } catch (e: any) {
      alert(`Restoration failed: ${e.message}`);
    }
  };

  const handleCreateMemory = async () => {
    if (!newMemKey.trim() || !newMemContent.trim()) return;
    try {
      await api.createMemory({
        key: newMemKey.trim(),
        content: newMemContent.trim(),
        source_tool: 'custom',
        category: 'general',
        enabled: true
      });
      setNewMemKey('');
      setNewMemContent('');
      const updatedMems = await api.listMemories();
      setMemories(updatedMems);
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteMemory = async (id: string) => {
    try {
      await api.deleteMemory(id);
      setMemories(memories.filter(m => m.id !== id));
    } catch (e) {
      console.error(e);
    }
  };

  const handleSaveProjectContext = async () => {
    if (!projectContext) return;
    try {
      await api.updateProjectContext(projectContext.instructions, projectContext.context_summary);
      setSaveStatus('Project instructions saved.');
      setTimeout(() => setSaveStatus(null), 3500);
    } catch (e) {
      console.error(e);
    }
  };

  if (!settings) {
    return (
      <div className="flex-1 flex items-center justify-center text-xs text-muted">
        Loading configuration...
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-canvas overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto w-full flex flex-col gap-6">
        {/* Header Bar */}
        <div className="card p-5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-soft border border-accent/20 flex items-center justify-center text-accent">
              <SettingsIcon size={20} />
            </div>
            <div>
              <h2 className="text-base font-bold text-main">Workbench Settings & Data Management</h2>
              <p className="text-xs text-muted">
                Configure local service endpoints, security boundaries, persistent memories, and database snapshots.
              </p>
            </div>
          </div>

          {saveStatus && (
            <span className="badge badge-success text-2xs flex items-center gap-1.5 py-1.5 px-3">
              <CheckCircle size={13} />
              <span>{saveStatus}</span>
            </span>
          )}
        </div>

        {/* Theme Appearance Display */}
        <div className="card p-5 flex flex-col gap-3">
          <div className="flex items-center justify-between border-b pb-2.5">
            <span className="text-xs font-bold text-main uppercase tracking-wider">
              Interface Appearance
            </span>
            <span className="badge badge-success text-2xs font-semibold">Light Mode Active</span>
          </div>

          <div className="flex items-center gap-3 p-3.5 rounded-xl border border-indigo-200 bg-indigo-50/50 max-w-md">
            <div className="w-9 h-9 rounded-lg bg-white border border-indigo-100 flex items-center justify-center text-amber-500 shadow-xs">
              <Sun size={18} />
            </div>
            <div className="flex flex-col">
              <span className="text-xs font-bold text-slate-900">Professional Light Workstation</span>
              <span className="text-2xs text-slate-600">Standardized on high-legibility crisp light mode for optimal focus and comfort.</span>
            </div>
          </div>
        </div>

        {/* Service Endpoints & Core Controls */}
        <div className="card p-5 flex flex-col gap-4">
          <div className="flex items-center justify-between border-b pb-2.5">
            <div className="flex items-center gap-2">
              <Sliders size={16} className="text-accent" />
              <span className="text-xs font-bold text-main uppercase tracking-wider">
                Service Endpoints & Inference Defaults
              </span>
            </div>
            <button
              onClick={handleSaveSettings}
              className="btn btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5"
            >
              <Save size={13} />
              <span>Save Changes</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-main">Ollama Local Daemon URL</label>
              <input
                type="text"
                value={settings.ollama_base_url}
                onChange={e => setSettings({ ...settings, ollama_base_url: e.target.value })}
                className="input-text text-xs font-mono"
              />
              <span className="text-2xs text-muted">Default: http://127.0.0.1:11434</span>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-main">ComfyUI Service URL</label>
              <input
                type="text"
                value={settings.comfyui_base_url}
                onChange={e => setSettings({ ...settings, comfyui_base_url: e.target.value })}
                className="input-text text-xs font-mono"
              />
              <span className="text-2xs text-muted">Default: http://127.0.0.1:8188</span>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-main">Default Ollama Model</label>
              <select
                value={settings.default_model}
                onChange={e => setSettings({ ...settings, default_model: e.target.value })}
                className="input-select text-xs font-mono"
              >
                {models.map(m => (
                  <option key={m.name} value={m.name}>
                    {m.name}
                  </option>
                ))}
              </select>
              <span className="text-2xs text-muted">Model selected for new chats and workflows</span>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-main">Authorized Workspace Root</label>
              <div className="relative">
                <input
                  type="text"
                  value={settings.workspace_root}
                  disabled
                  className="input-text text-xs font-mono opacity-80 bg-panel cursor-not-allowed pr-24"
                />
                <span className="absolute right-2 top-2 badge badge-accent text-2xs">
                  SANDBOXED
                </span>
              </div>
              <span className="text-2xs text-muted">Strict file-system isolation boundary</span>
            </div>
          </div>

          {/* Privacy & Web Search Control */}
          <div className="p-4 bg-panel rounded-xl border flex items-center justify-between gap-4 mt-1">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-accent-soft flex items-center justify-center text-accent">
                <Shield size={16} />
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-bold text-main">External Web Search Tool</span>
                <span className="text-2xs text-muted">
                  When disabled, no external network connections are made. Local prompts and data remain 100% on-device.
                </span>
              </div>
            </div>

            <label className="relative inline-flex items-center cursor-pointer shrink-0">
              <input
                type="checkbox"
                checked={settings.enable_web_search}
                onChange={e => setSettings({ ...settings, enable_web_search: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-card-hover peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
            </label>
          </div>
        </div>

        {/* Project Memory & Custom Workspace Instructions */}
        {projectContext && (
          <div className="card p-5 flex flex-col gap-3">
            <div className="flex items-center justify-between border-b pb-2.5">
              <div className="flex items-center gap-2">
                <Folder size={16} className="text-accent" />
                <span className="text-xs font-bold text-main uppercase tracking-wider">
                  Project Context & Workspace Rules
                </span>
              </div>
              <button
                onClick={handleSaveProjectContext}
                className="btn btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
              >
                <Save size={13} />
                <span>Save Instructions</span>
              </button>
            </div>

            <p className="text-xs text-muted">
              These guidelines are loaded automatically for every conversation and coding agent task inside this workspace.
            </p>

            <textarea
              value={projectContext.instructions}
              onChange={e => setProjectContext({ ...projectContext, instructions: e.target.value })}
              placeholder="e.g. Always write clean Python 3.12 code, write comprehensive docstrings, and maintain unit tests..."
              rows={4}
              className="input-textarea text-xs resize-none font-mono"
            />
          </div>
        )}

        {/* Persistent Long-Term Memories */}
        <div className="card p-5 flex flex-col gap-4">
          <div className="flex items-center justify-between border-b pb-2.5">
            <div className="flex items-center gap-2">
              <Brain size={16} className="text-accent" />
              <span className="text-xs font-bold text-main uppercase tracking-wider">
                Transparent User Memories ({memories.length})
              </span>
            </div>
          </div>

          {/* Add Memory Form */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input
              type="text"
              placeholder="Key (e.g. preferred_language)"
              value={newMemKey}
              onChange={e => setNewMemKey(e.target.value)}
              className="input-text text-xs font-mono"
            />
            <input
              type="text"
              placeholder="Value (e.g. TypeScript and strict typing)"
              value={newMemContent}
              onChange={e => setNewMemContent(e.target.value)}
              className="input-text text-xs md:col-span-2"
            />
          </div>

          <button
            onClick={handleCreateMemory}
            disabled={!newMemKey.trim() || !newMemContent.trim()}
            className="btn btn-secondary self-start text-xs py-1.5 px-3 flex items-center gap-1.5"
          >
            <Plus size={13} />
            <span>Store Memory</span>
          </button>

          {/* Memories List */}
          <div className="flex flex-col gap-2 mt-1">
            {memories.length === 0 ? (
              <p className="text-xs text-muted italic py-2">No persistent memories saved yet.</p>
            ) : (
              memories.map(m => (
                <div key={m.id} className="p-3 rounded-xl bg-panel border flex items-center justify-between gap-3 hover:border-main transition">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="badge badge-accent font-mono text-2xs">{m.key}</span>
                    <span className="text-xs text-main truncate">{m.content}</span>
                  </div>
                  <button
                    onClick={() => handleDeleteMemory(m.id)}
                    title="Delete memory"
                    className="text-muted hover:text-danger p-1 transition shrink-0"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Database Hot Backups & Disaster Recovery */}
        <div className="card p-5 flex flex-col gap-4">
          <div className="flex items-center justify-between border-b pb-2.5">
            <div className="flex items-center gap-2">
              <Database size={16} className="text-accent" />
              <span className="text-xs font-bold text-main uppercase tracking-wider">
                SQLite Hot Backups & Snapshot Management
              </span>
            </div>
            <button
              onClick={handleCreateBackup}
              disabled={isBackingUp}
              className="btn btn-primary text-xs py-1.5 px-3.5 flex items-center gap-1.5"
            >
              <Download size={13} className={isBackingUp ? 'animate-spin' : ''} />
              <span>{isBackingUp ? 'Snapshotting...' : 'Create Snapshot'}</span>
            </button>
          </div>

          <p className="text-xs text-muted">
            Creates an atomic hot backup of the SQLite database without locking read or write transactions.
          </p>

          <div className="flex flex-col gap-2">
            {backups.length === 0 ? (
              <p className="text-xs text-muted italic py-2">No backup snapshots created yet.</p>
            ) : (
              backups.map(b => (
                <div key={b.filename} className="p-3 rounded-xl bg-panel border flex items-center justify-between gap-3 hover:border-main transition font-mono text-xs">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-card border flex items-center justify-center text-muted">
                      <HardDrive size={15} />
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="font-semibold text-main truncate">{b.filename}</span>
                      <span className="text-2xs text-muted">
                        {(b.size_bytes / 1024).toFixed(1)} KB • {new Date(b.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleRestoreBackup(b.filename)}
                    className="btn btn-danger text-2xs py-1.5 px-2.5 flex items-center gap-1"
                  >
                    <RotateCcw size={12} />
                    <span>Restore</span>
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
