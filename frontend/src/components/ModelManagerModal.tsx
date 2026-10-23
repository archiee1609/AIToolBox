import React, { useState, useRef, useEffect } from 'react';
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
  Plus,
  Zap,
  ShieldCheck
} from 'lucide-react';
import { api } from '../services/api';
import {
  ModelDetails,
  ModelPullProgress,
  ModelRecommendationsResponse,
  ModelRecommendation
} from '../types';

interface ModelManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  models: ModelDetails[];
  selectedModel: string;
  onSelectModel: (name: string) => void;
  onRefreshModels: () => Promise<void>;
}

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
  const [recommendationsData, setRecommendationsData] = useState<ModelRecommendationsResponse | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const abortControllerRef = useRef<AbortController | null>(null);

  // Fetch hardware-tailored recommendations when modal opens
  useEffect(() => {
    if (!isOpen) return;
    let active = true;
    api.getModelRecommendations()
      .then(data => {
        if (active) setRecommendationsData(data);
      })
      .catch(err => {
        console.warn('Failed to retrieve hardware model recommendations:', err);
      });
    return () => {
      active = false;
    };
  }, [isOpen]);

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

  const handleDeleteModel = async (name: string) => {
    if (name === selectedModel) {
      setErrorMsg('Cannot delete the currently active model. Switch to another model first.');
      return;
    }
    if (!window.confirm(`Are you sure you want to delete model "${name}"? This will free local disk storage.`)) {
      return;
    }

    try {
      await api.deleteModel(name);
      setSuccessMsg(`Model "${name}" was deleted successfully.`);
      await onRefreshModels();
    } catch (err: any) {
      setErrorMsg(err.message || `Failed to delete model "${name}".`);
    }
  };

  const spec = recommendationsData?.system_spec;
  const primary = recommendationsData?.primary_recommendation;
  const rawRecs = recommendationsData?.recommendations || [];
  const filteredRecs = activeCategory === 'all'
    ? rawRecs
    : rawRecs.filter(r => r.category === activeCategory);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in">
      <div className="bg-canvas border rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col p-6 gap-4 overflow-y-auto">
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-3 border-b">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent-soft text-accent flex items-center justify-center">
              <Bot size={18} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-main">Local LLM Models Manager</h3>
              <p className="text-2xs text-muted">
                Hardware-tailored suggestions, downloads, and disk management for Ollama.
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

        {/* Hardware-Tuned Recommendation Advisor */}
        {spec && (
          <div className="p-3.5 bg-gradient-to-r from-emerald-50/70 to-sky-50/70 border border-emerald-200/60 rounded-xl flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Sparkles size={14} className="text-emerald-600" />
                <span className="text-xs font-bold text-slate-800">Hardware-Tuned LLM Advisor</span>
              </div>
              <span className="text-2xs font-bold px-2 py-0.5 rounded-full bg-white border border-emerald-200 text-emerald-700">
                {spec.tier_badge}
              </span>
            </div>

            <div className="text-2xs text-slate-600 font-mono flex flex-wrap gap-2">
              <span><b>CPU:</b> {spec.cpu_name} ({spec.cpu_cores}T)</span>
              <span>•</span>
              <span><b>RAM:</b> {spec.ram_total_gb.toFixed(1)} GB</span>
              <span>•</span>
              <span><b>GPU:</b> {spec.gpu_name} ({spec.vram_gb.toFixed(1)} GB{spec.is_unified_memory ? ' Unified' : ''})</span>
            </div>

            {primary && (
              <div className="p-2.5 bg-white border border-emerald-300 rounded-lg flex items-center justify-between gap-3 shadow-sm">
                <div className="flex flex-col min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-2xs font-bold text-emerald-700 uppercase tracking-wider">★ Top Rig Pick:</span>
                    <span className="text-xs font-bold text-main truncate">{primary.name}</span>
                    <code className="text-2xs bg-slate-100 text-sky-700 px-1 rounded">{primary.tag}</code>
                  </div>
                  <span className="text-2xs text-slate-600 line-clamp-1 mt-0.5">{primary.reason}</span>
                  <span className="text-3xs text-muted font-mono mt-0.5">
                    Size: {primary.download_size} • Mode: {primary.execution_mode}
                  </span>
                </div>

                <div className="shrink-0">
                  {models.some(m => m.name.toLowerCase().startsWith(primary.tag.toLowerCase())) ? (
                    <span className="text-2xs font-semibold text-emerald-600 flex items-center gap-1 bg-emerald-50 px-2 py-1 rounded border border-emerald-200">
                      <CheckCircle size={11} /> Installed
                    </span>
                  ) : (
                    <button
                      type="button"
                      disabled={isPulling}
                      onClick={() => handlePull(primary.tag)}
                      className="btn btn-primary text-2xs py-1.5 px-3 flex items-center gap-1 font-semibold"
                    >
                      <Zap size={12} />
                      <span>1-Click Install</span>
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Install / Pull Input Section */}
        <div className="p-4 bg-panel rounded-xl border flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-main uppercase tracking-wider">
              Install / Pull Models
            </span>
            <span className="text-2xs font-mono text-muted">Downloads directly from Ollama library</span>
          </div>

          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="Enter model tag e.g. qwen2.5:7b, mistral, deepseek-r1:14b..."
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

          {/* Hardware-Tuned Models Grid */}
          <div className="flex flex-col gap-2 mt-1">
            <div className="flex items-center justify-between">
              <span className="text-2xs font-semibold text-muted">
                Hardware-Matched Recommendations (Click to Install):
              </span>
              <div className="flex gap-1 text-3xs font-mono">
                {[
                  { key: 'all', label: 'All' },
                  { key: 'daily_driver', label: 'Daily' },
                  { key: 'coding', label: 'Code' },
                  { key: 'reasoning', label: 'Logic' },
                  { key: 'lightweight', label: 'Fast' },
                  { key: 'vision', label: 'Vision' }
                ].map(cat => (
                  <button
                    key={cat.key}
                    type="button"
                    onClick={() => setActiveCategory(cat.key)}
                    className={`px-1.5 py-0.5 rounded transition ${
                      activeCategory === cat.key
                        ? 'bg-accent text-white font-bold'
                        : 'bg-card text-muted hover:text-main'
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {filteredRecs.slice(0, 6).map(m => {
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
                      <span className="text-xs font-bold font-mono text-main truncate">{m.name}</span>
                      <span className="text-2xs font-mono text-muted shrink-0">{m.download_size}</span>
                    </div>
                    <span className="text-2xs text-muted line-clamp-1">{m.description}</span>
                    <div className="flex items-center justify-between mt-0.5">
                      <span className="text-3xs font-mono text-sky-700 bg-sky-50 px-1 py-0.2 rounded">
                        {m.fit_badge}
                      </span>
                      <span className="text-2xs font-semibold">
                        {isInstalled ? (
                          <span className="text-success flex items-center gap-1">
                            <CheckCircle size={10} /> Ready
                          </span>
                        ) : (
                          <span className="text-accent flex items-center gap-1">
                            <Download size={10} /> Pull
                          </span>
                        )}
                      </span>
                    </div>
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
