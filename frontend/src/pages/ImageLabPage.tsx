import React, { useState, useEffect } from 'react';
import {
  Image as ImageIcon,
  Sparkles,
  AlertCircle,
  Download,
  RefreshCw,
  Sliders,
  History,
  Check,
  Maximize2,
  X,
  Play,
  Square,
  HardDrive,
  Copy,
  Layers,
  ArrowRight
} from 'lucide-react';
import { api } from '../services/api';
import { ComfyUIStatus, ImageHistoryItem } from '../types';

export const ImageLabPage: React.FC = () => {
  const [status, setStatus] = useState<ComfyUIStatus | null>(null);
  const [history, setHistory] = useState<ImageHistoryItem[]>([]);
  const [prompt, setPrompt] = useState('a futuristic cyberpunk workstation with neon lights, high detail, 8k');
  const [negativePrompt, setNegativePrompt] = useState('blurry, deformed, low quality, artifacts, distorted');
  const [width, setWidth] = useState(512);
  const [height, setHeight] = useState(512);
  const [steps, setSteps] = useState(20);
  const [cfgScale, setCfgScale] = useState(7.0);
  const [seed, setSeed] = useState(-1);
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isStartingService, setIsStartingService] = useState(false);
  const [currentResult, setCurrentResult] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [lightboxImage, setLightboxImage] = useState<string | null>(null);
  const [copiedPrompt, setCopiedPrompt] = useState(false);

  const samplePrompts = [
    'A cozy minimalist coffee shop interior, warm sunlight through glass window, 8k photography',
    'Futuristic cybernetic cat with glowing blue neon eyes, hyper-detailed mechanical parts',
    'Breathtaking fantasy castle perched high on mist-covered alpine mountains, golden hour lighting',
    'Modern glass and cedar architectural villa by a serene lake, cinematic twilight view'
  ];

  const loadStatus = async () => {
    try {
      const s = await api.getComfyStatus();
      setStatus(s);
      if (s.available_checkpoints && s.available_checkpoints.length > 0) {
        if (!selectedCheckpoint || !s.available_checkpoints.includes(selectedCheckpoint)) {
          setSelectedCheckpoint(s.available_checkpoints[0]);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadHistory = async () => {
    try {
      const h = await api.getImageHistory();
      setHistory(h);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadStatus();
    loadHistory();
    const interval = setInterval(loadStatus, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleStartComfy = async () => {
    setIsStartingService(true);
    setErrorMsg(null);
    try {
      await api.startComfyService();
      await loadStatus();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start ComfyUI service.');
    } finally {
      setIsStartingService(false);
    }
  };

  const handleDownloadModel = async (modelKey: string) => {
    setErrorMsg(null);
    try {
      await api.downloadComfyModel(modelKey);
      await loadStatus();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to trigger model download.');
    }
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setIsGenerating(true);
    setErrorMsg(null);
    setCurrentResult(null);

    try {
      const res = await api.generateImage({
        prompt,
        negative_prompt: negativePrompt,
        width,
        height,
        steps,
        cfg_scale: cfgScale,
        seed: seed === -1 ? undefined : seed,
        checkpoint: selectedCheckpoint || undefined
      });

      if (res.status === 'failed') {
        setErrorMsg(res.error || 'Image generation failed.');
      } else {
        setCurrentResult(res);
      }
      loadHistory();
    } catch (err: any) {
      setErrorMsg(err.message || 'Generation error.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopyPrompt = () => {
    if (prompt) {
      navigator.clipboard.writeText(prompt);
      setCopiedPrompt(true);
      setTimeout(() => setCopiedPrompt(false), 2000);
    }
  };

  const applyDimensions = (w: number, h: number) => {
    setWidth(w);
    setHeight(h);
  };

  const hasCheckpoints = status?.available_checkpoints && status.available_checkpoints.length > 0;
  const isDownloading = status?.download_progress?.status === 'downloading';

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto p-6 gap-6 bg-slate-50">
      <div className="max-w-5xl mx-auto w-full flex flex-col gap-6">

        {/* Top Header Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
              <ImageIcon size={22} />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 tracking-tight">Image Generation Lab</h2>
              <p className="text-xs text-slate-500">
                Native integration with local ComfyUI instance • 100% private & offline
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Service Status Badge */}
            <div
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border ${
                status?.is_reachable
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-amber-50 text-amber-700 border-amber-200'
              }`}
            >
              <span className={`status-dot ${status?.is_reachable ? 'status-dot-active' : 'status-dot-warning'}`} />
              <span>{status?.is_reachable ? 'ComfyUI Online' : 'ComfyUI Offline'}</span>
            </div>

            {/* Start / Restart Button */}
            {!status?.is_reachable && (
              <button
                onClick={handleStartComfy}
                disabled={isStartingService}
                className="btn btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5 shadow-sm"
              >
                <Play size={13} />
                <span>{isStartingService ? 'Starting...' : 'Start ComfyUI'}</span>
              </button>
            )}

            <button
              onClick={loadStatus}
              className="btn btn-secondary text-xs py-1.5 px-2.5 flex items-center gap-1"
              title="Refresh ComfyUI Status"
            >
              <RefreshCw size={13} />
            </button>
          </div>
        </div>

        {/* Model Missing or Download in Progress Alert */}
        {(!hasCheckpoints || isDownloading) && (
          <div className="bg-white border border-indigo-100 rounded-xl p-5 shadow-xs flex flex-col gap-3">
            <div className="flex items-center gap-2 text-indigo-700 font-bold text-xs uppercase tracking-wider">
              <Layers size={16} />
              <span>{isDownloading ? 'Downloading Image Generation Model' : 'No Model Checkpoint Detected'}</span>
            </div>

            {isDownloading ? (
              <div className="flex flex-col gap-2">
                <p className="text-xs text-slate-600">
                  {status?.download_progress?.message || 'Downloading model weights from HuggingFace...'}
                </p>
                <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden border border-slate-200">
                  <div
                    className="bg-indigo-600 h-full transition-all duration-300 rounded-full"
                    style={{ width: `${status?.download_progress?.percent || 5}%` }}
                  />
                </div>
                <div className="flex justify-between text-2xs text-slate-400 font-mono">
                  <span>{status?.download_progress?.filename}</span>
                  <span>{status?.download_progress?.percent || 0}%</span>
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                <p className="text-xs text-slate-600 leading-relaxed">
                  ComfyUI needs at least one model checkpoint (<code className="font-mono text-indigo-700 bg-indigo-50 px-1 py-0.5 rounded">.safetensors</code>) to generate images.
                  You can download a recommended model with 1 click, or place your own files into <code className="font-mono text-slate-800 bg-slate-100 px-1 py-0.5 rounded">ComfyUI/models/checkpoints/</code>.
                </p>
                <div className="flex flex-wrap items-center gap-2.5 pt-1">
                  <button
                    onClick={() => handleDownloadModel('sd15')}
                    className="btn btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5"
                  >
                    <Download size={13} />
                    <span>Download SD 1.5 (~4.2 GB)</span>
                  </button>
                  <button
                    onClick={() => handleDownloadModel('sdturbo')}
                    className="btn btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
                  >
                    <Download size={13} />
                    <span>Download SD-Turbo Fast (~2.4 GB)</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Main Workstation Studio */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Controls Column */}
          <div className="lg:col-span-1 bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                <Sliders size={14} className="text-indigo-600" />
                <span>Prompt & Parameters</span>
              </h3>
            </div>

            {/* Checkpoint Model Selection */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-800">Model Checkpoint</label>
              {hasCheckpoints ? (
                <select
                  value={selectedCheckpoint}
                  onChange={e => setSelectedCheckpoint(e.target.value)}
                  className="input-select text-xs font-medium"
                >
                  {status?.available_checkpoints.map(ckpt => (
                    <option key={ckpt} value={ckpt}>
                      {ckpt}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-2 font-medium">
                  No checkpoints in folder yet.
                </div>
              )}
            </div>

            {/* Prompt */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-800">Prompt</label>
                <button
                  onClick={handleCopyPrompt}
                  className="text-2xs text-slate-400 hover:text-indigo-600 flex items-center gap-1"
                >
                  {copiedPrompt ? <Check size={11} className="text-emerald-600" /> : <Copy size={11} />}
                  <span>{copiedPrompt ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
              <textarea
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
                rows={3}
                className="input-textarea text-xs resize-none"
                placeholder="Describe your scene in detail..."
              />
            </div>

            {/* Negative Prompt */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-600">Negative Prompt</label>
              <textarea
                value={negativePrompt}
                onChange={e => setNegativePrompt(e.target.value)}
                rows={2}
                className="input-textarea text-xs resize-none text-slate-600"
                placeholder="What to exclude (e.g. blurry, low quality)..."
              />
            </div>

            {/* Dimension Presets */}
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-center text-xs font-semibold text-slate-800">
                <span>Aspect Ratio</span>
                <span className="text-2xs font-mono text-slate-500">{width} × {height}</span>
              </div>
              <div className="grid grid-cols-3 gap-1.5">
                <button
                  type="button"
                  onClick={() => applyDimensions(512, 512)}
                  className={`btn text-2xs py-1.5 ${width === 512 && height === 512 ? 'btn-primary' : 'btn-secondary'}`}
                >
                  1:1 Square
                </button>
                <button
                  type="button"
                  onClick={() => applyDimensions(768, 512)}
                  className={`btn text-2xs py-1.5 ${width === 768 && height === 512 ? 'btn-primary' : 'btn-secondary'}`}
                >
                  3:2 Wide
                </button>
                <button
                  type="button"
                  onClick={() => applyDimensions(512, 768)}
                  className={`btn text-2xs py-1.5 ${width === 512 && height === 768 ? 'btn-primary' : 'btn-secondary'}`}
                >
                  2:3 Tall
                </button>
              </div>
            </div>

            {/* Steps & CFG Sliders */}
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="flex flex-col gap-1">
                <div className="flex justify-between text-2xs font-semibold text-slate-700">
                  <span>Steps</span>
                  <span className="font-mono text-indigo-600">{steps}</span>
                </div>
                <input
                  type="range"
                  min={10}
                  max={50}
                  value={steps}
                  onChange={e => setSteps(parseInt(e.target.value))}
                  className="accent-indigo-600 cursor-pointer"
                />
              </div>

              <div className="flex flex-col gap-1">
                <div className="flex justify-between text-2xs font-semibold text-slate-700">
                  <span>CFG Scale</span>
                  <span className="font-mono text-indigo-600">{cfgScale}</span>
                </div>
                <input
                  type="range"
                  min={1.0}
                  max={20.0}
                  step={0.5}
                  value={cfgScale}
                  onChange={e => setCfgScale(parseFloat(e.target.value))}
                  className="accent-indigo-600 cursor-pointer"
                />
              </div>
            </div>

            {/* Generate Action Button */}
            <button
              onClick={handleGenerate}
              disabled={isGenerating || !status?.is_reachable}
              className="btn btn-primary w-full py-2.5 mt-2 flex items-center justify-center gap-2 text-xs font-bold shadow-md"
            >
              <Sparkles size={16} />
              <span>{isGenerating ? 'Rendering in ComfyUI...' : 'Generate Image'}</span>
            </button>

            {errorMsg && (
              <div className="p-3 rounded-lg border border-red-200 bg-red-50 text-xs text-red-700 font-medium leading-relaxed">
                {errorMsg}
              </div>
            )}
          </div>

          {/* Active Canvas / Preview Column */}
          <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-700">
                Render Preview
              </h3>
              {currentResult && (
                <span className="badge badge-success text-[10px] py-0.5 px-2">Completed</span>
              )}
            </div>

            {currentResult && currentResult.image_url ? (
              <div className="flex flex-col gap-3">
                <div className="rounded-xl overflow-hidden border border-slate-200 bg-slate-900 flex items-center justify-center max-h-[440px] relative group shadow-inner">
                  <img
                    src={currentResult.image_url}
                    alt={currentResult.prompt}
                    className="object-contain max-h-[420px] w-full"
                  />
                  <button
                    onClick={() => setLightboxImage(currentResult.image_url)}
                    className="btn btn-secondary absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition p-2 text-xs shadow-md"
                    title="Zoom Fullscreen"
                  >
                    <Maximize2 size={15} />
                  </button>
                </div>

                <div className="flex items-center justify-between text-xs text-slate-600 pt-1">
                  <span className="font-mono text-2xs text-slate-500">Seed: {currentResult.seed}</span>
                  <a
                    href={currentResult.image_url}
                    download={currentResult.image_filename}
                    className="btn btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5 shadow-xs"
                  >
                    <Download size={14} />
                    <span>Download Image</span>
                  </a>
                </div>
              </div>
            ) : (
              <div className="border-2 border-dashed border-slate-200 rounded-xl p-10 flex flex-col items-center justify-center gap-4 text-center min-h-[380px] bg-slate-50/50">
                <div className="w-16 h-16 rounded-2xl bg-white border border-slate-200 flex items-center justify-center text-slate-300 shadow-xs">
                  <ImageIcon size={32} />
                </div>
                <div className="max-w-sm flex flex-col gap-1">
                  <p className="text-xs font-bold text-slate-700">
                    {isGenerating
                      ? 'Submitting prompt graph to ComfyUI...'
                      : 'Your generated image will appear here'}
                  </p>
                  <p className="text-2xs text-slate-400">
                    Try choosing an example prompt below or typing your own custom scene.
                  </p>
                </div>

                {/* Example Prompts Chips */}
                {!isGenerating && (
                  <div className="flex flex-col gap-1.5 w-full max-w-md pt-2">
                    <span className="text-2xs font-semibold uppercase text-slate-400 text-left">
                      Inspiration Prompts:
                    </span>
                    <div className="flex flex-col gap-1.5 text-left">
                      {samplePrompts.slice(0, 3).map((sample, idx) => (
                        <button
                          key={idx}
                          onClick={() => setPrompt(sample)}
                          className="text-left text-2xs text-slate-600 hover:text-indigo-600 hover:bg-white p-2 rounded-lg border border-slate-200 transition bg-slate-50 flex items-center justify-between group"
                        >
                          <span className="truncate">{sample}</span>
                          <ArrowRight size={12} className="opacity-0 group-hover:opacity-100 text-indigo-600 shrink-0" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Saved Gallery */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
              <History size={14} className="text-indigo-600" />
              <span>Image Gallery ({history.length})</span>
            </h3>
            <button
              onClick={loadHistory}
              className="btn btn-ghost text-xs py-1 px-2.5 flex items-center gap-1 text-slate-500 hover:text-slate-800"
            >
              <RefreshCw size={13} />
              <span>Refresh Gallery</span>
            </button>
          </div>

          {history.length === 0 ? (
            <p className="text-xs text-slate-400 italic py-4 text-center">No images saved in your gallery yet.</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {history.map(item => (
                <div
                  key={item.id}
                  className="bg-white border border-slate-200 hover:border-indigo-300 rounded-xl p-2.5 flex flex-col gap-2 group cursor-pointer shadow-xs hover:shadow-md transition"
                  onClick={() => item.image_url && setLightboxImage(item.image_url)}
                >
                  {item.image_url ? (
                    <img
                      src={item.image_url}
                      alt={item.prompt}
                      className="h-36 w-full object-cover rounded-lg border border-slate-100 group-hover:scale-102 transition"
                    />
                  ) : (
                    <div className="h-36 bg-slate-100 rounded-lg flex items-center justify-center text-2xs text-red-600 p-2 text-center font-medium">
                      Generation Failed
                    </div>
                  )}
                  <p className="text-xs text-slate-800 truncate font-semibold">{item.prompt}</p>
                  <span className="text-2xs text-slate-400 font-mono">
                    {new Date(item.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Lightbox Zoom Modal */}
      {lightboxImage && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-6 backdrop-blur-sm"
          onClick={() => setLightboxImage(null)}
        >
          <div className="relative max-w-4xl max-h-full" onClick={e => e.stopPropagation()}>
            <button
              onClick={() => setLightboxImage(null)}
              className="absolute -top-10 right-0 text-white hover:text-red-400 p-1"
            >
              <X size={26} />
            </button>
            <img src={lightboxImage} alt="Fullscreen preview" className="rounded-xl shadow-2xl max-h-[85vh] object-contain" />
          </div>
        </div>
      )}
    </div>
  );
};
