import React, { useState, useRef } from 'react';
import {
  X,
  Download,
  Trash2,
  Bot,
  HardDrive,
  Cpu,
  Layers,
  Sparkles,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Search,
  Plus
} from 'lucide-react';
import { api } from '../services/api';
import { ModelDetails, ModelPullProgress } from '../types';

interface ModelManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  models: ModelDetails[];
  selectedModel: string;
  onSelectModel: (name: string) => void;
  onRefreshModels: () => Promise<void>;
}

const POPULAR_MODELS = [
  { tag: 'llama3.2', size: '2.0 GB', desc: 'Meta 3B lightweight, fast general assistant' },
  { tag: 'mistral', size: '4.1 GB', desc: '7B balanced high-precision reasoning and coding' },
  { tag: 'deepseek-r1:14b', size: '9.0 GB', desc: '14B state-of-the-art chain-of-thought reasoning' },
  { tag: 'qwen2.5-coder', size: '4.7 GB', desc: '7B specialized coding and software development' },
  { tag: 'phi4', size: '9.1 GB', desc: '14B high-performance compact synthetic reasoning' },
  { tag: 'llava', size: '4.7 GB', desc: '7B vision & multimodal visual understanding' }
];

export const ModelManagerModal: React.FC<ModelManagerModalProps> = ({
  isOpen,
  onClose,
  models,
  selectedModel,
  onSelectModel,
  onRefreshModels
}) => {
  const [modelToPull, setModelToPull] = useState('');
  const [isPulling, setIsPulling] = useState(false);
  const [pullProgress, setPullProgress] = useState<ModelPullProgress | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  if (!isOpen) return null;

  const handlePull = async (targetTag?: string) => {
    const tag = (targetTag || modelToPull).trim();
    if (!tag || isPulling) return;

    setIsPulling(true);
    setPullProgress({ status: 'Starting download...' });
    setErrorMsg(null);
    setSuccessMsg(null);

    abortControllerRef.current = new AbortController();

    try {
      await api.pullModel(
        tag,
        (progress) => {
          setPullProgress(progress);
          if (progress.error) {
            setErrorMsg(progress.error);
          }
        },
        abortControllerRef.current.signal
      );

      setSuccessMsg(`Model '${tag}' installed successfully!`);
      setModelToPull('');
      await onRefreshModels();
      onSelectModel(tag);
    } catch (err: any) {
      if (err.name === 'AbortError') {
        setErrorMsg('Model download was cancelled.');
      } else {
        setErrorMsg(err.message || 'Failed to install model.');
      }
    } finally {
      setIsPulling(false);
      setPullProgress(null);
    }
  };

  const handleCancelPull = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsPulling(false);
    setPullProgress(null);
  };

  const handleDeleteModel = async (modelName: string) => {
    if (modelName === selectedModel) {
      alert(`Cannot delete '${modelName}' because it is currently selected. Switch to another model first.`);
      return;
    }

    if (!confirm(`Are you sure you want to delete model '${modelName}' from your local disk? This will free up storage.`)) {
      return;
    }

    try {
      await api.deleteModel(modelName);
      await onRefreshModels();
      setSuccessMsg(`Model '${modelName}' removed from local storage.`);
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err: any) {
      setErrorMsg(`Failed to delete model: ${err.message}`);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="card max-w-2xl w-full p-6 flex flex-col gap-5 bg-card shadow-2xl border max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent-soft flex items-center justify-center text-accent">
              <Bot size={18} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-main">Local LLM Models Manager</h3>
              <p className="text-2xs text-muted">
                Install, update, or remove models from your local Ollama runtime.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-muted hover:text-main p-1 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Status Alerts */}
        {errorMsg && (
          <div className="p-3 bg-danger-soft border border-danger/30 rounded-lg text-xs text-danger flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle size={15} />
              <span>{errorMsg}</span>
            </div>
            <button onClick={() => setErrorMsg(null)} className="text-danger hover:underline text-2xs">
              Dismiss
            </button>
          </div>
        )}

        {successMsg && (
          <div className="p-3 bg-success-soft border border-success/30 rounded-lg text-xs text-success flex items-center gap-2">
            <CheckCircle size={15} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Install New Model Section */}
        <div className="p-4 bg-panel rounded-xl border flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-main uppercase tracking-wider">
              Install / Pull Other LLM Models
            </span>
            <span className="text-2xs font-mono text-muted">Downloads directly from ollama.com</span>
          </div>

          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="Enter model tag e.g. llama3.2, mistral, deepseek-r1:14b..."
                value={modelToPull}
                disabled={isPulling}
                onChange={e => setModelToPull(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handlePull()}
                className="input-text text-xs font-mono"
              />
            </div>
            {isPulling ? (
              <button
                onClick={handleCancelPull}
                className="btn btn-danger text-xs py-2 px-4"
              >
                Cancel
              </button>
            ) : (
              <button
                onClick={() => handlePull()}
                disabled={!modelToPull.trim()}
                className="btn btn-primary text-xs py-2 px-4 flex items-center gap-1.5 font-semibold"
              >
                <Download size={14} />
                <span>Pull Model</span>
              </button>
            )}
          </div>

          {/* Active Pull Progress Bar */}
          {isPulling && pullProgress && (
            <div className="p-3 bg-canvas rounded-lg border flex flex-col gap-2">
              <div className="flex items-center justify-between text-2xs font-mono">
                <span className="text-main font-semibold truncate max-w-[280px]">
                  {pullProgress.status}
                </span>
                <span className="text-accent font-bold">
                  {pullProgress.percent !== undefined ? `${pullProgress.percent}%` : 'Connecting...'}
                </span>
              </div>
              <div className="w-full bg-card-hover h-2 rounded-full overflow-hidden border border-subtle">
                <div
                  className="bg-accent h-full transition-all duration-200"
                  style={{ width: `${pullProgress.percent || 0}%` }}
                />
              </div>
              {pullProgress.total && pullProgress.completed && (
                <div className="flex justify-between text-2xs font-mono text-muted">
                  <span>{(pullProgress.completed / (1024 * 1024)).toFixed(1)} MB</span>
                  <span>{(pullProgress.total / (1024 * 1024)).toFixed(1)} MB</span>
                </div>
              )}
            </div>
          )}

          {/* Popular Curated Recommendations */}
          <div className="flex flex-col gap-1.5 mt-1">
            <span className="text-2xs font-semibold text-muted">Popular Local Models (1-Click Install):</span>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {POPULAR_MODELS.map(m => {
                const isInstalled = models.some(existing => existing.name.toLowerCase().startsWith(m.tag.toLowerCase()));
                return (
                  <button
                    key={m.tag}
                    type="button"
                    disabled={isInstalled || isPulling}
                    onClick={() => handlePull(m.tag)}
                    className={`p-2.5 rounded-lg border text-left flex flex-col gap-1 transition ${
                      isInstalled
                        ? 'opacity-60 bg-canvas border-subtle cursor-default'
                        : 'bg-card hover:border-accent hover:bg-card-hover border-subtle'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold font-mono text-main">{m.tag}</span>
                      <span className="text-2xs font-mono text-muted">{m.size}</span>
                    </div>
                    <span className="text-2xs text-muted line-clamp-1">{m.desc}</span>
                    <span className="text-2xs font-semibold mt-0.5">
                      {isInstalled ? (
                        <span className="text-success flex items-center gap-1">
                          <CheckCircle size={10} /> Installed
                        </span>
                      ) : (
                        <span className="text-accent flex items-center gap-1">
                          <Download size={10} /> Install
                        </span>
                      )}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Installed Models List */}
        <div className="flex flex-col gap-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-main uppercase tracking-wider">
              Locally Installed Models ({models.length})
            </span>
            <button
              onClick={onRefreshModels}
              className="text-2xs text-muted hover:text-main flex items-center gap-1 font-mono transition"
            >
              <RefreshCw size={11} />
              <span>Refresh</span>
            </button>
          </div>

          <div className="flex flex-col gap-2">
            {models.map(m => {
              const isSelected = m.name === selectedModel;
              const sizeMB = m.size_bytes ? (m.size_bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB' : 'Local';
              return (
                <div
                  key={m.name}
                  className={`p-3 rounded-xl border flex items-center justify-between gap-3 transition ${
                    isSelected ? 'bg-panel border-accent' : 'bg-canvas border-subtle hover:border-main'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${
                      isSelected ? 'bg-accent text-white border-accent' : 'bg-card text-muted border-subtle'
                    }`}>
                      <Bot size={16} />
                    </div>
                    <div className="flex flex-col min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold font-mono text-main truncate">{m.name}</span>
                        {isSelected && <span className="badge badge-accent text-2xs">ACTIVE</span>}
                      </div>
                      <span className="text-2xs font-mono text-muted">
                        {sizeMB} • {m.family || 'Model'} • {m.quantization_level || 'Default'}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {!isSelected && (
                      <button
                        onClick={() => {
                          onSelectModel(m.name);
                          onClose();
                        }}
                        className="btn btn-secondary text-2xs py-1 px-2.5"
                      >
                        Select
                      </button>
                    )}
                    <button
                      onClick={() => handleDeleteModel(m.name)}
                      disabled={isSelected}
                      title={isSelected ? 'Switch model before deleting' : 'Delete model'}
                      className={`p-1.5 rounded text-muted hover:text-danger transition ${
                        isSelected ? 'opacity-30 cursor-not-allowed' : 'hover:bg-danger-soft'
                      }`}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end pt-3 border-t">
          <button
            onClick={onClose}
            className="btn btn-secondary text-xs py-2 px-4"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
